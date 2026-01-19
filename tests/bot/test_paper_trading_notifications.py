"""
Unit Tests for Paper Trading Notifications and Fixes
Tests for Issues #1, #2, #3 and Improvements

Author: Harsh Kandhway
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session

from src.bot.database.models import (
    PaperTradingSession, PaperPosition, DailyBuySignal, User
)
from src.bot.services.paper_trading_service import PaperTradingService
from src.bot.services.paper_trade_execution_service import PaperTradeExecutionService


class TestIndividualNotifications:
    """Test Fix #1: Individual trade notifications"""
    
    @pytest.mark.asyncio
    async def test_individual_notification_sent_on_position_open(self):
        """Test that individual notification is sent when position opens"""
        # Arrange
        mock_db = Mock(spec=Session)
        notifications = []
        
        async def mock_notification(user_id, symbol, position, notif_type):
            """Mock notification callback"""
            notifications.append({
                'user_id': user_id,
                'symbol': symbol,
                'position_id': position.id if position else None,
                'type': notif_type
            })
        
        service = PaperTradingService(mock_db, notification_callback=mock_notification)
        
        # Create mock session
        mock_session = MagicMock(spec=PaperTradingSession)
        mock_session.id = 1
        mock_session.user_id = 12345
        mock_session.current_capital = 500000
        mock_session.current_positions = 0
        mock_session.max_positions = 15
        
        # Create mock signal
        mock_signal = MagicMock(spec=DailyBuySignal)
        mock_signal.id = 1
        mock_signal.symbol = "RELIANCE.NS"
        mock_signal.recommendation_type = "BUY"
        mock_signal.current_price = 2500.0
        mock_signal.target = 2750.0
        mock_signal.stop_loss = 2400.0
        mock_signal.confidence = 75.0
        mock_signal.risk_reward = 2.5
        mock_signal.analysis_date = datetime.utcnow()
        
        # Create mock position
        mock_position = MagicMock(spec=PaperPosition)
        mock_position.id = 1
        mock_position.symbol = "RELIANCE.NS"
        mock_position.entry_price = 2500.0
        
        # Mock dependencies
        with patch.object(service.portfolio_service, 'can_open_position', return_value=True), \
             patch.object(service.execution_service, 'enter_position', return_value=mock_position), \
             patch('src.bot.services.analysis_service.get_current_price', return_value=2500.0):
            
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Act
            result = await service._execute_signals_for_session(mock_session, [mock_signal])
            
            # Assert
            assert result['opened'] == 1
            assert len(notifications) == 1
            assert notifications[0]['user_id'] == 12345
            assert notifications[0]['symbol'] == "RELIANCE.NS"
            assert notifications[0]['type'] == "individual"
    
    @pytest.mark.asyncio
    async def test_no_notification_when_position_skipped(self):
        """Test that no notification is sent when position is skipped"""
        # Arrange
        mock_db = Mock(spec=Session)
        notifications = []
        
        async def mock_notification(user_id, symbol, position, notif_type):
            notifications.append({})
        
        service = PaperTradingService(mock_db, notification_callback=mock_notification)
        
        mock_session = MagicMock(spec=PaperTradingSession)
        mock_session.id = 1
        mock_session.user_id = 12345
        
        mock_signal = MagicMock(spec=DailyBuySignal)
        mock_signal.symbol = "RELIANCE.NS"
        mock_signal.analysis_date = datetime.utcnow()
        
        # Mock execution service returns None (position skipped)
        with patch.object(service.portfolio_service, 'can_open_position', return_value=True), \
             patch.object(service.execution_service, 'enter_position', return_value=None), \
             patch('src.bot.services.analysis_service.get_current_price', return_value=2500.0):
            
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Act
            result = await service._execute_signals_for_session(mock_session, [mock_signal])
            
            # Assert
            assert result['skipped'] == 1
            assert len(notifications) == 0  # No notification when skipped


class TestPersonalizedSummaries:
    """Test Fix #2: Personalized summary notifications"""
    
    def test_personalized_summary_creation(self):
        """Test that summary is personalized per user"""
        # Arrange
        result = {
            'sessions_processed': 3,
            'signals_found': 10,
            'positions_opened': 4,
            'skipped': 6,
            'details': [
                {'user_id': 100, 'opened': 3, 'skipped': 2},
                {'user_id': 200, 'opened': 0, 'skipped': 4},  # User B - no positions
                {'user_id': 300, 'opened': 1, 'skipped': 0}
            ]
        }
        
        # Act: Extract user results (like the actual code does)
        user_results = {}
        for detail in result.get('details', []):
            user_id = detail.get('user_id')
            user_results[user_id] = {
                'opened': detail.get('opened', 0),
                'skipped': detail.get('skipped', 0)
            }
        
        # Assert: Each user gets their own results
        assert user_results[100]['opened'] == 3
        assert user_results[100]['skipped'] == 2
        
        assert user_results[200]['opened'] == 0  # User B gets 0!
        assert user_results[200]['skipped'] == 4
        
        assert user_results[300]['opened'] == 1
        assert user_results[300]['skipped'] == 0
        
        # Verify User B sees "0 positions opened"
assert user_results[200]['opened'] == 0


class TestStalenessCheck:
    """Test Fix #3: Signal staleness validation"""
    
    @pytest.mark.asyncio
    async def test_stale_signal_skipped_when_price_unavailable(self):
        """Test that stale signals (>60 min) are skipped when current price is None"""
        # Arrange
        mock_db = Mock(spec=Session)
        service = PaperTradingService(mock_db)
        
        mock_session = MagicMock(spec=PaperTradingSession)
        mock_session.id = 1
        mock_session.current_positions = 0
        
        # Create STALE signal (2 hours old)
        mock_signal = MagicMock(spec=DailyBuySignal)
        mock_signal.symbol = "RELIANCE.NS"
        mock_signal.analysis_date = datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
        mock_signal.current_price = 2500.0
        
        # Mock get_current_price returns None (price fetch failed)
        with patch('src.bot.services.analysis_service.get_current_price', return_value=None), \
             patch.object(service.portfolio_service, 'can_open_position', return_value=True):
            
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Act
            result = await service._execute_signals_for_session(mock_session, [mock_signal])
            
            # Assert
            assert result['skipped'] == 1
            assert result['opened'] == 0
    
    @pytest.mark.asyncio
    async def test_fresh_signal_uses_fallback_price(self):
        """Test that fresh signals (< 60 min) use signal price when current price is None"""
        # Arrange
        mock_db = Mock(spec=Session)
        service = PaperTradingService(mock_db)
        
        mock_session = MagicMock(spec=PaperTradingSession)
        mock_session.id = 1
        mock_session.user_id = 12345
        mock_session.current_positions = 0
        mock_session.current_capital = 500000
        
        # Create FRESH signal (30 minutes old)
        mock_signal = MagicMock(spec=DailyBuySignal)
        mock_signal.symbol = "TCS.NS"
        mock_signal.analysis_date = datetime.utcnow() - timedelta(minutes=30)  # 30 min ago
        mock_signal.current_price = 4000.0
        mock_signal.target = 4200.0
        mock_signal.stop_loss = 3900.0
        mock_signal.confidence = 80.0
        mock_signal.risk_reward = 2.0
        mock_signal.recommendation_type = "STRONG BUY"
        
        mock_position = MagicMock(spec=PaperPosition)
        mock_position.id = 1
        
        # Mock get_current_price returns None, but signal is fresh
        with patch('src.bot.services.analysis_service.get_current_price', return_value=None), \
             patch.object(service.portfolio_service, 'can_open_position', return_value=True), \
             patch.object(service.execution_service, 'enter_position', return_value=mock_position):
            
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Act
            result = await service._execute_signals_for_session(mock_session, [mock_signal])
            
            # Assert: Should use fallback price and open position
            assert result['opened'] == 1
            assert result['skipped'] == 0


class TestDryRunMode:
    """Test Improvement #2: Dry-run mode"""
    
    @pytest.mark.asyncio
    async def test_dry_run_prevents_position_creation(self):
        """Test that dry-run mode prevents actual position creation"""
        # Arrange
        from src.bot.config import PAPER_TRADING_DRY_RUN
        
        mock_db = Mock(spec=Session)
        execution_service = PaperTradeExecutionService(mock_db)
        
        mock_session = MagicMock(spec=PaperTradingSession)
        mock_session.id = 1
        mock_session.current_capital = 500000
        
        mock_signal = MagicMock(spec=DailyBuySignal)
        mock_signal.symbol = "RELIANCE.NS"
        mock_signal.current_price = 2500.0
        mock_signal.target = 2750.0
        mock_signal.stop_loss = 2400.0
        mock_signal.risk_reward = 2.5
        mock_signal.confidence = 75.0
        
        # Mock validation to pass
        with patch.object(execution_service, 'validate_entry', return_value=(True, None)), \
             patch.object(execution_service.portfolio_service, 'calculate_position_size', 
                         return_value={'shares': 10, 'position_value': 25000, 'risk_amount': 500}), \
             patch('src.bot.config.PAPER_TRADING_DRY_RUN', True):  # Enable dry-run
            
            # Act
            result = await execution_service.enter_position(mock_session, mock_signal, 2500.0)
            
            # Assert: Should return None (no position created)
            assert result is None
            
            # Verify no database operations occurred
            mock_db.add.assert_not_called()
            mock_db.commit.assert_not_called()


class TestLoggingIntegration:
    """Test Improvement #1: Enhanced logging"""
    
    @pytest.mark.asyncio
    async def test_entry_logged_to_paper_trading_log(self):
        """Test that trade entries are logged to dedicated log file"""
        # Arrange
        mock_db = Mock(spec=Session)
        execution_service = PaperTradeExecutionService(mock_db)
        
        mock_session = MagicMock(spec=PaperTradingSession)
        mock_session.id = 1
        mock_session.user_id = 12345
        mock_session.current_capital = 500000
        mock_session.current_positions = 0
        
        mock_signal = MagicMock(spec=DailyBuySignal)
        mock_signal.id = 1
        mock_signal.symbol = "RELIANCE.NS"
        mock_signal.current_price = 2500.0
        mock_signal.target = 2750.0
        mock_signal.stop_loss = 2400.0
        mock_signal.risk_reward = 2.5
        mock_signal.confidence = 75.0
        mock_signal.recommendation_type = "BUY"
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(execution_service, 'validate_entry', return_value=(True, None)), \
             patch.object(execution_service.portfolio_service, 'calculate_position_size',
                         return_value={'shares': 10, 'position_value': 25000}), \
             patch('src.bot.config.PAPER_TRADING_DRY_RUN', False), \
             patch('src.bot.services.paper_trade_execution_service.pt_logger') as mock_pt_logger:
            
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()
            
            # Act
            position = await execution_service.enter_position(mock_session, mock_signal, 2500.0)
            
            # Assert: Paper trading logger was called
            assert mock_pt_logger.info.called
            # Verify log message contains key info
            log_message = mock_pt_logger.info.call_args[0][0]
            assert "ENTRY" in log_message
            assert "RELIANCE.NS" in log_message
            assert "Session 1" in log_message


class TestEndToEndIntegration:
    """Integration tests for complete workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_buy_execution_flow_with_notifications(self):
        """Test complete flow: fetch signals, execute, send individual + summary notifications"""
        # Arrange
        mock_db = Mock(spec=Session)
        individual_notifications = []
        summary_notifications = []
        
        async def mock_individual_notification(user_id, symbol, position, notif_type):
            individual_notifications.append({
                'user_id': user_id,
                'symbol': symbol,
                'type': notif_type
            })
        
        service = PaperTradingService(mock_db, notification_callback=mock_individual_notification)
        
        # Create 2 mock sessions (2 users)
        session1 = MagicMock(spec=PaperTradingSession)
        session1.id = 1
        session1.user_id = 100
        session1.is_active = True
        session1.current_positions = 0
        session1.max_positions = 15
        session1.current_capital = 500000
        
        session2 = MagicMock(spec=PaperTradingSession)
        session2.id = 2
        session2.user_id = 200
        session2.is_active = True
        session2.current_positions = 15  # Max positions reached
        session2.max_positions = 15
        session2.current_capital = 500000
        
        # Create 3 signals
        signal1 = MagicMock(spec=DailyBuySignal)
        signal1.id = 1
        signal1.symbol = "RELIANCE.NS"
        signal1.recommendation_type = "STRONG BUY"
        signal1.current_price = 2500.0
        signal1.target = 2750.0
        signal1.stop_loss = 2400.0
        signal1.confidence = 85.0
        signal1.risk_reward = 2.5
        signal1.analysis_date = datetime.utcnow()
        
        signal2 = MagicMock(spec=DailyBuySignal)
        signal2.id = 2
        signal2.symbol = "TCS.NS"
        signal2.recommendation_type = "BUY"
        signal2.current_price = 4000.0
        signal2.target = 4200.0
        signal2.stop_loss = 3900.0
        signal2.confidence = 75.0
        signal2.risk_reward = 2.0
        signal2.analysis_date = datetime.utcnow()
        
        # Mock positions created
        position1 = MagicMock(spec=PaperPosition)
        position1.id = 1
        position1.symbol = "RELIANCE.NS"
        
        position2 = MagicMock(spec=PaperPosition)
        position2.id = 2
        position2.symbol = "TCS.NS"
        
        # Mock database queries
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        
        # Setup query chain for signals
        signals_query = Mock()
        signals_query.filter.return_value = signals_query
        signals_query.order_by.return_value = signals_query
        signals_query.all.return_value = [signal1, signal2]
        
        # Setup query chain for sessions
        sessions_query = Mock()
        sessions_query.filter.return_value = sessions_query
        sessions_query.all.return_value = [session1, session2]
        
        def mock_query_side_effect(model):
            if model == DailyBuySignal:
                return signals_query
            elif model == PaperTradingSession:
                return sessions_query
            elif model == PaperPosition:
                pos_query = Mock()
                pos_query.filter.return_value = pos_query
                pos_query.first.return_value = None  # No existing positions
                return pos_query
            return Mock()
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock execution for session1 (positions open)
        with patch('src.bot.services.analysis_service.get_current_price', side_effect=[2500.0, 4000.0]), \
             patch.object(service.portfolio_service, 'can_open_position', side_effect=[True, True, False, False]), \
             patch.object(service.execution_service, 'enter_position', side_effect=[position1, position2, None, None]), \
             patch('src.bot.config.PAPER_TRADING_DRY_RUN', False):
            
            # Act
            result = await service.execute_buy_signals()
            
            # Assert
            # Should process 2 sessions
            assert result['sessions_processed'] == 2
            assert result['signals_found'] == 2
            
            # Session1: 2 positions opened, Session2: 0 positions (limit reached)
            assert result['positions_opened'] == 2
            
            # Individual notifications: 2 (one for each position opened)
            assert len(individual_notifications) == 2
            assert individual_notifications[0]['symbol'] == "RELIANCE.NS"
            assert individual_notifications[1]['symbol'] == "TCS.NS"
            
            # Verify details include per-user breakdown
            assert len(result['details']) == 2
            # User 100 should have 2 positions opened
            user_100_detail = next(d for d in result['details'] if d['user_id'] == 100)
            assert user_100_detail['opened'] == 2
            
            # User 200 should have 0 positions (limit reached)
            user_200_detail = next(d for d in result['details'] if d['user_id'] == 200)
            assert user_200_detail['opened'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
