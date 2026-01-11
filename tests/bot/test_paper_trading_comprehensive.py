"""
Comprehensive Integration Tests for Paper Trading System
End-to-end tests covering complete trading flows

Author: Harsh Kandhway
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import json

from src.bot.database.models import (
    User, UserSettings, PaperTradingSession, PaperPosition, PaperTrade,
    DailyBuySignal, PendingPaperTrade
)
from src.bot.services.paper_trading_service import PaperTradingService
from src.bot.services.paper_trade_execution_service import PaperTradeExecutionService
from src.bot.services.paper_portfolio_service import PaperPortfolioService
from src.bot.services.market_hours_service import get_market_hours_service


class TestPaperTradingCompleteFlow:
    """Test complete paper trading flow end-to-end"""

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
            first_name="Test",
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
            paper_trading_capital=500000.0,
            paper_trading_max_positions=15,
            paper_trading_risk_per_trade_pct=1.0
        )
        test_db.add(settings)
        test_db.commit()
        test_db.refresh(settings)
        return settings

    @pytest.mark.asyncio
    async def test_complete_trading_cycle(self, test_db, test_user, test_settings):
        """Test complete trading cycle: start -> queue -> execute -> monitor -> exit"""
        # 1. Start session
        trading_service = PaperTradingService(test_db)
        session = await trading_service.start_session(
            test_user.telegram_id,
            test_settings.paper_trading_capital,
            test_settings.paper_trading_max_positions
        )
        
        assert session is not None
        assert session.is_active is True
        assert session.initial_capital == 500000.0
        
        # 2. Create BUY signal
        signal = DailyBuySignal(
            symbol='RELIANCE.NS',
            analysis_date=datetime.utcnow(),
            recommendation='Strong buy signal',
            recommendation_type='STRONG BUY',
            current_price=2450.0,
            target=2680.0,
            stop_loss=2325.0,
            risk_reward=1.84,
            confidence=85.0,
            overall_score_pct=88.0,
            analysis_data='{}'
        )
        test_db.add(signal)
        test_db.commit()
        test_db.refresh(signal)
        
        # 3. Queue trade (market closed scenario)
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
            session_id=session.id,
            symbol='RELIANCE.NS',
            requested_by_user_id=test_user.id,
            signal_data=json.dumps(signal_data),
            status='PENDING'
        )
        test_db.add(pending)
        test_db.commit()
        test_db.refresh(pending)
        
        assert pending.status == 'PENDING'
        
        # 4. Execute pending trade (simulate market open)
        execution_service = PaperTradeExecutionService(test_db)
        
        # Validate entry (no need to patch get_current_price - execution service doesn't use it)
        is_valid, error = execution_service.validate_entry(session, signal, 2450.0)
        assert is_valid is True
        
        # Enter position
        position = await execution_service.enter_position(session, signal, 2450.0)
        
        assert position is not None
        assert position.symbol == 'RELIANCE.NS'
        assert position.is_open is True
        
        # Update pending trade
        pending.status = 'EXECUTED'
        pending.position_id = position.id
        pending.executed_at = datetime.utcnow()
        test_db.commit()
        
        assert pending.status == 'EXECUTED'
        
        # 5. Monitor position (simulate price movement)
        portfolio_service = PaperPortfolioService(test_db)
        
        # Update position with new price
        current_price = 2500.0  # Price moved up
        pnl_result = portfolio_service.calculate_unrealized_pnl(position, current_price)
        
        position.current_price = current_price
        position.unrealized_pnl = pnl_result['unrealized_pnl']
        position.unrealized_pnl_pct = pnl_result['unrealized_pnl_pct']
        test_db.commit()
        
        assert position.unrealized_pnl > 0  # Profit
        
        # 6. Exit position (target hit)
        exit_price = 2680.0  # Target price
        exit_reason = 'TARGET_HIT'
        
        closed_trade = await execution_service.exit_position(
            position, exit_price, exit_reason
        )
        
        assert closed_trade is not None
        assert closed_trade.is_winner is True
        assert closed_trade.pnl > 0
        assert closed_trade.exit_reason == 'TARGET_HIT'
        
        # 7. Verify session updated
        test_db.refresh(session)
        assert session.total_trades == 1
        assert session.winning_trades == 1
        assert session.current_positions == 0

    @pytest.mark.asyncio
    async def test_multiple_positions_management(self, test_db, test_user, test_settings):
        """Test managing multiple positions"""
        trading_service = PaperTradingService(test_db)
        session = await trading_service.start_session(
            test_user.telegram_id,
            test_settings.paper_trading_capital,
            test_settings.paper_trading_max_positions
        )
        
        execution_service = PaperTradeExecutionService(test_db)
        
        # Create multiple signals
        symbols = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']
        positions = []
        
        for symbol in symbols:
            signal = DailyBuySignal(
                symbol=symbol,
                analysis_date=datetime.utcnow(),
                recommendation='Buy signal',
                recommendation_type='BUY',
                current_price=1000.0,
                target=1100.0,
                stop_loss=950.0,
                risk_reward=2.0,
                confidence=75.0,
                overall_score_pct=80.0,
                analysis_data='{}'
            )
            test_db.add(signal)
            test_db.flush()
            
            # No need to patch get_current_price
            is_valid, error = execution_service.validate_entry(session, signal, 1000.0)
            if is_valid:
                position = await execution_service.enter_position(session, signal, 1000.0)
                if position:
                    positions.append(position)
        
        test_db.commit()
        
        # Verify positions were created
        assert len(positions) > 0
        
        # Verify session position count
        test_db.refresh(session)
        assert session.current_positions == len(positions)
        
        # Verify position limit enforcement
        if len(positions) >= session.max_positions:
            # Try to create one more - should fail validation
            extra_signal = DailyBuySignal(
                symbol='HDFCBANK.NS',
                analysis_date=datetime.utcnow(),
                recommendation='Buy',
                recommendation_type='BUY',
                current_price=1500.0,
                target=1650.0,
                stop_loss=1425.0,
                risk_reward=2.0,
                confidence=70.0,
                overall_score_pct=75.0,
                analysis_data='{}'
            )
            test_db.add(extra_signal)
            test_db.flush()
            
            # No need to patch get_current_price
            is_valid, error = execution_service.validate_entry(session, extra_signal, 1500.0)
            # Should fail due to position limit
            assert not is_valid or session.current_positions < session.max_positions

    @pytest.mark.asyncio
    async def test_stop_loss_exit(self, test_db, test_user, test_settings):
        """Test position exit via stop loss"""
        trading_service = PaperTradingService(test_db)
        session = await trading_service.start_session(
            test_user.telegram_id,
            test_settings.paper_trading_capital,
            test_settings.paper_trading_max_positions
        )
        
        # Create signal
        signal = DailyBuySignal(
            symbol='RELIANCE.NS',
            analysis_date=datetime.utcnow(),
            recommendation='Buy',
            recommendation_type='BUY',
            current_price=2450.0,
            target=2680.0,
            stop_loss=2325.0,
            risk_reward=1.84,
            confidence=80.0,
            overall_score_pct=85.0,
            analysis_data='{}'
        )
        test_db.add(signal)
        test_db.commit()
        test_db.refresh(signal)
        
        execution_service = PaperTradeExecutionService(test_db)
        
        # Enter position (no need to patch get_current_price)
        position = await execution_service.enter_position(session, signal, 2450.0)
        assert position is not None
        
        # Exit via stop loss
        exit_price = 2325.0  # Stop loss price
        closed_trade = await execution_service.exit_position(
            position, exit_price, 'STOP_LOSS'
        )
        
        assert closed_trade is not None
        assert closed_trade.is_winner is False
        assert closed_trade.hit_stop_loss is True
        assert closed_trade.exit_reason == 'STOP_LOSS'
        
        # Verify session updated
        test_db.refresh(session)
        assert session.total_trades == 1
        assert session.losing_trades == 1

    @pytest.mark.asyncio
    async def test_capital_tracking(self, test_db, test_user, test_settings):
        """Test capital tracking throughout trading"""
        trading_service = PaperTradingService(test_db)
        session = await trading_service.start_session(
            test_user.telegram_id,
            test_settings.paper_trading_capital,
            test_settings.paper_trading_max_positions
        )
        
        initial_capital = session.current_capital
        
        # Create and enter position
        signal = DailyBuySignal(
            symbol='RELIANCE.NS',
            analysis_date=datetime.utcnow(),
            recommendation='Buy',
            recommendation_type='BUY',
            current_price=2450.0,
            target=2680.0,
            stop_loss=2325.0,
            risk_reward=1.84,
            confidence=80.0,
            overall_score_pct=85.0,
            analysis_data='{}'
        )
        test_db.add(signal)
        test_db.commit()
        test_db.refresh(signal)
        
        execution_service = PaperTradeExecutionService(test_db)
        
        # Enter position (no need to patch get_current_price)
        position = await execution_service.enter_position(session, signal, 2450.0)
        
        # Verify capital was deployed
        test_db.refresh(session)
        deployed_capital = initial_capital - session.current_capital
        assert deployed_capital > 0
        assert deployed_capital == position.position_value
        
        # Exit with profit
        exit_price = 2680.0
        closed_trade = await execution_service.exit_position(
            position, exit_price, 'TARGET_HIT'
        )
        
        # Verify capital increased
        test_db.refresh(session)
        assert session.current_capital > initial_capital
        assert session.total_profit > 0

