"""
Paper Trading Scheduler
Manages automated paper trading tasks during market hours

Author: Harsh Kandhway
"""

import asyncio
import logging
import json
from datetime import datetime, time, timedelta
from typing import Optional

from telegram.ext import Application

from src.bot.services.market_hours_service import get_market_hours_service
from src.bot.services.paper_trading_service import get_paper_trading_service
from src.bot.services.paper_trade_analysis_service import get_paper_trade_analysis_service
from src.bot.database.db import get_db_context

logger = logging.getLogger(__name__)


class PaperTradingScheduler:
    """Scheduler for automated paper trading operations"""

    # Execution times (IST)
    BUY_EXECUTION_TIME = time(9, 20)      # 9:20 AM - After market open
    DAILY_SUMMARY_TIME = time(16, 0)      # 4:00 PM - After market close
    WEEKLY_SUMMARY_DAY = 6                # Sunday = 6
    WEEKLY_SUMMARY_TIME = time(18, 0)     # 6:00 PM
    POSITION_REBALANCE_TIME = time(11, 0) # 11:00 AM - Mid-market

    # Monitoring interval
    MONITOR_INTERVAL_SECONDS = 300  # 5 minutes

    def __init__(self, application: Application):
        """
        Initialize paper trading scheduler

        Args:
            application: Telegram application instance
        """
        self.application = application
        self.market_hours = get_market_hours_service()
        self.is_running = False

        # Task handles
        self.buy_execution_task: Optional[asyncio.Task] = None
        self.position_monitoring_task: Optional[asyncio.Task] = None
        self.daily_summary_task: Optional[asyncio.Task] = None
        self.weekly_summary_task: Optional[asyncio.Task] = None
        self.position_rebalancing_task: Optional[asyncio.Task] = None

        logger.info("PaperTradingScheduler initialized")

    async def start(self):
        """Start all scheduler tasks"""
        if self.is_running:
            logger.warning("Paper trading scheduler already running")
            return

        self.is_running = True

        # Start all 5 tasks concurrently
        self.buy_execution_task = asyncio.create_task(self._run_buy_execution_task())
        self.position_monitoring_task = asyncio.create_task(self._run_position_monitoring_task())
        self.daily_summary_task = asyncio.create_task(self._run_daily_summary_task())
        self.weekly_summary_task = asyncio.create_task(self._run_weekly_summary_task())
        self.position_rebalancing_task = asyncio.create_task(self._run_position_rebalancing_task())

        logger.info("✅ Paper trading scheduler started - all 5 tasks running")

    async def stop(self):
        """Stop all scheduler tasks gracefully"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel all tasks
        tasks = [
            self.buy_execution_task,
            self.position_monitoring_task,
            self.daily_summary_task,
            self.weekly_summary_task,
            self.position_rebalancing_task
        ]

        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("🛑 Paper trading scheduler stopped")

    async def _run_buy_execution_task(self):
        """
        TASK 1: Execute BUY signals at market open

        Schedule: 9:20 AM IST (daily)
        Reason: 5 min after market open, volatility settled
        """
        logger.info("📋 BUY execution task started")

        while self.is_running:
            try:
                now = datetime.now(self.market_hours.TIMEZONE)

                # Check if today is a trading day
                if not self.market_hours.is_market_day(now.date()):
                    # Wait until next market day
                    next_open = self.market_hours.get_next_market_open(now)
                    sleep_seconds = (next_open - now).total_seconds()
                    logger.debug("Waiting for next trading day: %d seconds", sleep_seconds)
                    await asyncio.sleep(min(sleep_seconds, 3600))  # Max 1 hour sleep
                    continue

                # Calculate next execution time (9:20 AM today or tomorrow)
                target_time = now.replace(
                    hour=self.BUY_EXECUTION_TIME.hour,
                    minute=self.BUY_EXECUTION_TIME.minute,
                    second=0,
                    microsecond=0
                )

                # If already past 9:20 AM today, schedule for next trading day
                if now >= target_time:
                    target_time += timedelta(days=1)
                    # Find next trading day
                    while not self.market_hours.is_market_day(target_time.date()):
                        target_time += timedelta(days=1)

                # Wait until target time
                sleep_seconds = (target_time - now).total_seconds()
                logger.info("⏰ Next BUY execution at %s (in %.1f hours)",
                           target_time.strftime('%Y-%m-%d %H:%M %Z'),
                           sleep_seconds / 3600)

                await asyncio.sleep(sleep_seconds)

                # Execute pending trades first (queued when market was closed)
                await self._execute_pending_trades()
                
                # Execute BUY signals
                await self._execute_buy_signals()

            except asyncio.CancelledError:
                logger.info("BUY execution task cancelled")
                break
            except Exception as e:
                logger.error("Error in BUY execution task: %s", str(e), exc_info=True)
                await asyncio.sleep(3600)  # Wait 1 hour before retry

    async def _run_position_monitoring_task(self):
        """
        TASK 2: Monitor positions for stop/target/trailing

        Schedule: Every 5 minutes during market hours
        """
        logger.info("📊 Position monitoring task started")

        while self.is_running:
            try:
                # Check if market is open
                if self.market_hours.is_market_open():
                    # Monitor all positions
                    await self._monitor_positions()

                    # Sleep for monitoring interval
                    await asyncio.sleep(self.MONITOR_INTERVAL_SECONDS)
                else:
                    # Market closed - wait until next market open
                    seconds_until_open = self.market_hours.seconds_until_market_open()
                    logger.debug("Market closed - waiting %d seconds until open", seconds_until_open)
                    await asyncio.sleep(min(seconds_until_open, 300))  # Check every 5 min

            except asyncio.CancelledError:
                logger.info("Position monitoring task cancelled")
                break
            except Exception as e:
                logger.error("Error in position monitoring: %s", str(e), exc_info=True)
                await asyncio.sleep(300)  # Wait 5 min before retry

    async def _run_daily_summary_task(self):
        """
        TASK 3: Generate daily summary

        Schedule: 4:00 PM IST (daily)
        Reason: 30 min after market close
        """
        logger.info("📊 Daily summary task started")

        while self.is_running:
            try:
                now = datetime.now(self.market_hours.TIMEZONE)

                # Check if today is a trading day
                if not self.market_hours.is_market_day(now.date()):
                    # Wait until next market day
                    next_open = self.market_hours.get_next_market_open(now)
                    sleep_seconds = (next_open - now).total_seconds()
                    await asyncio.sleep(min(sleep_seconds, 3600))
                    continue

                # Calculate next summary time (4:00 PM today or next trading day)
                target_time = now.replace(
                    hour=self.DAILY_SUMMARY_TIME.hour,
                    minute=self.DAILY_SUMMARY_TIME.minute,
                    second=0,
                    microsecond=0
                )

                # If already past 4:00 PM today, schedule for next trading day
                if now >= target_time:
                    target_time += timedelta(days=1)
                    while not self.market_hours.is_market_day(target_time.date()):
                        target_time += timedelta(days=1)

                # Wait until target time
                sleep_seconds = (target_time - now).total_seconds()
                logger.debug("Next daily summary at %s", target_time.strftime('%Y-%m-%d %H:%M'))

                await asyncio.sleep(sleep_seconds)

                # Generate daily summary
                await self._generate_daily_summary()

            except asyncio.CancelledError:
                logger.info("Daily summary task cancelled")
                break
            except Exception as e:
                logger.error("Error in daily summary task: %s", str(e), exc_info=True)
                await asyncio.sleep(3600)

    async def _run_weekly_summary_task(self):
        """
        TASK 4: Generate weekly summary

        Schedule: Sunday 6:00 PM IST (weekly)
        """
        logger.info("📈 Weekly summary task started")

        while self.is_running:
            try:
                now = datetime.now(self.market_hours.TIMEZONE)

                # Calculate next Sunday 6:00 PM
                days_until_sunday = (self.WEEKLY_SUMMARY_DAY - now.weekday()) % 7
                if days_until_sunday == 0 and now.time() >= self.WEEKLY_SUMMARY_TIME:
                    days_until_sunday = 7  # Next Sunday

                target_time = now + timedelta(days=days_until_sunday)
                target_time = target_time.replace(
                    hour=self.WEEKLY_SUMMARY_TIME.hour,
                    minute=self.WEEKLY_SUMMARY_TIME.minute,
                    second=0,
                    microsecond=0
                )

                # Wait until target time
                sleep_seconds = (target_time - now).total_seconds()
                logger.info("⏰ Next weekly summary at %s (in %.1f days)",
                           target_time.strftime('%Y-%m-%d %H:%M %Z'),
                           sleep_seconds / 86400)

                await asyncio.sleep(sleep_seconds)

                # Generate weekly summary
                await self._generate_weekly_summary()

            except asyncio.CancelledError:
                logger.info("Weekly summary task cancelled")
                break
            except Exception as e:
                logger.error("Error in weekly summary task: %s", str(e), exc_info=True)
                await asyncio.sleep(3600)

    async def _run_position_rebalancing_task(self):
        """
        TASK 5: Position rebalancing and integrity check

        Schedule: 11:00 AM IST (daily)
        Reason: Mid-market check
        """
        logger.info("⚖️ Position rebalancing task started")

        while self.is_running:
            try:
                now = datetime.now(self.market_hours.TIMEZONE)

                # Check if today is a trading day
                if not self.market_hours.is_market_day(now.date()):
                    next_open = self.market_hours.get_next_market_open(now)
                    sleep_seconds = (next_open - now).total_seconds()
                    await asyncio.sleep(min(sleep_seconds, 3600))
                    continue

                # Calculate next rebalancing time
                target_time = now.replace(
                    hour=self.POSITION_REBALANCE_TIME.hour,
                    minute=self.POSITION_REBALANCE_TIME.minute,
                    second=0,
                    microsecond=0
                )

                if now >= target_time:
                    target_time += timedelta(days=1)
                    while not self.market_hours.is_market_day(target_time.date()):
                        target_time += timedelta(days=1)

                sleep_seconds = (target_time - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

                # Perform rebalancing
                await self._rebalance_positions()

            except asyncio.CancelledError:
                logger.info("Position rebalancing task cancelled")
                break
            except Exception as e:
                logger.error("Error in position rebalancing: %s", str(e), exc_info=True)
                await asyncio.sleep(3600)

    async def _execute_pending_trades(self):
        """Execute pending paper trades that were queued when market was closed"""
        from ..database.models import PendingPaperTrade, DailyBuySignal, PaperPosition
        from ..services.paper_trade_execution_service import get_paper_trade_execution_service
        from ..services.analysis_service import get_current_price
        from datetime import datetime
        import asyncio
        
        logger.info("📋 Executing pending paper trades...")
        
        try:
            with get_db_context() as db:
                # Get all pending trades
                pending_trades = db.query(PendingPaperTrade).filter(
                    PendingPaperTrade.status == 'PENDING'
                ).all()
                
                if not pending_trades:
                    logger.info("No pending trades to execute")
                    return
                
                logger.info(f"Found {len(pending_trades)} pending trades")
                
                executed = 0
                failed = 0
                
                for pending in pending_trades:
                    try:
                        # Check if session is still active
                        session = pending.session
                        if not session or not session.is_active:
                            pending.status = 'CANCELLED'
                            pending.error_message = "Session no longer active"
                            db.commit()
                            continue
                        
                        # Check if already have position
                        existing = db.query(PaperPosition).filter(
                            PaperPosition.session_id == session.id,
                            PaperPosition.symbol == pending.symbol,
                            PaperPosition.is_open == True
                        ).first()
                        
                        if existing:
                            pending.status = 'CANCELLED'
                            pending.error_message = "Already have position"
                            db.commit()
                            continue
                        
                        # Get signal data
                        signal_data = pending.signal_data_dict
                        
                        # Create DailyBuySignal from stored data
                        signal = DailyBuySignal(
                            symbol=pending.symbol,
                            analysis_date=datetime.utcnow(),
                            recommendation=signal_data.get('recommendation', ''),
                            recommendation_type=signal_data.get('recommendation_type', 'BUY'),
                            current_price=signal_data.get('current_price', 0.0),
                            target=signal_data.get('target'),
                            stop_loss=signal_data.get('stop_loss'),
                            risk_reward=signal_data.get('risk_reward', 0.0),
                            confidence=signal_data.get('confidence', 0.0),
                            overall_score_pct=signal_data.get('overall_score_pct', 50.0),
                            analysis_data=json.dumps(signal_data.get('analysis', {}), default=str)
                        )
                        db.add(signal)
                        db.flush()
                        
                        # Get current price
                        loop = asyncio.get_event_loop()
                        current_price = await loop.run_in_executor(None, get_current_price, pending.symbol)
                        
                        if current_price is None:
                            current_price = signal.current_price
                        
                        # Execute trade
                        execution_service = get_paper_trade_execution_service(db)
                        
                        # Validate
                        is_valid, error_msg = execution_service.validate_entry(session, signal, current_price)
                        
                        if not is_valid:
                            pending.status = 'FAILED'
                            pending.error_message = error_msg
                            pending.execution_attempts += 1
                            pending.last_attempt_at = datetime.utcnow()
                            db.commit()
                            failed += 1
                            logger.warning(f"Pending trade validation failed for {pending.symbol}: {error_msg}")
                            continue
                        
                        # Enter position
                        position = await execution_service.enter_position(session, signal, current_price)
                        
                        if position:
                            pending.status = 'EXECUTED'
                            pending.position_id = position.id
                            pending.executed_at = datetime.utcnow()
                            executed += 1
                            logger.info(f"Executed pending trade for {pending.symbol}")

                            # Send individual trade execution notification
                            try:
                                await self._send_trade_execution_notification(
                                    session.user_id, pending.symbol, position, "individual"
                                )
                            except Exception as notify_error:
                                logger.error(f"Failed to send individual trade notification: {notify_error}")

                        else:
                            pending.status = 'FAILED'
                            pending.error_message = "Position entry returned None"
                            pending.execution_attempts += 1
                            pending.last_attempt_at = datetime.utcnow()
                            failed += 1
                        
                        db.commit()
                        
                    except Exception as e:
                        logger.error(f"Error executing pending trade {pending.id}: {e}", exc_info=True)
                        pending.status = 'FAILED'
                        pending.error_message = str(e)[:200]
                        pending.execution_attempts += 1
                        pending.last_attempt_at = datetime.utcnow()
                        failed += 1
                        db.commit()
                
                logger.info(f"Pending trades execution complete: {executed} executed, {failed} failed")

                # Send summary notification if any trades were executed
                if executed > 0:
                    try:
                        await self._send_trade_execution_summary_notification(executed, failed)
                    except Exception as notify_error:
                        logger.error(f"Failed to send summary notification: {notify_error}")

        except Exception as e:
            logger.error(f"Error executing pending trades: {e}", exc_info=True)

    async def _send_buy_signals_summary_notification(self, result: dict):
        """Send personalized summary notification for buy signals execution"""
        try:
            with get_db_context() as db:
                # Fix #2: Send personalized summary to each user showing only THEIR results
                from ..database.models import PaperTradingSession
                
                # Create dict mapping user_id to their results
                user_results = {}
                for detail in result.get('details', []):
                    user_id = detail.get('user_id')
                    user_results[user_id] = {
                        'opened': detail.get('opened', 0),
                        'skipped': detail.get('skipped', 0)
                    }
                
                # Send personalized notification to each user
                for user_id, user_result in user_results.items():
                    try:
                        # Create personalized message showing only THIS user's results
                        summary_message = (
                            f"🎯 *Daily Buy Signals Executed*\n\n"
                            f"✅ *{user_result['opened']}* position(s) opened for you\n"
                            f"⏭️ *{user_result['skipped']}* signal(s) skipped\n\n"
                        )
                        
                        # Add context based on results
                        if user_result['opened'] > 0:
                            summary_message += f"Check /papertrade status for details."
                        elif user_result['skipped'] > 0:
                            summary_message += f"Positions were skipped (limit reached or already have position)."
                        
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=summary_message,
                            parse_mode='Markdown'
                        )
                        logger.info(f"Sent personalized summary to user {user_id}: {user_result['opened']} opened, {user_result['skipped']} skipped")
                    except Exception as e:
                        logger.error(f"Failed to send summary to user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to send buy signals summary notifications: {e}")

    async def _send_trade_execution_notification(self, user_id: int, symbol: str, position, notification_type: str = "individual"):
        """Send notification to user about trade execution"""
        try:
            if notification_type == "individual":
                message = (
                    f"✅ *Paper Trade Executed*\n\n"
                    f"📈 *{symbol}*\n"
                    f"💰 Entry Price: ₹{position.entry_price:.2f}\n"
                    f"🎯 Target: ₹{position.target_price:.2f}\n"
                    f"🛡️ Stop Loss: ₹{position.stop_loss_price:.2f}\n"
                    f"📊 Shares: {position.shares:.2f}\n\n"
                    f"Trade executed automatically at market open."
                )
            else:
                # Summary notification
                message = f"✅ {position} paper trade(s) executed automatically at market open."

            # Send via Telegram bot
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )

            logger.info(f"Sent {notification_type} trade notification to user {user_id} for {symbol}")

        except Exception as e:
            logger.error(f"Failed to send trade notification to user {user_id}: {e}")

    async def _send_trade_execution_summary_notification(self, executed_count: int, failed_count: int):
        """Send summary notification to all users with active sessions"""
        try:
            with get_db_context() as db:
                # Get all active sessions
                from ..database.models import PaperTradingSession
                active_sessions = db.query(PaperTradingSession).filter(
                    PaperTradingSession.is_active == True
                ).all()

                summary_message = (
                    f"📊 *Paper Trading Summary*\n\n"
                    f"✅ *{executed_count}* trade(s) executed successfully\n"
                    f"❌ *{failed_count}* trade(s) failed\n\n"
                    f"All pending trades have been processed at market open."
                )

                for session in active_sessions:
                    try:
                        await self.application.bot.send_message(
                            chat_id=session.user_id,
                            text=summary_message,
                            parse_mode='Markdown'
                        )
                        logger.info(f"Sent summary notification to user {session.user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send summary to user {session.user_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to send summary notifications: {e}")

    async def _execute_buy_signals(self):
        """Execute BUY signals for all active sessions"""
        logger.info("🎯 Executing BUY signals...")

        try:
            with get_db_context() as db:
                # Pass notification callback to service for individual notifications
                trading_service = get_paper_trading_service(
                    db, 
                    notification_callback=self._send_trade_execution_notification
                )
                result = await trading_service.execute_buy_signals()

                logger.info(
                    "✅ BUY execution complete: %d sessions, %d signals, %d opened, %d skipped",
                    result['sessions_processed'],
                    result['signals_found'],
                    result['positions_opened'],
                    result['skipped']
                )

                # Send notifications about opened positions
                if result['positions_opened'] > 0:
                    try:
                        await self._send_buy_signals_summary_notification(result)
                    except Exception as notify_error:
                        logger.error(f"Failed to send buy signals summary notification: {notify_error}")

        except Exception as e:
            logger.error("Failed to execute BUY signals: %s", str(e), exc_info=True)

    async def _monitor_positions(self):
        """Monitor all open positions"""
        try:
            with get_db_context() as db:
                trading_service = get_paper_trading_service(db)
                result = await trading_service.monitor_positions()

                if result['positions_exited'] > 0 or result['trailing_stops_updated'] > 0:
                    logger.info(
                        "📊 Position monitoring: %d positions, %d exits, %d trailing stops",
                        result['positions_monitored'],
                        result['positions_exited'],
                        result['trailing_stops_updated']
                    )

                # TODO: Send notifications about closed positions

        except Exception as e:
            logger.error("Failed to monitor positions: %s", str(e), exc_info=True)

    async def _generate_daily_summary(self):
        """Generate and send daily summary"""
        logger.info("📊 Generating daily summary...")

        try:
            with get_db_context() as db:
                # Get all active sessions
                trading_service = get_paper_trading_service(db)
                analysis_service = get_paper_trade_analysis_service(db)

                # For each active session, generate summary
                from src.bot.database.models import PaperTradingSession
                sessions = db.query(PaperTradingSession).filter(
                    PaperTradingSession.is_active == True
                ).all()

                for session in sessions:
                    summary = await analysis_service.generate_daily_summary(session)

                    logger.info(
                        "📊 Daily summary for session %d: %d trades",
                        session.id,
                        summary['analytics'].trades_count if summary.get('analytics') else 0
                    )

                    # TODO: Send summary notification to user

        except Exception as e:
            logger.error("Failed to generate daily summary: %s", str(e), exc_info=True)

    async def _generate_weekly_summary(self):
        """Generate and send weekly summary"""
        logger.info("📈 Generating weekly summary...")

        try:
            with get_db_context() as db:
                trading_service = get_paper_trading_service(db)
                analysis_service = get_paper_trade_analysis_service(db)

                from src.bot.database.models import PaperTradingSession
                sessions = db.query(PaperTradingSession).filter(
                    PaperTradingSession.is_active == True
                ).all()

                for session in sessions:
                    summary = await analysis_service.generate_weekly_summary(session)

                    logger.info(
                        "📈 Weekly summary for session %d: %d trades, %d recommendations",
                        session.id,
                        summary['analytics'].trades_count if summary.get('analytics') else 0,
                        len(summary.get('recommendations', []))
                    )

                    # TODO: Send summary notification to user

        except Exception as e:
            logger.error("Failed to generate weekly summary: %s", str(e), exc_info=True)

    async def _rebalance_positions(self):
        """Validate and rebalance positions"""
        logger.debug("⚖️ Performing position rebalancing check...")

        try:
            with get_db_context() as db:
                from src.bot.database.models import PaperTradingSession, PaperPosition

                sessions = db.query(PaperTradingSession).filter(
                    PaperTradingSession.is_active == True
                ).all()

                for session in sessions:
                    # Validate position count
                    open_positions = db.query(PaperPosition).filter(
                        PaperPosition.session_id == session.id,
                        PaperPosition.is_open == True
                    ).count()

                    if open_positions != session.current_positions:
                        logger.warning(
                            "Position count mismatch for session %d: DB=%d, Session=%d",
                            session.id, open_positions, session.current_positions
                        )
                        session.current_positions = open_positions
                        db.commit()

                logger.debug("✅ Position rebalancing complete")

        except Exception as e:
            logger.error("Failed to rebalance positions: %s", str(e), exc_info=True)


# Module-level instance (will be set by scheduler_service)
_paper_trading_scheduler: Optional[PaperTradingScheduler] = None


def get_paper_trading_scheduler(application: Application) -> PaperTradingScheduler:
    """
    Get or create paper trading scheduler instance

    Args:
        application: Telegram application

    Returns:
        PaperTradingScheduler instance
    """
    global _paper_trading_scheduler
    if _paper_trading_scheduler is None:
        _paper_trading_scheduler = PaperTradingScheduler(application)
    return _paper_trading_scheduler
