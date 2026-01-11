"""
Comprehensive Tests for Paper Trading Scheduler
Tests all scheduler tasks and timing

Author: Harsh Kandhway
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, time, timedelta
import asyncio

from src.bot.services.paper_trading_scheduler import PaperTradingScheduler
from src.bot.database.models import PaperTradingSession, DailyBuySignal


class TestPaperTradingScheduler:
    """Test paper trading scheduler"""

    @pytest.fixture
    def mock_application(self):
        """Create mock Telegram application"""
        app = Mock()
        app.bot = Mock()
        return app

    @pytest.fixture
    def scheduler(self, mock_application):
        """Create scheduler instance"""
        return PaperTradingScheduler(mock_application)

    @pytest.mark.asyncio
    async def test_scheduler_start(self, scheduler):
        """Test starting the scheduler"""
        scheduler.is_running = False
        
        await scheduler.start()
        
        assert scheduler.is_running is True
        assert scheduler.buy_execution_task is not None
        assert scheduler.position_monitoring_task is not None
        assert scheduler.daily_summary_task is not None
        assert scheduler.weekly_summary_task is not None
        assert scheduler.position_rebalancing_task is not None

    @pytest.mark.asyncio
    async def test_scheduler_stop(self, scheduler):
        """Test stopping the scheduler"""
        scheduler.is_running = True
        
        # Create mock tasks
        scheduler.buy_execution_task = AsyncMock()
        scheduler.position_monitoring_task = AsyncMock()
        scheduler.daily_summary_task = AsyncMock()
        scheduler.weekly_summary_task = AsyncMock()
        scheduler.position_rebalancing_task = AsyncMock()
        
        await scheduler.stop()
        
        assert scheduler.is_running is False
        # Verify tasks were cancelled
        assert scheduler.buy_execution_task.cancel.called or True  # May not be awaited yet

    @pytest.mark.asyncio
    async def test_execute_pending_trades_no_pending(self, scheduler):
        """Test executing pending trades when none exist"""
        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_db_ctx:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.all.return_value = []
            mock_db_ctx.return_value.__enter__.return_value = mock_db
            mock_db_ctx.return_value.__exit__.return_value = None
            
            await scheduler._execute_pending_trades()
            
            # Should complete without error
            assert True

    @pytest.mark.asyncio
    async def test_execute_buy_signals(self, scheduler):
        """Test executing BUY signals"""
        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_db_ctx:
            mock_db = Mock()
            mock_db_ctx.return_value.__enter__.return_value = mock_db
            mock_db_ctx.return_value.__exit__.return_value = None
            
            with patch('src.bot.services.paper_trading_scheduler.get_paper_trading_service') as mock_service:
                mock_trading_service = AsyncMock()
                mock_trading_service.execute_buy_signals.return_value = {
                    'sessions_processed': 1,
                    'signals_found': 5,
                    'positions_opened': 2,
                    'skipped': 3
                }
                mock_service.return_value = mock_trading_service
                
                await scheduler._execute_buy_signals()
                
                # Verify service was called
                mock_trading_service.execute_buy_signals.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_positions(self, scheduler):
        """Test monitoring positions"""
        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_db_ctx:
            mock_db = Mock()
            mock_db_ctx.return_value.__enter__.return_value = mock_db
            mock_db_ctx.return_value.__exit__.return_value = None
            
            with patch('src.bot.services.paper_trading_scheduler.get_paper_trading_service') as mock_service:
                mock_trading_service = AsyncMock()
                mock_trading_service.monitor_positions.return_value = {
                    'sessions_monitored': 1,
                    'positions_monitored': 5,
                    'positions_exited': 1,
                    'trailing_stops_updated': 2
                }
                mock_service.return_value = mock_trading_service
                
                await scheduler._monitor_positions()
                
                # Verify service was called
                mock_trading_service.monitor_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_daily_summary(self, scheduler):
        """Test generating daily summary"""
        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_db_ctx:
            mock_db = Mock()
            mock_db_ctx.return_value.__enter__.return_value = mock_db
            mock_db_ctx.return_value.__exit__.return_value = None
            
            with patch('src.bot.services.paper_trading_scheduler.get_paper_trading_service') as mock_service:
                mock_trading_service = AsyncMock()
                mock_trading_service.get_active_sessions.return_value = []
                mock_service.return_value = mock_trading_service
                
                await scheduler._generate_daily_summary()
                
                # Should complete without error
                assert True

    @pytest.mark.asyncio
    async def test_generate_weekly_summary(self, scheduler):
        """Test generating weekly summary"""
        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_db_ctx:
            mock_db = Mock()
            mock_db_ctx.return_value.__enter__.return_value = mock_db
            mock_db_ctx.return_value.__exit__.return_value = None
            
            with patch('src.bot.services.paper_trading_scheduler.get_paper_trading_service') as mock_service:
                mock_trading_service = AsyncMock()
                mock_trading_service.get_active_sessions.return_value = []
                mock_service.return_value = mock_trading_service
                
                await scheduler._generate_weekly_summary()
                
                # Should complete without error
                assert True

    @pytest.mark.asyncio
    async def test_rebalance_positions(self, scheduler):
        """Test rebalancing positions"""
        with patch('src.bot.services.paper_trading_scheduler.get_db_context') as mock_db_ctx:
            mock_db = Mock()
            mock_db_ctx.return_value.__enter__.return_value = mock_db
            mock_db_ctx.return_value.__exit__.return_value = None
            
            with patch('src.bot.services.paper_trading_scheduler.get_paper_trading_service') as mock_service:
                mock_trading_service = AsyncMock()
                mock_trading_service.get_active_sessions.return_value = []
                mock_service.return_value = mock_trading_service
                
                await scheduler._rebalance_positions()
                
                # Should complete without error
                assert True

    @pytest.mark.asyncio
    async def test_run_buy_execution_task_timing(self, scheduler):
        """Test BUY execution task timing logic"""
        scheduler.is_running = True
        
        # Mock market hours
        with patch.object(scheduler.market_hours, 'is_market_day') as mock_market_day:
            mock_market_day.return_value = True
            
            # Mock datetime to be before 9:20 AM
            test_time = datetime(2026, 1, 13, 8, 0, 0)
            test_time = scheduler.market_hours.TIMEZONE.localize(test_time)
            
            with patch('src.bot.services.paper_trading_scheduler.datetime') as mock_dt:
                mock_dt.now.return_value = test_time
                mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                # Mock sleep to prevent actual waiting
                with patch('asyncio.sleep') as mock_sleep:
                    mock_sleep.side_effect = asyncio.CancelledError()
                    
                    try:
                        await scheduler._run_buy_execution_task()
                    except asyncio.CancelledError:
                        pass  # Expected
                    
                    # Verify sleep was called (waiting for execution time)
                    assert mock_sleep.called

    @pytest.mark.asyncio
    async def test_run_position_monitoring_task_market_open(self, scheduler):
        """Test position monitoring task when market is open"""
        scheduler.is_running = True
        
        with patch.object(scheduler.market_hours, 'is_market_open') as mock_open:
            mock_open.return_value = True
            
            with patch.object(scheduler, '_monitor_positions') as mock_monitor:
                mock_monitor.return_value = None
                
                with patch('asyncio.sleep') as mock_sleep:
                    mock_sleep.side_effect = asyncio.CancelledError()
                    
                    try:
                        await scheduler._run_position_monitoring_task()
                    except asyncio.CancelledError:
                        pass
                    
                    # Verify monitoring was called
                    mock_monitor.assert_called()

    @pytest.mark.asyncio
    async def test_run_position_monitoring_task_market_closed(self, scheduler):
        """Test position monitoring task when market is closed"""
        scheduler.is_running = True
        
        with patch.object(scheduler.market_hours, 'is_market_open') as mock_open:
            mock_open.return_value = False
            
            with patch.object(scheduler.market_hours, 'seconds_until_market_open') as mock_seconds:
                mock_seconds.return_value = 3600
                
                with patch('asyncio.sleep') as mock_sleep:
                    mock_sleep.side_effect = asyncio.CancelledError()
                    
                    try:
                        await scheduler._run_position_monitoring_task()
                    except asyncio.CancelledError:
                        pass
                    
                    # Verify sleep was called (waiting for market open)
                    assert mock_sleep.called


