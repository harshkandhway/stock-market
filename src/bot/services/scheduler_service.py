"""
Daily BUY Alerts Scheduler Service
Handles scheduling and execution of daily stock analysis and notifications

Author: Harsh Kandhway
"""

import logging
import asyncio
from datetime import datetime, time, timedelta
from typing import List, Dict, Any
import pytz

from telegram import Bot
from telegram.ext import Application

from src.bot.config import TELEGRAM_BOT_TOKEN, DEFAULT_TIMEZONE
from src.bot.database.db import get_db_context
from src.bot.database.models import User, UserSettings, DailyBuySignal
from src.bot.services.analysis_service import analyze_stock
from src.bot.utils.formatters import format_analysis_full
from src.bot.services.notification_service import send_daily_buy_alerts

logger = logging.getLogger(__name__)


class DailyBuyAlertsScheduler:
    """Scheduler for daily BUY alerts analysis and notifications"""

    def __init__(self, application: Application):
        """
        Initialize scheduler

        Args:
            application: Telegram bot application instance
        """
        self.application = application
        self.bot = application.bot
        self.is_running = False
        self.analysis_task = None
        self.notification_task = None
        self.retry_task = None

        # Paper trading scheduler (NEW)
        self.paper_trading_scheduler = None
    
    async def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True
        logger.info("Starting Daily BUY Alerts Scheduler...")

        # Start analysis task (runs once daily)
        self.analysis_task = asyncio.create_task(self._run_daily_analysis())

        # Start notification task (runs every 30 seconds to check for users to notify)
        self.notification_task = asyncio.create_task(self._run_notification_checker())

        # Start retry task (runs every 2 minutes to retry failed alerts)
        self.retry_task = asyncio.create_task(self._run_retry_checker())

        logger.info("Daily BUY Alerts Scheduler started")

        # Start paper trading scheduler (NEW)
        try:
            from src.bot.services.paper_trading_scheduler import get_paper_trading_scheduler
            self.paper_trading_scheduler = get_paper_trading_scheduler(self.application)
            await self.paper_trading_scheduler.start()
            logger.info("✅ Paper Trading Scheduler integrated and started")
        except Exception as e:
            logger.error("Failed to start paper trading scheduler: %s", str(e), exc_info=True)
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping Daily BUY Alerts Scheduler...")
        
        if self.analysis_task:
            self.analysis_task.cancel()
        if self.notification_task:
            self.notification_task.cancel()
        if self.retry_task:
            self.retry_task.cancel()
        
        # Stop paper trading scheduler
        if self.paper_trading_scheduler:
            try:
                await self.paper_trading_scheduler.stop()
                logger.info("✅ Paper Trading Scheduler stopped")
            except Exception as e:
                logger.error("Error stopping paper trading scheduler: %s", str(e), exc_info=True)
        
        logger.info("Daily BUY Alerts Scheduler stopped")
    
    async def _run_daily_analysis(self):
        """Run daily analysis of all stocks"""
        while self.is_running:
            try:
                # Run analysis at 4:15 AM IST (for testing - normally 6:00 AM before market opens)
                now = datetime.now(pytz.timezone(DEFAULT_TIMEZONE))
                target_time = now.replace(hour=4, minute=15, second=0, microsecond=0)
                
                # If already past 6 AM today, schedule for tomorrow
                if now > target_time:
                    target_time += timedelta(days=1)
                
                # Calculate seconds until target time
                wait_seconds = (target_time - now).total_seconds()
                
                logger.info(f"Daily analysis scheduled for {target_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                logger.info(f"Waiting {wait_seconds/3600:.1f} hours until next analysis")
                
                # Wait until target time
                await asyncio.sleep(wait_seconds)
                
                # Run the analysis
                logger.info("Starting daily BUY signals analysis...")
                await self._analyze_all_stocks()
                logger.info("Daily BUY signals analysis completed")
                
            except asyncio.CancelledError:
                logger.info("Daily analysis task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in daily analysis task: {e}", exc_info=True)
                # Wait 1 hour before retrying on error
                await asyncio.sleep(3600)
    
    async def _analyze_all_stocks(self):
        """
        Analyze all stocks from CSV and save BUY signals to database
        """
        import csv
        import os
        import pandas as pd
        
        csv_path = os.path.join(os.path.dirname(__file__), '../../../data/stock_tickers_enhanced.csv')
        
        if not os.path.exists(csv_path):
            logger.error(f"Enhanced stock tickers CSV not found at {csv_path}")
            raise FileNotFoundError(f"Required file not found: {csv_path}")
            return
        
        # Read all stock symbols
        stocks = []
        try:
            # Read enhanced CSV with pandas
            df = pd.read_csv(csv_path)
            
            # Filter out ETFs - only analyze stocks for daily alerts
            if 'is_etf' in df.columns:
                original_count = len(df)
                df = df[df['is_etf'] == False]
                logger.info(f"Filtered {original_count} entries to {len(df)} stocks (excluded {original_count - len(df)} ETFs)")
            
            # Extract stock symbols
            for _, row in df.iterrows():
                symbol = row['ticker'].strip().upper()
                if symbol:
                    stocks.append(symbol)
        except Exception as e:
            logger.error(f"Error reading stock tickers CSV: {e}")
            return
        
        logger.info(f"Analyzing {len(stocks)} stocks for BUY signals...")
        
        # Get default settings for analysis
        mode = 'balanced'
        timeframe = 'medium'
        horizon = '3months'
        
        buy_signals = []
        errors = 0
        analyzed = 0
        
        # Analyze each stock
        for i, symbol in enumerate(stocks, 1):
            try:
                # Analyze stock (run in executor since analyze_stock is synchronous)
                loop = asyncio.get_event_loop()
                # Use functools.partial to avoid lambda closure issues
                from functools import partial
                analysis = await loop.run_in_executor(
                    None,
                    partial(
                        analyze_stock,
                        symbol=symbol,
                        mode=mode,
                        timeframe=timeframe,
                        horizon=horizon,
                        use_cache=False
                    )
                )
                
                analyzed += 1
                
                # Check if it's a BUY signal
                recommendation_type = analysis.get('recommendation_type', '')
                recommendation = analysis.get('recommendation', '')
                
                # Filter for BUY signals (STRONG BUY, BUY, WEAK BUY)
                # Exclude "AVOID - BUY BLOCKED" and other blocked signals
                is_buy_signal = (
                    recommendation_type == 'BUY' and 
                    'BLOCKED' not in recommendation.upper() and
                    'AVOID' not in recommendation.upper()
                )
                
                if is_buy_signal:
                    # Save to database
                    await self._save_buy_signal(symbol, analysis)
                    buy_signals.append(symbol)
                    
                    if len(buy_signals) % 10 == 0:
                        logger.info(f"Found {len(buy_signals)} BUY signals so far...")
                
                # Progress logging
                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{len(stocks)} stocks analyzed ({analyzed} successful, {errors} errors)")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                errors += 1
                if errors <= 10:  # Log first 10 errors
                    logger.warning(f"Error analyzing {symbol}: {e}")
                continue
        
        logger.info(f"Daily analysis complete: {len(buy_signals)} BUY signals found from {analyzed} successful analyses ({errors} errors)")
        
        # Store summary in database
        with get_db_context() as db:
            # Clean old signals (older than 2 days)
            cutoff_date = datetime.utcnow() - timedelta(days=2)
            deleted = db.query(DailyBuySignal).filter(
                DailyBuySignal.analysis_date < cutoff_date
            ).delete()
            db.commit()
            logger.info(f"Cleaned up {deleted} old BUY signals")
    
    async def _save_buy_signal(self, symbol: str, analysis: Dict[str, Any]):
        """
        Save BUY signal to database
        
        Args:
            symbol: Stock symbol
            analysis: Analysis dictionary
        """
        import json
        
        with get_db_context() as db:
            # Check if signal already exists for today
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            existing = db.query(DailyBuySignal).filter(
                DailyBuySignal.symbol == symbol,
                DailyBuySignal.analysis_date >= today
            ).first()
            
            if existing:
                # Update existing signal
                existing.recommendation = analysis.get('recommendation', '')
                existing.recommendation_type = analysis.get('recommendation_type', '')
                existing.confidence = analysis.get('confidence', 0.0)
                existing.overall_score_pct = analysis.get('overall_score_pct', 0.0)
                existing.risk_reward = analysis.get('risk_reward', 0.0)
                existing.current_price = analysis.get('current_price', 0.0)
                existing.target = analysis.get('target')
                existing.stop_loss = analysis.get('stop_loss')
                existing.analysis_data = json.dumps(analysis, default=str)
                existing.analysis_date = datetime.utcnow()
            else:
                # Create new signal
                signal = DailyBuySignal(
                    symbol=symbol,
                    analysis_date=datetime.utcnow(),
                    recommendation=analysis.get('recommendation', ''),
                    recommendation_type=analysis.get('recommendation_type', ''),
                    confidence=analysis.get('confidence', 0.0),
                    overall_score_pct=analysis.get('overall_score_pct', 0.0),
                    risk_reward=analysis.get('risk_reward', 0.0),
                    current_price=analysis.get('current_price', 0.0),
                    target=analysis.get('target'),
                    stop_loss=analysis.get('stop_loss'),
                    analysis_data=json.dumps(analysis, default=str)
                )
                db.add(signal)
            
            db.commit()
    
    async def _run_notification_checker(self):
        """Check every 30 seconds if any users need to be notified"""
        while self.is_running:
            try:
                # Check every 30 seconds for more reliable triggering
                await asyncio.sleep(30)
                
                # Get current time in various timezones
                now_utc = datetime.utcnow()
                
                # Get all subscribed users and their settings within session
                from src.bot.database.db import get_subscribed_users_for_daily_buy_alerts
                from src.bot.database.models import UserSettings
                
                users_to_notify = []
                
                with get_db_context() as db:
                    users = get_subscribed_users_for_daily_buy_alerts(db)
                    
                    if not users:
                        continue
                    
                    # Check each user's alert time (access settings within session)
                    for user in users:
                        # Access settings within session to avoid detached instance error
                        settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
                        
                        if not settings or not settings.daily_buy_alerts_enabled:
                            continue
                        
                        alert_time_str = settings.daily_buy_alert_time or '09:00'
                        user_timezone = settings.timezone or DEFAULT_TIMEZONE
                        
                        try:
                            # Parse alert time
                            hour, minute = map(int, alert_time_str.split(':'))
                            
                            # Get current time in user's timezone
                            user_tz = pytz.timezone(user_timezone)
                            now_user = datetime.now(user_tz)
                            
                            # Check if it's time to notify
                            # Strategy: Check if current hour:minute matches target hour:minute
                            # This ensures we trigger during the entire target minute
                            current_hour = now_user.hour
                            current_minute = now_user.minute
                            
                            # Calculate time difference (positive = after target, negative = before target)
                            target_time = now_user.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            time_diff_seconds = (now_user - target_time).total_seconds()
                            
                            # Notify if:
                            # 1. Current hour:minute exactly matches target hour:minute (triggers during entire minute)
                            # 2. OR we're within 30 seconds AFTER target time (for edge cases, but not before)
                            # Note: We check every 30 seconds, so we'll catch the target minute reliably
                            # We don't trigger BEFORE the target time to avoid premature alerts
                            should_notify = (
                                (current_hour == hour and current_minute == minute) or
                                (0 <= time_diff_seconds <= 30)  # Only trigger during or slightly after target
                            )
                            
                            if should_notify:
                                # CRITICAL: Extract telegram_id while still in session
                                # Store both user.id and telegram_id to avoid detached instance errors
                                telegram_id = user.telegram_id
                                user_id = user.id
                                users_to_notify.append({
                                    'user_id': user_id,
                                    'telegram_id': telegram_id
                                })
                                # Calculate time difference for logging
                                target_time = now_user.replace(hour=hour, minute=minute, second=0, microsecond=0)
                                time_diff_seconds = abs((now_user - target_time).total_seconds())
                                
                                logger.info(
                                    f"User {telegram_id} scheduled for notification "
                                    f"(current: {current_hour:02d}:{current_minute:02d}, "
                                    f"target: {hour:02d}:{minute:02d}, diff: {time_diff_seconds:.0f}s)"
                                )
                        except Exception as e:
                            logger.warning(f"Error checking alert time for user {user.telegram_id}: {e}")
                            continue
                
                # Send notifications to users
                if users_to_notify:
                    logger.info(f"Sending daily BUY alerts to {len(users_to_notify)} users")
                    result = await send_daily_buy_alerts(self.bot, users_to_notify)
                    
                    # Track failed alerts for retry (save to database)
                    if result and result.get('failed'):
                        from src.bot.database.db import create_pending_alert
                        for failed_user in result['failed']:
                            user_id = failed_user.get('user_id')
                            telegram_id = failed_user.get('telegram_id')
                            error = failed_user.get('error', 'Unknown error')
                            
                            if user_id and telegram_id:
                                # Save to database for persistent retry
                                with get_db_context() as db:
                                    create_pending_alert(
                                        db,
                                        user_id=user_id,
                                        telegram_id=telegram_id,
                                        target_time=datetime.now(pytz.timezone(DEFAULT_TIMEZONE)),
                                        error_message=error
                                    )
                                logger.warning(
                                    f"Alert failed for user {telegram_id}, saved to database for retry. Error: {error}"
                                )
                    
                    # Log successful sends and remove from pending
                    if result and result.get('success'):
                        from src.bot.database.db import delete_pending_alert
                        for success_user in result['success']:
                            telegram_id = success_user.get('telegram_id')
                            user_id = success_user.get('user_id')
                            logger.info(f"Successfully sent alert to user {telegram_id}")
                            
                            # Remove from pending alerts in database
                            if user_id:
                                with get_db_context() as db:
                                    if delete_pending_alert(db, user_id):
                                        logger.info(f"Removed user {user_id} from pending alerts (successfully sent)")
                
            except asyncio.CancelledError:
                logger.info("Notification checker task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in notification checker: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _run_retry_checker(self):
        """Retry failed alerts every 2 minutes until successfully sent"""
        from src.bot.database.db import (
            get_pending_alerts, delete_pending_alert, increment_pending_alert_retry,
            get_pending_alert_by_user_id
        )
        
        while self.is_running:
            try:
                # Check every 2 minutes
                await asyncio.sleep(120)
                
                # Get pending alerts from database
                with get_db_context() as db:
                    pending_alerts = get_pending_alerts(db)
                
                if not pending_alerts:
                    continue
                
                logger.info(f"Checking {len(pending_alerts)} pending alerts for retry")
                
                # Retry pending alerts
                users_to_retry = []
                for pending in pending_alerts:
                    # Maximum 10 retries (20 minutes total)
                    if pending.retry_count >= 10:
                        logger.error(
                            f"Max retries reached for user {pending.telegram_id}. "
                            f"Removing from pending alerts."
                        )
                        with get_db_context() as db:
                            delete_pending_alert(db, pending.user_id)
                        continue
                    
                    # Increment retry count in database
                    with get_db_context() as db:
                        increment_pending_alert_retry(db, pending.user_id)
                    
                    # Add to retry list
                    users_to_retry.append({
                        'user_id': pending.user_id,
                        'telegram_id': pending.telegram_id
                    })
                
                if users_to_retry:
                    logger.info(f"Retrying {len(users_to_retry)} failed alerts")
                    result = await send_daily_buy_alerts(self.bot, users_to_retry)
                    
                    # Process results
                    if result:
                        # Remove successfully sent from pending
                        if result.get('success'):
                            for success_user in result['success']:
                                user_id = success_user.get('user_id')
                                telegram_id = success_user.get('telegram_id')
                                if user_id:
                                    with get_db_context() as db:
                                        pending = get_pending_alert_by_user_id(db, user_id)
                                        if pending:
                                            retry_count = pending.retry_count
                                            delete_pending_alert(db, user_id)
                                            logger.info(
                                                f"Successfully sent alert to user {telegram_id} on retry "
                                                f"(attempt {retry_count})"
                                            )
                        
                        # Update error message for still-failed alerts
                        if result.get('failed'):
                            for failed_user in result['failed']:
                                user_id = failed_user.get('user_id')
                                telegram_id = failed_user.get('telegram_id')
                                error = failed_user.get('error', 'Unknown error')
                                
                                if user_id:
                                    with get_db_context() as db:
                                        pending = get_pending_alert_by_user_id(db, user_id)
                                        if pending:
                                            pending.error_message = error
                                            pending.last_retry_at = datetime.now()
                                            db.commit()
                                            logger.warning(
                                                f"Retry {pending.retry_count} failed for user {telegram_id}. "
                                                f"Error: {error}. Will retry again."
                                            )
                
            except asyncio.CancelledError:
                logger.info("Retry checker task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in retry checker: {e}", exc_info=True)
                await asyncio.sleep(120)  # Wait before retrying


# Global scheduler instance
_scheduler: DailyBuyAlertsScheduler = None


def get_scheduler(application: Application = None) -> DailyBuyAlertsScheduler:
    """
    Get or create scheduler instance
    
    Args:
        application: Telegram bot application (required for first call)
    
    Returns:
        DailyBuyAlertsScheduler instance
    """
    global _scheduler
    
    if _scheduler is None and application is not None:
        _scheduler = DailyBuyAlertsScheduler(application)
    
    return _scheduler


async def start_scheduler(application: Application):
    """Start the daily BUY alerts scheduler"""
    scheduler = get_scheduler(application)
    await scheduler.start()


async def stop_scheduler():
    """Stop the daily BUY alerts scheduler"""
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.stop()

