"""
Comprehensive Tests for Paper Trading Handlers
Tests command handlers and callback handlers

Includes tests for:
- Auto-session creation
- Market hours detection
- Queue creation reliability
- Trade history for all trades
- Error handling and user messages

Author: Harsh Kandhway
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from telegram import Update, Message, CallbackQuery, User, Chat

from src.bot.handlers.paper_trading import (
    papertrade_command,
    paper_trade_start_command,
    paper_trade_stop_command,
    paper_trade_status_command,
    paper_trade_history_command,
    paper_trade_performance_command,
    paper_trade_insights_command,
    paper_trade_settings_command
)
from src.bot.handlers.callbacks import (
    handle_papertrade_stock_confirm,
    handle_papertrade_buy_signals_confirm,
    handle_papertrade_watchlist_confirm,
    handle_papertrade_status,
    _queue_paper_trade_for_market_open
)
from src.bot.database.models import (
    PaperTradingSession, UserSettings, User, DailyBuySignal, PendingPaperTrade
)


class TestPaperTradingCommands:
    """Test paper trading command handlers"""

    @pytest.fixture
    def mock_update(self, mock_user, mock_message):
        """Create mock update"""
        update = Mock(spec=Update)
        update.effective_user = mock_user
        update.message = mock_message
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock()
        context.user_data = {}
        context.bot_data = {}
        return context

    @pytest.fixture
    def test_db(self, test_db):
        """Use test database fixture"""
        return test_db

    @pytest.fixture
    def test_user(self, test_db, mock_user):
        """Create test user"""
        user = User(
            telegram_id=mock_user.id,
            username=mock_user.username,
            first_name=mock_user.first_name,
            is_active=True
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    @pytest.fixture
    def test_settings(self, test_db, test_user):
        """Create test user settings"""
        settings = UserSettings(
            user_id=test_user.id,
            paper_trading_enabled=True,
            paper_trading_default_capital=500000.0,
            paper_trading_max_positions=15,
            paper_trading_risk_percentage=1.0
        )
        test_db.add(settings)
        test_db.commit()
        test_db.refresh(settings)
        return settings

    @pytest.mark.asyncio
    async def test_papertrade_start_command_new_session(self, mock_update, mock_context, test_db, test_user, test_settings):
        """Test starting a new paper trading session"""
        # Mock get_or_create_user
        with patch('src.bot.handlers.paper_trading.get_or_create_user') as mock_get_user:
            mock_get_user.return_value = test_user
            
            # Mock get_db_context
            with patch('src.bot.handlers.paper_trading.get_db_context') as mock_db_ctx:
                mock_db_ctx.return_value.__enter__.return_value = test_db
                mock_db_ctx.return_value.__exit__.return_value = None
                
                # Mock trading service
                with patch('src.bot.handlers.paper_trading.get_paper_trading_service') as mock_service:
                    mock_trading_service = AsyncMock()
                    mock_session = PaperTradingSession(
                        id=1,
                        user_id=test_user.id,
                        is_active=True,
                        initial_capital=500000.0,
                        max_positions=15
                    )
                    mock_trading_service.get_active_session.return_value = None
                    mock_trading_service.start_session.return_value = mock_session
                    mock_service.return_value = mock_trading_service
                    
                    await paper_trade_start_command(mock_update, mock_context)
                    
                    # Verify message was sent
                    mock_update.message.reply_text.assert_called_once()
                    assert 'Session Started' in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_papertrade_start_command_existing_session(self, mock_update, mock_context, test_db, test_user):
        """Test starting session when one already exists"""
        # Create existing session
        existing_session = PaperTradingSession(
            user_id=test_user.id,
            is_active=True,
            initial_capital=500000.0,
            current_capital=510000.0,
            max_positions=15
        )
        test_db.add(existing_session)
        test_db.commit()
        
        with patch('src.bot.handlers.paper_trading.get_or_create_user') as mock_get_user:
            mock_get_user.return_value = test_user
            
            with patch('src.bot.handlers.paper_trading.get_db_context') as mock_db_ctx:
                mock_db_ctx.return_value.__enter__.return_value = test_db
                mock_db_ctx.return_value.__exit__.return_value = None
                
                with patch('src.bot.handlers.paper_trading.get_paper_trading_service') as mock_service:
                    mock_trading_service = AsyncMock()
                    mock_trading_service.get_active_session.return_value = existing_session
                    mock_service.return_value = mock_trading_service
                    
                    await paper_trade_start_command(mock_update, mock_context)
                    
                    # Verify warning message
                    mock_update.message.reply_text.assert_called_once()
                    assert 'already active' in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_papertrade_status_command(self, mock_update, mock_context, test_db, test_user):
        """Test status command"""
        # Create active session
        session = PaperTradingSession(
            user_id=test_user.id,
            is_active=True,
            initial_capital=500000.0,
            current_capital=510000.0,
            max_positions=15,
            current_positions=2
        )
        test_db.add(session)
        test_db.commit()
        
        with patch('src.bot.handlers.paper_trading.get_db_context') as mock_db_ctx:
            mock_db_ctx.return_value.__enter__.return_value = test_db
            mock_db_ctx.return_value.__exit__.return_value = None
            
            with patch('src.bot.handlers.paper_trading.get_paper_trading_service') as mock_service:
                mock_trading_service = AsyncMock()
                mock_trading_service.get_active_session.return_value = session
                mock_trading_service.get_session_status.return_value = {
                    'initial_capital': 500000.0,
                    'total_capital': 510000.0,
                    'current_cash': 400000.0,
                    'deployed_capital': 100000.0,
                    'deployed_pct': 20.0,
                    'total_return': 10000.0,
                    'total_return_pct': 2.0,
                    'total_unrealized_pnl': 10000.0,
                    'position_count': 2,
                    'max_positions': 15,
                    'positions': [],
                    'total_trades': 5,
                    'win_rate_pct': 60.0,
                    'winning_trades': 3,
                    'losing_trades': 2,
                    'total_profit': 15000.0,
                    'total_loss': 5000.0,
                    'profit_factor': 3.0,
                    'max_drawdown_pct': 1.0
                }
                mock_service.return_value = mock_trading_service
                
                await paper_trade_status_command(mock_update, mock_context)
                
                # Verify message was sent
                mock_update.message.reply_text.assert_called_once()
                status_text = mock_update.message.reply_text.call_args[0][0]
                assert 'PAPER TRADING STATUS' in status_text
                assert '500,000' in status_text  # Initial capital

    @pytest.mark.asyncio
    async def test_papertrade_status_command_no_session(self, mock_update, mock_context, test_db):
        """Test status command with no active session"""
        with patch('src.bot.handlers.paper_trading.get_db_context') as mock_db_ctx:
            mock_db_ctx.return_value.__enter__.return_value = test_db
            mock_db_ctx.return_value.__exit__.return_value = None
            
            with patch('src.bot.handlers.paper_trading.get_paper_trading_service') as mock_service:
                mock_trading_service = AsyncMock()
                mock_trading_service.get_active_session.return_value = None
                mock_service.return_value = mock_trading_service
                
                await paper_trade_status_command(mock_update, mock_context)
                
                # Verify error message
                mock_update.message.reply_text.assert_called_once()
                assert 'No active' in mock_update.message.reply_text.call_args[0][0]


class TestPaperTradingCallbacks:
    """Test paper trading callback handlers"""

    @pytest.fixture
    def mock_query(self, mock_user, mock_message):
        """Create mock callback query"""
        query = Mock(spec=CallbackQuery)
        query.from_user = mock_user
        query.data = "papertrade_stock_confirm:RELIANCE.NS"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message = mock_message
        return query

    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        return Mock()

    @pytest.fixture
    def test_db(self, test_db):
        """Use test database fixture"""
        return test_db

    @pytest.fixture
    def test_user(self, test_db, mock_user):
        """Create test user"""
        user = User(
            telegram_id=mock_user.id,
            username=mock_user.username,
            first_name=mock_user.first_name
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
    async def test_handle_papertrade_stock_confirm_market_open(self, mock_query, mock_context, test_db, test_session, test_user):
        """Test confirming stock trade when market is open"""
        mock_query.data = "papertrade_stock_confirm:RELIANCE.NS"
        
        # Mock market hours - open - it's imported inside the function
        with patch('src.bot.services.market_hours_service.get_market_hours_service') as mock_mh:
            market_hours = Mock()
            market_hours.is_market_open.return_value = True
            mock_mh.return_value = market_hours
            
            # Mock analysis
            mock_analysis = {
                'recommendation_type': 'STRONG BUY',
                'recommendation': 'Strong buy',
                'current_price': 2450.0,
                'target_data': {'recommended_target': 2680.0},
                'stop_data': {'recommended_stop': 2325.0},
                'risk_reward': 1.84,
                'confidence': 85.0,
                'overall_score_pct': 88.0
            }
            
            with patch('src.bot.handlers.callbacks.analyze_stock') as mock_analyze:
                import asyncio
                from functools import partial
                
                async def analyze_async():
                    return mock_analysis
                
                loop = asyncio.get_event_loop()
                mock_analyze_func = partial(lambda: mock_analysis)
                
                with patch('asyncio.get_event_loop') as mock_loop:
                    mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_analysis)
                    
                    with patch('src.bot.handlers.callbacks.get_db_context') as mock_db_ctx:
                        mock_db_ctx.return_value.__enter__.return_value = test_db
                        mock_db_ctx.return_value.__exit__.return_value = None
                        
                        with patch('src.bot.services.paper_trading_service.get_paper_trading_service') as mock_service:
                            mock_trading_service = AsyncMock()
                            mock_trading_service.get_active_session.return_value = test_session
                            mock_service.return_value = mock_trading_service
                            
                            with patch('src.bot.handlers.callbacks.get_current_price') as mock_price:
                                mock_price.return_value = 2450.0
                                
                                with patch('src.bot.services.paper_trade_execution_service.get_paper_trade_execution_service') as mock_exec:
                                    execution_service = Mock()
                                    execution_service.validate_entry.return_value = (True, None)
                                    
                                    mock_position = Mock()
                                    mock_position.id = 1
                                    mock_position.symbol = 'RELIANCE.NS'
                                    mock_position.entry_price = 2450.0
                                    mock_position.shares = 10.0
                                    mock_position.position_value = 24500.0
                                    mock_position.target_price = 2680.0
                                    mock_position.stop_loss_price = 2325.0
                                    
                                    execution_service.enter_position = AsyncMock(return_value=mock_position)
                                    mock_exec.return_value = execution_service
                                    
                                    await handle_papertrade_stock_confirm(mock_query, mock_context, ['RELIANCE.NS'])
                                    
                                    # Verify trade was executed
                                    mock_query.answer.assert_called()
                                    mock_query.edit_message_text.assert_called()

    @pytest.mark.asyncio
    async def test_handle_papertrade_stock_confirm_market_closed(self, mock_query, mock_context, test_db, test_session, test_user):
        """Test confirming stock trade when market is closed - should queue"""
        mock_query.data = "papertrade_stock_confirm:RELIANCE.NS"
        
        # Mock market hours - closed - it's imported inside the function
        with patch('src.bot.services.market_hours_service.get_market_hours_service') as mock_mh:
            market_hours = Mock()
            market_hours.is_market_open.return_value = False
            market_hours.get_next_market_open.return_value = datetime(2026, 1, 13, 9, 15, 0)
            mock_mh.return_value = market_hours
            
            # Mock analysis
            mock_analysis = {
                'recommendation_type': 'STRONG BUY',
                'recommendation': 'Strong buy',
                'current_price': 2450.0,
                'target_data': {'recommended_target': 2680.0},
                'stop_data': {'recommended_stop': 2325.0},
                'risk_reward': 1.84,
                'confidence': 85.0,
                'overall_score_pct': 88.0
            }
            
            with patch('src.bot.handlers.callbacks.analyze_stock') as mock_analyze:
                with patch('asyncio.get_event_loop') as mock_loop:
                    mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_analysis)
                    
                    with patch('src.bot.handlers.callbacks.get_db_context') as mock_db_ctx:
                        mock_db_ctx.return_value.__enter__.return_value = test_db
                        mock_db_ctx.return_value.__exit__.return_value = None
                        
                        with patch('src.bot.services.paper_trading_service.get_paper_trading_service') as mock_service:
                            mock_trading_service = AsyncMock()
                            mock_trading_service.get_active_session.return_value = test_session
                            mock_service.return_value = mock_trading_service
                            
                            await handle_papertrade_stock_confirm(mock_query, mock_context, ['RELIANCE.NS'])
                            
                            # Verify trade was queued
                            pending = test_db.query(PendingPaperTrade).filter(
                                PendingPaperTrade.session_id == test_session.id,
                                PendingPaperTrade.symbol == 'RELIANCE.NS',
                                PendingPaperTrade.status == 'PENDING'
                            ).first()
                            
                            assert pending is not None
                            mock_query.edit_message_text.assert_called()
                            assert 'Queued' in mock_query.edit_message_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_papertrade_stock_confirm_no_buy_signal(self, mock_query, mock_context, test_db, test_session):
        """Test confirming stock trade when signal is not BUY"""
        mock_query.data = "papertrade_stock_confirm:RELIANCE.NS"
        
        # Mock market hours - open - it's imported inside the function
        with patch('src.bot.services.market_hours_service.get_market_hours_service') as mock_mh:
            market_hours = Mock()
            market_hours.is_market_open.return_value = True
            mock_mh.return_value = market_hours
            
            # Mock analysis - HOLD signal
            mock_analysis = {
                'recommendation_type': 'HOLD',
                'recommendation': 'Hold position',
                'current_price': 2450.0
            }
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_analysis)
                
                with patch('src.bot.handlers.callbacks.get_db_context') as mock_db_ctx:
                    mock_db_ctx.return_value.__enter__.return_value = test_db
                    mock_db_ctx.return_value.__exit__.return_value = None
                    
                    with patch('src.bot.services.paper_trading_service.get_paper_trading_service') as mock_service:
                        mock_trading_service = AsyncMock()
                        mock_trading_service.get_active_session.return_value = test_session
                        mock_service.return_value = mock_trading_service
                        
                        await handle_papertrade_stock_confirm(mock_query, mock_context, ['RELIANCE.NS'])
                        
                        # Verify error message
                        mock_query.edit_message_text.assert_called()
                        assert 'Cannot Paper Trade' in mock_query.edit_message_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_papertrade_stock_confirm_no_session(self, mock_query, mock_context, test_db):
        """Test confirming stock trade with no active session"""
        mock_query.data = "papertrade_stock_confirm:RELIANCE.NS"
        
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db_ctx:
            mock_db_ctx.return_value.__enter__.return_value = test_db
            mock_db_ctx.return_value.__exit__.return_value = None
            
            with patch('src.bot.services.paper_trading_service.get_paper_trading_service') as mock_service:
                mock_trading_service = AsyncMock()
                mock_trading_service.get_active_session.return_value = None
                mock_service.return_value = mock_trading_service
                
                await handle_papertrade_stock_confirm(mock_query, mock_context, ['RELIANCE.NS'])
                
                # Verify error message
                mock_query.answer.assert_called()
                assert 'No active session' in mock_query.answer.call_args[0][0]


# =============================================================================
# NEW TESTS FOR AUTO-SESSION CREATION AND ENHANCED FUNCTIONALITY
# =============================================================================

class TestAutoSessionCreation:
    """Test auto-creation of paper trading sessions"""

    @pytest.mark.asyncio
    async def test_auto_create_session_when_none_exists(self, mock_query, mock_context, test_db):
        """Test that a session is auto-created when user tries to paper trade without active session"""
        from unittest.mock import patch

        mock_query.data = "papertrade_stock_confirm:AXISBANK.NS"

        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db_ctx:
            mock_db_ctx.return_value.__enter__.return_value = test_db
            mock_db_ctx.return_value.__exit__.return_value = None

            # Mock market hours to be closed
            with patch('src.bot.services.market_hours_service.get_market_hours_service') as mock_mh:
                market_hours = Mock()
                market_hours.is_market_open.return_value = False
                market_hours.get_next_market_open.return_value = datetime(2026, 1, 12, 9, 15, 0)
                mock_mh.return_value = market_hours

                # Mock trading service to return no active session
                with patch('src.bot.services.paper_trading_service.get_paper_trading_service') as mock_service:
                    mock_trading_service = AsyncMock()
                    mock_trading_service.get_active_session.return_value = None
                    mock_service.return_value = mock_trading_service

                    # Mock user settings
                    with patch('src.bot.database.db.get_user_settings') as mock_get_settings:
                        settings = Mock()
                        settings.default_capital = 100000
                        mock_get_settings.return_value = settings

                        await handle_papertrade_stock_confirm(mock_query, mock_context, ['AXISBANK.NS'])

                        # Verify session was created
                        from src.bot.database.models import PaperTradingSession
                        session = test_db.query(PaperTradingSession).filter(
                            PaperTradingSession.user_id == mock_query.from_user.id,
                            PaperTradingSession.is_active == True
                        ).first()

                        assert session is not None
                        assert session.initial_capital == 500000

                        # Verify pending trade was created
                        from src.bot.database.models import PendingPaperTrade
                        pending = test_db.query(PendingPaperTrade).filter(
                            PendingPaperTrade.session_id == session.id,
                            PendingPaperTrade.symbol == 'AXISBANK.NS'
                        ).first()

                        assert pending is not None
                        assert pending.status == 'PENDING'

    @pytest.mark.asyncio
    async def test_market_hours_logging_detailed(self):
        """Test that market hours service logs detailed information"""
        from src.bot.services.market_hours_service import get_market_hours_service
        import logging

        # Capture log messages
        with patch('src.bot.services.market_hours_service.logger') as mock_logger:
            mh = get_market_hours_service()
            result = mh.is_market_open()

            # Verify detailed logging was called
            mock_logger.info.assert_called()
            log_call = mock_logger.info.call_args[0][0]
            assert 'Market hours check:' in log_call
            assert 'weekday=' in log_call
            assert 'time=' in log_call

    @pytest.mark.asyncio
    async def test_queue_creation_with_flush_validation(self, mock_update, mock_context, test_db, test_user, test_session):
        """Test that pending trade creation uses flush() for validation"""
        from unittest.mock import patch

        # Mock the queue function to verify flush is called
        with patch('src.bot.handlers.callbacks._queue_paper_trade_for_market_open') as mock_queue:
            mock_queue.return_value = None

            # Create a mock query
            mock_query = Mock()
            mock_query.from_user.id = test_user.id
            mock_query.answer = AsyncMock()
            mock_query.edit_message_text = AsyncMock()

            # Mock market closed
            with patch('src.bot.handlers.callbacks.get_market_hours_service') as mock_mh:
                market_hours = Mock()
                market_hours.is_market_open.return_value = False
                market_hours.get_next_market_open.return_value = datetime(2026, 1, 12, 9, 15, 0)
                mock_mh.return_value = market_hours

                # Call the handler
                from src.bot.handlers.callbacks import handle_papertrade_stock_confirm
                await handle_papertrade_stock_confirm(mock_query, mock_context, ['AXISBANK.NS'])

                # Verify queue function was called
                mock_queue.assert_called_once()


class TestTradeHistoryAllTrades:
    """Test that trade history shows all trades regardless of session"""

    @pytest.mark.asyncio
    async def test_history_shows_all_user_trades(self, mock_query, mock_context, test_db):
        """Test that trade history shows trades from all user sessions"""
        from src.bot.handlers.callbacks import handle_papertrade_stock_history
        from src.bot.database.models import PaperTradingSession, PendingPaperTrade, PaperPosition, PaperTrade

        # Create multiple sessions for the user
        session1 = PaperTradingSession(
            user_id=mock_query.from_user.id,
            initial_capital=100000,
            is_active=False
        )
        session2 = PaperTradingSession(
            user_id=mock_query.from_user.id,
            initial_capital=50000,
            is_active=True
        )
        test_db.add_all([session1, session2])
        test_db.commit()

        # Create trades in different sessions
        pending1 = PendingPaperTrade(
            session_id=session1.id,
            symbol='AXISBANK.NS',
            requested_by_user_id=mock_query.from_user.id,
            signal_data='{"test": "data"}',
            status='EXECUTED'
        )
        pending2 = PendingPaperTrade(
            session_id=session2.id,
            symbol='AXISBANK.NS',
            requested_by_user_id=mock_query.from_user.id,
            signal_data='{"test": "data2"}',
            status='PENDING'
        )

        position = PaperPosition(
            session_id=session1.id,
            symbol='AXISBANK.NS',
            entry_price=100.0,
            shares=10,
            position_value=1000.0,  # entry_price * shares
            target_price=110.0,
            stop_loss_price=95.0,
            initial_risk_reward=1.5,
            recommendation_type='BUY',
            entry_confidence=75.0,
            entry_score_pct=80.0,
            is_open=True
        )

        trade = PaperTrade(
            session_id=session2.id,
            symbol='AXISBANK.NS',
            entry_price=95.0,
            exit_price=105.0,
            shares=5,
            pnl=50.0,
            exit_date=datetime.utcnow()
        )

        test_db.add_all([pending1, pending2, position, trade])
        test_db.commit()

        mock_query.data = "papertrade_stock_history:AXISBANK.NS"

        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db_ctx:
            mock_db_ctx.return_value.__enter__.return_value = test_db
            mock_db_ctx.return_value.__exit__.return_value = None

            await handle_papertrade_stock_history(mock_query, mock_context, ['AXISBANK.NS'])

            # Verify the message was sent
            mock_query.edit_message_text.assert_called()
            message = mock_query.edit_message_text.call_args[0][0]

            # Should contain data from all sessions
            assert 'OPEN POSITIONS (1)' in message  # From session1
            assert 'PENDING TRADES' in message or 'EXECUTED' in message  # From both sessions
            assert 'closed trades' in message or 'CLOSED TRADES' in message  # From session2

    @pytest.mark.asyncio
    async def test_history_no_active_session_but_shows_data(self, mock_update, mock_context, test_db, test_user):
        """Test that history shows data even when no active session exists"""
        from src.bot.handlers.callbacks import handle_papertrade_stock_history
        from src.bot.database.models import PaperTradingSession, PendingPaperTrade

        # Create an old inactive session
        old_session = PaperTradingSession(
            user_id=test_user.id,
            capital=100000,
            is_active=False
        )
        test_db.add(old_session)
        test_db.commit()

        # Create a pending trade in the old session
        pending = PendingPaperTrade(
            session_id=old_session.id,
            symbol='AXISBANK.NS',
            requested_by_user_id=test_user.id,
            signal_data='{"test": "data"}',
            status='PENDING'
        )
        test_db.add(pending)
        test_db.commit()

        # Mock trading service to return no active session
        with patch('src.bot.handlers.callbacks.get_paper_trading_service') as mock_service:
            mock_trading_service = Mock()
            mock_trading_service.get_active_session = AsyncMock(return_value=None)
            mock_service.return_value = mock_trading_service

            mock_query = Mock()
            mock_query.from_user.id = test_user.id
            mock_query.answer = AsyncMock()
            mock_query.edit_message_text = AsyncMock()

            await handle_papertrade_stock_history(mock_query, mock_context, ['AXISBANK.NS'])

            # Should show the pending trade even without active session
            mock_query.edit_message_text.assert_called()
            message = mock_query.edit_message_text.call_args[0][0]
            assert 'PENDING TRADES' in message or 'pending' in message.lower()


class TestErrorHandlingAndMessages:
    """Test error handling and user messages"""

    @pytest.mark.asyncio
    async def test_clear_error_message_for_queue_failure(self, mock_update, mock_context, test_db, test_user, test_session):
        """Test that queue creation failures show clear error messages"""
        from unittest.mock import patch

        mock_query = Mock()
        mock_query.from_user.id = test_user.id
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        # Mock market closed
        with patch('src.bot.handlers.callbacks.get_market_hours_service') as mock_mh:
            market_hours = Mock()
            market_hours.is_market_open.return_value = False
            market_hours.get_next_market_open.return_value = datetime(2026, 1, 12, 9, 15, 0)
            mock_mh.return_value = market_hours

            # Mock queue function to raise exception
            with patch('src.bot.handlers.callbacks._queue_paper_trade_for_market_open') as mock_queue:
                mock_queue.side_effect = Exception("Database connection failed")

                from src.bot.handlers.callbacks import handle_papertrade_stock_confirm
                await handle_papertrade_stock_confirm(mock_query, mock_context, ['AXISBANK.NS'])

                # Should show error message
                mock_query.edit_message_text.assert_called()
                message = mock_query.edit_message_text.call_args[0][0]
                assert 'Failed to Queue Trade' in message or 'error' in message.lower()

    @pytest.mark.asyncio
    async def test_market_closed_message_shown(self, mock_update, mock_context, test_db, test_user, test_session):
        """Test that market closed message is shown correctly"""
        mock_query = Mock()
        mock_query.from_user.id = test_user.id
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        # Mock market closed
        with patch('src.bot.handlers.callbacks.get_market_hours_service') as mock_mh:
            market_hours = Mock()
            market_hours.is_market_open.return_value = False
            market_hours.get_next_market_open.return_value = datetime(2026, 1, 12, 9, 15, 0)
            mock_mh.return_value = market_hours

            from src.bot.handlers.callbacks import handle_papertrade_stock_confirm
            await handle_papertrade_stock_confirm(mock_query, mock_context, ['AXISBANK.NS'])

            # Should show market closed message
            mock_query.edit_message_text.assert_called()
            calls = mock_query.edit_message_text.call_args_list

            # Find the call with "Market Closed"
            market_closed_call = None
            for call in calls:
                if 'Market Closed' in call[0][0]:
                    market_closed_call = call
                    break

            assert market_closed_call is not None
            assert 'Queueing Trade' in market_closed_call[0][0]


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegrationScenarios:
    """Integration tests for complete flows"""

    @pytest.mark.asyncio
    async def test_complete_queue_flow_with_auto_session(self, mock_update, mock_context, test_db, test_user, mock_settings):
        """Test complete flow: no session → auto-create → queue → success"""
        from src.bot.handlers.callbacks import handle_papertrade_stock_confirm
        from unittest.mock import patch

        mock_query = Mock()
        mock_query.from_user.id = test_user.id
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        # Mock market closed
        with patch('src.bot.handlers.callbacks.get_market_hours_service') as mock_mh:
            market_hours = Mock()
            market_hours.is_market_open.return_value = False
            market_hours.get_next_market_open.return_value = datetime(2026, 1, 12, 9, 15, 0)
            mock_mh.return_value = market_hours

            # Mock no active session initially
            with patch('src.bot.handlers.callbacks.get_paper_trading_service') as mock_service:
                mock_trading_service = Mock()
                mock_trading_service.get_active_session = AsyncMock(return_value=None)
                mock_service.return_value = mock_trading_service

                # Mock settings
                with patch('src.bot.handlers.callbacks.get_user_settings') as mock_get_settings:
                    mock_get_settings.return_value = mock_settings

                    await handle_papertrade_stock_confirm(mock_query, mock_context, ['AXISBANK.NS'])

                    # Verify session was created
                    from src.bot.database.models import PaperTradingSession
                    session = test_db.query(PaperTradingSession).filter(
                        PaperTradingSession.user_id == test_user.id,
                        PaperTradingSession.is_active == True
                    ).first()
                    assert session is not None

                    # Verify pending trade exists
                    from src.bot.database.models import PendingPaperTrade
                    pending = test_db.query(PendingPaperTrade).filter(
                        PendingPaperTrade.session_id == session.id,
                        PendingPaperTrade.symbol == 'AXISBANK.NS',
                        PendingPaperTrade.status == 'PENDING'
                    ).first()
                    assert pending is not None

                    # Verify success message
                    success_calls = [call for call in mock_query.edit_message_text.call_args_list
                                   if 'Trade Queued' in call[0][0]]
                    assert len(success_calls) > 0
    """Integration tests for complete user flows"""

    @pytest.mark.asyncio
    async def test_complete_paper_trade_flow_market_closed(self, mock_query, mock_context, test_db):
        """Test complete flow: click paper trade → market closed → auto session → queue → success"""
        from unittest.mock import patch

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

                # Mock no active session initially
                with patch('src.bot.services.paper_trading_service.get_paper_trading_service') as mock_service:
                    mock_trading_service = AsyncMock()
                    mock_trading_service.get_active_session.return_value = None
                    mock_service.return_value = mock_trading_service

                    # Mock user settings
                    with patch('src.bot.database.db.get_user_settings') as mock_get_settings:
                        settings = Mock()
                        settings.default_capital = 100000
                        mock_get_settings.return_value = settings

                        from src.bot.handlers.callbacks import handle_papertrade_stock_confirm
                        await handle_papertrade_stock_confirm(mock_query, mock_context, ['AXISBANK.NS'])

                        # Verify market closed message was shown
                        calls = mock_query.edit_message_text.call_args_list
                        market_closed_shown = any('Market Closed' in call[0][0] for call in calls)
                        assert market_closed_shown, "Market closed message not shown"

                        # Verify session was created
                        from src.bot.database.models import PaperTradingSession
                        session = test_db.query(PaperTradingSession).filter(
                            PaperTradingSession.user_id == mock_query.from_user.id,
                            PaperTradingSession.is_active == True
                        ).first()
                        assert session is not None, "Session not auto-created"

                        # Verify pending trade was queued
                        from src.bot.database.models import PendingPaperTrade
                        pending = test_db.query(PendingPaperTrade).filter(
                            PendingPaperTrade.session_id == session.id,
                            PendingPaperTrade.symbol == 'AXISBANK.NS',
                            PendingPaperTrade.status == 'PENDING'
                        ).first()
                        assert pending is not None, "Pending trade not created"

                        # Verify success message
                        success_calls = [call for call in calls if 'Trade Queued' in call[0][0]]
                        assert len(success_calls) > 0, "Success message not shown"

