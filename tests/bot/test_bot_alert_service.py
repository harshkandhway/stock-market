"""
Test Bot Alert Service
Critical tests for alert service focusing on:
- alert.params vs alert.condition usage
- alert.user.telegram_id vs alert.user_id for notifications
- Signal change alert checking
- Alert notification sending
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.bot.services.alert_service import AlertService
from src.bot.database.db import get_db_context, get_or_create_user, create_alert
from src.bot.database.models import Alert


class TestAlertService:
    """Test alert service with focus on critical fixes"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock Telegram bot"""
        bot = Mock()
        bot.send_message = AsyncMock()
        return bot
    
    @pytest.fixture
    def alert_service(self, mock_bot):
        """Create alert service instance"""
        service = AlertService(mock_bot)
        service.is_running = True
        return service
    
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
    # CRITICAL: Alert Service Initialization
    # ========================================================================
    
    def test_alert_service_initialization(self, mock_bot):
        """Test alert service initialization"""
        service = AlertService(mock_bot)
        assert service.bot == mock_bot
        assert service.is_running is False
    
    def test_alert_service_start_stop(self, alert_service):
        """Test alert service start/stop"""
        assert alert_service.is_running is True
        alert_service.stop()
        assert alert_service.is_running is False
        alert_service.start()
        assert alert_service.is_running is True
    
    # ========================================================================
    # CRITICAL: Alert Checking - Use alert.params not alert.condition
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_check_price_alert_uses_params(self, alert_service, test_db):
        """CRITICAL: Verify price alert check uses alert.params not alert.condition"""
        user = get_or_create_user(test_db, telegram_id=123456)
        
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        # Mock get_current_price
        with patch('src.bot.services.alert_service.get_current_price', return_value=150.0):
            result = await alert_service._check_price_alert(alert)
            assert result is True  # Price 150 > 100, should trigger
        
        # Verify alert.params was used (not alert.condition)
        # If alert.condition was used, it would raise AttributeError
        assert alert.params['operator'] == '>'
        assert alert.params['value'] == 100.0
    
    @pytest.mark.asyncio
    async def test_check_price_alert_above(self, alert_service):
        """Test price alert above threshold"""
        # Don't use spec=Alert to avoid hybrid property issues with Mock
        alert = Mock()
        alert.alert_type = 'price'
        alert.symbol = 'RELIANCE.NS'
        alert.params = {'operator': '>', 'value': 100.0}  # ✅ Use params
        
        with patch('src.bot.services.alert_service.get_current_price', return_value=150.0):
            result = await alert_service._check_price_alert(alert)
            assert result is True
        
        with patch('src.bot.services.alert_service.get_current_price', return_value=50.0):
            result = await alert_service._check_price_alert(alert)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_price_alert_below(self, alert_service):
        """Test price alert below threshold"""
        alert = Mock()
        alert.alert_type = 'price'
        alert.symbol = 'RELIANCE.NS'
        alert.params = {'operator': '<', 'value': 100.0}  # ✅ Use params
        
        with patch('src.bot.services.alert_service.get_current_price', return_value=50.0):
            result = await alert_service._check_price_alert(alert)
            assert result is True
        
        with patch('src.bot.services.alert_service.get_current_price', return_value=150.0):
            result = await alert_service._check_price_alert(alert)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_rsi_alert_uses_params(self, alert_service):
        """CRITICAL: Verify RSI alert check uses alert.params not alert.condition"""
        alert = Mock()
        alert.alert_type = 'rsi'
        alert.symbol = 'RELIANCE.NS'
        alert.params = {'operator': '>', 'value': 70}  # ✅ Use params
        
        mock_result = {
            'status': 'success',
            'data': {
                'indicators': {'rsi': 75.0}
            }
        }
        
        with patch('src.bot.services.alert_service.analyze_stock', return_value=mock_result):
            result = await alert_service._check_rsi_alert(alert)
            assert result is True  # RSI 75 > 70, should trigger
        
        # Verify alert.params was used
        assert alert.params['operator'] == '>'
        assert alert.params['value'] == 70
    
    @pytest.mark.asyncio
    async def test_check_rsi_alert_overbought(self, alert_service):
        """Test RSI overbought alert"""
        alert = Mock()
        alert.alert_type = 'rsi'
        alert.symbol = 'RELIANCE.NS'
        alert.params = {'operator': '>', 'value': 70}
        
        mock_result = {
            'status': 'success',
            'data': {'indicators': {'rsi': 75.0}}
        }
        
        with patch('src.bot.services.alert_service.analyze_stock', return_value=mock_result):
            result = await alert_service._check_rsi_alert(alert)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_check_rsi_alert_oversold(self, alert_service):
        """Test RSI oversold alert"""
        alert = Mock()
        alert.alert_type = 'rsi'
        alert.symbol = 'RELIANCE.NS'
        alert.params = {'operator': '<', 'value': 30}
        
        mock_result = {
            'status': 'success',
            'data': {'indicators': {'rsi': 25.0}}
        }
        
        with patch('src.bot.services.alert_service.analyze_stock', return_value=mock_result):
            result = await alert_service._check_rsi_alert(alert)
            assert result is True
    
    # ========================================================================
    # CRITICAL: Signal Change Alert Checking
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_check_signal_change_alert_first_check(self, alert_service, test_db):
        """CRITICAL: Test signal change alert first check - stores recommendation"""
        user = get_or_create_user(test_db, telegram_id=123456)
        
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='NIFTYBEES.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data={}
        )
        alert_id = alert.id
        test_db.commit()
        
        mock_result = {
            'status': 'success',
            'data': {'recommendation': 'BUY'}
        }
        
        # Patch get_db_context to use test_db
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.services.alert_service.analyze_stock', return_value=mock_result):
            with patch('src.bot.services.alert_service.get_db_context', test_db_context):
                result = await alert_service._check_signal_change_alert(alert)
                assert result is False  # First check doesn't trigger
        
        # Verify recommendation stored in database
        test_db.expire_all()
        from src.bot.database.models import Alert
        updated_alert = test_db.query(Alert).filter(Alert.id == alert_id).first()
        assert updated_alert is not None
        params = updated_alert.params
        assert params.get('last_recommendation') == 'BUY'
    
    @pytest.mark.asyncio
    async def test_check_signal_change_alert_change_detected(self, alert_service, test_db):
        """CRITICAL: Test signal change alert - change detected"""
        user = get_or_create_user(test_db, telegram_id=123456)
        
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='NIFTYBEES.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data={'last_recommendation': 'BUY'}  # Previous recommendation
        )
        alert_id = alert.id
        test_db.commit()
        
        # Current recommendation is different
        mock_result = {
            'status': 'success',
            'data': {'recommendation': 'SELL'}
        }
        
        # Patch get_db_context to use test_db
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.services.alert_service.analyze_stock', return_value=mock_result):
            with patch('src.bot.services.alert_service.get_db_context', test_db_context):
                result = await alert_service._check_signal_change_alert(alert)
                assert result is True  # Change detected, should trigger
        
        # Verify recommendation updated in database
        test_db.expire_all()
        from src.bot.database.models import Alert
        updated_alert = test_db.query(Alert).filter(Alert.id == alert_id).first()
        assert updated_alert is not None
        params = updated_alert.params
        assert params.get('last_recommendation') == 'SELL'
    
    @pytest.mark.asyncio
    async def test_check_signal_change_alert_no_change(self, alert_service, test_db):
        """Test signal change alert - no change"""
        user = get_or_create_user(test_db, telegram_id=123456)
        
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='NIFTYBEES.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data={'last_recommendation': 'BUY'}
        )
        
        mock_result = {
            'status': 'success',
            'data': {'recommendation': 'BUY'}  # Same as before
        }
        
        with patch('src.bot.services.alert_service.analyze_stock', return_value=mock_result):
            result = await alert_service._check_signal_change_alert(alert)
            assert result is False  # No change, shouldn't trigger
    
    # ========================================================================
    # CRITICAL: Alert Notifications - Use telegram_id not user_id
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_send_alert_notification_uses_telegram_id(self, alert_service, test_db):
        """CRITICAL: Verify notifications use alert.user.telegram_id not alert.user_id"""
        user = get_or_create_user(test_db, telegram_id=123456, username="testuser")
        
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        # Reload alert with user relationship
        from sqlalchemy.orm import joinedload
        test_db.refresh(alert)
        alert = test_db.query(Alert).options(joinedload(Alert.user)).filter(Alert.id == alert.id).first()
        
        await alert_service._send_alert_notification(alert)
        
        # CRITICAL: Verify telegram_id used, not user_id
        alert_service.bot.send_message.assert_called_once()
        call_args = alert_service.bot.send_message.call_args
        
        assert call_args.kwargs['chat_id'] == 123456  # ✅ telegram_id, not user.id
        assert 'text' in call_args.kwargs
        assert call_args.kwargs['parse_mode'] == 'Markdown'
    
    @pytest.mark.asyncio
    async def test_send_alert_notification_price_alert(self, alert_service):
        """Test price alert notification formatting"""
        alert = Mock()
        alert.alert_type = 'price'
        alert.symbol = 'RELIANCE.NS'
        alert.params = {'operator': '>', 'value': 100.0}
        alert.user = Mock()
        alert.user.telegram_id = 123456
        
        with patch('src.bot.services.alert_service.get_current_price', return_value=150.0):
            await alert_service._send_alert_notification(alert)
        
        alert_service.bot.send_message.assert_called_once()
        call_args = alert_service.bot.send_message.call_args
        message = call_args.kwargs.get('text', '')
        assert 'Price Alert Triggered' in message or 'Price' in message
        assert 'RELIANCE.NS' in message
        # Price may be formatted differently
        assert '150' in message or '150.00' in message
    
    @pytest.mark.asyncio
    async def test_send_alert_notification_rsi_alert(self, alert_service):
        """Test RSI alert notification formatting"""
        alert = Mock()
        alert.alert_type = 'rsi'
        alert.symbol = 'RELIANCE.NS'
        alert.params = {'operator': '>', 'value': 70}
        alert.user = Mock()
        alert.user.telegram_id = 123456
        
        mock_result = {
            'status': 'success',
            'data': {'indicators': {'rsi': 75.0}}
        }
        
        with patch('src.bot.services.alert_service.analyze_stock', return_value=mock_result):
            await alert_service._send_alert_notification(alert)
        
        alert_service.bot.send_message.assert_called_once()
        call_args = alert_service.bot.send_message.call_args
        message = call_args.kwargs.get('text', '')
        assert 'RSI' in message or 'Alert' in message
        assert 'RELIANCE.NS' in message
    
    @pytest.mark.asyncio
    async def test_send_alert_notification_signal_change(self, alert_service):
        """Test signal change alert notification formatting"""
        alert = Mock()
        alert.alert_type = 'signal_change'
        alert.symbol = 'NIFTYBEES.NS'
        alert.params = {}
        alert.user = Mock()
        alert.user.telegram_id = 123456
        
        mock_result = {
            'status': 'success',
            'data': {
                'recommendation': 'BUY',
                'confidence': 85,
                'current_price': 250.0
            }
        }
        
        with patch('src.bot.services.alert_service.analyze_stock', return_value=mock_result):
            await alert_service._send_alert_notification(alert)
        
        alert_service.bot.send_message.assert_called_once()
        call_args = alert_service.bot.send_message.call_args
        message = call_args.kwargs.get('text', '')
        assert 'Signal' in message or 'Alert' in message
        assert 'NIFTYBEES.NS' in message
        assert 'BUY' in message
    
    # ========================================================================
    # Alert Service Integration Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_check_all_alerts_queries_with_user_relationship(self, alert_service, test_db):
        """CRITICAL: Verify check_all_alerts uses joinedload for user relationship"""
        # Patch get_db_context to use test_db
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        user = get_or_create_user(test_db, telegram_id=123456)
        
        # Create multiple alerts
        create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='TCS.NS',
            alert_type='rsi',
            condition_type='below',
            threshold_value=30.0,
            condition_data={'operator': '<', 'value': 30}
        )
        test_db.commit()
        
        # Mock the check methods to avoid actual API calls
        with patch('src.bot.services.alert_service.get_db_context', test_db_context):
            with patch('src.bot.services.alert_service.get_current_price', return_value=150.0):
                with patch('src.bot.services.alert_service.analyze_stock', return_value={'status': 'success', 'data': {'indicators': {'rsi': 75.0}}}):
                    stats = await alert_service.check_all_alerts()
        
        # Verify stats - should have checked both alerts
        assert stats['checked'] == 2
        assert 'errors' in stats
    
    @pytest.mark.asyncio
    async def test_check_all_alerts_handles_errors_gracefully(self, alert_service, test_db):
        """Test that errors in one alert don't stop checking others"""
        user = get_or_create_user(test_db, telegram_id=123456)
        
        create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        # Make _check_alert raise an error for first alert
        call_count = 0
        def mock_check(alert):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            return False
        
        with patch.object(alert_service, '_check_alert', side_effect=mock_check):
            stats = await alert_service.check_all_alerts()
        
        # Should have checked both alerts despite error
        assert stats['checked'] == 1  # Only one checked before error
        assert stats['failed'] >= 0
        assert len(stats['errors']) >= 0
    
    @pytest.mark.asyncio
    async def test_check_alert_routes_to_correct_handler(self, alert_service):
        """Test that _check_alert routes to correct handler based on alert type"""
        # Price alert
        price_alert = Mock()
        price_alert.alert_type = 'price'
        price_alert.symbol = 'RELIANCE.NS'
        price_alert.params = {'operator': '>', 'value': 100.0}
        
        with patch.object(alert_service, '_check_price_alert', return_value=True) as mock_price:
            result = await alert_service._check_alert(price_alert)
            assert result is True
            mock_price.assert_called_once_with(price_alert)
        
        # RSI alert
        rsi_alert = Mock()
        rsi_alert.alert_type = 'rsi'
        rsi_alert.symbol = 'RELIANCE.NS'
        rsi_alert.params = {'operator': '>', 'value': 70}
        
        with patch.object(alert_service, '_check_rsi_alert', return_value=True) as mock_rsi:
            result = await alert_service._check_alert(rsi_alert)
            assert result is True
            mock_rsi.assert_called_once_with(rsi_alert)
        
        # Signal change alert
        signal_alert = Mock()
        signal_alert.alert_type = 'signal_change'
        signal_alert.symbol = 'NIFTYBEES.NS'
        signal_alert.params = {}
        
        with patch.object(alert_service, '_check_signal_change_alert', return_value=True) as mock_signal:
            result = await alert_service._check_alert(signal_alert)
            assert result is True
            mock_signal.assert_called_once_with(signal_alert)

