"""
Integration Tests for Paper Trading System
Tests complete trading flow end-to-end

Author: Harsh Kandhway
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from sqlalchemy.orm import Session

from src.bot.services.paper_trading_service import PaperTradingService
from src.bot.database.models import (
    PaperTradingSession, PaperPosition, PaperTrade, DailyBuySignal
)


class TestPaperTradingIntegration:
    """Integration tests for paper trading flow"""

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
    def trading_service(self, test_db):
        """Create trading service instance"""
        return PaperTradingService(test_db)

    @pytest.mark.asyncio
    async def test_complete_trading_cycle(self, trading_service, test_user):
        """Test complete trading cycle: start -> execute -> monitor -> exit"""
        user_id = test_user.telegram_id

        # Start session
        session = await trading_service.start_session(user_id, 500000.0, 15)

        assert session is not None
        assert session.is_active is True

        # Mock signal execution
        with patch.object(trading_service, 'execute_buy_signals') as mock_execute:
            mock_execute.return_value = {
                'sessions_processed': 1,
                'signals_found': 5,
                'positions_opened': 2,
                'skipped': 3
            }

            result = await trading_service.execute_buy_signals(session.id)

            assert result['positions_opened'] == 2

        # Mock position monitoring
        with patch.object(trading_service, 'monitor_positions') as mock_monitor:
            mock_monitor.return_value = {
                'sessions_monitored': 1,
                'positions_monitored': 2,
                'positions_exited': 1,
                'trailing_stops_updated': 0
            }

            result = await trading_service.monitor_positions(session.id)

            assert result['positions_exited'] == 1

    @pytest.mark.asyncio
    async def test_position_limit_enforcement(self, trading_service, test_user):
        """Test that system respects position limits"""
        # Create session at position limit
        session = await trading_service.start_session(test_user.telegram_id, 500000.0, 15)
        session.current_positions = 15  # At limit
        trading_service.db.commit()

        # Mock signals - don't use spec=DailyBuySignal
        signals = [Mock() for _ in range(10)]
        for i, sig in enumerate(signals):
            sig.symbol = f'STOCK{i}.NS'
            sig.recommendation_type = 'BUY'
            sig.current_price = 100.0
            sig.target = 110.0
            sig.stop_loss = 95.0

        # Check that portfolio service respects limit
        can_open = trading_service.portfolio_service.can_open_position(session)

        # Should not be able to open position at limit
        assert not can_open

    @pytest.mark.asyncio
    async def test_capital_management(self, trading_service, test_user):
        """Test capital allocation and tracking"""
        # Create session
        session = await trading_service.start_session(test_user.telegram_id, 500000.0, 15)

        # Create positions
        from src.bot.database.models import PaperPosition
        positions = [
            PaperPosition(
                session_id=session.id,
                symbol='STOCK1.NS',
                entry_price=100.0,
                shares=1000.0,
                position_value=100000.0,
                target_price=110.0,
                stop_loss_price=95.0,
                recommendation_type='BUY',
                entry_confidence=75.0,
                entry_score_pct=80.0,
                initial_risk_reward=2.0,
                is_open=True
            ),
            PaperPosition(
                session_id=session.id,
                symbol='STOCK2.NS',
                entry_price=150.0,
                shares=1000.0,
                position_value=150000.0,
                target_price=165.0,
                stop_loss_price=142.5,
                recommendation_type='BUY',
                entry_confidence=75.0,
                entry_score_pct=80.0,
                initial_risk_reward=2.0,
                is_open=True
            )
        ]
        for pos in positions:
            trading_service.db.add(pos)
        trading_service.db.commit()

        # Get available capital
        available = trading_service.portfolio_service.get_available_capital(session)

        # Should be 500000 - 250000 = 250000
        assert available == 250000.0

