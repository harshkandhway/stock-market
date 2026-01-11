"""
Paper Trade Execution Service
Handles entry and exit of paper trading positions

Author: Harsh Kandhway
"""

import logging
import json
from typing import Dict, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.bot.database.models import (
    PaperTradingSession, PaperPosition, PaperTrade,
    PaperTradingLog, DailyBuySignal
)
from src.bot.services.paper_portfolio_service import PaperPortfolioService

logger = logging.getLogger(__name__)


class PaperTradeExecutionService:
    """Service for executing paper trades (entry and exit)"""

    # Trailing stop percentages by signal type
    TRAILING_STOP_PCT = {
        'STRONG BUY': 0.15,  # 15% from peak
        'BUY': 0.20,         # 20% from peak
        'WEAK BUY': 0.25     # 25% from peak
    }

    # Maximum price drift from signal price (3%)
    MAX_PRICE_DRIFT_PCT = 3.0

    def __init__(self, db_session: Session):
        """
        Initialize execution service

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.portfolio_service = PaperPortfolioService(db_session)

    def validate_entry(
        self,
        session: PaperTradingSession,
        signal: DailyBuySignal,
        current_price: float
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if entry can be executed

        Checks:
        1. Can open position (position limit, capital)
        2. No duplicate symbol
        3. Price drift < 3% from signal price

        Args:
            session: Paper trading session
            signal: Buy signal
            current_price: Current market price

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if already have position in this symbol
        existing = self.db.query(PaperPosition).filter(
            PaperPosition.session_id == session.id,
            PaperPosition.symbol == signal.symbol,
            PaperPosition.is_open == True
        ).first()

        if existing:
            return False, f"Already have open position in {signal.symbol}"

        # Calculate position size to check capital requirement
        sizing = self.portfolio_service.calculate_position_size(
            session, current_price, signal.stop_loss
        )

        if 'error' in sizing:
            return False, sizing['error']

        # Check if can open position with required capital
        if not self.portfolio_service.can_open_position(session, sizing['position_value']):
            return False, "Position limit reached or insufficient capital"

        # Check price drift
        price_drift_pct = abs((current_price - signal.current_price) / signal.current_price * 100)

        if price_drift_pct > self.MAX_PRICE_DRIFT_PCT:
            return False, f"Price moved {price_drift_pct:.1f}% from signal (max: {self.MAX_PRICE_DRIFT_PCT}%)"

        return True, None

    async def enter_position(
        self,
        session: PaperTradingSession,
        signal: DailyBuySignal,
        current_price: float
    ) -> Optional[PaperPosition]:
        """
        Execute position entry

        Steps:
        1. Validate entry
        2. Calculate position size (1% risk rule)
        3. Create PaperPosition record
        4. Update session stats
        5. Create log entry

        Args:
            session: Paper trading session
            signal: Buy signal from daily analysis
            current_price: Current market price

        Returns:
            PaperPosition if successful, None otherwise
        """
        # Validate entry
        is_valid, error = self.validate_entry(session, signal, current_price)

        if not is_valid:
            logger.warning(
                "Entry validation failed for %s: %s",
                signal.symbol, error
            )
            self._create_log(
                session, 'WARNING', 'ENTRY', signal.symbol,
                f"Entry rejected: {error}"
            )
            return None

        # Calculate position size
        sizing = self.portfolio_service.calculate_position_size(
            session, current_price, signal.stop_loss
        )

        if 'error' in sizing:
            logger.error("Position sizing failed for %s: %s", signal.symbol, sizing['error'])
            return None

        # Create position
        position = PaperPosition(
            session_id=session.id,
            symbol=signal.symbol,
            signal_id=signal.id,

            # Entry details
            entry_date=datetime.utcnow(),
            entry_price=current_price,
            shares=sizing['shares'],
            position_value=sizing['position_value'],

            # Risk management
            target_price=signal.target,
            stop_loss_price=signal.stop_loss,
            trailing_stop=None,  # Will be set when in profit
            initial_risk_reward=signal.risk_reward,

            # Signal metadata
            recommendation_type=signal.recommendation_type,
            entry_confidence=signal.confidence,
            entry_score_pct=signal.overall_score_pct,

            # Current state
            current_price=current_price,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            highest_price=current_price,
            is_open=True,
            days_held=0,

            # Analysis snapshot
            entry_analysis=signal.analysis_data if hasattr(signal, 'analysis_data') else json.dumps(signal.data)
        )

        # Update session
        session.current_positions += 1
        session.current_capital -= sizing['position_value']  # Reduce capital by position value
        session.updated_at = datetime.utcnow()

        # Save to database
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)

        # Create log
        self._create_log(
            session, 'TRADE', 'ENTRY', signal.symbol,
            f"Position opened: {sizing['shares']} shares @ ₹{current_price:.2f}",
            details={
                'position_id': position.id,
                'entry_price': current_price,
                'shares': sizing['shares'],
                'position_value': sizing['position_value'],
                'target': signal.target,
                'stop_loss': signal.stop_loss,
                'risk_reward': signal.risk_reward,
                'confidence': signal.confidence,
                'recommendation': signal.recommendation_type
            },
            position_id=position.id
        )

        logger.info(
            "✅ Position opened: %s - %d shares @ ₹%.2f = ₹%.2f (Target: ₹%.2f, Stop: ₹%.2f, R:R: %.2f)",
            signal.symbol, sizing['shares'], current_price, sizing['position_value'],
            signal.target, signal.stop_loss, signal.risk_reward
        )

        return position

    async def exit_position(
        self,
        position: PaperPosition,
        current_price: float,
        exit_reason: str
    ) -> Optional[PaperTrade]:
        """
        Execute position exit

        Steps:
        1. Calculate realized P&L and R-multiple
        2. Create PaperTrade record (historical)
        3. Update session stats
        4. Close position (is_open = False)
        5. Create log entry

        Args:
            position: Open position to close
            current_price: Exit price
            exit_reason: Reason for exit (STOP_LOSS, TARGET_HIT, TRAILING_STOP, SELL_SIGNAL)

        Returns:
            PaperTrade record if successful, None otherwise
        """
        session = self.db.query(PaperTradingSession).get(position.session_id)

        if not session:
            logger.error("Session not found for position %d", position.id)
            return None

        # Calculate P&L
        exit_value = position.shares * current_price
        pnl = exit_value - position.position_value
        pnl_pct = (pnl / position.position_value) * 100 if position.position_value > 0 else 0

        # Calculate R-multiple
        initial_risk = abs(position.entry_price - position.stop_loss_price) * position.shares
        r_multiple = pnl / initial_risk if initial_risk > 0 else 0

        # Calculate hold time
        days_held = (datetime.utcnow() - position.entry_date).days

        # Determine trade outcome
        is_winner = pnl > 0
        met_target = (exit_reason == 'TARGET_HIT')
        hit_stop_loss = (exit_reason == 'STOP_LOSS')

        # Calculate max unrealized gain/loss
        max_unrealized_gain = 0.0
        max_unrealized_loss = 0.0

        if position.highest_price:
            max_unrealized_gain = (position.highest_price - position.entry_price) * position.shares
            if max_unrealized_gain < 0:
                max_unrealized_gain = 0.0

        if pnl < 0:
            max_unrealized_loss = abs(pnl)

        # Create trade record
        trade = PaperTrade(
            session_id=session.id,
            position_id=position.id,
            symbol=position.symbol,

            # Entry details
            entry_date=position.entry_date,
            entry_price=position.entry_price,
            shares=position.shares,
            entry_value=position.position_value,

            # Exit details
            exit_date=datetime.utcnow(),
            exit_price=current_price,
            exit_value=exit_value,
            exit_reason=exit_reason,

            # Performance metrics
            pnl=pnl,
            pnl_pct=pnl_pct,
            days_held=days_held,
            r_multiple=r_multiple,
            is_winner=is_winner,
            met_target=met_target,
            hit_stop_loss=hit_stop_loss,

            # Signal metadata (copy from position)
            recommendation_type=position.recommendation_type,
            entry_confidence=position.entry_confidence,
            entry_score_pct=position.entry_score_pct,
            initial_risk_reward=position.initial_risk_reward,

            # Risk management (from position)
            target_price=position.target_price,
            stop_loss_price=position.stop_loss_price,

            # Price extremes
            highest_price=position.highest_price,
            max_unrealized_gain=max_unrealized_gain,
            max_unrealized_loss=max_unrealized_loss,

            # Analysis snapshots
            entry_analysis=position.entry_analysis,
            exit_analysis=None  # Can be populated if re-analyzing at exit
        )

        # Update session stats
        session.current_positions -= 1
        session.total_trades += 1

        if is_winner:
            session.winning_trades += 1
            session.total_profit += pnl
        else:
            session.losing_trades += 1
            session.total_loss += abs(pnl)

        # Update session capital (add exit proceeds)
        session.current_capital += exit_value
        session.updated_at = datetime.utcnow()

        # Update position
        position.is_open = False
        position.current_price = current_price
        position.unrealized_pnl = 0.0  # Now realized
        position.unrealized_pnl_pct = 0.0

        # Save to database
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)

        # Create log
        self._create_log(
            session, 'TRADE', 'EXIT', position.symbol,
            f"Position closed: {exit_reason} - P&L: ₹{pnl:.2f} ({pnl_pct:+.2f}%, {r_multiple:.2f}R)",
            details={
                'trade_id': trade.id,
                'position_id': position.id,
                'exit_price': current_price,
                'exit_reason': exit_reason,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'r_multiple': r_multiple,
                'days_held': days_held,
                'is_winner': is_winner
            },
            position_id=position.id,
            trade_id=trade.id
        )

        logger.info(
            "🔴 Position closed: %s - %s | P&L: ₹%.2f (%+.2f%%) | %.2fR | %d days | Session: %d/%d wins",
            position.symbol, exit_reason, pnl, pnl_pct, r_multiple, days_held,
            session.winning_trades, session.total_trades
        )

        return trade

    async def update_trailing_stop(
        self,
        position: PaperPosition,
        current_price: float
    ) -> Optional[float]:
        """
        Update trailing stop for a position

        Trailing stop strategy:
        - STRONG BUY: 15% from peak
        - BUY: 20% from peak
        - WEAK BUY: 25% from peak

        Stop only moves UP, never down

        Args:
            position: Open position
            current_price: Current market price

        Returns:
            New trailing stop price, or None if not updated
        """
        # Update highest price
        if position.highest_price is None or current_price > position.highest_price:
            position.highest_price = current_price
            logger.debug("New high for %s: ₹%.2f", position.symbol, current_price)

        # Get trailing stop percentage for this signal type
        trailing_pct = self.TRAILING_STOP_PCT.get(position.recommendation_type, 0.20)

        # Calculate new trailing stop
        new_trailing = current_price * (1 - trailing_pct)

        # Only update if new trailing is higher than current (or if not set)
        if position.trailing_stop is None:
            # Also ensure it's above the initial stop loss
            if new_trailing > position.stop_loss_price:
                position.trailing_stop = new_trailing
                logger.info(
                    "Trailing stop activated for %s: ₹%.2f (%.0f%% from peak)",
                    position.symbol, new_trailing, trailing_pct * 100
                )
                return new_trailing
        elif new_trailing > position.trailing_stop:
            old_trailing = position.trailing_stop
            position.trailing_stop = new_trailing
            logger.info(
                "Trailing stop updated for %s: ₹%.2f → ₹%.2f",
                position.symbol, old_trailing, new_trailing
            )
            return new_trailing

        return None

    def _create_log(
        self,
        session: PaperTradingSession,
        log_level: str,
        category: str,
        symbol: str,
        message: str,
        details: Optional[Dict] = None,
        position_id: Optional[int] = None,
        trade_id: Optional[int] = None
    ):
        """
        Create log entry

        Args:
            session: Paper trading session
            log_level: Log level (INFO, WARNING, ERROR, TRADE)
            category: Category (ENTRY, EXIT, MONITORING, ANALYSIS, ERROR)
            symbol: Stock symbol
            message: Log message
            details: Additional details (JSON)
            position_id: Position ID (optional)
            trade_id: Trade ID (optional)
        """
        log = PaperTradingLog(
            session_id=session.id,
            timestamp=datetime.utcnow(),
            log_level=log_level,
            category=category,
            symbol=symbol,
            message=message,
            details=json.dumps(details) if details else None,
            position_id=position_id,
            trade_id=trade_id
        )

        self.db.add(log)
        self.db.commit()


def get_paper_trade_execution_service(db_session: Session) -> PaperTradeExecutionService:
    """
    Factory function to create execution service

    Args:
        db_session: Database session

    Returns:
        PaperTradeExecutionService instance
    """
    return PaperTradeExecutionService(db_session)
