"""
Paper Trading Service
Main orchestrator for paper trading operations

Author: Harsh Kandhway
"""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.bot.database.models import (
    PaperTradingSession, PaperPosition, PaperTrade,
    DailyBuySignal, User, UserSettings
)
from src.bot.services.paper_portfolio_service import PaperPortfolioService
from src.bot.services.paper_trade_execution_service import PaperTradeExecutionService
from src.bot.services.analysis_service import get_current_price

logger = logging.getLogger(__name__)


class PaperTradingService:
    """Main service for orchestrating paper trading operations"""

    def __init__(self, db_session: Session, notification_callback=None):
        """
        Initialize paper trading service

        Args:
            db_session: Database session
            notification_callback: Optional callback for sending notifications
                                  Signature: async def callback(user_id, symbol, position, type)
        """
        self.db = db_session
        self.portfolio_service = PaperPortfolioService(db_session)
        self.execution_service = PaperTradeExecutionService(db_session)
        self.notification_callback = notification_callback

    async def start_session(
        self,
        user_id: int,
        initial_capital: Optional[float] = None,
        max_positions: Optional[int] = None
    ) -> PaperTradingSession:
        """
        Start a new paper trading session

        Args:
            user_id: User ID
            initial_capital: Initial capital (default: ₹500,000 or from user settings)
            max_positions: Maximum positions (default: 15 or from user settings)

        Returns:
            New PaperTradingSession
        """
        # Close any existing active session
        existing = self.db.query(PaperTradingSession).filter(
            PaperTradingSession.user_id == user_id,
            PaperTradingSession.is_active == True
        ).first()

        if existing:
            logger.warning("Closing existing active session %d before starting new one", existing.id)
            existing.is_active = False
            existing.session_end = datetime.utcnow()

        # Get user settings for defaults
        settings = self.db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

        if initial_capital is None:
            initial_capital = settings.paper_trading_capital if settings else 500000.0

        if max_positions is None:
            max_positions = settings.paper_trading_max_positions if settings else 15

        # Create new session
        session = PaperTradingSession(
            user_id=user_id,
            is_active=True,
            session_start=datetime.utcnow(),
            initial_capital=initial_capital,
            current_capital=initial_capital,
            peak_capital=initial_capital,
            max_positions=max_positions
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        logger.info(
            "📊 Paper trading session started: ID=%d, Capital=₹%.2f, Max Positions=%d",
            session.id, initial_capital, max_positions
        )

        return session

    async def stop_session(self, session_id: int) -> Dict:
        """
        Stop paper trading session

        Closes all open positions and generates final summary

        Args:
            session_id: Session ID

        Returns:
            Final session summary
        """
        session = self.db.query(PaperTradingSession).get(session_id)

        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.is_active:
            logger.warning("Session %d is already inactive", session_id)

        # Close all open positions
        open_positions = self.db.query(PaperPosition).filter(
            PaperPosition.session_id == session_id,
            PaperPosition.is_open == True
        ).all()

        for position in open_positions:
            # Get current price (run in executor since it's synchronous)
            loop = asyncio.get_event_loop()
            current_price = await loop.run_in_executor(None, get_current_price, position.symbol)
            if current_price is None:
                current_price = position.current_price or position.entry_price

            # Exit position
            await self.execution_service.exit_position(
                position, current_price, 'SESSION_STOPPED'
            )

        # Mark session as inactive
        session.is_active = False
        session.session_end = datetime.utcnow()
        self.db.commit()

        # Get final summary
        summary = self.portfolio_service.get_portfolio_summary(session)

        logger.info(
            "🛑 Paper trading session stopped: ID=%d, Final P&L: ₹%.2f (%+.2f%%)",
            session_id, summary['net_pnl'], summary['total_return_pct']
        )

        return summary

    async def get_active_session(self, user_id: Optional[int] = None) -> Optional[PaperTradingSession]:
        """
        Get active paper trading session

        Args:
            user_id: User ID (optional, for filtering)

        Returns:
            Active session or None
        """
        query = self.db.query(PaperTradingSession).filter(
            PaperTradingSession.is_active == True
        )

        if user_id is not None:
            query = query.filter(PaperTradingSession.user_id == user_id)

        session = query.first()

        if session:
            logger.debug("Active session found: ID=%d, User=%d", session.id, session.user_id)
        else:
            logger.debug("No active session found")

        return session

    async def execute_buy_signals(self, session_id: Optional[int] = None) -> Dict:
        """
        Execute BUY signals from daily analysis

        Process:
        1. Get active session(s)
        2. Query DailyBuySignal table for today's signals
        3. Filter for STRONG BUY, BUY, WEAK BUY (exclude BLOCKED/AVOID)
        4. Order by confidence DESC
        5. For each signal:
           - Check position limit
           - Check duplicate symbol
           - Validate price drift
           - Execute entry

        Args:
            session_id: Specific session ID (optional, otherwise all active)

        Returns:
            Execution summary
        """
        # Get today's date (start of day)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Get today's BUY signals
        signals = self.db.query(DailyBuySignal).filter(
            DailyBuySignal.analysis_date >= today,
            DailyBuySignal.recommendation_type.in_(['STRONG BUY', 'BUY', 'WEAK BUY']),
            ~DailyBuySignal.recommendation.contains('BLOCKED'),
            ~DailyBuySignal.recommendation.contains('AVOID')
        ).order_by(DailyBuySignal.confidence.desc()).all()

        logger.info("📋 Found %d BUY signals for today", len(signals))

        # Get active sessions
        if session_id:
            sessions = [self.db.query(PaperTradingSession).get(session_id)]
            sessions = [s for s in sessions if s and s.is_active]
        else:
            sessions = self.db.query(PaperTradingSession).filter(
                PaperTradingSession.is_active == True
            ).all()

        logger.info("🎯 Processing %d active paper trading session(s)", len(sessions))

        # Execute signals for each session
        results = {
            'sessions_processed': len(sessions),
            'signals_found': len(signals),
            'positions_opened': 0,
            'skipped': 0,
            'errors': 0,
            'details': []
        }

        for session in sessions:
            session_result = await self._execute_signals_for_session(session, signals)
            results['positions_opened'] += session_result['opened']
            results['skipped'] += session_result['skipped']
            results['errors'] += session_result['errors']
            results['details'].append({
                'session_id': session.id,
                'user_id': session.user_id,
                'opened': session_result['opened'],
                'skipped': session_result['skipped']
            })

        logger.info(
            "✅ Signal execution complete: %d opened, %d skipped, %d errors",
            results['positions_opened'], results['skipped'], results['errors']
        )

        return results

    async def _execute_signals_for_session(
        self,
        session: PaperTradingSession,
        signals: List[DailyBuySignal]
    ) -> Dict:
        """
        Execute signals for a specific session

        Args:
            session: Paper trading session
            signals: List of buy signals

        Returns:
            Execution summary for this session
        """
        result = {'opened': 0, 'skipped': 0, 'errors': 0}

        for signal in signals:
            # Check if position limit reached
            if not self.portfolio_service.can_open_position(session):
                logger.debug("Position limit reached for session %d", session.id)
                break

            # Check if already have this symbol
            existing = self.db.query(PaperPosition).filter(
                PaperPosition.session_id == session.id,
                PaperPosition.symbol == signal.symbol,
                PaperPosition.is_open == True
            ).first()

            if existing:
                logger.debug("Skipping %s - already have position", signal.symbol)
                result['skipped'] += 1
                continue

            # Get current price (run in executor since it's synchronous)
            try:
                loop = asyncio.get_event_loop()
                current_price = await loop.run_in_executor(None, get_current_price, signal.symbol)

                if current_price is None:
                    # Fix #3: Check signal staleness before using fallback price
                    signal_age_minutes = (datetime.utcnow() - signal.analysis_date).total_seconds() / 60
                    
                    if signal_age_minutes > 60:  # Signal older than 1 hour
                        logger.error(
                            "Skipping %s - cannot fetch current price and signal is %.0f minutes old (stale)",
                            signal.symbol, signal_age_minutes
                        )
                        result['skipped'] += 1
                        continue  # Skip this stale signal
                    
                    # Signal is fresh (< 1 hour), safe to use
                    current_price =signal.current_price
                    logger.warning(
                        "Using signal price for %s: ₹%.2f (signal is %.0f min old - acceptable)",
                        signal.symbol, current_price, signal_age_minutes
                    )

                # Execute entry
                position = await self.execution_service.enter_position(
                    session, signal, current_price
                )

                if position:
                    result['opened'] += 1
                    
                    # Fix #1: Send individual notification for this position
                    if self.notification_callback:
                        try:
                            await self.notification_callback(
                                session.user_id, 
                                signal.symbol, 
                                position, 
                                "individual"
                            )
                        except Exception as notify_error:
                            logger.error(f"Failed to send individual notification: {notify_error}")
                else:
                    result['skipped'] += 1

            except Exception as e:
                logger.error("Error executing entry for %s: %s", signal.symbol, str(e))
                result['errors'] += 1

        return result

    async def monitor_positions(self, session_id: Optional[int] = None) -> Dict:
        """
        Monitor all open positions for exit conditions

        Checks (in priority order):
        1. Stop loss hit → EXIT
        2. Target hit → EXIT
        3. Trailing stop hit → EXIT
        4. Update trailing stop if in profit

        Args:
            session_id: Specific session ID (optional, otherwise all active)

        Returns:
            Monitoring summary
        """
        # Get active sessions
        if session_id:
            sessions = [self.db.query(PaperTradingSession).get(session_id)]
            sessions = [s for s in sessions if s and s.is_active]
        else:
            sessions = self.db.query(PaperTradingSession).filter(
                PaperTradingSession.is_active == True
            ).all()

        results = {
            'sessions_monitored': len(sessions),
            'positions_monitored': 0,
            'positions_exited': 0,
            'trailing_stops_updated': 0,
            'details': []
        }

        for session in sessions:
            session_result = await self._monitor_session_positions(session)
            results['positions_monitored'] += session_result['monitored']
            results['positions_exited'] += session_result['exited']
            results['trailing_stops_updated'] += session_result['trailing_updated']
            results['details'].append({
                'session_id': session.id,
                'monitored': session_result['monitored'],
                'exited': session_result['exited']
            })

        logger.debug(
            "📊 Position monitoring: %d positions, %d exits, %d trailing stops updated",
            results['positions_monitored'], results['positions_exited'],
            results['trailing_stops_updated']
        )

        return results

    async def _monitor_session_positions(self, session: PaperTradingSession) -> Dict:
        """
        Monitor positions for a specific session

        Args:
            session: Paper trading session

        Returns:
            Monitoring summary for this session
        """
        positions = self.db.query(PaperPosition).filter(
            PaperPosition.session_id == session.id,
            PaperPosition.is_open == True
        ).all()

        result = {'monitored': len(positions), 'exited': 0, 'trailing_updated': 0}

        for position in positions:
            try:
                # Get current price (run in executor since it's synchronous)
                loop = asyncio.get_event_loop()
                current_price = await loop.run_in_executor(None, get_current_price, position.symbol)

                if current_price is None:
                    logger.warning("Could not get current price for %s", position.symbol)
                    continue

                # Update position price and P&L
                pnl_data = self.portfolio_service.calculate_unrealized_pnl(position, current_price)
                position.current_price = current_price
                position.unrealized_pnl = pnl_data['unrealized_pnl']
                position.unrealized_pnl_pct = pnl_data['unrealized_pnl_pct']

                # Update days held
                position.days_held = (datetime.utcnow() - position.entry_date).days

                # Check exit conditions (priority order)
                exit_reason = None

                # 1. Stop loss
                if current_price <= position.stop_loss_price:
                    exit_reason = 'STOP_LOSS'
                    logger.info("🛑 Stop loss hit for %s: ₹%.2f <= ₹%.2f",
                               position.symbol, current_price, position.stop_loss_price)

                # 2. Target
                elif current_price >= position.target_price:
                    exit_reason = 'TARGET_HIT'
                    logger.info("🎯 Target hit for %s: ₹%.2f >= ₹%.2f",
                               position.symbol, current_price, position.target_price)

                # 3. Trailing stop
                elif position.trailing_stop and current_price <= position.trailing_stop:
                    exit_reason = 'TRAILING_STOP'
                    logger.info("📉 Trailing stop hit for %s: ₹%.2f <= ₹%.2f",
                               position.symbol, current_price, position.trailing_stop)

                # Exit if triggered
                if exit_reason:
                    await self.execution_service.exit_position(
                        position, current_price, exit_reason
                    )
                    result['exited'] += 1

                # Update trailing stop if in profit
                elif pnl_data['unrealized_pnl'] > 0:
                    new_trailing = await self.execution_service.update_trailing_stop(
                        position, current_price
                    )
                    if new_trailing:
                        result['trailing_updated'] += 1

                # Commit updates
                self.db.commit()

            except Exception as e:
                logger.error("Error monitoring position %s: %s", position.symbol, str(e))
                self.db.rollback()

        return result

    async def get_session_status(self, session_id: int) -> Dict:
        """
        Get real-time session status

        Args:
            session_id: Session ID

        Returns:
            Session status dictionary
        """
        session = self.db.query(PaperTradingSession).get(session_id)

        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get portfolio summary
        summary = self.portfolio_service.get_portfolio_summary(session)

        return summary

    async def get_trade_history(
        self,
        session_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[PaperTrade]:
        """
        Get trade history for a session

        Args:
            session_id: Session ID
            limit: Number of trades to return
            offset: Offset for pagination

        Returns:
            List of completed trades
        """
        trades = self.db.query(PaperTrade).filter(
            PaperTrade.session_id == session_id
        ).order_by(
            PaperTrade.exit_date.desc()
        ).limit(limit).offset(offset).all()

        logger.debug("Retrieved %d trades for session %d", len(trades), session_id)

        return trades

    async def reset_session(self, session_id: int) -> PaperTradingSession:
        """
        Reset session (close current and start new)

        Args:
            session_id: Session ID to reset

        Returns:
            New session
        """
        old_session = self.db.query(PaperTradingSession).get(session_id)

        if not old_session:
            raise ValueError(f"Session {session_id} not found")

        # Stop old session
        await self.stop_session(session_id)

        # Start new session with same settings
        new_session = await self.start_session(
            old_session.user_id,
            old_session.initial_capital,
            old_session.max_positions
        )

        logger.info("🔄 Session reset: %d → %d", session_id, new_session.id)

        return new_session


def get_paper_trading_service(
    db_session: Session, 
    notification_callback=None
) -> PaperTradingService:
    """
    Factory function to create paper trading service

    Args:
        db_session: Database session
        notification_callback: Optional callback for sending notifications

    Returns:
        PaperTradingService instance
    """
    return PaperTradingService(db_session, notification_callback)
