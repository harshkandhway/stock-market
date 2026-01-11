"""
Paper Trading Notification Service
Sends real-time trade alerts and daily/weekly summaries

Author: Harsh Kandhway
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from telegram import Bot
from telegram.error import TelegramError

from src.bot.database.models import User, PaperTradingSession

logger = logging.getLogger(__name__)


async def send_trade_execution_alert(
    bot: Bot,
    telegram_id: int,
    trade_type: str,  # 'entry' or 'exit'
    trade_data: Dict
) -> bool:
    """
    Send real-time trade execution alert

    Args:
        bot: Telegram bot instance
        telegram_id: User's Telegram ID
        trade_type: 'entry' or 'exit'
        trade_data: Trade data dictionary

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        if trade_type == 'entry':
            message = _format_entry_alert(trade_data)
        elif trade_type == 'exit':
            message = _format_exit_alert(trade_data)
        else:
            logger.error(f"Invalid trade_type: {trade_type}")
            return False

        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='Markdown'
        )

        logger.info(f"✅ Sent {trade_type} alert to user {telegram_id}")
        return True

    except TelegramError as e:
        logger.error(f"Telegram error sending {trade_type} alert: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending {trade_type} alert: {e}", exc_info=True)
        return False


def _format_entry_alert(data: Dict) -> str:
    """Format position entry alert"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    shares = data.get('shares', 0)
    position_value = data.get('position_value', 0)
    risk_amount = data.get('risk_amount', 0)
    recommendation = data.get('recommendation_type', 'BUY')
    confidence = data.get('confidence', 0)
    score = data.get('score_pct', 0)
    target = data.get('target_price', 0)
    stop_loss = data.get('stop_loss_price', 0)
    risk_reward = data.get('risk_reward', 0)
    entry_time = data.get('entry_time', datetime.utcnow().strftime('%H:%M:%S'))
    open_positions = data.get('open_positions', 0)
    max_positions = data.get('max_positions', 15)
    capital_deployed = data.get('capital_deployed', 0)
    capital_deployed_pct = data.get('capital_deployed_pct', 0)
    available_capital = data.get('available_capital', 0)

    message = (
        f"🟢 *PAPER TRADE - POSITION OPENED*\n\n"
        f"*Symbol:* `{symbol}`\n"
        f"*Entry Price:* ₹{entry_price:,.2f}\n"
        f"*Shares:* {shares}\n"
        f"*Position Value:* ₹{position_value:,.2f}\n"
        f"*Risk Amount:* ₹{risk_amount:,.2f} (1% of capital)\n\n"
        f"*Signal:* {recommendation}\n"
        f"*Confidence:* {confidence:.1f}%\n"
        f"*Score:* {score:.1f}%\n\n"
        f"*Target:* ₹{target:,.2f} (+{((target - entry_price) / entry_price * 100):.1f}%)\n"
        f"*Stop Loss:* ₹{stop_loss:,.2f} (-{((entry_price - stop_loss) / entry_price * 100):.1f}%)\n"
        f"*Risk/Reward:* 1:{risk_reward:.2f}\n\n"
        f"*Entry Time:* {entry_time} IST\n\n"
        f"*Portfolio Status:*\n"
        f"Open Positions: {open_positions}/{max_positions}\n"
        f"Capital Deployed: ₹{capital_deployed:,.2f} ({capital_deployed_pct:.1f}%)\n"
        f"Available Capital: ₹{available_capital:,.2f} ({100 - capital_deployed_pct:.1f}%)"
    )

    return message


def _format_exit_alert(data: Dict) -> str:
    """Format position exit alert"""
    symbol = data.get('symbol', 'N/A')
    exit_price = data.get('exit_price', 0)
    exit_reason = data.get('exit_reason', 'UNKNOWN')
    entry_price = data.get('entry_price', 0)
    entry_date = data.get('entry_date', 'N/A')
    exit_date = data.get('exit_date', 'N/A')
    days_held = data.get('days_held', 0)
    pnl = data.get('pnl', 0)
    pnl_pct = data.get('pnl_pct', 0)
    r_multiple = data.get('r_multiple', 0)
    session_pnl = data.get('session_pnl', 0)
    session_pnl_pct = data.get('session_pnl_pct', 0)
    win_rate = data.get('win_rate', 0)
    winning_trades = data.get('winning_trades', 0)
    total_trades = data.get('total_trades', 0)

    # Exit reason emoji
    exit_emoji = {
        'TARGET_HIT': '🎯',
        'STOP_LOSS': '🛡️',
        'TRAILING_STOP': '📉',
        'SELL_SIGNAL': '🔴',
        'SESSION_STOPPED': '🔚',
        'MANUAL': '✋'
    }.get(exit_reason, '❓')

    message = (
        f"🔴 *PAPER TRADE - POSITION CLOSED*\n\n"
        f"*Symbol:* `{symbol}`\n"
        f"*Exit Price:* ₹{exit_price:,.2f}\n"
        f"*Exit Reason:* {exit_emoji} {exit_reason.replace('_', ' ')}\n\n"
        f"*Entry:* ₹{entry_price:,.2f} on {entry_date}\n"
        f"*Exit:* ₹{exit_price:,.2f} on {exit_date}\n"
        f"*Hold Time:* {days_held} days\n\n"
        f"*Profit/Loss:* ₹{pnl:+,.2f} ({pnl_pct:+.2f}%)\n"
        f"*R-Multiple:* {r_multiple:.2f}R\n\n"
        f"*Session P&L:* ₹{session_pnl:+,.2f} ({session_pnl_pct:+.2f}%)\n"
        f"*Win Rate:* {win_rate:.1f}% ({winning_trades}W / {total_trades - winning_trades}L)"
    )

    return message


async def send_daily_paper_trading_summary(
    bot: Bot,
    telegram_id: int,
    summary_data: Dict
) -> bool:
    """
    Send daily paper trading summary

    Args:
        bot: Telegram bot instance
        telegram_id: User's Telegram ID
        summary_data: Daily summary data dictionary

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        message = _format_daily_summary(summary_data)

        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='Markdown'
        )

        logger.info(f"✅ Sent daily summary to user {telegram_id}")
        return True

    except TelegramError as e:
        logger.error(f"Telegram error sending daily summary: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending daily summary: {e}", exc_info=True)
        return False


def _format_daily_summary(data: Dict) -> str:
    """Format daily summary message"""
    date = data.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    analytics = data.get('analytics')
    winners = data.get('winners_analysis', {})
    losers = data.get('losers_analysis', {})

    if not analytics:
        return f"📊 *PAPER TRADING - DAILY SUMMARY*\n\n*Date:* {date}\n\nNo trades today."

    # Trading activity
    positions_opened = data.get('positions_opened', 0)
    positions_closed = analytics.trades_count if analytics else 0
    open_positions = data.get('open_positions', 0)
    max_positions = data.get('max_positions', 15)

    # Daily performance
    today_pnl = analytics.net_pnl if analytics else 0
    today_pnl_pct = analytics.period_return_pct if analytics else 0
    session_pnl = data.get('session_pnl', 0)
    session_pnl_pct = data.get('session_pnl_pct', 0)

    # Trades
    trades_today = analytics.trades_count if analytics else 0
    winners_today = analytics.winning_trades if analytics else 0
    losers_today = analytics.losing_trades if analytics else 0
    best_trade = analytics.best_trade_pnl if analytics else 0
    worst_trade = analytics.worst_trade_pnl if analytics else 0

    # Portfolio status
    total_capital = data.get('total_capital', 0)
    available = data.get('available_capital', 0)
    deployed = data.get('deployed_capital', 0)
    deployed_pct = data.get('deployed_pct', 0)
    unrealized_pnl = data.get('unrealized_pnl', 0)
    unrealized_pnl_pct = data.get('unrealized_pnl_pct', 0)

    # Session stats
    total_trades = data.get('total_trades', 0)
    win_rate = data.get('win_rate_pct', 0)
    profit_factor = data.get('profit_factor', 0)

    message = (
        f"📊 *PAPER TRADING - DAILY SUMMARY*\n"
        f"*Date:* {date}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*TRADING ACTIVITY*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Positions Opened: {positions_opened}\n"
        f"Positions Closed: {positions_closed}\n"
        f"Open Positions: {open_positions}/{max_positions}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*DAILY PERFORMANCE*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Today's P&L: ₹{today_pnl:+,.2f} ({today_pnl_pct:+.2f}%)\n"
        f"Session P&L: ₹{session_pnl:+,.2f} ({session_pnl_pct:+.2f}%)\n\n"
        f"Trades Today: {trades_today}\n"
        f"Winners: {winners_today} | Losers: {losers_today}\n\n"
        f"Best Trade: ₹{best_trade:+,.2f}\n"
        f"Worst Trade: ₹{worst_trade:+,.2f}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*PORTFOLIO STATUS*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Total Capital: ₹{total_capital:,.2f}\n"
        f"Available: ₹{available:,.2f} ({100 - deployed_pct:.1f}%)\n"
        f"Deployed: ₹{deployed:,.2f} ({deployed_pct:.1f}%)\n\n"
        f"Open P&L: ₹{unrealized_pnl:+,.2f} ({unrealized_pnl_pct:+.2f}%)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*KEY METRICS*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Total Trades: {total_trades}\n"
        f"Win Rate: {win_rate:.1f}%\n"
        f"Profit Factor: {profit_factor:.2f}\n\n"
        f"Next Trading Day: Tomorrow 09:15 IST"
    )

    return message


async def send_weekly_paper_trading_summary(
    bot: Bot,
    telegram_id: int,
    summary_data: Dict
) -> bool:
    """
    Send weekly paper trading summary

    Args:
        bot: Telegram bot instance
        telegram_id: User's Telegram ID
        summary_data: Weekly summary data dictionary

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        message = _format_weekly_summary(summary_data)

        # Split into chunks if too long
        if len(message) > 4000:
            # Send in parts
            parts = message.split('\n\n━━━━━━━━━━━━━━━━━━━━\n')
            for i, part in enumerate(parts):
                if i == 0:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=part,
                        parse_mode='Markdown'
                    )
                else:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=f"━━━━━━━━━━━━━━━━━━━━\n{part}",
                        parse_mode='Markdown'
                    )
        else:
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode='Markdown'
            )

        logger.info(f"✅ Sent weekly summary to user {telegram_id}")
        return True

    except TelegramError as e:
        logger.error(f"Telegram error sending weekly summary: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending weekly summary: {e}", exc_info=True)
        return False


def _format_weekly_summary(data: Dict) -> str:
    """Format weekly summary message"""
    week_start = data.get('week_start', datetime.utcnow())
    analytics = data.get('analytics')
    winners = data.get('winners_analysis', {})
    losers = data.get('losers_analysis', {})
    recommendations = data.get('recommendations', [])

    if not analytics:
        return f"📈 *PAPER TRADING - WEEKLY SUMMARY*\n\n*Week:* {week_start}\n\nNo trades this week."

    # Week overview
    trades_count = analytics.trades_count if analytics else 0
    weekly_pnl = analytics.net_pnl if analytics else 0
    weekly_pnl_pct = analytics.period_return_pct if analytics else 0

    # Performance
    winning_trades = analytics.winning_trades if analytics else 0
    losing_trades = analytics.losing_trades if analytics else 0
    win_rate = analytics.win_rate_pct if analytics else 0
    profit_factor = analytics.profit_factor if analytics else 0

    # By signal type
    by_signal = data.get('by_signal_type', {})

    # What worked
    what_worked = winners.get('common_patterns', [])

    # What didn't work
    what_didnt_work = losers.get('common_patterns', [])

    message = (
        f"📈 *PAPER TRADING - WEEKLY SUMMARY*\n"
        f"*Week:* {week_start.strftime('%b %d')} - {week_start.strftime('%b %d, %Y')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*WEEK OVERVIEW*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Trading Days: 5\n"
        f"Total Trades: {trades_count}\n"
        f"Weekly P&L: ₹{weekly_pnl:+,.2f} ({weekly_pnl_pct:+.2f}%)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*PERFORMANCE*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Winners: {winning_trades} ({win_rate:.1f}%)\n"
        f"Losers: {losing_trades} ({100 - win_rate:.1f}%)\n"
        f"Profit Factor: {profit_factor:.2f}\n\n"
    )

    # Add by signal type if available
    if by_signal:
        message += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"*BY SIGNAL TYPE*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        for signal_type, stats in by_signal.items():
            message += f"{signal_type}: {stats.get('trades', 0)} trades, {stats.get('win_rate', 0):.1f}% win\n"
        message += "\n"

    # What worked
    if what_worked:
        message += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"*WHAT WORKED ✅*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        for pattern in what_worked[:5]:  # Top 5
            message += f"• {pattern}\n"
        message += "\n"

    # What didn't work
    if what_didnt_work:
        message += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"*WHAT DIDN'T WORK ❌*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        for pattern in what_didnt_work[:5]:  # Top 5
            message += f"• {pattern}\n"
        message += "\n"

    # Recommendations
    if recommendations:
        message += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"*RECOMMENDATIONS*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        for i, rec in enumerate(recommendations[:5], 1):  # Top 5
            priority_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(rec.get('priority', 'LOW'), '⚪')
            message += (
                f"{i}. {priority_emoji} {rec.get('recommendation', 'N/A')}\n"
                f"   Impact: {rec.get('expected_impact', 'N/A')}\n\n"
            )

    return message


async def send_paper_trading_notification_to_user(
    bot: Bot,
    user_id: int,
    message: str,
    parse_mode: Optional[str] = 'Markdown'
) -> bool:
    """
    Send a paper trading notification to a user

    Args:
        bot: Telegram bot instance
        user_id: Database user ID
        message: Message to send
        parse_mode: Parse mode (default: Markdown)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        from src.bot.database.db import get_db_context
        from src.bot.database.models import User

        with get_db_context() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return False

            telegram_id = user.telegram_id

        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode=parse_mode
        )

        logger.info(f"✅ Sent notification to user {user_id} (telegram: {telegram_id})")
        return True

    except TelegramError as e:
        logger.error(f"Telegram error sending notification: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending notification: {e}", exc_info=True)
        return False


