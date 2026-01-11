"""
Test Bot Feature Handlers
Tests for Portfolio, Position Sizing, Refresh Analysis, Schedule Reports, 
Compare Stocks, Settings (Horizon, Risk, Capital, Report Style)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes

from src.bot.handlers.portfolio import portfolio_command, show_portfolio
from src.bot.handlers.compare import compare_command
from src.bot.handlers.schedule import schedule_command, show_scheduled_reports
from src.bot.handlers.settings import (
    settings_command,
    setcapital_command,
    sethorizon_command,
    setmode_command,
    handle_settings_callback
)
from src.bot.handlers.callbacks import (
    handle_position_sizing,
    handle_analyze_refresh
)
from src.bot.database.db import (
    get_or_create_user,
    get_user_settings,
    update_user_settings
)


class TestPortfolioFeature:
    """Test Portfolio functionality"""
    
    @pytest.fixture
    def mock_update(self):
        """Create mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.effective_user.username = "testuser"
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        update.message.text = "/portfolio"
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
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
    
    @pytest.mark.asyncio
    async def test_portfolio_command_empty(self, mock_update, mock_context, test_db):
        """Test /portfolio command with empty portfolio"""
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.portfolio.get_db_context', test_db_context):
            with patch('src.bot.services.portfolio_service.calculate_portfolio_summary', return_value={'total_positions': 0}):
                await portfolio_command(mock_update, mock_context)
        
        # Verify message sent
        mock_update.message.reply_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_portfolio_command_with_positions(self, mock_update, mock_context, test_db):
        """Test /portfolio command with positions"""
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        mock_summary = {
            'total_positions': 2,
            'total_value': 50000.0,
            'total_cost': 45000.0,
            'total_pnl': 5000.0,
            'total_pnl_percent': 11.11
        }
        
        with patch('src.bot.handlers.portfolio.get_db_context', test_db_context):
            with patch('src.bot.services.portfolio_service.calculate_portfolio_summary', return_value=mock_summary):
                await portfolio_command(mock_update, mock_context)
        
        # Verify message sent
        mock_update.message.reply_text.assert_called()


class TestPositionSizingFeature:
    """Test Position Sizing functionality"""
    
    @pytest.fixture
    def mock_query(self):
        """Create mock callback query"""
        query = Mock(spec=CallbackQuery)
        query.from_user = Mock(spec=User)
        query.from_user.id = 123456
        query.from_user.username = "testuser"
        query.data = "position_sizing:RELIANCE.NS"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        return query
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
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
    
    @pytest.mark.asyncio
    async def test_position_sizing_callback(self, mock_query, mock_context, test_db):
        """Test position sizing callback"""
        # Create user with settings
        user = get_or_create_user(test_db, telegram_id=123456, username="testuser")
        settings = get_user_settings(test_db, telegram_id=123456)
        settings.default_capital = 100000.0
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        mock_analysis = {
            'status': 'success',
            'data': {
                'current_price': 2500.0,
                'target_price': 2800.0,
                'stop_loss': 2400.0,
                'recommendation': 'BUY'
            }
        }
        
        with patch('src.bot.handlers.callbacks.get_db_context', test_db_context):
            with patch('src.bot.handlers.analyze.analyze_stock_with_settings', return_value=mock_analysis):
                await handle_position_sizing(mock_query, mock_context, ["RELIANCE.NS"])
        
        # Verify message sent
        mock_query.edit_message_text.assert_called()
        call_args = mock_query.edit_message_text.call_args
        message = call_args[0][0] if call_args[0] else call_args.kwargs.get('text', '')
        assert len(message) > 0


class TestRefreshAnalysisFeature:
    """Test Refresh Analysis functionality"""
    
    @pytest.fixture
    def mock_query(self):
        """Create mock callback query"""
        query = Mock(spec=CallbackQuery)
        query.from_user = Mock(spec=User)
        query.from_user.id = 123456
        query.data = "analyze:RELIANCE.NS"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        return query
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
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
    
    @pytest.mark.asyncio
    async def test_refresh_analysis_callback(self, mock_query, mock_context, test_db):
        """Test refresh analysis callback"""
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        mock_analysis = {
            'status': 'success',
            'data': {
                'recommendation': 'BUY',
                'current_price': 2500.0,
                'confidence': 85
            }
        }
        
        with patch('src.bot.handlers.callbacks.get_db_context', test_db_context):
            with patch('src.bot.handlers.analyze.analyze_stock_with_settings', return_value=mock_analysis):
                await handle_analyze_refresh(mock_query, mock_context, ["RELIANCE.NS"])
        
        # Verify message sent
        mock_query.edit_message_text.assert_called()


class TestCompareStocksFeature:
    """Test Compare Stocks functionality"""
    
    @pytest.fixture
    def mock_update(self):
        """Create mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_compare_command_no_args(self, mock_update, mock_context):
        """Test /compare command with no arguments"""
        mock_update.message.text = "/compare"
        
        await compare_command(mock_update, mock_context)
        
        # Should show usage instructions
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_compare_command_valid(self, mock_update, mock_context, test_db):
        """Test /compare command with valid symbols"""
        mock_update.message.text = "/compare RELIANCE.NS TCS.NS"
        
        # Create user first
        get_or_create_user(test_db, telegram_id=123456, username="testuser")
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        mock_comparison = {
            'status': 'success',
            'data': [
                {'symbol': 'RELIANCE.NS', 'recommendation': 'BUY', 'current_price': 2500.0},
                {'symbol': 'TCS.NS', 'recommendation': 'HOLD', 'current_price': 3500.0}
            ]
        }
        
        with patch('src.bot.handlers.compare.get_db_context', test_db_context):
            with patch('src.bot.services.analysis_service.analyze_multiple_stocks', return_value=mock_comparison):
                await compare_command(mock_update, mock_context)
        
        # Verify message sent
        mock_update.message.reply_text.assert_called()


class TestScheduleReportsFeature:
    """Test Schedule Reports functionality"""
    
    @pytest.fixture
    def mock_update(self):
        """Create mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
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
    
    @pytest.mark.asyncio
    async def test_schedule_command_empty(self, mock_update, mock_context, test_db):
        """Test /schedule command with no scheduled reports"""
        mock_update.message.text = "/schedule"
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.schedule.get_db_context', test_db_context):
            with patch('src.bot.database.db.get_user_scheduled_reports', return_value=[]):
                await schedule_command(mock_update, mock_context)
        
        # Verify message sent
        mock_update.message.reply_text.assert_called_once()


class TestSettingsFeatures:
    """Test Settings features: Horizon, Risk, Capital, Report Style"""
    
    @pytest.fixture
    def mock_update(self):
        """Create mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.effective_user.username = "testuser"
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
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
    
    @pytest.mark.asyncio
    async def test_settings_command_view_all(self, mock_update, mock_context, test_db):
        """Test /settings command - View All Settings"""
        mock_update.message.text = "/settings"
        
        # Create user with settings
        user = get_or_create_user(test_db, telegram_id=123456, username="testuser")
        settings = get_user_settings(test_db, telegram_id=123456)
        settings.risk_mode = 'balanced'
        settings.investment_horizon = '3months'
        settings.default_capital = 100000.0
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.settings.get_db_context', test_db_context):
            await settings_command(mock_update, mock_context)
        
        # Verify message sent with all settings
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args.kwargs.get('text', '')
        assert "Settings" in message or "settings" in message.lower()
        assert "Capital" in message or "capital" in message.lower()
        assert "Risk" in message or "risk" in message.lower()
    
    @pytest.mark.asyncio
    async def test_view_all_settings_callback(self, mock_query, mock_update, mock_context, test_db):
        """Test 'View All Settings' callback - settings_show"""
        mock_query.data = "settings_show"
        mock_update.callback_query = mock_query
        
        # Create user with settings
        user = get_or_create_user(test_db, telegram_id=123456, username="testuser")
        settings = get_user_settings(test_db, telegram_id=123456)
        settings.risk_mode = 'aggressive'
        settings.investment_horizon = '6months'
        settings.default_capital = 200000.0
        settings.timeframe = 'long'
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.settings.get_db_context', test_db_context):
            await handle_settings_callback(mock_update, mock_context)
        
        # Verify all settings displayed
        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args
        message = call_args[0][0] if call_args[0] else call_args.kwargs.get('text', '')
        assert "ALL YOUR SETTINGS" in message or "All Your Settings" in message
        assert "INVESTMENT PERIOD" in message or "Investment Period" in message
        assert "RISK MODE" in message or "Risk Mode" in message
        assert "CAPITAL" in message or "Capital" in message
        assert "REPORT STYLE" in message or "Report Style" in message
    
    @pytest.mark.asyncio
    async def test_setcapital_command(self, mock_update, mock_context, test_db):
        """Test /setcapital command - Investment Amount"""
        mock_update.message.text = "/setcapital 150000"
        
        # Create user
        get_or_create_user(test_db, telegram_id=123456, username="testuser")
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        # parse_command_args needs command name as second parameter
        with patch('src.bot.handlers.settings.parse_command_args', return_value=['150000']):
            with patch('src.bot.handlers.settings.get_db_context', test_db_context):
                await setcapital_command(mock_update, mock_context)
        
        test_db.commit()
        test_db.expire_all()
        
        # Verify capital updated
        settings = get_user_settings(test_db, telegram_id=123456)
        assert settings.default_capital == 150000.0
        
        # Verify success message sent
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sethorizon_command(self, mock_update, mock_context, test_db):
        """Test /sethorizon command - How Long to Hold"""
        mock_update.message.text = "/sethorizon 6months"
        
        # Create user
        get_or_create_user(test_db, telegram_id=123456, username="testuser")
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        # Mock parse_command_args - horizon validation happens in handler
        with patch('src.bot.handlers.settings.parse_command_args', return_value=['6months']):
            with patch('src.bot.handlers.settings.get_db_context', test_db_context):
                await sethorizon_command(mock_update, mock_context)
        
        test_db.commit()
        test_db.expire_all()
        
        # Verify horizon updated
        settings = get_user_settings(test_db, telegram_id=123456)
        assert settings.investment_horizon == '6months'
    
    @pytest.mark.asyncio
    async def test_setmode_command(self, mock_update, mock_context, test_db):
        """Test /setmode command - Risk Comfort Level"""
        mock_update.message.text = "/setmode aggressive"
        
        # Create user
        get_or_create_user(test_db, telegram_id=123456, username="testuser")
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        # Mock parse_command_args and validate_mode
        with patch('src.bot.handlers.settings.parse_command_args', return_value=['aggressive']):
            with patch('src.bot.handlers.settings.validate_mode', return_value=(True, None)):
                with patch('src.bot.handlers.settings.get_db_context', test_db_context):
                    await setmode_command(mock_update, mock_context)
        
        test_db.commit()
        test_db.expire_all()
        
        # Verify risk mode updated
        settings = get_user_settings(test_db, telegram_id=123456)
        assert settings.risk_mode == 'aggressive'


# Report Style feature removed - using unified format_analysis_comprehensive formatter

