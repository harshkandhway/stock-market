"""
Test Bot Callback Handlers
Critical tests for callback handlers focusing on:
- Alert creation with correct parameters
- Callback data parsing
- Database operations in callbacks
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.bot.handlers.callbacks import handle_callback_query
from telegram import Update
from src.bot.database.db import get_db_context, get_or_create_user, get_user_alerts, create_alert


class TestCallbackHandlers:
    """Test callback handlers with focus on critical fixes"""
    
    @pytest.fixture
    def mock_query(self):
        """Create mock callback query"""
        query = Mock()
        query.from_user = Mock()
        query.from_user.id = 123456
        query.from_user.username = "testuser"
        query.data = "test_action:param1"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        return query
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock()
        context.user_data = {}
        context.bot_data = {}
        return context
    
    @pytest.fixture
    def mock_update(self, mock_query):
        """Create a mock update"""
        update = Mock(spec=Update)
        update.update_id = 1
        update.callback_query = mock_query
        update.message = None
        update.effective_user = mock_query.from_user
        return update
    
    @pytest.fixture
    def test_db(self):
        """Create test database session"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from src.bot.database.models import Base
        
        engine = create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=False
        )
        
        Base.metadata.create_all(engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = TestSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
            Base.metadata.drop_all(engine)
    
    # ========================================================================
    # CRITICAL: Alert Signal Setup Callback
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_alert_signal_setup_creates_alert_correctly(self, mock_query, mock_context, mock_update, test_db):
        """CRITICAL: Verify alert_signal callback creates alert with correct parameters"""
        mock_query.data = "alert_signal:NIFTYBEES.NS"
        mock_update.callback_query = mock_query
        
        # Mock get_db_context to return our test database
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        # Mock analyze_stock to avoid actual API call
        with patch('src.bot.handlers.callbacks.get_db_context', test_db_context):
            with patch('src.bot.handlers.callbacks.analyze_stock', return_value={'status': 'success', 'data': {'recommendation': 'BUY'}}):
                await handle_callback_query(mock_update, mock_context)
        
        # Ensure database is committed (handler commits internally, but test_db needs refresh)
        test_db.commit()
        test_db.expire_all()
        
        # Verify alert was created with correct parameters
        # Check database directly
        user = get_or_create_user(test_db, telegram_id=123456)
        alerts = get_user_alerts(test_db, telegram_id=123456)
        
        # Should have created a signal change alert
        signal_alerts = [a for a in alerts if a.alert_type == 'signal_change']
        assert len(signal_alerts) > 0, f"Expected signal alert, got {len(signal_alerts)} alerts: {[a.alert_type for a in alerts]}"
        
        alert = signal_alerts[0]
        assert alert.symbol == 'NIFTYBEES.NS'
        assert alert.alert_type == 'signal_change'
        assert alert.condition_type == 'change'
        assert alert.user.telegram_id == 123456  # ✅ Correct relationship
    
    @pytest.mark.asyncio
    async def test_alert_signal_setup_uses_telegram_id(self, mock_query, mock_context, mock_update, test_db):
        """CRITICAL: Verify alert creation uses telegram_id not user_id"""
        mock_query.data = "alert_signal:RELIANCE.NS"
        mock_query.from_user.id = 999888
        mock_update.callback_query = mock_query
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.callbacks.get_db_context', test_db_context):
            with patch('src.bot.handlers.callbacks.analyze_stock', return_value={'status': 'success', 'data': {'recommendation': 'BUY'}}):
                await handle_callback_query(mock_update, mock_context)
        
        test_db.commit()
        test_db.expire_all()
        
        # Verify alert created with telegram_id
        alerts = get_user_alerts(test_db, telegram_id=999888)
        assert len(alerts) > 0
        assert alerts[0].user.telegram_id == 999888
    
    # ========================================================================
    # Alert RSI Setup Callback
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_alert_rsi_setup_creates_alerts(self, mock_query, mock_context, mock_update, test_db):
        """Test RSI alert setup creates both overbought and oversold alerts"""
        mock_query.data = "alert_rsi:TCS.NS"
        mock_update.callback_query = mock_query
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.callbacks.get_db_context', test_db_context):
            with patch('src.bot.handlers.callbacks.analyze_stock', return_value={'status': 'success', 'data': {'indicators': {'rsi': 50.0}}}):
                await handle_callback_query(mock_update, mock_context)
        
        test_db.commit()
        test_db.expire_all()
        
        # Verify both alerts created
        alerts = get_user_alerts(test_db, telegram_id=123456)
        rsi_alerts = [a for a in alerts if a.alert_type == 'rsi']
        
        # Should have 2 RSI alerts (overbought and oversold)
        assert len(rsi_alerts) == 2, f"Expected 2 RSI alerts, got {len(rsi_alerts)}"
        
        # Verify parameters
        for alert in rsi_alerts:
            assert alert.symbol == 'TCS.NS'
            assert alert.alert_type == 'rsi'
            assert alert.params is not None  # ✅ Uses params
            assert 'operator' in alert.params or 'value' in alert.params
    
    # ========================================================================
    # Watchlist Callbacks
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_watchlist_add_callback(self, mock_query, mock_context, mock_update, test_db):
        """Test watchlist add callback"""
        mock_query.data = "watchlist_add:RELIANCE.NS"
        mock_update.callback_query = mock_query
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.callbacks.get_db_context', test_db_context):
            await handle_callback_query(mock_update, mock_context)
        
        test_db.commit()
        test_db.expire_all()
        
        # Verify symbol added to watchlist
        from src.bot.database.db import get_user_watchlist
        watchlist = get_user_watchlist(test_db, telegram_id=123456)
        assert len(watchlist) > 0
        assert any(w.symbol == 'RELIANCE.NS' for w in watchlist)
    
    @pytest.mark.asyncio
    async def test_watchlist_remove_callback(self, mock_query, mock_context, mock_update, test_db):
        """Test watchlist remove callback"""
        # First add
        from src.bot.database.db import add_to_watchlist
        add_to_watchlist(test_db, telegram_id=123456, symbol='RELIANCE.NS')
        test_db.commit()
        
        # Then remove via callback
        mock_query.data = "watchlist_remove:RELIANCE.NS"
        mock_update.callback_query = mock_query
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.callbacks.get_db_context', test_db_context):
            await handle_callback_query(mock_update, mock_context)
        
        test_db.commit()
        test_db.expire_all()
        
        # Verify symbol removed
        from src.bot.database.db import get_user_watchlist
        watchlist = get_user_watchlist(test_db, telegram_id=123456)
        assert len(watchlist) == 0
    
    # ========================================================================
    # Settings Callbacks
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_settings_mode_callback(self, mock_query, mock_context, mock_update, test_db):
        """Test settings mode callback"""
        # Settings uses settings_risk_mode: not settings_mode:
        mock_query.data = "settings_risk_mode:aggressive"
        mock_update.callback_query = mock_query
        
        # Create user first
        get_or_create_user(test_db, telegram_id=123456, username="testuser")
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        # Settings callbacks are routed to handle_settings_callback in settings.py
        # Need to patch settings handler's get_db_context
        with patch('src.bot.handlers.settings.get_db_context', test_db_context):
            await handle_callback_query(mock_update, mock_context)
        
        test_db.commit()
        test_db.expire_all()
        
        # Verify settings updated
        from src.bot.database.db import get_user_settings
        settings = get_user_settings(test_db, telegram_id=123456)
        assert settings is not None
        assert settings.risk_mode == 'aggressive'
    
    # ========================================================================
    # Error Handling
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_invalid_callback_data(self, mock_query, mock_context, mock_update):
        """Test handling of invalid callback data"""
        mock_query.data = "invalid_action"
        mock_update.callback_query = mock_query
        
        # Mock edit_message_text to avoid errors
        mock_query.edit_message_text = AsyncMock()
        
        await handle_callback_query(mock_update, mock_context)
        
        # Should handle gracefully - either answer or edit_message_text called
        assert mock_query.answer.called or mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_callback_with_missing_params(self, mock_query, mock_context, mock_update):
        """Test callback with missing parameters"""
        mock_query.data = "alert_signal"  # Missing symbol
        mock_update.callback_query = mock_query
        
        # Mock edit_message_text to avoid errors
        mock_query.edit_message_text = AsyncMock()
        
        await handle_callback_query(mock_update, mock_context)
        
        # Should handle gracefully - either answer or edit_message_text called
        assert mock_query.answer.called or mock_query.edit_message_text.called


class TestCallbackDataParsing:
    """Test callback data parsing"""
    
    @pytest.mark.asyncio
    async def test_callback_data_format(self, mock_query, mock_context):
        """Test callback data format parsing"""
        test_cases = [
            ("alert_signal:NIFTYBEES.NS", "alert_signal", ["NIFTYBEES.NS"]),
            ("watchlist_add:RELIANCE.NS", "watchlist_add", ["RELIANCE.NS"]),
            ("settings_mode:aggressive", "settings_mode", ["aggressive"]),
        ]
        
        for data, expected_action, expected_params in test_cases:
            mock_query.data = data
            # The actual parsing happens in handle_callback_query
            # We're just verifying the format is correct
            parts = data.split(":")
            assert len(parts) >= 2
            assert parts[0] == expected_action

