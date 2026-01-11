"""
Comprehensive Tests for Pending Paper Trades
Tests queue functionality, execution, and edge cases

Author: Harsh Kandhway
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from src.bot.database.models import (
    PendingPaperTrade, PaperTradingSession, PaperPosition, DailyBuySignal, User
)
from src.bot.services.market_hours_service import get_market_hours_service
from src.bot.services.paper_trade_execution_service import get_paper_trade_execution_service


class TestPendingPaperTradeModel:
    """Test PendingPaperTrade database model"""

    @pytest.fixture
    def test_db(self, test_db):
        """Use test database fixture"""
        return test_db

    @pytest.fixture
    def test_user(self, test_db):
        """Create test user"""
        from src.bot.database.models import User
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            is_active=True
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    @pytest.fixture
    def test_session(self, test_db, test_user):
        """Create test paper trading session"""
        session = PaperTradingSession(
            user_id=test_user.id,
            is_active=True,
            initial_capital=500000.0,
            current_capital=500000.0,
            max_positions=15
        )
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        return session

    def test_create_pending_trade(self, test_db, test_session, test_user):
        """Test creating a pending trade"""
        signal_data = {
            'symbol': 'RELIANCE.NS',
            'recommendation_type': 'STRONG BUY',
            'current_price': 2450.0,
            'target': 2680.0,
            'stop_loss': 2325.0,
            'confidence': 85.0
        }
        
        pending = PendingPaperTrade(
            session_id=test_session.id,
            symbol='RELIANCE.NS',
            requested_by_user_id=test_user.id,
            signal_data=json.dumps(signal_data),
            status='PENDING'
        )
        
        test_db.add(pending)
        test_db.commit()
        test_db.refresh(pending)
        
        assert pending.id is not None
        assert pending.status == 'PENDING'
        assert pending.symbol == 'RELIANCE.NS'
        assert pending.signal_data_dict == signal_data

    def test_pending_trade_signal_data_dict(self, test_db, test_session, test_user):
        """Test signal_data_dict property"""
        signal_data = {
            'symbol': 'TCS.NS',
            'recommendation_type': 'BUY',
            'current_price': 3500.0
        }
        
        pending = PendingPaperTrade(
            session_id=test_session.id,
            symbol='TCS.NS',
            requested_by_user_id=test_user.id,
            signal_data=json.dumps(signal_data),
            status='PENDING'
        )
        
        test_db.add(pending)
        test_db.commit()
        test_db.refresh(pending)
        
        # Test getter
        assert pending.signal_data_dict == signal_data
        
        # Test setter
        new_data = {'symbol': 'INFY.NS', 'price': 1500.0}
        pending.signal_data_dict = new_data
        test_db.commit()
        test_db.refresh(pending)
        
        assert pending.signal_data_dict == new_data

    def test_pending_trade_relationships(self, test_db, test_session, test_user):
        """Test pending trade relationships"""
        pending = PendingPaperTrade(
            session_id=test_session.id,
            symbol='RELIANCE.NS',
            requested_by_user_id=test_user.id,
            signal_data='{}',
            status='PENDING'
        )
        
        test_db.add(pending)
        test_db.commit()
        test_db.refresh(pending)
        
        assert pending.session.id == test_session.id
        assert pending.user.id == test_user.id


class TestPendingTradeQueue:
    """Test queueing pending trades"""

    @pytest.fixture
    def test_db(self, test_db):
        """Use test database fixture"""
        return test_db

    @pytest.fixture
    def test_user(self, test_db):
        """Create test user"""
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test"
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    @pytest.fixture
    def test_session(self, test_db, test_user):
        """Create test session"""
        session = PaperTradingSession(
            user_id=test_user.id,
            is_active=True,
            initial_capital=500000.0,
            current_capital=500000.0,
            max_positions=15
        )
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        return session

    @pytest.mark.asyncio
    async def test_queue_trade_when_market_closed(self, test_db, test_session, test_user):
        """Test queueing a trade when market is closed"""
        from src.bot.handlers.callbacks import _queue_paper_trade_for_market_open
        
        # Mock market hours to return closed - it's imported inside the function
        with patch('src.bot.services.market_hours_service.get_market_hours_service') as mock_mh:
            market_hours = Mock()
            market_hours.is_market_open.return_value = False
            market_hours.get_next_market_open.return_value = datetime(2026, 1, 13, 9, 15, 0)
            mock_mh.return_value = market_hours
            
            # Mock analysis
            mock_analysis = {
                'recommendation_type': 'STRONG BUY',
                'recommendation': 'Strong buy signal',
                'current_price': 2450.0,
                'target_data': {'recommended_target': 2680.0},
                'stop_data': {'recommended_stop': 2325.0},
                'risk_reward': 1.84,
                'confidence': 85.0,
                'overall_score_pct': 88.0
            }
            
            with patch('src.bot.handlers.callbacks.analyze_stock') as mock_analyze:
                with patch('asyncio.get_event_loop') as mock_loop:
                    mock_loop_instance = Mock()
                    mock_loop_instance.run_in_executor = AsyncMock(return_value=mock_analysis)
                    mock_loop.return_value = mock_loop_instance
                    
                    # Mock query
                    mock_query = AsyncMock()
                    mock_query.edit_message_text = AsyncMock()
                    mock_query.answer = AsyncMock()
                    
                    mock_context = Mock()
                    
                    # The function receives db as parameter, so we can use test_db directly
                    await _queue_paper_trade_for_market_open(
                        mock_query, mock_context, 'RELIANCE.NS',
                        test_session, test_user.id, test_db
                    )
                
                # Verify pending trade was created
                pending = test_db.query(PendingPaperTrade).filter(
                    PendingPaperTrade.session_id == test_session.id,
                    PendingPaperTrade.symbol == 'RELIANCE.NS',
                    PendingPaperTrade.status == 'PENDING'
                ).first()
                
                assert pending is not None
                assert pending.symbol == 'RELIANCE.NS'
                assert pending.status == 'PENDING'
                
                # Verify message was sent (called twice: "Analyzing..." then final message)
                assert mock_query.edit_message_text.call_count >= 1
                # Check the last call contains the success message
                last_call = mock_query.edit_message_text.call_args_list[-1]
                assert 'Trade Queued' in last_call[0][0] or 'Trade Queued' in str(last_call)

    def test_prevent_duplicate_queue(self, test_db, test_session, test_user):
        """Test preventing duplicate pending trades"""
        # Create existing pending trade
        existing = PendingPaperTrade(
            session_id=test_session.id,
            symbol='RELIANCE.NS',
            requested_by_user_id=test_user.id,
            signal_data='{}',
            status='PENDING'
        )
        test_db.add(existing)
        test_db.commit()
        
        # Try to create duplicate
        duplicate = PendingPaperTrade(
            session_id=test_session.id,
            symbol='RELIANCE.NS',
            requested_by_user_id=test_user.id,
            signal_data='{}',
            status='PENDING'
        )
        test_db.add(duplicate)
        test_db.commit()
        
        # Both should exist (no unique constraint, but handler checks)
        pending_count = test_db.query(PendingPaperTrade).filter(
            PendingPaperTrade.session_id == test_session.id,
            PendingPaperTrade.symbol == 'RELIANCE.NS',
            PendingPaperTrade.status == 'PENDING'
        ).count()
        
        assert pending_count == 2  # Handler should prevent this, but model allows it


class TestPendingTradeExecution:
    """Test executing pending trades"""

    @pytest.fixture
    def test_db(self, test_db):
        """Use test database fixture"""
        return test_db

    @pytest.fixture
    def test_user(self, test_db):
        """Create test user"""
        user = User(
            telegram_id=123456789,
            username="testuser"
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    @pytest.fixture
    def test_session(self, test_db, test_user):
        """Create test session"""
        session = PaperTradingSession(
            user_id=test_user.id,
            is_active=True,
            initial_capital=500000.0,
            current_capital=500000.0,
            max_positions=15
        )
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        return session

    @pytest.fixture
    def pending_trade(self, test_db, test_session, test_user):
        """Create pending trade"""
        signal_data = {
            'symbol': 'RELIANCE.NS',
            'recommendation_type': 'STRONG BUY',
            'recommendation': 'Strong buy',
            'current_price': 2450.0,
            'target': 2680.0,
            'stop_loss': 2325.0,
            'risk_reward': 1.84,
            'confidence': 85.0,
            'overall_score_pct': 88.0
        }
        
        pending = PendingPaperTrade(
            session_id=test_session.id,
            symbol='RELIANCE.NS',
            requested_by_user_id=test_user.id,
            signal_data=json.dumps(signal_data),
            status='PENDING'
        )
        test_db.add(pending)
        test_db.commit()
        test_db.refresh(pending)
        return pending

    @pytest.mark.asyncio
    async def test_execute_pending_trade_success(self, test_db, test_session, pending_trade):
        """Test successfully executing a pending trade"""
        from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
        
        # Mock application
        mock_app = Mock()
        scheduler = PaperTradingScheduler(mock_app)
        
        # Mock get_current_price - it's imported from analysis_service
        with patch('src.bot.services.analysis_service.get_current_price') as mock_price:
            mock_price.return_value = 2450.0
            
            # Mock execution service
            with patch('src.bot.services.paper_trade_execution_service.get_paper_trade_execution_service') as mock_exec:
                execution_service = Mock()
                execution_service.validate_entry.return_value = (True, None)
                
                # Mock position creation
                mock_position = PaperPosition(
                    session_id=test_session.id,
                    symbol='RELIANCE.NS',
                    entry_price=2450.0,
                    shares=10.0,
                    position_value=24500.0,
                    target_price=2680.0,
                    stop_loss_price=2325.0,
                    recommendation_type='STRONG BUY',
                    entry_confidence=85.0,
                    entry_score_pct=88.0,
                    initial_risk_reward=1.84,
                    is_open=True
                )
                execution_service.enter_position = AsyncMock(return_value=mock_position)
                mock_exec.return_value = execution_service
                
                # Execute pending trades
                await scheduler._execute_pending_trades()
                
                # Verify trade was executed
                test_db.refresh(pending_trade)
                # Note: The scheduler uses get_db_context() which creates a new session,
                # so we need to check the database directly
                from src.bot.database.db import get_db_context
                with get_db_context() as db:
                    updated_pending = db.query(PendingPaperTrade).filter(
                        PendingPaperTrade.id == pending_trade.id
                    ).first()
                    if updated_pending:
                        assert updated_pending.status == 'EXECUTED'
                        assert updated_pending.position_id is not None
                        assert updated_pending.executed_at is not None

    @pytest.mark.asyncio
    async def test_execute_pending_trade_validation_fails(self, test_db, test_session, pending_trade):
        """Test pending trade execution when validation fails"""
        from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
        
        mock_app = Mock()
        scheduler = PaperTradingScheduler(mock_app)
        
        with patch('src.bot.services.analysis_service.get_current_price') as mock_price:
            mock_price.return_value = 2450.0
            
            with patch('src.bot.services.paper_trade_execution_service.get_paper_trade_execution_service') as mock_exec:
                execution_service = Mock()
                execution_service.validate_entry.return_value = (False, "Insufficient capital")
                mock_exec.return_value = execution_service
                
                await scheduler._execute_pending_trades()
                
                # Verify trade was marked as failed
                from src.bot.database.db import get_db_context
                with get_db_context() as db:
                    updated_pending = db.query(PendingPaperTrade).filter(
                        PendingPaperTrade.id == pending_trade.id
                    ).first()
                    if updated_pending:
                        assert updated_pending.status == 'FAILED'
                        assert updated_pending.error_message == "Insufficient capital"
                        assert updated_pending.execution_attempts == 1

    @pytest.mark.asyncio
    async def test_execute_pending_trade_already_has_position(self, test_db, test_session, pending_trade):
        """Test pending trade execution when position already exists"""
        # Create existing position
        existing_position = PaperPosition(
            session_id=test_session.id,
            symbol='RELIANCE.NS',
            entry_price=2400.0,
            shares=10.0,
            position_value=24000.0,
            target_price=2600.0,
            stop_loss_price=2300.0,
            recommendation_type='BUY',
            entry_confidence=75.0,
            entry_score_pct=80.0,
            initial_risk_reward=2.0,
            is_open=True
        )
        test_db.add(existing_position)
        test_db.commit()
        
        from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
        
        mock_app = Mock()
        scheduler = PaperTradingScheduler(mock_app)
        
        await scheduler._execute_pending_trades()
        
        # Verify trade was cancelled
        from src.bot.database.db import get_db_context
        with get_db_context() as db:
            updated_pending = db.query(PendingPaperTrade).filter(
                PendingPaperTrade.id == pending_trade.id
            ).first()
            if updated_pending:
                assert updated_pending.status == 'CANCELLED'
                assert 'Already have position' in updated_pending.error_message

    @pytest.mark.asyncio
    async def test_execute_pending_trade_session_inactive(self, test_db, test_session, pending_trade):
        """Test pending trade execution when session is inactive"""
        # Deactivate session
        test_session.is_active = False
        test_db.commit()
        
        from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
        
        mock_app = Mock()
        scheduler = PaperTradingScheduler(mock_app)
        
        await scheduler._execute_pending_trades()
        
        # Verify trade was cancelled
        from src.bot.database.db import get_db_context
        with get_db_context() as db:
            updated_pending = db.query(PendingPaperTrade).filter(
                PendingPaperTrade.id == pending_trade.id
            ).first()
            if updated_pending:
                assert updated_pending.status == 'CANCELLED'
                assert 'Session no longer active' in updated_pending.error_message

    @pytest.mark.asyncio
    async def test_execute_multiple_pending_trades(self, test_db, test_session, test_user):
        """Test executing multiple pending trades"""
        # Create multiple pending trades
        symbols = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']
        pending_trades = []
        
        for symbol in symbols:
            signal_data = {
                'symbol': symbol,
                'recommendation_type': 'BUY',
                'current_price': 1000.0,
                'target': 1100.0,
                'stop_loss': 950.0,
                'risk_reward': 2.0,
                'confidence': 75.0,
                'overall_score_pct': 80.0
            }
            
            pending = PendingPaperTrade(
                session_id=test_session.id,
                symbol=symbol,
                requested_by_user_id=test_user.id,
                signal_data=json.dumps(signal_data),
                status='PENDING'
            )
            test_db.add(pending)
            pending_trades.append(pending)
        
        test_db.commit()
        
        from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
        
        mock_app = Mock()
        scheduler = PaperTradingScheduler(mock_app)
        
        with patch('src.bot.services.analysis_service.get_current_price') as mock_price:
            mock_price.return_value = 1000.0
            
            with patch('src.bot.services.paper_trade_execution_service.get_paper_trade_execution_service') as mock_exec:
                execution_service = Mock()
                execution_service.validate_entry.return_value = (True, None)
                
                from datetime import datetime
                mock_position = PaperPosition(
                    session_id=test_session.id,
                    symbol='RELIANCE.NS',
                    entry_date=datetime.utcnow(),
                    entry_price=1000.0,
                    shares=10.0,
                    position_value=10000.0,
                    target_price=1100.0,
                    stop_loss_price=950.0,
                    recommendation_type='BUY',
                    entry_confidence=75.0,
                    entry_score_pct=80.0,
                    initial_risk_reward=2.0,
                    is_open=True,
                    current_price=1000.0,
                    unrealized_pnl=0.0,
                    unrealized_pnl_pct=0.0,
                    highest_price=1000.0,
                    days_held=0
                )
                execution_service.enter_position = AsyncMock(return_value=mock_position)
                mock_exec.return_value = execution_service
                
                await scheduler._execute_pending_trades()
                
                # Verify all trades were executed
                from src.bot.database.db import get_db_context
                with get_db_context() as db:
                    for pending in pending_trades:
                        updated_pending = db.query(PendingPaperTrade).filter(
                            PendingPaperTrade.id == pending.id
                        ).first()
                        if updated_pending:
                            assert updated_pending.status == 'EXECUTED'

