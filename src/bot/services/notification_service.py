"""
Notification Service for Daily BUY Alerts
Sends formatted BUY signal reports to subscribed users

Author: Harsh Kandhway
"""

import logging
import asyncio
from typing import List
from datetime import datetime, timedelta
from telegram import Bot, User as TelegramUser

from src.bot.database.db import get_db_context
from src.bot.database.models import User, DailyBuySignal
from src.core.formatters import format_analysis_comprehensive, chunk_message
from src.bot.utils.formatters import format_analysis_condensed
from src.bot.utils.keyboards import create_full_report_keyboard
from src.bot.config import MAX_MESSAGE_LENGTH

logger = logging.getLogger(__name__)


async def send_daily_buy_alerts(bot: Bot, users) -> dict:
    """
    Send daily BUY alerts to subscribed users
    
    Args:
        bot: Telegram bot instance
        users: List of User objects OR list of dicts with {'user_id': int, 'telegram_id': int}
    
    Returns:
        dict with 'success': list of telegram_ids that received alerts,
                     'failed': list of dicts with {'telegram_id': int, 'error': str}
    """
    # Extract telegram_ids and user_ids from users
    # Support both User objects and dict format (from scheduler)
    user_data = []  # List of {'user_id': int, 'telegram_id': int}
    
    for user_item in users:
        try:
            # Check if it's a dict (from scheduler) or User object
            if isinstance(user_item, dict):
                # Scheduler passes dict with user_id and telegram_id
                user_id = user_item.get('user_id')
                telegram_id = user_item.get('telegram_id')
                if telegram_id:
                    user_data.append({'user_id': user_id, 'telegram_id': telegram_id})
            else:
                # Legacy: User object (try to extract telegram_id)
                telegram_id = getattr(user_item, 'telegram_id', None)
                user_id = getattr(user_item, 'id', None)
                if telegram_id:
                    user_data.append({'user_id': user_id, 'telegram_id': telegram_id})
        except Exception as e:
            logger.warning(f"Could not extract user data from user item: {e}")
            continue
    
    if not user_data:
        logger.warning("No valid users found for daily BUY alerts")
        return {'success': [], 'failed': []}
    
    # Get today's BUY signals and extract data within session
    from src.bot.database.db import get_today_buy_signals
    buy_signals_data = []
    
    with get_db_context() as db:
        buy_signals = get_today_buy_signals(db)
        
        # Extract all data from signals while in session
        # CRITICAL: Double-check filter to ensure no AVOID/BLOCKED signals are sent
        for signal in buy_signals:
            # Additional validation: Exclude any signals that shouldn't be sent
            # This is a safety check in case old data exists in database
            recommendation = signal.recommendation or ''
            recommendation_type = signal.recommendation_type or ''
            
            # Skip if it's not a valid BUY signal
            is_valid_buy = (
                recommendation_type == 'BUY' and
                'BLOCKED' not in recommendation.upper() and
                'AVOID' not in recommendation.upper()
            )
            
            if not is_valid_buy:
                logger.warning(
                    f"Skipping invalid BUY signal: {signal.symbol} - "
                    f"{recommendation} (Type: {recommendation_type})"
                )
                continue
            
            buy_signals_data.append({
                'symbol': signal.symbol,
                'recommendation': recommendation,
                'recommendation_type': recommendation_type,
                'confidence': signal.confidence,
                'overall_score_pct': signal.overall_score_pct,
                'risk_reward': signal.risk_reward,
                'current_price': signal.current_price,
                'target': signal.target,
                'stop_loss': signal.stop_loss,
                'data': signal.data  # This uses the hybrid_property which should work
            })
    
    # Track success and failures
    success_list = []
    failed_list = []
    
    if not buy_signals_data:
        # No BUY signals today
        for user_info in user_data:
            telegram_id = user_info['telegram_id']
            user_id = user_info.get('user_id')
            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        "🔔 *Daily BUY Alerts*\n\n"
                        "No BUY signals found today from our analysis of 4000+ stocks.\n\n"
                        "This is normal - we only show high-quality opportunities.\n\n"
                        "Check again tomorrow! 📊"
                    ),
                    parse_mode='Markdown'
                )
                # Mark as successfully sent
                success_list.append({'user_id': user_id, 'telegram_id': telegram_id})
                # Update last_sent timestamp
                if user_id:
                    from src.bot.database.db import update_user_settings
                    with get_db_context() as db:
                        update_user_settings(db, telegram_id, last_daily_alert_sent=datetime.now())
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error sending no-signals message to user {telegram_id}: {e}")
                failed_list.append({'user_id': user_id, 'telegram_id': telegram_id, 'error': error_msg})
        return {'success': success_list, 'failed': failed_list}
    
    # Group signals by recommendation type for better organization
    STRONG_BUY_KEY = 'STRONG BUY'
    WEAK_BUY_KEY = 'WEAK BUY'
    
    strong_buy = [s for s in buy_signals_data if STRONG_BUY_KEY in s['recommendation'].upper()]
    regular_buy = [s for s in buy_signals_data if s not in strong_buy and WEAK_BUY_KEY not in s['recommendation'].upper()]
    weak_buy = [s for s in buy_signals_data if WEAK_BUY_KEY in s['recommendation'].upper()]
    
    # Send alerts to each user
    # Track success and failures for retry mechanism
    success_list = []
    failed_list = []
    sent_alerts_today = set()  # Track sent alerts to prevent duplicates
    
    for user_info in user_data:
        telegram_id = user_info['telegram_id']
        user_id = user_info.get('user_id')
        
        # Skip if already sent alert to this user today (prevent duplicates)
        if telegram_id in sent_alerts_today:
            logger.debug(f"Skipping duplicate alert for user {telegram_id}")
            continue
        
        try:
            # Header message
            header = (
                f"🔔 *Daily BUY Alerts - {datetime.now().strftime('%d %b %Y')}*\n\n"
                f"Found *{len(buy_signals_data)}* BUY opportunities from 4000+ stocks:\n\n"
                f"• 🟢 STRONG BUY: {len(strong_buy)}\n"
                f"• ✅ BUY: {len(regular_buy)}\n"
                f"• 🟡 WEAK BUY: {len(weak_buy)}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            
            await bot.send_message(
                chat_id=telegram_id,
                text=header,
                parse_mode='Markdown'
            )
            
            # Send each signal (limit to top 20 to avoid spam)
            signals_to_send = buy_signals_data[:20]
            
            for i, signal_data in enumerate(signals_to_send, 1):
                try:
                    # Reconstruct full analysis dictionary from stored data
                    # This ensures we use the same comprehensive format as /analyze command
                    analysis_dict = signal_data.get('data', {})
                    
                    # Ensure analysis_dict has all required fields for format_analysis_comprehensive
                    required_fields = ['indicators', 'target_data', 'stop_data', 'safety_score', 'time_estimate']
                    
                    # If analysis_dict is empty or missing required fields, create fallback
                    if not analysis_dict or not isinstance(analysis_dict, dict) or not all(field in analysis_dict for field in required_fields):
                        # Fallback: Create minimal analysis dict from stored fields
                        symbol = signal_data['symbol']
                        
                        # Create minimal required structures with all required fields
                        # Get indicators from stored data if available, otherwise create minimal fallback
                        stored_indicators = analysis_dict.get('indicators', {}) if isinstance(analysis_dict, dict) else {}
                        
                        # Create complete indicators dict with all required fields for formatter
                        price = signal_data['current_price']
                        indicators = {
                            'price_vs_trend_ema': stored_indicators.get('price_vs_trend_ema', 'above'),
                            'price_vs_medium_ema': stored_indicators.get('price_vs_medium_ema', 'above'),
                            'price_vs_fast_ema': stored_indicators.get('price_vs_fast_ema', 'above'),
                            'market_phase': stored_indicators.get('market_phase', 'strong_uptrend'),
                            'ema_alignment': stored_indicators.get('ema_alignment', 'strong_bullish'),
                            'rsi': stored_indicators.get('rsi', 50.0),
                            'rsi_zone': stored_indicators.get('rsi_zone', 'neutral'),
                            'rsi_period': stored_indicators.get('rsi_period', 14),
                            'macd_hist': stored_indicators.get('macd_hist', 0.0),
                            'adx': stored_indicators.get('adx', 25.0),
                            'adx_strength': stored_indicators.get('adx_strength', 'strong_trend'),
                            'volume_ratio': stored_indicators.get('volume_ratio', 1.0),
                            'strongest_pattern': stored_indicators.get('strongest_pattern'),
                            'pattern_bias': stored_indicators.get('pattern_bias', 'bullish'),
                            'pattern_bullish_count': stored_indicators.get('pattern_bullish_count', 0),
                            'pattern_bearish_count': stored_indicators.get('pattern_bearish_count', 0),
                            'candlestick_patterns': stored_indicators.get('candlestick_patterns', []),
                            'chart_patterns': stored_indicators.get('chart_patterns', []),
                            'divergence': stored_indicators.get('divergence', 'none'),
                            'support': stored_indicators.get('support', price * 0.95),
                            'resistance': stored_indicators.get('resistance', price * 1.05),
                        }
                        
                        target_data = analysis_dict.get('target_data', {}) if isinstance(analysis_dict, dict) else {}
                        stop_data = analysis_dict.get('stop_data', {}) if isinstance(analysis_dict, dict) else {}
                        
                        # Ensure target_data and stop_data have required fields
                        if not target_data or 'recommended_target' not in target_data:
                            target = signal_data.get('target', price * 1.1)
                            target_data = {
                                'recommended_target': target,
                                'recommended_target_pct': ((target - price) / price) * 100 if price else 0,
                                'horizon_targets': {},
                                'recommended_timeframe': 90
                            }
                        
                        if not stop_data or 'recommended_stop' not in stop_data:
                            stop = signal_data.get('stop_loss', price * 0.95)
                            stop_data = {
                                'recommended_stop': stop,
                                'recommended_stop_pct': ((price - stop) / price) * 100 if price else 0
                            }
                        
                        analysis_dict = {
                            'symbol': symbol,
                            'current_price': signal_data['current_price'],
                            'recommendation': signal_data['recommendation'],
                            'recommendation_type': signal_data['recommendation_type'],
                            'confidence': signal_data['confidence'],
                            'overall_score_pct': signal_data['overall_score_pct'],
                            'risk_reward': signal_data['risk_reward'],
                            'target': signal_data.get('target'),
                            'stop_loss': signal_data.get('stop_loss'),
                            'mode': analysis_dict.get('mode', 'balanced') if isinstance(analysis_dict, dict) else 'balanced',
                            'timeframe': analysis_dict.get('timeframe', 'medium') if isinstance(analysis_dict, dict) else 'medium',
                            'horizon': analysis_dict.get('horizon', '3months') if isinstance(analysis_dict, dict) else '3months',
                            'indicators': indicators,
                            'target_data': target_data,
                            'stop_data': stop_data,
                            'safety_score': analysis_dict.get('safety_score', {}) if isinstance(analysis_dict, dict) else {},
                            'time_estimate': analysis_dict.get('time_estimate', {}) if isinstance(analysis_dict, dict) else {},
                            'is_buy_blocked': analysis_dict.get('is_buy_blocked', False) if isinstance(analysis_dict, dict) else False,
                            'buy_block_reasons': analysis_dict.get('buy_block_reasons', []) if isinstance(analysis_dict, dict) else [],
                            'rr_valid': analysis_dict.get('rr_valid', signal_data['risk_reward'] >= 2.0) if isinstance(analysis_dict, dict) else (signal_data['risk_reward'] >= 2.0),
                        }
                    else:
                        # Use stored analysis data (complete)
                        # Ensure all required fields are present
                        if 'target' not in analysis_dict:
                            analysis_dict['target'] = signal_data.get('target')
                        if 'stop_loss' not in analysis_dict:
                            analysis_dict['stop_loss'] = signal_data.get('stop_loss')
                        
                        # Ensure required nested structures exist with all required fields
                        price = signal_data['current_price']
                        
                        if 'indicators' not in analysis_dict or not analysis_dict['indicators']:
                            # Create complete indicators dict
                            stored_indicators = analysis_dict.get('indicators', {}) if 'indicators' in analysis_dict else {}
                            analysis_dict['indicators'] = {
                                'price_vs_trend_ema': stored_indicators.get('price_vs_trend_ema', 'above'),
                                'price_vs_medium_ema': stored_indicators.get('price_vs_medium_ema', 'above'),
                                'price_vs_fast_ema': stored_indicators.get('price_vs_fast_ema', 'above'),
                                'market_phase': stored_indicators.get('market_phase', 'strong_uptrend'),
                                'ema_alignment': stored_indicators.get('ema_alignment', 'strong_bullish'),
                                'rsi': stored_indicators.get('rsi', 50.0),
                                'rsi_zone': stored_indicators.get('rsi_zone', 'neutral'),
                                'rsi_period': stored_indicators.get('rsi_period', 14),
                                'macd_hist': stored_indicators.get('macd_hist', 0.0),
                                'adx': stored_indicators.get('adx', 25.0),
                                'adx_strength': stored_indicators.get('adx_strength', 'strong_trend'),
                                'volume_ratio': stored_indicators.get('volume_ratio', 1.0),
                                'strongest_pattern': stored_indicators.get('strongest_pattern'),
                                'pattern_bias': stored_indicators.get('pattern_bias', 'bullish'),
                                'pattern_bullish_count': stored_indicators.get('pattern_bullish_count', 0),
                                'pattern_bearish_count': stored_indicators.get('pattern_bearish_count', 0),
                                'candlestick_patterns': stored_indicators.get('candlestick_patterns', []),
                                'chart_patterns': stored_indicators.get('chart_patterns', []),
                                'divergence': stored_indicators.get('divergence', 'none'),
                                'support': stored_indicators.get('support', price * 0.95),
                                'resistance': stored_indicators.get('resistance', price * 1.05),
                            }
                        else:
                            # Ensure all required fields exist in existing indicators
                            stored_indicators = analysis_dict['indicators']
                            required_indicator_fields = {
                                'price_vs_trend_ema': 'above',
                                'market_phase': 'strong_uptrend',
                                'rsi': 50.0,
                                'rsi_zone': 'neutral',
                                'adx': 25.0,
                                'adx_strength': 'strong_trend',
                                'volume_ratio': 1.0,
                                'pattern_bias': 'bullish',
                                'divergence': 'none',
                            }
                            for field, default_value in required_indicator_fields.items():
                                if field not in stored_indicators:
                                    stored_indicators[field] = default_value
                            if 'support' not in stored_indicators:
                                stored_indicators['support'] = price * 0.95
                            if 'resistance' not in stored_indicators:
                                stored_indicators['resistance'] = price * 1.05
                        
                        if 'target_data' not in analysis_dict or 'recommended_target' not in analysis_dict.get('target_data', {}):
                            target = signal_data.get('target', price * 1.1)
                            analysis_dict['target_data'] = {
                                'recommended_target': target,
                                'recommended_target_pct': ((target - price) / price) * 100 if price else 0,
                                'horizon_targets': {},
                                'recommended_timeframe': 90
                            }
                        if 'stop_data' not in analysis_dict or 'recommended_stop' not in analysis_dict.get('stop_data', {}):
                            stop = signal_data.get('stop_loss', price * 0.95)
                            analysis_dict['stop_data'] = {
                                'recommended_stop': stop,
                                'recommended_stop_pct': ((price - stop) / price) * 100 if price else 0
                            }
                        if 'safety_score' not in analysis_dict:
                            analysis_dict['safety_score'] = {}
                        if 'time_estimate' not in analysis_dict:
                            analysis_dict['time_estimate'] = {}
                    
                    # Use CONDENSED formatter for notifications (much shorter)
                    symbol = signal_data['symbol']
                    formatted = format_analysis_condensed(analysis_dict)
                    
                    # Add signal number header
                    signal_header = f"*[{i}/{len(signals_to_send)}] {symbol}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    condensed_message = signal_header + formatted
                    
                    # Create keyboard with button to get full report
                    keyboard = create_full_report_keyboard(symbol)
                    
                    # Send condensed message with button
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=condensed_message,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                    
                    # Delay between signals
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error sending signal {signal_data.get('symbol', 'UNKNOWN')} to user {telegram_id}: {e}", exc_info=True)
                    continue
            
            # Footer message if there are more signals
            if len(buy_signals_data) > 20:
                footer = (
                    f"\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"*Showing top 20 signals*\n"
                    f"Total BUY signals today: {len(buy_signals_data)}\n\n"
                    f"Use `/analyze SYMBOL` to analyze any specific stock."
                )
                await bot.send_message(
                    chat_id=telegram_id,
                    text=footer,
                    parse_mode='Markdown'
                )
            
            logger.info(f"Sent daily BUY alerts to user {telegram_id} ({len(signals_to_send)} signals)")
            
            # Mark as successfully sent
            success_list.append({'user_id': user_id, 'telegram_id': telegram_id})
            
            # Update last_sent timestamp in database
            if user_id:
                from src.bot.database.db import update_user_settings
                with get_db_context() as db:
                    update_user_settings(db, telegram_id, last_daily_alert_sent=datetime.now())
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error sending daily BUY alerts to user {telegram_id}: {e}", exc_info=True)
            failed_list.append({'user_id': user_id, 'telegram_id': telegram_id, 'error': error_msg})
    
    # Return status for retry mechanism
    return {'success': success_list, 'failed': failed_list}


async def send_test_alert(bot: Bot, user_id: int):
    """
    Send a test alert to a user (for testing purposes)
    
    Args:
        bot: Telegram bot instance
        user_id: Telegram user ID
    """
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🧪 *Test Daily BUY Alert*\n\n"
                "This is a test message to verify your daily BUY alerts subscription is working.\n\n"
                "You'll receive real BUY signals daily at your preferred time.\n\n"
                "Use `/settings` to manage your subscription."
            ),
            parse_mode='Markdown'
        )
        logger.info(f"Sent test alert to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending test alert to user {user_id}: {e}")

