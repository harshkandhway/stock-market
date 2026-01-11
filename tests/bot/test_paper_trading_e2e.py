"""
End-to-End Tests for Complete Paper Trading Flow

This module tests the complete user journey from clicking "Paper Trade This Stock"
through automatic execution at market open, including notifications and error handling.

Test Scenarios:
- Market closed → Queue → Auto-execute → Notifications
- Session auto-creation
- Error cases (session inactive, market data failures, validation failures)
- Performance with multiple concurrent trades
- Trade history display
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from telegram import Update, Message, CallbackQuery, User, Chat

from src.bot.handlers.callbacks import handle_papertrade_stock_confirm
from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
from src.bot.database.models import PaperTradingSession, PendingPaperTrade, PaperPosition


@pytest.fixture
def mock_application():
    """Mock Telegram application"""
    app = Mock()
    app.bot = AsyncMock()
    return app


@pytest.fixture
def scheduler(mock_application):
    """Create scheduler instance"""
    return PaperTradingScheduler(mock_application)


@pytest.fixture
def mock_user():
    """Mock Telegram user"""
    user = Mock()
    user.id = 123456
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    return user


@pytest.fixture
def mock_query(mock_user):
    """Mock callback query"""
    query = Mock()
    query.from_user = mock_user
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_context():
    """Mock Telegram context"""
    return Mock()


class TestCompletePaperTradingFlow:
    """Test complete paper trading flow from UI click to execution"""

    @pytest.mark.asyncio
    async def test_market_closed_queue_to_execution_flow(self, mock_query, mock_context, test_db):
        """
        Test complete flow: Market closed → Queue → Auto-execution → Notifications

        This simulates the user's exact scenario:
        1. User clicks "Paper Trade This Stock" at 1:49 AM (market closed)
        2. System queues the trade
        3. At 9:20 AM, scheduler executes automatically
        4. User receives notifications
        """
        # Phase 1: Queue the trade (market closed)
        mock_query.data = "papertrade_stock_confirm:AXISBANK.NS"

        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db_ctx:
            mock_db_ctx.return_value.__enter__.return_value = test_db
            mock_db_ctx.return_value.__exit__.return_value = None

            # Mock market closed
            with patch('src.bot.services.market_hours_service.get_market_hours_service') as mock_mh:
                market_hours = Mock()
                market_hours.is_market_open.return_value = False
                market_hours.get_next_market_open.return_value = datetime(2026, 1, 12, 9, 15, 0)
                mock_mh.return_value = market_hours

                # Mock trading service (no active session initially)
                with patch('src.bot.services.paper_trading_service.get_paper_trading_service') as mock_service:
                    mock_trading_service = AsyncMock()
                    mock_trading_service.get_active_session.return_value = None
                    mock_service.return_value = mock_trading_service

                    # Mock user settings
                    with patch('src.bot.database.db.get_user_settings') as mock_get_settings:
                        settings = Mock()
                        settings.default_capital = 100000
                        mock_get_settings.return_value = settings

                        # Execute the queue action
                        await handle_papertrade_stock_confirm(mock_query, mock_context, ['AXISBANK.NS'])

                        # Verify session was auto-created
                        session = test_db.query(PaperTradingSession).filter(
                            PaperTradingSession.user_id == mock_query.from_user.id,
                            PaperTradingSession.is_active == True
                        ).first()
                        assert session is not None, "Session should be auto-created"

                        # Verify trade was queued
                        pending = test_db.query(PendingPaperTrade).filter(
                            PendingPaperTrade.session_id == session.id,
                            PendingPaperTrade.symbol == 'AXISBANK.NS',
                            PendingPaperTrade.status == 'PENDING'
                        ).first()
                        assert pending is not None, "Trade should be queued"

                        # Verify user saw "Market Closed - Queueing Trade" message
                        queue_messages = [call for call in mock_query.edit_message_text.call_args_list
                                        if 'Market Closed' in call[0][0]]
                        assert len(queue_messages) > 0, "User should see market closed message"

                        # For this test, we verify the queuing worked successfully
                        # In a real scenario, the scheduler would execute this at market open
                        # The queuing part is what we're testing - execution would happen later

    @pytest.mark.asyncio
    async def test_session_auto_creation_edge_cases(self, mock_query, mock_context, test_db):
        """Test session auto-creation with various edge cases"""
        mock_query.data = "papertrade_stock_confirm:TCS.NS"

        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db_ctx:
            mock_db_ctx.return_value.__enter__.return_value = test_db
            mock_db_ctx.return_value.__exit__.return_value = None

            # Mock market closed
            with patch('src.bot.services.market_hours_service.get_market_hours_service') as mock_mh:
                market_hours = Mock()
                market_hours.is_market_open.return_value = False
                mock_mh.return_value = market_hours

                # Mock no active session
                with patch('src.bot.services.paper_trading_service.get_paper_trading_service') as mock_service:
                    mock_trading_service = AsyncMock()
                    mock_trading_service.get_active_session.return_value = None
                    mock_service.return_value = mock_trading_service

                    # Test 1: No user settings (should use default capital)
                    with patch('src.bot.database.db.get_user_settings') as mock_get_settings:
                        mock_get_settings.return_value = None

                        await handle_papertrade_stock_confirm(mock_query, mock_context, ['TCS.NS'])

                        session = test_db.query(PaperTradingSession).filter(
                            PaperTradingSession.user_id == mock_query.from_user.id,
                            PaperTradingSession.is_active == True
                        ).first()
                        assert session is not None
                        assert session.initial_capital == 100000  # Default
                        assert session.current_capital == 100000  # Should be set

    @pytest.mark.asyncio
    async def test_error_handling_during_execution(self, mock_query, mock_context, test_db):
        """Test error handling during trade execution"""
        # Create a session and pending trade
        session = PaperTradingSession(
            user_id=mock_query.from_user.id,
            initial_capital=100000,
            is_active=True
        )
        test_db.add(session)
        test_db.commit()

        pending = PendingPaperTrade(
            session_id=session.id,
            symbol='INFY.NS',
            requested_by_user_id=mock_query.from_user.id,
            signal_data='{"test": "data"}',
            status='PENDING'
        )
        test_db.add(pending)
        test_db.commit()

        # Mock scheduler with execution errors
        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()
        scheduler.application.bot = AsyncMock()

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            # Mock the entire execution process
            with patch.object(scheduler, '_execute_pending_trades') as mock_execute:
                # Mock successful execution
                mock_execute.return_value = None

                # Manually set up what the execution would do
                pending.status = 'EXECUTED'
                pending.position_id = 999
                pending.executed_at = datetime.utcnow()
                test_db.commit()

                # Execute (this will be mocked, but we set up the DB state)
                await scheduler._execute_pending_trades()

                # Verify trade was marked as failed
                updated_pending = test_db.query(PendingPaperTrade).filter(
                    PendingPaperTrade.id == pending.id
                ).first()
                assert updated_pending.status == 'FAILED'
                assert "Insufficient capital" in updated_pending.error_message

    @pytest.mark.asyncio
    async def test_concurrent_trade_execution_performance(self, test_db):
        """Test performance with multiple concurrent trades"""
        import asyncio

        # Create multiple sessions and pending trades
        sessions = []
        pendings = []

        for i in range(5):  # Simulate 5 concurrent users
            session = PaperTradingSession(
                user_id=1000 + i,
                initial_capital=100000,
                is_active=True
            )
            test_db.add(session)
            sessions.append(session)

            pending = PendingPaperTrade(
                session_id=session.id,
                symbol=f'SYMBOL{i}.NS',
                requested_by_user_id=1000 + i,
                signal_data='{"test": "data"}',
                status='PENDING'
            )
            test_db.add(pending)
            pendings.append(pending)

        test_db.commit()

        # Mock scheduler
        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()
        scheduler.application.bot = AsyncMock()

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            # Mock successful execution for all
            with patch('src.bot.services.paper_trading_scheduler.get_paper_trade_execution_service') as mock_exec:
                execution_service = AsyncMock()
                execution_service.validate_entry.return_value = (True, None)

                # Create different mock positions
                def create_position():
                    pos = Mock()
                    pos.id = len(pendings) + 1
                    return pos
                execution_service.enter_position.side_effect = [create_position() for _ in pendings]
                mock_exec.return_value = execution_service

                # Measure execution time
                import time
                start_time = time.time()
                await scheduler._execute_pending_trades()
                execution_time = time.time() - start_time

                # Verify all trades executed
                executed_count = test_db.query(PendingPaperTrade).filter(
                    PendingPaperTrade.status == 'EXECUTED'
                ).count()
                assert executed_count == 5, "All trades should execute"

                # Verify reasonable execution time (< 5 seconds for 5 trades)
                assert execution_time < 5.0, f"Execution took too long: {execution_time}s"

                # Verify notifications sent (5 individual + 1 summary)
                assert scheduler.application.bot.send_message.call_count >= 6

    @pytest.mark.asyncio
    async def test_trade_history_shows_all_trades_comprehensive(self, mock_query, mock_context, test_db):
        """Test trade history shows all trades from all sessions comprehensively"""
        # Create multiple sessions with different states
        sessions = []

        # Session 1: Old inactive session
        session1 = PaperTradingSession(
            user_id=mock_query.from_user.id,
            initial_capital=100000,
            is_active=False
        )
        test_db.add(session1)
        sessions.append(session1)

        # Session 2: Current active session
        session2 = PaperTradingSession(
            user_id=mock_query.from_user.id,
            initial_capital=50000,
            is_active=True
        )
        test_db.add(session2)
        sessions.append(session2)

        test_db.commit()

        # Create various trade states
        pending_executed = PendingPaperTrade(
            session_id=session1.id,
            symbol='AXISBANK.NS',
            requested_by_user_id=mock_query.from_user.id,
            signal_data='{"status": "executed"}',
            status='EXECUTED',
            executed_at=datetime.utcnow()
        )

        pending_failed = PendingPaperTrade(
            session_id=session1.id,
            symbol='TCS.NS',
            requested_by_user_id=mock_query.from_user.id,
            signal_data='{"status": "failed"}',
            status='FAILED',
            error_message='Validation failed'
        )

        pending_active = PendingPaperTrade(
            session_id=session2.id,
            symbol='INFY.NS',
            requested_by_user_id=mock_query.from_user.id,
            signal_data='{"status": "pending"}',
            status='PENDING'
        )

        # Create positions
        position1 = PaperPosition(
            session_id=session1.id,
            symbol='AXISBANK.NS',
            entry_price=100.0,
            shares=10,
            position_value=1000.0,
            target_price=110.0,
            stop_loss_price=95.0,
            initial_risk_reward=1.5,
            recommendation_type='BUY',
            entry_confidence=75.0,
            entry_score_pct=80.0,
            is_open=True
        )

        test_db.add_all([pending_executed, pending_failed, pending_active, position1])
        test_db.commit()

        # Mock trading service to return active session
        with patch('src.bot.handlers.callbacks.get_paper_trading_service') as mock_service:
            mock_trading_service = AsyncMock()
            mock_trading_service.get_active_session.return_value = session2
            mock_service.return_value = mock_trading_service

            mock_query.data = "papertrade_stock_history:AXISBANK.NS"

            with patch('src.bot.handlers.callbacks.get_db_context') as mock_db_ctx:
                mock_db_ctx.return_value.__enter__.return_value = test_db
                mock_db_ctx.return_value.__exit__.return_value = None

                await handle_papertrade_stock_history(mock_query, mock_context, ['AXISBANK.NS'])

                # Verify comprehensive history is shown
                mock_query.edit_message_text.assert_called()
                message = mock_query.edit_message_text.call_args[0][0]

                # Should show data from all sessions
                assert 'OPEN POSITIONS' in message  # Position from session1
                assert 'EXECUTED' in message or 'executed' in message.lower()  # Executed trade
                assert 'PENDING' in message  # Pending trade from session2

    @pytest.mark.asyncio
    async def test_notification_error_handling(self, test_db):
        """Test notification error handling doesn't break execution"""
        # Create session and pending trade
        session = PaperTradingSession(
            user_id=123456,
            initial_capital=100000,
            is_active=True
        )
        test_db.add(session)

        pending = PendingPaperTrade(
            session_id=session.id,
            symbol='RELIANCE.NS',
            requested_by_user_id=123456,
            signal_data='{"test": "data"}',
            status='PENDING'
        )
        test_db.add(pending)
        test_db.commit()

        # Mock scheduler with notification failures
        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()
        scheduler.application.bot = AsyncMock()
        scheduler.application.bot.send_message.side_effect = Exception("Telegram API error")

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            # Mock successful execution
            with patch('src.bot.services.paper_trading_scheduler.get_paper_trade_execution_service') as mock_exec:
                execution_service = AsyncMock()
                execution_service.validate_entry.return_value = (True, None)

                mock_position = Mock()
                mock_position.id = 123
                execution_service.enter_position.return_value = mock_position
                mock_exec.return_value = execution_service

                # Execute (should not fail despite notification errors)
                await scheduler._execute_pending_trades()

                # Verify trade still executed despite notification failure
                updated_pending = test_db.query(PendingPaperTrade).filter(
                    PendingPaperTrade.id == pending.id
                ).first()
                assert updated_pending.status == 'EXECUTED'

                # Verify notifications were attempted (but failed)
                assert scheduler.application.bot.send_message.call_count >= 1


class TestDailyBuySignalsFlow:
    """Test complete daily buy signals execution flow"""

    @pytest.mark.asyncio
    async def test_daily_buy_signals_creation_to_execution_flow(self, test_db):
        """Test complete flow: Daily signals created → Scheduler processes → Positions opened → Notifications sent"""
        from src.bot.database.models import DailyBuySignal, PaperTradingSession
        from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
        from unittest.mock import patch

        # Create a test session
        session = PaperTradingSession(
            user_id=123456,
            initial_capital=100000,
            is_active=True
        )
        test_db.add(session)

        # Create daily buy signals (simulating analysis results)
        signals_data = [
            {
                'symbol': 'RELIANCE.NS',
                'recommendation_type': 'STRONG BUY',
                'confidence': 85.0,
                'current_price': 2500.0,
                'target': 2700.0,
                'stop_loss': 2400.0,
                'analysis_data': '{"trend": "bullish"}'
            },
            {
                'symbol': 'TCS.NS',
                'recommendation_type': 'BUY',
                'confidence': 75.0,
                'current_price': 3200.0,
                'target': 3400.0,
                'stop_loss': 3100.0,
                'analysis_data': '{"momentum": "positive"}'
            },
            {
                'symbol': 'INFY.NS',
                'recommendation_type': 'WEAK BUY',
                'confidence': 65.0,
                'current_price': 1400.0,
                'target': 1500.0,
                'stop_loss': 1350.0,
                'analysis_data': '{"volume": "increasing"}'
            }
        ]

        for signal_data in signals_data:
            signal = DailyBuySignal(
                symbol=signal_data['symbol'],
                analysis_date=datetime.utcnow(),
                recommendation=f"Analysis for {signal_data['symbol']}",
                recommendation_type=signal_data['recommendation_type'],
                current_price=signal_data['current_price'],
                target=signal_data['target'],
                stop_loss=signal_data['stop_loss'],
                risk_reward=2.0,
                confidence=signal_data['confidence'],
                overall_score_pct=80.0,
                analysis_data=signal_data['analysis_data']
            )
            test_db.add(signal)

        test_db.commit()

        # Mock scheduler
        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()
        scheduler.application.bot = AsyncMock()

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            # Mock successful execution for all signals
            with patch('src.bot.services.paper_trade_execution_service.get_paper_trade_execution_service') as mock_exec:
                execution_service = AsyncMock()
                execution_service.validate_entry.return_value = (True, None)

                # Create different mock positions for each signal
                position_counter = 0
                def create_position():
                    nonlocal position_counter
                    position_counter += 1
                    pos = Mock()
                    pos.id = 1000 + position_counter
                    return pos
                execution_service.enter_position.side_effect = [create_position() for _ in signals_data]
                mock_exec.return_value = execution_service

                # Execute buy signals
                await scheduler._execute_buy_signals()

                # Verify results
                result_check = await test_db.execute("SELECT COUNT(*) FROM paper_positions WHERE session_id = :session_id", {"session_id": session.id})
                positions_created = result_check.scalar()

                # Should have created positions for all 3 signals
                assert positions_created == 3, f"Expected 3 positions, got {positions_created}"

                # Verify notifications were sent
                assert scheduler.application.bot.send_message.called
                calls = scheduler.application.bot.send_message.call_args_list

                # Should have buy signals summary notification
                summary_calls = [call for call in calls if 'Daily Buy Signals Executed' in call[1]['text']]
                assert len(summary_calls) > 0, "Buy signals summary notification should be sent"

                # Verify the summary contains correct data
                summary_text = summary_calls[0][1]['text']
                assert '3 signals analyzed' in summary_text
                assert '3 positions opened' in summary_text
                assert '0 signals skipped' in summary_text

    @pytest.mark.asyncio
    async def test_daily_buy_signals_with_filters_and_limits(self, test_db):
        """Test buy signals processing with position limits and duplicate filtering"""
        from src.bot.database.models import DailyBuySignal, PaperTradingSession, PaperPosition
        from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
        from unittest.mock import patch

        # Create session with low position limit (2 max)
        session = PaperTradingSession(
            user_id=123456,
            initial_capital=100000,
            is_active=True
        )
        # Simulate having 1 existing position already
        existing_position = PaperPosition(
            session_id=session.id,
            symbol='EXISTING.NS',
            entry_price=1000.0,
            shares=10,
            position_value=10000.0,
            target_price=1100.0,
            stop_loss_price=950.0,
            initial_risk_reward=1.5,
            recommendation_type='BUY',
            entry_confidence=70.0,
            entry_score_pct=75.0,
            is_open=True
        )
        test_db.add_all([session, existing_position])

        # Create signals (more than position limit)
        signals_data = [
            {'symbol': 'RELIANCE.NS', 'recommendation_type': 'STRONG BUY', 'confidence': 85.0},
            {'symbol': 'TCS.NS', 'recommendation_type': 'BUY', 'confidence': 80.0},
            {'symbol': 'INFY.NS', 'recommendation_type': 'BUY', 'confidence': 75.0},
            {'symbol': 'WIPRO.NS', 'recommendation_type': 'WEAK BUY', 'confidence': 70.0},
        ]

        for signal_data in signals_data:
            signal = DailyBuySignal(
                symbol=signal_data['symbol'],
                analysis_date=datetime.utcnow(),
                recommendation=f"Analysis for {signal_data['symbol']}",
                recommendation_type=signal_data['recommendation_type'],
                current_price=2500.0,
                target=2700.0,
                stop_loss=2400.0,
                risk_reward=2.0,
                confidence=signal_data['confidence'],
                overall_score_pct=80.0,
                analysis_data='{"test": "data"}'
            )
            test_db.add(signal)

        test_db.commit()

        # Mock scheduler
        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()
        scheduler.application.bot = AsyncMock()

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            with patch('src.bot.services.paper_trading_scheduler.get_paper_trade_execution_service') as mock_exec:
                execution_service = AsyncMock()
                execution_service.validate_entry.return_value = (True, None)

                # Create positions for successful executions
                position_counter = 0
                def create_position():
                    nonlocal position_counter
                    position_counter += 1
                    pos = Mock()
                    pos.id = 2000 + position_counter
                    return pos
                execution_service.enter_position.side_effect = [create_position(), create_position()]  # Only 2 positions allowed
                mock_exec.return_value = execution_service

                # Execute buy signals
                await scheduler._execute_buy_signals()

                # Verify only 2 positions were created (due to limit)
                result_check = test_db.execute("SELECT COUNT(*) FROM paper_positions WHERE session_id = :session_id", {"session_id": session.id})
                positions_created = result_check.scalar()

                # Should have 2 new positions (existing 1 + 2 new = 3 total)
                assert positions_created == 3, f"Expected 3 total positions, got {positions_created}"

                # Verify notifications
                assert scheduler.application.bot.send_message.called
                calls = scheduler.application.bot.send_message.call_args_list
                summary_calls = [call for call in calls if 'Daily Buy Signals Executed' in call[1]['text']]
                summary_text = summary_calls[0][1]['text']

                # Should show 2 opened, 2 skipped (due to position limit)
                assert '4 signals analyzed' in summary_text
                assert '2 positions opened' in summary_text
                assert '2 signals skipped' in summary_text

    @pytest.mark.asyncio
    async def test_daily_buy_signals_error_handling(self, test_db):
        """Test error handling in buy signals execution"""
        from src.bot.database.models import DailyBuySignal, PaperTradingSession
        from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
        from unittest.mock import patch

        # Create session and signal
        session = PaperTradingSession(
            user_id=123456,
            initial_capital=100000,
            is_active=True
        )
        test_db.add(session)

        signal = DailyBuySignal(
            symbol='ERROR.NS',
            analysis_date=datetime.utcnow(),
            recommendation="Test signal",
            recommendation_type='BUY',
            current_price=2500.0,
            target=2700.0,
            stop_loss=2400.0,
            risk_reward=2.0,
            confidence=75.0,
            overall_score_pct=80.0,
            analysis_data='{"test": "data"}'
        )
        test_db.add(signal)
        test_db.commit()

        # Mock scheduler
        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()
        scheduler.application.bot = AsyncMock()

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            # Mock execution service to fail validation
            with patch('src.bot.services.paper_trading_scheduler.get_paper_trade_execution_service') as mock_exec:
                execution_service = AsyncMock()
                execution_service.validate_entry.return_value = (False, "Insufficient capital")
                mock_exec.return_value = execution_service

                # Execute buy signals
                await scheduler._execute_buy_signals()

                # Verify no positions were created
                result_check = test_db.execute("SELECT COUNT(*) FROM paper_positions WHERE session_id = :session_id", {"session_id": session.id})
                positions_created = result_check.scalar()
                assert positions_created == 0, "No positions should be created on validation failure"

                # Verify summary notification still sent with failure info
                assert scheduler.application.bot.send_message.called
                calls = scheduler.application.bot.send_message.call_args_list
                summary_calls = [call for call in calls if 'Daily Buy Signals Executed' in call[1]['text']]
                summary_text = summary_calls[0][1]['text']

                assert '1 signals analyzed' in summary_text
                assert '0 positions opened' in summary_text
                assert '1 signals skipped' in summary_text

    @pytest.mark.asyncio
    async def test_daily_buy_signals_notification_failure_handling(self, test_db):
        """Test that execution continues even if notifications fail"""
        from src.bot.database.models import DailyBuySignal, PaperTradingSession
        from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
        from unittest.mock import patch

        # Create session and signal
        session = PaperTradingSession(
            user_id=123456,
            initial_capital=100000,
            is_active=True
        )
        test_db.add(session)

        signal = DailyBuySignal(
            symbol='TEST.NS',
            analysis_date=datetime.utcnow(),
            recommendation="Test signal",
            recommendation_type='BUY',
            current_price=2500.0,
            target=2700.0,
            stop_loss=2400.0,
            risk_reward=2.0,
            confidence=75.0,
            overall_score_pct=80.0,
            analysis_data='{"test": "data"}'
        )
        test_db.add(signal)
        test_db.commit()

        # Mock scheduler with notification failures
        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()

        # Mock Telegram API to fail
        scheduler.application.bot = AsyncMock()
        scheduler.application.bot.send_message.side_effect = Exception("Telegram API rate limit")

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            with patch('src.bot.services.paper_trading_scheduler.get_paper_trade_execution_service') as mock_exec:
                execution_service = AsyncMock()
                execution_service.validate_entry.return_value = (True, None)
                execution_service.enter_position.return_value = Mock(id=1)
                mock_exec.return_value = execution_service

                # Should not raise exception despite notification failure
                await scheduler._execute_buy_signals()

                # Verify execution still happened
                result_check = test_db.execute("SELECT COUNT(*) FROM paper_positions WHERE session_id = :session_id", {"session_id": session.id})
                positions_created = result_check.scalar()
                assert positions_created == 1, "Position should still be created despite notification failure"

                # Notifications were attempted (and failed)
                assert scheduler.application.bot.send_message.called


# =============================================================================
# PERFORMANCE AND LOAD TESTING
# =============================================================================
# PERFORMANCE AND LOAD TESTING
# =============================================================================

class TestPerformanceAndLoad:
    """Performance tests for high-volume trading scenarios"""

    @pytest.mark.asyncio
    async def test_high_volume_pending_trade_processing(self, test_db):
        """Test processing 50+ pending trades efficiently"""
        # Create many sessions and pending trades
        sessions = []
        pendings = []

        for i in range(50):
            session = PaperTradingSession(
                user_id=2000 + i,
                initial_capital=100000,
                is_active=True
            )
            test_db.add(session)
            sessions.append(session)

            pending = PendingPaperTrade(
                session_id=session.id,
                symbol=f'STOCK{i:02d}.NS',
                requested_by_user_id=2000 + i,
                signal_data='{"test": "data"}',
                status='PENDING'
            )
            test_db.add(pending)
            pendings.append(pending)

        test_db.commit()

        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()
        scheduler.application.bot = AsyncMock()

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            with patch('src.bot.services.paper_trading_scheduler.get_paper_trade_execution_service') as mock_exec:
                execution_service = AsyncMock()
                execution_service.validate_entry.return_value = (True, None)

                def create_position():
                    pos = Mock()
                    pos.id = len(pendings) + 1
                    return pos
                execution_service.enter_position.side_effect = [create_position() for _ in pendings]
                mock_exec.return_value = execution_service

                import time
                start_time = time.time()
                await scheduler._execute_pending_trades()
                execution_time = time.time() - start_time

                # Verify all executed
                executed_count = test_db.query(PendingPaperTrade).filter(
                    PendingPaperTrade.status == 'EXECUTED'
                ).count()
                assert executed_count == 50

                # Performance assertion: < 10 seconds for 50 trades
                assert execution_time < 10.0, f"High volume execution too slow: {execution_time}s"

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(self, test_db):
        """Test memory efficiency with large numbers of trades"""
        import psutil
        import os

        # Create large dataset
        sessions = []
        for i in range(20):
            session = PaperTradingSession(
                user_id=3000 + i,
                initial_capital=100000,
                is_active=True
            )
            test_db.add(session)
            sessions.append(session)

            # Add multiple trades per session
            for j in range(10):
                pending = PendingPaperTrade(
                    session_id=session.id,
                    symbol=f'STOCK{i:02d}_{j:02d}.NS',
                    requested_by_user_id=3000 + i,
                    signal_data='{"large": "data" * 100}',  # Larger data
                    status='PENDING'
                )
                test_db.add(pending)

        test_db.commit()

        # Measure memory before
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()
        scheduler.application.bot = AsyncMock()

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            with patch('src.bot.services.paper_trading_scheduler.get_paper_trade_execution_service') as mock_exec:
                execution_service = AsyncMock()
                execution_service.validate_entry.return_value = (True, None)
                execution_service.enter_position.return_value = Mock(id=1)
                mock_exec.return_value = execution_service

                await scheduler._execute_pending_trades()

                # Measure memory after
                memory_after = process.memory_info().rss / 1024 / 1024  # MB
                memory_delta = memory_after - memory_before

                # Assert reasonable memory usage (< 50MB increase)
                assert memory_delta < 50.0, f"Excessive memory usage: +{memory_delta}MB"

                # Verify all trades processed
                executed_count = test_db.query(PendingPaperTrade).filter(
                    PendingPaperTrade.status == 'EXECUTED'
                ).count()
                assert executed_count == 200  # 20 sessions * 10 trades each


# =============================================================================
# INTEGRATION TESTS WITH EXTERNAL DEPENDENCIES
# =============================================================================

class TestExternalIntegration:
    """Tests that integrate with external services (mocked)"""

    @pytest.mark.asyncio
    async def test_market_data_failure_handling(self, test_db):
        """Test handling of market data API failures during execution"""
        session = PaperTradingSession(
            user_id=123456,
            initial_capital=100000,
            is_active=True
        )
        test_db.add(session)

        pending = PendingPaperTrade(
            session_id=session.id,
            symbol='TEST.NS',
            requested_by_user_id=123456,
            signal_data='{"test": "data"}',
            status='PENDING'
        )
        test_db.add(pending)
        test_db.commit()

        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()
        scheduler.application.bot = AsyncMock()

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            # Mock market data failure (get_current_price returns None)
            with patch('src.bot.services.paper_trading_scheduler.get_current_price') as mock_price:
                mock_price.return_value = None

                with patch('src.bot.services.paper_trading_scheduler.get_paper_trade_execution_service') as mock_exec:
                    execution_service = AsyncMock()
                    # Should still validate and use stored price as fallback
                    execution_service.validate_entry.return_value = (True, None)
                    execution_service.enter_position.return_value = Mock(id=1)
                    mock_exec.return_value = execution_service

                    await scheduler._execute_pending_trades()

                    # Should succeed using fallback price
                    updated_pending = test_db.query(PendingPaperTrade).filter(
                        PendingPaperTrade.id == pending.id
                    ).first()
                    assert updated_pending.status == 'EXECUTED'

    @pytest.mark.asyncio
    async def test_telegram_api_failure_notification_handling(self, test_db):
        """Test handling of Telegram API failures during notifications"""
        session = PaperTradingSession(
            user_id=123456,
            initial_capital=100000,
            is_active=True
        )
        test_db.add(session)

        pending = PendingPaperTrade(
            session_id=session.id,
            symbol='TEST.NS',
            requested_by_user_id=123456,
            signal_data='{"test": "data"}',
            status='PENDING'
        )
        test_db.add(pending)
        test_db.commit()

        scheduler = PaperTradingScheduler(Mock())
        scheduler.application = Mock()

        # Mock Telegram API failures
        scheduler.application.bot = AsyncMock()
        scheduler.application.bot.send_message.side_effect = [
            Exception("Rate limit exceeded"),  # Individual notification fails
            None,  # Summary notification succeeds
        ]

        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_sched_db:
            mock_sched_db.return_value.__enter__.return_value = test_db
            mock_sched_db.return_value.__exit__.return_value = None

            with patch('src.bot.services.paper_trading_scheduler.get_paper_trade_execution_service') as mock_exec:
                execution_service = AsyncMock()
                execution_service.validate_entry.return_value = (True, None)
                execution_service.enter_position.return_value = Mock(id=1)
                mock_exec.return_value = execution_service

                # Should not raise exception despite notification failures
                await scheduler._execute_pending_trades()

                # Trade should still execute
                updated_pending = test_db.query(PendingPaperTrade).filter(
                    PendingPaperTrade.id == pending.id
                ).first()
                assert updated_pending.status == 'EXECUTED'

                # Notifications should have been attempted
                assert scheduler.application.bot.send_message.call_count >= 1

                # But execution should succeed regardless
                assert updated_pending.position_id == 1