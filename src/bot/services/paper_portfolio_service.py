"""
Paper Portfolio Service
Manages position sizing, capital allocation, and P&L calculations for paper trading

Author: Harsh Kandhway
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.bot.database.models import (
    PaperTradingSession, PaperPosition
)

logger = logging.getLogger(__name__)


class PaperPortfolioService:
    """Service for managing paper trading portfolio and capital"""

    # Maximum position size as percentage of total capital
    MAX_POSITION_SIZE_PCT = 20.0  # 20% max per position

    def __init__(self, db_session: Session):
        """
        Initialize portfolio service

        Args:
            db_session: Database session
        """
        self.db = db_session

    def calculate_position_size(
        self,
        session: PaperTradingSession,
        entry_price: float,
        stop_loss: float,
        risk_pct: Optional[float] = None
    ) -> Dict:
        """
        Calculate position size using professional 1% risk rule

        Formula:
        - risk_amount = current_capital * risk_pct (default 1%)
        - risk_per_share = abs(entry_price - stop_loss)
        - shares = risk_amount / risk_per_share
        - Cap at 20% of total capital per position

        Args:
            session: Paper trading session
            entry_price: Entry price per share
            stop_loss: Stop loss price
            risk_pct: Risk percentage (default from session settings or 1.0%)

        Returns:
            Dictionary with position sizing details
        """
        if risk_pct is None:
            risk_pct = 1.0  # Default 1% risk

        # Calculate risk amount
        risk_amount = session.current_capital * (risk_pct / 100.0)

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share <= 0:
            logger.error("Invalid stop loss: risk per share is zero or negative")
            return {
                'error': 'Invalid stop loss',
                'shares': 0,
                'position_value': 0,
                'risk_amount': 0,
                'actual_risk_pct': 0
            }

        # Calculate shares based on risk
        shares = int(risk_amount / risk_per_share)

        if shares <= 0:
            logger.warning("Calculated shares is zero - entry price too close to stop loss")
            return {
                'error': 'Position size too small',
                'shares': 0,
                'position_value': 0,
                'risk_amount': risk_amount,
                'actual_risk_pct': 0
            }

        # Calculate position value
        position_value = shares * entry_price

        # Cap at maximum position size (20% of capital)
        max_position_value = session.current_capital * (self.MAX_POSITION_SIZE_PCT / 100.0)

        if position_value > max_position_value:
            logger.info(
                "Position value ₹%.2f exceeds max (₹%.2f). Capping to 20%% of capital",
                position_value, max_position_value
            )
            shares = int(max_position_value / entry_price)
            position_value = shares * entry_price

        # Recalculate actual risk
        actual_risk_amount = shares * risk_per_share
        actual_risk_pct = (actual_risk_amount / session.current_capital) * 100

        result = {
            'shares': shares,
            'position_value': position_value,
            'risk_amount': actual_risk_amount,
            'actual_risk_pct': actual_risk_pct,
            'risk_per_share': risk_per_share,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'position_size_pct': (position_value / session.current_capital) * 100
        }

        logger.info(
            "Position sizing: %d shares @ ₹%.2f = ₹%.2f (%.1f%% of capital, risk: ₹%.2f / %.2f%%)",
            shares, entry_price, position_value,
            result['position_size_pct'], actual_risk_amount, actual_risk_pct
        )

        return result

    def get_available_capital(self, session: PaperTradingSession) -> float:
        """
        Get available (undeployed) capital

        session.current_capital already represents the available cash
        (it's updated when positions are entered/exited)

        Args:
            session: Paper trading session

        Returns:
            Available capital amount
        """
        # session.current_capital is already the available cash
        available = session.current_capital

        logger.debug(
            "Available capital: ₹%.2f",
            available
        )

        return max(0, available)

    def can_open_position(
        self,
        session: PaperTradingSession,
        required_capital: Optional[float] = None
    ) -> bool:
        """
        Check if new position can be opened

        Checks:
        1. Position count < max_positions
        2. Available capital > 0 (or >= required_capital if specified)

        Args:
            session: Paper trading session
            required_capital: Minimum capital required (optional)

        Returns:
            True if position can be opened, False otherwise
        """
        # Check position limit
        if session.current_positions >= session.max_positions:
            logger.warning(
                "Cannot open position: at position limit (%d/%d)",
                session.current_positions, session.max_positions
            )
            return False

        # Check available capital
        available = self.get_available_capital(session)

        if required_capital is not None:
            if available < required_capital:
                logger.warning(
                    "Cannot open position: insufficient capital (need: ₹%.2f, available: ₹%.2f)",
                    required_capital, available
                )
                return False
        else:
            if available <= 0:
                logger.warning("Cannot open position: no available capital")
                return False

        logger.debug("Can open position: %d/%d used, ₹%.2f available",
                    session.current_positions, session.max_positions, available)
        return True

    def calculate_unrealized_pnl(
        self,
        position: PaperPosition,
        current_price: float
    ) -> Dict:
        """
        Calculate unrealized P&L for an open position

        Args:
            position: Paper position
            current_price: Current market price

        Returns:
            Dictionary with P&L details
        """
        current_value = position.shares * current_price
        unrealized_pnl = current_value - position.position_value
        unrealized_pnl_pct = (unrealized_pnl / position.position_value) * 100 if position.position_value > 0 else 0

        # Calculate R-multiple (profit as multiple of initial risk)
        initial_risk = abs(position.entry_price - position.stop_loss_price) * position.shares
        r_multiple = unrealized_pnl / initial_risk if initial_risk > 0 else 0

        result = {
            'current_price': current_price,
            'current_value': current_value,
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pnl_pct': unrealized_pnl_pct,
            'r_multiple': r_multiple,
            'entry_value': position.position_value,
            'shares': position.shares
        }

        return result

    def get_total_unrealized_pnl(self, session: PaperTradingSession) -> Dict:
        """
        Calculate total unrealized P&L for all open positions

        Note: This requires current prices to be updated in position records

        Args:
            session: Paper trading session

        Returns:
            Dictionary with total P&L details
        """
        open_positions = self.db.query(PaperPosition).filter(
            PaperPosition.session_id == session.id,
            PaperPosition.is_open == True
        ).all()

        total_unrealized_pnl = 0.0
        total_entry_value = 0.0
        total_current_value = 0.0

        for pos in open_positions:
            if pos.current_price is not None:
                total_entry_value += pos.position_value
                current_value = pos.shares * pos.current_price
                total_current_value += current_value
                total_unrealized_pnl += (current_value - pos.position_value)

        unrealized_pnl_pct = (total_unrealized_pnl / total_entry_value * 100) if total_entry_value > 0 else 0

        return {
            'total_unrealized_pnl': total_unrealized_pnl,
            'unrealized_pnl_pct': unrealized_pnl_pct,
            'total_entry_value': total_entry_value,
            'total_current_value': total_current_value,
            'position_count': len(open_positions)
        }

    def update_session_capital(self, session: PaperTradingSession) -> float:
        """
        Recalculate total session capital (cash + positions)

        Total Capital = session.current_capital (cash including invested) + sum(open_position_current_values)

        The session.current_capital already reflects cash after position entries,
        so we simply add the current market value of all open positions.

        Args:
            session: Paper trading session

        Returns:
            Updated total capital
        """
        # Get open positions
        open_positions = self.db.query(PaperPosition).filter(
            PaperPosition.session_id == session.id,
            PaperPosition.is_open == True
        ).all()

        # Calculate deployed capital with current prices
        current_deployed_value = 0.0
        for pos in open_positions:
            if pos.current_price is not None:
                current_deployed_value += (pos.shares * pos.current_price)
            else:
                current_deployed_value += pos.position_value  # Use entry value if current price not available

        # Total capital = session.current_capital + current deployed value
        # session.current_capital already has cash (after position entries)
        # Adding current_deployed_value gives total portfolio value
        total_capital = session.current_capital + current_deployed_value

        # Update peak capital if new high
        if total_capital > session.peak_capital:
            session.peak_capital = total_capital
            logger.info("New peak capital: %.2f", total_capital)

        logger.debug(
            "Total capital: %.2f (cash: %.2f + positions: %.2f)",
            total_capital, session.current_capital, current_deployed_value
        )

        return total_capital

    def get_portfolio_summary(self, session: PaperTradingSession) -> Dict:
        """
        Get complete portfolio snapshot

        Args:
            session: Paper trading session

        Returns:
            Dictionary with comprehensive portfolio details
        """
        # Get open positions
        open_positions = self.db.query(PaperPosition).filter(
            PaperPosition.session_id == session.id,
            PaperPosition.is_open == True
        ).all()

        # Capital breakdown
        # Calculate deployed capital at current market prices (for consistency with total_capital)
        deployed_capital = 0.0
        for pos in open_positions:
            if pos.current_price is not None:
                deployed_capital += pos.shares * pos.current_price
            else:
                deployed_capital += pos.position_value  # Fallback to entry value

        available_capital = self.get_available_capital(session)

        # Unrealized P&L
        unrealized_data = self.get_total_unrealized_pnl(session)

        # Total capital
        total_capital = self.update_session_capital(session)

        # Win rate
        win_rate = 0.0
        if session.total_trades > 0:
            win_rate = (session.winning_trades / session.total_trades) * 100

        # Profit factor
        profit_factor = 0.0
        if session.total_loss > 0:
            profit_factor = session.total_profit / session.total_loss

        # Position breakdown
        position_details = []
        for pos in open_positions:
            pnl_data = self.calculate_unrealized_pnl(pos, pos.current_price) if pos.current_price else None

            position_details.append({
                'symbol': pos.symbol,
                'shares': pos.shares,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'entry_value': pos.position_value,
                'unrealized_pnl': pnl_data['unrealized_pnl'] if pnl_data else 0,
                'unrealized_pnl_pct': pnl_data['unrealized_pnl_pct'] if pnl_data else 0,
                'r_multiple': pnl_data['r_multiple'] if pnl_data else 0,
                'target': pos.target_price,
                'stop_loss': pos.stop_loss_price,
                'trailing_stop': pos.trailing_stop,
                'days_held': pos.days_held,
                'recommendation_type': pos.recommendation_type
            })

        summary = {
            # Session Info
            'session_id': session.id,
            'is_active': session.is_active,
            'session_start': session.session_start,

            # Capital
            'total_capital': total_capital,
            'initial_capital': session.initial_capital,
            'current_cash': available_capital,
            'deployed_capital': deployed_capital,
            'deployed_pct': (deployed_capital / session.current_capital * 100) if session.current_capital > 0 else 0,
            'available_pct': (available_capital / session.current_capital * 100) if session.current_capital > 0 else 0,
            'peak_capital': session.peak_capital,

            # Positions
            'position_count': len(open_positions),
            'max_positions': session.max_positions,
            'positions': position_details,

            # Unrealized P&L
            'total_unrealized_pnl': unrealized_data['total_unrealized_pnl'],
            'unrealized_pnl_pct': unrealized_data['unrealized_pnl_pct'],

            # Realized Performance
            'total_trades': session.total_trades,
            'winning_trades': session.winning_trades,
            'losing_trades': session.losing_trades,
            'win_rate_pct': win_rate,
            'total_profit': session.total_profit,
            'total_loss': session.total_loss,
            'net_pnl': session.total_profit - session.total_loss,
            'profit_factor': profit_factor,

            # Overall Return
            'total_return': total_capital - session.initial_capital,
            'total_return_pct': ((total_capital - session.initial_capital) / session.initial_capital * 100) if session.initial_capital > 0 else 0,
            'max_drawdown_pct': session.max_drawdown_pct
        }

        return summary

    def allocate_capital(self, session: PaperTradingSession, amount: float) -> bool:
        """
        Reserve capital for a new position

        This is implicitly handled by position tracking, but can be used
        for validation before creating a position

        Args:
            session: Paper trading session
            amount: Amount to allocate

        Returns:
            True if allocation successful, False otherwise
        """
        available = self.get_available_capital(session)

        if amount > available:
            logger.error(
                "Cannot allocate ₹%.2f - only ₹%.2f available",
                amount, available
            )
            return False

        logger.debug("Capital allocation successful: ₹%.2f", amount)
        return True

    def release_capital(self, session: PaperTradingSession, amount: float):
        """
        Release capital after closing a position

        Note: Capital is automatically released when position is closed
        This method is for logging/tracking purposes

        Args:
            session: Paper trading session
            amount: Amount released
        """
        logger.debug("Capital released: ₹%.2f", amount)


def get_paper_portfolio_service(db_session: Session) -> PaperPortfolioService:
    """
    Factory function to create portfolio service

    Args:
        db_session: Database session

    Returns:
        PaperPortfolioService instance
    """
    return PaperPortfolioService(db_session)
