"""
Alert Checking Service

This service runs in the background and checks all active alerts periodically.
When an alert condition is met, it sends a notification to the user.

Uses APScheduler to run checks every N minutes (configured in config.py).
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

from ..database.db import (
    get_db_context,
    get_user_alerts,
    update_alert_status,
    update_alert_last_checked
)
from ..database.models import Alert
from .analysis_service import get_current_price, analyze_stock
from ..utils.formatters import format_success, format_warning
from ..config import ALERT_CHECK_INTERVAL_MINUTES

logger = logging.getLogger(__name__)


class AlertService:
    """
    Background service for checking and triggering alerts.
    """
    
    def __init__(self, bot: Bot):
        """
        Initialize alert service.
        
        Args:
            bot: Telegram bot instance for sending notifications
        """
        self.bot = bot
        self.is_running = False
        logger.info("Alert service initialized")
    
    async def check_all_alerts(self) -> Dict[str, Any]:
        """
        Check all active alerts across all users.
        
        Returns:
            Dict with statistics about checked and triggered alerts
        """
        if not self.is_running:
            return {'error': 'Alert service not running'}
        
        stats = {
            'checked': 0,
            'triggered': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            with get_db_context() as db:
                # Get all active alerts
                # Note: get_user_alerts only gets alerts for specific user
                # We need to get all active alerts across all users
                from ..database.models import Alert
                from sqlalchemy.orm import joinedload
                alerts = db.query(Alert).options(joinedload(Alert.user)).filter(Alert.is_active == True).all()
                
                logger.info(f"Checking {len(alerts)} active alerts")
                
                for alert in alerts:
                    try:
                        stats['checked'] += 1
                        
                        # Check alert condition
                        triggered = await self._check_alert(alert)
                        
                        if triggered:
                            # Send notification to user
                            await self._send_alert_notification(alert)
                            
                            # Mark alert as triggered
                            update_alert_status(db, alert.id, is_active=False)
                            stats['triggered'] += 1
                            
                            telegram_id = alert.user.telegram_id if alert.user else 'unknown'
                            logger.info(
                                f"Alert triggered: ID={alert.id}, "
                                f"User={telegram_id}, Symbol={alert.symbol}"
                            )
                        else:
                            # Update last checked time
                            update_alert_last_checked(db, alert.id)
                    
                    except Exception as e:
                        stats['failed'] += 1
                        error_msg = f"Error checking alert {alert.id}: {str(e)}"
                        stats['errors'].append(error_msg)
                        logger.error(error_msg, exc_info=True)
                
                logger.info(
                    f"Alert check complete: "
                    f"checked={stats['checked']}, "
                    f"triggered={stats['triggered']}, "
                    f"failed={stats['failed']}"
                )
        
        except Exception as e:
            error_msg = f"Error in check_all_alerts: {str(e)}"
            stats['errors'].append(error_msg)
            logger.error(error_msg, exc_info=True)
        
        return stats
    
    async def _check_alert(self, alert: Alert) -> bool:
        """
        Check if an alert condition is met.
        
        Args:
            alert: Alert object to check
        
        Returns:
            True if alert should be triggered, False otherwise
        """
        try:
            if alert.alert_type == 'price':
                return await self._check_price_alert(alert)
            elif alert.alert_type == 'rsi':
                return await self._check_rsi_alert(alert)
            elif alert.alert_type == 'signal_change':
                return await self._check_signal_change_alert(alert)
            else:
                logger.warning(f"Unknown alert type: {alert.alert_type}")
                return False
        
        except Exception as e:
            logger.error(f"Error checking alert {alert.id}: {e}", exc_info=True)
            return False
    
    async def _check_price_alert(self, alert: Alert) -> bool:
        """Check price alert condition."""
        try:
            current_price = get_current_price(alert.symbol)
            
            condition = alert.params
            operator = condition.get('operator')
            target_value = condition.get('value')
            
            if operator == '>':
                return current_price > target_value
            elif operator == '<':
                return current_price < target_value
            elif operator == '>=':
                return current_price >= target_value
            elif operator == '<=':
                return current_price <= target_value
            else:
                logger.warning(f"Unknown operator in price alert: {operator}")
                return False
        
        except Exception as e:
            logger.error(f"Error checking price alert: {e}")
            return False
    
    async def _check_rsi_alert(self, alert: Alert) -> bool:
        """Check RSI alert condition."""
        try:
            # Perform analysis to get RSI
            result = analyze_stock(alert.symbol)
            if result['status'] != 'success':
                return False
            analysis_data = result['data']
            
            rsi = analysis_data.get('indicators', {}).get('rsi')
            if rsi is None:
                return False
            
            condition = alert.params
            operator = condition.get('operator')
            target_value = condition.get('value')
            
            if operator == '>':
                return rsi > target_value
            elif operator == '<':
                return rsi < target_value
            else:
                logger.warning(f"Unknown operator in RSI alert: {operator}")
                return False
        
        except Exception as e:
            logger.error(f"Error checking RSI alert: {e}")
            return False
    
    async def _check_signal_change_alert(self, alert: Alert) -> bool:
        """Check signal change alert condition."""
        try:
            # Get current analysis
            result = analyze_stock(alert.symbol)
            if result['status'] != 'success':
                return False
            
            current_recommendation = result['data']['recommendation']
            
            # Get last known recommendation from alert data
            params = alert.params
            last_recommendation = params.get('last_recommendation')
            
            if last_recommendation is None:
                # First check - store current recommendation
                with get_db_context() as db:
                    # Reload alert in this session
                    db_alert = db.query(Alert).filter(Alert.id == alert.id).first()
                    if db_alert:
                        updated_params = db_alert.params.copy()
                        updated_params['last_recommendation'] = current_recommendation
                        db_alert.params = updated_params
                        db.commit()
                return False
            
            # Check if recommendation changed
            if current_recommendation != last_recommendation:
                # Update last recommendation
                with get_db_context() as db:
                    # Reload alert in this session
                    db_alert = db.query(Alert).filter(Alert.id == alert.id).first()
                    if db_alert:
                        updated_params = db_alert.params.copy()
                        updated_params['last_recommendation'] = current_recommendation
                        db_alert.params = updated_params
                        db.commit()
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking signal change alert: {e}")
            return False
    
    async def _send_alert_notification(self, alert: Alert) -> None:
        """
        Send alert notification to user.
        
        Args:
            alert: Alert that was triggered
        """
        try:
            # Format notification message based on alert type
            if alert.alert_type == 'price':
                message = await self._format_price_alert_notification(alert)
            elif alert.alert_type == 'rsi':
                message = await self._format_rsi_alert_notification(alert)
            elif alert.alert_type == 'signal_change':
                message = await self._format_signal_change_notification(alert)
            else:
                message = (
                    f"🔔 *Alert Triggered!*\n\n"
                    f"*Symbol:* {alert.symbol}\n"
                    f"*Type:* {alert.alert_type}\n"
                    f"*Message:* {alert.message}"
                )
            
            # Send notification
            # alert.user_id is the database foreign key, we need telegram_id
            telegram_id = alert.user.telegram_id if alert.user else None
            if not telegram_id:
                logger.error(f"Could not get telegram_id for alert {alert.id}")
                return
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Sent alert notification to user {telegram_id}")
        
        except TelegramError as e:
            logger.error(f"Error sending alert notification: {e}", exc_info=True)
            # Don't raise - we don't want to stop checking other alerts
        except Exception as e:
            logger.error(f"Unexpected error sending notification: {e}", exc_info=True)
    
    async def _format_price_alert_notification(self, alert: Alert) -> str:
        """Format price alert notification."""
        try:
            current_price = get_current_price(alert.symbol)
            target_price = alert.params.get('value')
            
            message = (
                f"🔔 *Price Alert Triggered!*\n\n"
                f"*Symbol:* {alert.symbol}\n"
                f"*Current Price:* ₹{current_price:.2f}\n"
                f"*Target Price:* ₹{target_price:.2f}\n\n"
                f"Your target price has been reached!\n\n"
                f"Use `/analyze {alert.symbol}` for current analysis."
            )
            
            return message
        
        except Exception as e:
            logger.error(f"Error formatting price alert: {e}")
            return f"🔔 Alert triggered for {alert.symbol}"
    
    async def _format_rsi_alert_notification(self, alert: Alert) -> str:
        """Format RSI alert notification."""
        try:
            # Get current RSI
            result = analyze_stock(alert.symbol)
            if result['status'] == 'success':
                rsi = result['data'].get('indicators', {}).get('rsi')
                rsi_str = f"{rsi:.2f}" if rsi else "N/A"
            else:
                rsi_str = "N/A"
            
            target_value = alert.params.get('value')
            operator = alert.params.get('operator')
            
            condition_str = "overbought (>70)" if operator == '>' else "oversold (<30)"
            
            message = (
                f"🔔 *RSI Alert Triggered!*\n\n"
                f"*Symbol:* {alert.symbol}\n"
                f"*Current RSI:* {rsi_str}\n"
                f"*Condition:* RSI is {condition_str}\n\n"
                f"Use `/analyze {alert.symbol}` for full analysis."
            )
            
            return message
        
        except Exception as e:
            logger.error(f"Error formatting RSI alert: {e}")
            return f"🔔 RSI alert triggered for {alert.symbol}"
    
    async def _format_signal_change_notification(self, alert: Alert) -> str:
        """Format signal change alert notification."""
        try:
            # Get current analysis
            result = analyze_stock(alert.symbol)
            if result['status'] == 'success':
                recommendation = result['data'].get('recommendation', 'UNKNOWN')
                confidence = result['data'].get('confidence', 0)
                price = result['data'].get('current_price', 0)
            else:
                recommendation = "UNKNOWN"
                confidence = 0
                price = 0
            
            # Get emoji for recommendation
            rec_emoji = {
                'STRONG BUY': '🟢',
                'BUY': '🟢',
                'HOLD': '🟡',
                'SELL': '🔴',
                'STRONG SELL': '🔴'
            }.get(recommendation, '⚪')
            
            message = (
                f"🔔 *Signal Change Alert!*\n\n"
                f"*Symbol:* {alert.symbol}\n"
                f"*New Signal:* {rec_emoji} {recommendation}\n"
                f"*Confidence:* {confidence:.0f}%\n"
                f"*Current Price:* ₹{price:.2f}\n\n"
                f"The recommendation has changed!\n\n"
                f"Use `/analyze {alert.symbol}` for full details."
            )
            
            return message
        
        except Exception as e:
            logger.error(f"Error formatting signal change alert: {e}")
            return f"🔔 Signal changed for {alert.symbol}"
    
    def start(self) -> None:
        """Start the alert service."""
        self.is_running = True
        logger.info("Alert service started")
    
    def stop(self) -> None:
        """Stop the alert service."""
        self.is_running = False
        logger.info("Alert service stopped")
