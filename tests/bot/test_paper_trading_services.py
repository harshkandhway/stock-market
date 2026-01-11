"""
Test Paper Trading Services
Tests for paper trading core services

Author: Harsh Kandhway
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.bot.services.paper_portfolio_service import PaperPortfolioService
from src.bot.services.paper_trade_execution_service import PaperTradeExecutionService
from src.bot.services.paper_trading_service import PaperTradingService
from src.bot.services.paper_trade_analysis_service import PaperTradeAnalysisService
from src.bot.database.models import (
    PaperTradingSession, PaperPosition, PaperTrade, DailyBuySignal
)


class TestPaperPortfolioService:
    """Test paper portfolio service"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_session(self):
        """Mock paper trading session"""
        session = Mock(spec=PaperTradingSession)
        session.current_capital = 500000.0
        session.initial_capital = 500000.0
        session.max_positions = 15
        session.current_positions = 0
        return session

    @pytest.fixture
    def portfolio_service(self, mock_db):
        """Create portfolio service instance"""
        return PaperPortfolioService(mock_db)

    def test_calculate_position_size_1_percent_rule(self, portfolio_service, mock_session):
        """Test position sizing with 1% risk rule"""
        entry_price = 100.0
        stop_loss = 95.0  # 5% risk
        risk_pct = 1.0

        result = portfolio_service.calculate_position_size(
            mock_session, entry_price, stop_loss, risk_pct
        )

        assert 'shares' in result
        assert 'position_value' in result
        assert 'risk_amount' in result
        assert result['shares'] > 0
        assert result['position_value'] > 0

        # Risk should be approximately 1% of capital
        expected_risk = mock_session.current_capital * 0.01
        assert abs(result['risk_amount'] - expected_risk) < expected_risk * 0.1  # Within 10%

    def test_calculate_position_size_max_position_cap(self, portfolio_service, mock_session):
        """Test that position size is capped at 20% of capital"""
        entry_price = 100.0
        stop_loss = 99.0  # Very tight stop (1% risk per share)

        result = portfolio_service.calculate_position_size(
            mock_session, entry_price, stop_loss
        )

        # Position value should not exceed 20% of capital
        max_position_value = mock_session.current_capital * 0.20
        assert result['position_value'] <= max_position_value

    def test_can_open_position_limit_enforcement(self, portfolio_service, mock_session):
        """Test position limit enforcement"""
        # Mock database query to return empty list
        portfolio_service.db.query.return_value.filter.return_value.all.return_value = []
        
        # At limit
        mock_session.current_positions = 15
        mock_session.max_positions = 15
        assert not portfolio_service.can_open_position(mock_session)

        # Below limit
        mock_session.current_positions = 10
        mock_session.max_positions = 15
        assert portfolio_service.can_open_position(mock_session)

    def test_calculate_unrealized_pnl(self, portfolio_service):
        """Test unrealized P&L calculation"""
        # Don't use spec=PaperPosition to avoid SQLAlchemy issues
        position = Mock()
        position.entry_price = 100.0
        position.shares = 10
        position.position_value = 1000.0
        position.stop_loss_price = 95.0

        current_price = 105.0

        result = portfolio_service.calculate_unrealized_pnl(position, current_price)

        assert result['unrealized_pnl'] == 50.0  # (105 - 100) * 10
        assert result['unrealized_pnl_pct'] == 5.0  # 5% gain
        assert result['r_multiple'] > 0  # Should be positive


class TestPaperTradeExecutionService:
    """Test paper trade execution service"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)

    @pytest.fixture
    def execution_service(self, mock_db):
        """Create execution service instance"""
        return PaperTradeExecutionService(mock_db)

    @pytest.fixture
    def mock_session(self):
        """Mock paper trading session"""
        session = Mock(spec=PaperTradingSession)
        session.id = 1
        session.current_capital = 500000.0
        session.current_positions = 0
        session.max_positions = 15
        return session

    @pytest.fixture
    def mock_signal(self):
        """Mock daily buy signal"""
        # Don't use spec=DailyBuySignal to avoid SQLAlchemy hybrid property conflicts
        signal = Mock()
        signal.id = 1
        signal.symbol = "RELIANCE.NS"
        signal.recommendation_type = "STRONG BUY"
        signal.confidence = 80.0
        signal.overall_score_pct = 85.0
        signal.current_price = 2450.0
        signal.target = 2680.0
        signal.stop_loss = 2325.0
        signal.risk_reward = 1.84
        signal.data = {}
        return signal

    @pytest.mark.asyncio
    async def test_validate_entry_duplicate_symbol(self, execution_service, mock_session, mock_signal):
        """Test entry validation rejects duplicate symbol"""
        # Mock existing position - don't use spec to avoid SQLAlchemy issues
        existing_position = Mock()
        existing_position.is_open = True

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = existing_position
        mock_query.filter.return_value = mock_filter
        execution_service.db.query.return_value = mock_query

        is_valid, error = execution_service.validate_entry(mock_session, mock_signal, 2450.0)

        assert not is_valid
        assert "already have" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_entry_price_drift(self, execution_service, mock_session, mock_signal):
        """Test entry validation rejects large price drift"""
        # Mock query chain - no existing position
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None  # No existing position
        mock_query.filter.return_value = mock_filter
        execution_service.db.query.return_value = mock_query
        
        # Mock portfolio service query for positions
        mock_pos_query = Mock()
        mock_pos_filter = Mock()
        mock_pos_filter.all.return_value = []  # No open positions
        mock_pos_query.filter.return_value = mock_pos_filter
        execution_service.db.query.side_effect = [mock_query, mock_pos_query]

        # Price moved 5% (exceeds 3% tolerance)
        current_price = mock_signal.current_price * 1.05

        is_valid, error = execution_service.validate_entry(mock_session, mock_signal, current_price)

        assert not is_valid
        assert "price moved" in error.lower()


class TestPaperTradingService:
    """Test paper trading service (orchestrator)"""

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
    async def test_start_session(self, trading_service, test_user):
        """Test starting a new session"""
        user_id = test_user.telegram_id
        initial_capital = 500000.0
        max_positions = 15

        session = await trading_service.start_session(user_id, initial_capital, max_positions)

        assert session is not None
        assert session.initial_capital == initial_capital
        assert session.max_positions == max_positions
        assert session.is_active is True

    @pytest.mark.asyncio
    async def test_get_active_session(self, trading_service, test_user):
        """Test getting active session"""
        user_id = test_user.telegram_id

        # Create active session
        session = await trading_service.start_session(user_id, 500000.0, 15)

        # Get active session
        active_session = await trading_service.get_active_session(user_id)

        assert active_session is not None
        assert active_session.id == session.id
        assert active_session.is_active is True


class TestPaperTradeAnalysisService:
    """Test paper trade analysis service"""

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
        """Create test session"""
        session = PaperTradingSession(
            user_id=test_user.id,
            is_active=True,
            initial_capital=500000.0,
            current_capital=500000.0,
            peak_capital=550000.0,
            max_positions=15
        )
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        return session

    @pytest.fixture
    def analysis_service(self, test_db):
        """Create analysis service instance"""
        return PaperTradeAnalysisService(test_db)

    def test_analyze_winning_trades(self, analysis_service, test_session):
        """Test winning trades analysis"""
        # Create winning trades
        from datetime import datetime, timedelta
        for i in range(3):
            trade = PaperTrade(
                session_id=test_session.id,
                symbol=f'STOCK{i}.NS',
                entry_date=datetime.utcnow() - timedelta(days=10+i),
                entry_price=100.0,
                shares=10.0,
                entry_value=1000.0,
                exit_date=datetime.utcnow() - timedelta(days=i),
                exit_price=105.0 + i,
                exit_value=(105.0 + i) * 10.0,
                exit_reason='TARGET_HIT',
                target_price=110.0,
                stop_loss_price=95.0,
                pnl=50.0 + (i * 10.0),
                pnl_pct=5.0 + i,
                days_held=5 + i,
                r_multiple=1.5 + (i * 0.5),
                is_winner=True,
                met_target=True,
                hit_stop_loss=False,
                recommendation_type="STRONG BUY" if i == 0 else "BUY",
                entry_confidence=75.0 + (i * 5),
                entry_score_pct=80.0 + i,
                initial_risk_reward=2.0
            )
            analysis_service.db.add(trade)
        analysis_service.db.commit()

        result = analysis_service.analyze_winning_trades(test_session)

        assert result['total_winners'] == 3
        assert 'avg_win_pct' in result
        assert 'avg_r_multiple' in result

    def test_analyze_losing_trades(self, analysis_service, test_session):
        """Test losing trades analysis"""
        # Create losing trades
        from datetime import datetime, timedelta
        for i in range(2):
            trade = PaperTrade(
                session_id=test_session.id,
                symbol=f'STOCK{i}.NS',
                entry_date=datetime.utcnow() - timedelta(days=10+i),
                entry_price=100.0,
                shares=10.0,
                entry_value=1000.0,
                exit_date=datetime.utcnow() - timedelta(days=i),
                exit_price=95.0 - i,
                exit_value=(95.0 - i) * 10.0,
                exit_reason='STOP_LOSS',
                target_price=110.0,
                stop_loss_price=95.0,
                pnl=-50.0 - (i * 10.0),
                pnl_pct=-5.0 - i,
                days_held=3 + i,
                r_multiple=-1.0 - (i * 0.2),
                is_winner=False,
                met_target=False,
                hit_stop_loss=True,
                recommendation_type="WEAK BUY",
                entry_confidence=65.0 - (i * 5),
                entry_score_pct=70.0 - i,
                initial_risk_reward=2.0
            )
            analysis_service.db.add(trade)
        analysis_service.db.commit()
        analysis_service.db.refresh(test_session)

        result = analysis_service.analyze_losing_trades(test_session)

        assert result['total_losers'] == 2
        assert 'avg_loss_pct' in result
        assert 'exit_reasons' in result

    def test_generate_improvement_recommendations_insufficient_data(self, analysis_service, test_session):
        """Test recommendations with insufficient data"""
        # Less than 10 trades - create 5 trades
        from datetime import datetime, timedelta
        for i in range(5):
            trade = PaperTrade(
                session_id=test_session.id,
                symbol=f'STOCK{i}.NS',
                entry_date=datetime.utcnow() - timedelta(days=10+i),
                entry_price=100.0,
                shares=10.0,
                entry_value=1000.0,
                exit_date=datetime.utcnow() - timedelta(days=i),
                exit_price=105.0,
                exit_value=1050.0,
                exit_reason='TARGET_HIT',
                target_price=110.0,
                stop_loss_price=95.0,
                pnl=50.0,
                pnl_pct=5.0,
                days_held=5,
                r_multiple=1.0,
                is_winner=True,
                met_target=True,
                hit_stop_loss=False,
                recommendation_type="BUY",
                entry_confidence=75.0,
                entry_score_pct=80.0,
                initial_risk_reward=2.0
            )
            analysis_service.db.add(trade)
        analysis_service.db.commit()
        analysis_service.db.refresh(test_session)

        recommendations = analysis_service.generate_improvement_recommendations(test_session)

        assert len(recommendations) >= 1
        # Should have insufficient data recommendation
        insufficient = [r for r in recommendations if r.get('category') == 'INSUFFICIENT_DATA']
        assert len(insufficient) > 0

