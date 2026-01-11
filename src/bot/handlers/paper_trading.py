"""
Paper Trading Command Handlers
Handles all paper trading bot commands

Author: Harsh Kandhway
"""

import logging
from typing import Optional
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.database.db import get_db_context, get_or_create_user
from src.bot.database.models import PaperTradingSession, UserSettings
from src.bot.services.paper_trading_service import get_paper_trading_service
from src.bot.services.paper_trade_analysis_service import get_paper_trade_analysis_service
from src.bot.utils.validators import parse_command_args
from src.bot.utils.formatters import format_error, format_success

logger = logging.getLogger(__name__)


async def papertrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /papertrade command with subcommands

    Usage:
        /papertrade start - Start paper trading session
        /papertrade stop - Stop paper trading session
        /papertrade status - Show current positions and P&L
        /papertrade history [N] - Show trade history
        /papertrade performance - Detailed performance metrics
        /papertrade insights - System improvement recommendations
        /papertrade reset - Reset paper trading session
        /papertrade settings - Configure paper trading settings
    """
    user_id = update.effective_user.id
    
    # Check if this is a menu button click (not a command)
    message_text = update.message.text.strip()
    if not message_text.startswith('/papertrade'):
        # This is likely a menu button click, show help/menu
        logger.info(f"User {user_id} accessed paper trading via menu button")
        await update.message.reply_text(
            "📊 *Paper Trading Commands*\n\n"
            "• `/papertrade start` - Start paper trading session\n"
            "• `/papertrade stop` - Stop paper trading session\n"
            "• `/papertrade status` - Current positions and P&L\n"
            "• `/papertrade history [N]` - Trade history (default: 10)\n"
            "• `/papertrade performance` - Detailed performance metrics\n"
            "• `/papertrade insights` - System improvement recommendations\n"
            "• `/papertrade reset` - Reset paper trading session\n"
            "• `/papertrade settings` - Configure settings\n\n"
            "_Example: `/papertrade start`_",
            parse_mode='Markdown'
        )
        return
    
    args = parse_command_args(update.message.text, 'papertrade')

    if not args:
        # Show help
        logger.info(f"User {user_id} requested paper trading help")
        await update.message.reply_text(
            "📊 *Paper Trading Commands*\n\n"
            "• `/papertrade start` - Start paper trading session\n"
            "• `/papertrade stop` - Stop paper trading session\n"
            "• `/papertrade status` - Current positions and P&L\n"
            "• `/papertrade history [N]` - Trade history (default: 10)\n"
            "• `/papertrade performance` - Detailed performance metrics\n"
            "• `/papertrade insights` - System improvement recommendations\n"
            "• `/papertrade reset` - Reset paper trading session\n"
            "• `/papertrade settings` - Configure settings\n\n"
            "_Example: `/papertrade start`_",
            parse_mode='Markdown'
        )
        return

    subcommand = args[0].lower().strip()
    
    # Validate subcommand is not empty
    if not subcommand:
        logger.warning(f"User {user_id} sent /papertrade with empty subcommand. Text: '{update.message.text}'")
        await update.message.reply_text(
            format_error("Empty subcommand.\n\nUse `/papertrade` for help"),
            parse_mode='Markdown'
        )
        return

    if subcommand == 'start':
        await paper_trade_start_command(update, context)
    elif subcommand == 'stop':
        await paper_trade_stop_command(update, context)
    elif subcommand == 'status':
        await paper_trade_status_command(update, context)
    elif subcommand == 'history':
        await paper_trade_history_command(update, context, args[1:] if len(args) > 1 else [])
    elif subcommand == 'performance':
        await paper_trade_performance_command(update, context)
    elif subcommand == 'insights':
        await paper_trade_insights_command(update, context)
    elif subcommand == 'reset':
        await paper_trade_reset_command(update, context)
    elif subcommand == 'settings':
        await paper_trade_settings_command(update, context)
    else:
        logger.warning(
            f"User {user_id} sent unknown paper trading subcommand: '{subcommand}'. "
            f"Full text: '{update.message.text}'"
        )
        await update.message.reply_text(
            format_error(f"Unknown subcommand: {subcommand}\n\nUse `/papertrade` for help"),
            parse_mode='Markdown'
        )


async def paper_trade_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start paper trading session"""
    user_id = update.effective_user.id

    try:
        with get_db_context() as db:
            user = get_or_create_user(db, user_id)
            settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()

            # Check if already active
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)

            if active_session:
                await update.message.reply_text(
                    f"⚠️ Paper trading session already active!\n\n"
                    f"Started: {active_session.session_start.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Current Capital: ₹{active_session.current_capital:,.2f}\n"
                    f"P&L: ₹{active_session.current_capital - active_session.initial_capital:+,.2f}\n\n"
                    "Use `/papertrade stop` to end current session.",
                    parse_mode='Markdown'
                )
                return

            # Get settings
            initial_capital = settings.paper_trading_capital if settings else 500000.0
            max_positions = settings.paper_trading_max_positions if settings else 15

            # Start session
            session = await trading_service.start_session(user_id, initial_capital, max_positions)

            # Create keyboard with navigation buttons
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Status", callback_data="papertrade_status")],
                [InlineKeyboardButton("📜 History", callback_data="papertrade_history")],
                [InlineKeyboardButton("📈 Performance", callback_data="papertrade_performance")],
                [InlineKeyboardButton("◀️ Back to Menu", callback_data="papertrade_menu")],
            ])

            await update.message.reply_text(
                f"🟢 *Paper Trading Session Started!*\n\n"
                f"Initial Capital: ₹{session.initial_capital:,.2f}\n"
                f"Max Positions: {session.max_positions}\n"
                f"Risk Per Trade: {settings.paper_trading_risk_per_trade_pct if settings else 1.0}%\n\n"
                f"System will automatically:\n"
                f"• Execute BUY signals at 9:20 AM IST\n"
                f"• Monitor positions every 5 minutes during market hours\n"
                f"• Send daily summary at 4:00 PM IST\n"
                f"• Send weekly summary on Sundays\n\n"
                f"Use `/papertrade status` to check positions anytime.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )

    except Exception as e:
        logger.error(f"Error starting paper trading session: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to start session: {str(e)}"),
            parse_mode='Markdown'
        )


async def paper_trade_stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop paper trading session"""
    user_id = update.effective_user.id

    try:
        with get_db_context() as db:
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)

            if not active_session:
                await update.message.reply_text(
                    format_error("No active paper trading session.\n\nUse `/papertrade start` to begin."),
                    parse_mode='Markdown'
                )
                return

            # Stop session
            summary = await trading_service.stop_session(active_session.id)

            await update.message.reply_text(
                f"🛑 *Paper Trading Session Stopped*\n\n"
                f"Final Capital: ₹{summary['total_capital']:,.2f}\n"
                f"Total Return: ₹{summary['total_return']:+,.2f} ({summary['total_return_pct']:+.2f}%)\n\n"
                f"*Performance:*\n"
                f"Total Trades: {summary['total_trades']}\n"
                f"Win Rate: {summary['win_rate_pct']:.1f}%\n"
                f"Profit Factor: {summary['profit_factor']:.2f}\n\n"
                f"All open positions have been closed.",
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error stopping paper trading session: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to stop session: {str(e)}"),
            parse_mode='Markdown'
        )


async def paper_trade_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current portfolio status"""
    user_id = update.effective_user.id

    try:
        with get_db_context() as db:
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)

            if not active_session:
                await update.message.reply_text(
                    format_error("No active paper trading session.\n\nUse `/papertrade start` to begin."),
                    parse_mode='Markdown'
                )
                return

            status = await trading_service.get_session_status(active_session.id)

            # Format message
            message = (
                f"📊 *PAPER TRADING STATUS*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"*SESSION OVERVIEW*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Started: {active_session.session_start.strftime('%Y-%m-%d %H:%M IST')}\n"
                f"Days Active: {(datetime.utcnow() - active_session.session_start).days}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"*CAPITAL*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Initial: ₹{status['initial_capital']:,.2f}\n"
                f"Current: ₹{status['total_capital']:,.2f}\n"
                f"Available: ₹{status['current_cash']:,.2f}\n"
                f"Deployed: ₹{status['deployed_capital']:,.2f} ({status['deployed_pct']:.1f}%)\n\n"
                f"Total P&L: ₹{status['total_return']:+,.2f} ({status['total_return_pct']:+.2f}%)\n"
                f"Unrealized P&L: ₹{status['total_unrealized_pnl']:+,.2f}\n\n"
            )

            # Add pending trades (queued when market was closed)
            from ..database.models import PendingPaperTrade
            from ..services.market_hours_service import get_market_hours_service
            pending_trades = db.query(PendingPaperTrade).filter(
                PendingPaperTrade.session_id == active_session.id,
                PendingPaperTrade.status == 'PENDING'
            ).order_by(PendingPaperTrade.requested_at.desc()).all()
            
            if pending_trades:
                market_hours = get_market_hours_service()
                next_open = market_hours.get_next_market_open()
                message += (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"*PENDING TRADES ({len(pending_trades)})*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ Will execute at: {next_open.strftime('%Y-%m-%d %H:%M IST')}\n\n"
                )
                for pending in pending_trades[:5]:  # Top 5
                    signal_data = pending.signal_data_dict
                    rec_type = signal_data.get('recommendation_type', 'BUY')
                    message += (
                        f"⏳ {pending.symbol} - {rec_type}\n"
                    )
                if len(pending_trades) > 5:
                    message += f"\n... and {len(pending_trades) - 5} more pending\n"
                message += "\n"
            
            # Add positions
            if status['positions']:
                message += (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"*OPEN POSITIONS ({status['position_count']}/{status['max_positions']})*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                )
                for pos in status['positions'][:10]:  # Top 10
                    pnl_emoji = "🟢" if pos['unrealized_pnl'] > 0 else "🔴" if pos['unrealized_pnl'] < 0 else "⚪"
                    message += (
                        f"{pnl_emoji} {pos['symbol']}: {pos['shares']} @ ₹{pos['entry_price']:.2f} "
                        f"({pos['unrealized_pnl_pct']:+.1f}%)\n"
                    )
                if len(status['positions']) > 10:
                    message += f"\n... and {len(status['positions']) - 10} more\n"

            message += (
                f"\n━━━━━━━━━━━━━━━━━━━━\n"
                f"*PERFORMANCE*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Total Trades: {status['total_trades']}\n"
                f"Win Rate: {status['win_rate_pct']:.1f}% ({status['winning_trades']}W / {status['losing_trades']}L)\n\n"
                f"Total Profit: ₹{status['total_profit']:,.2f}\n"
                f"Total Loss: ₹{status['total_loss']:,.2f}\n"
                f"Profit Factor: {status['profit_factor']:.2f}\n\n"
                f"Max Drawdown: {status['max_drawdown_pct']:.2f}%\n\n"
                f"Use `/papertrade performance` for detailed metrics\n"
                f"Use `/papertrade history` for trade history"
            )

            await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error getting paper trading status: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to get status: {str(e)}"),
            parse_mode='Markdown'
        )


async def paper_trade_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list) -> None:
    """Show trade history"""
    user_id = update.effective_user.id

    # Parse limit
    limit = 10
    if args and args[0].isdigit():
        limit = min(int(args[0]), 50)  # Max 50

    try:
        with get_db_context() as db:
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)

            if not active_session:
                await update.message.reply_text(
                    format_error("No active session."),
                    parse_mode='Markdown'
                )
                return

            # Get session status for history header
            status = await trading_service.get_session_status(active_session.id)
            
            # Build message with session info first
            message = f"📜 *TRADE HISTORY*\n\n"
            
            # Add session overview
            message += (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"*SESSION INFO*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🟢 Started: {active_session.session_start.strftime('%Y-%m-%d %H:%M IST')}\n"
                f"Days Active: {(datetime.utcnow() - active_session.session_start).days}\n"
                f"Initial Capital: ₹{status['initial_capital']:,.2f}\n"
                f"Current Capital: ₹{status['total_capital']:,.2f}\n"
                f"Total P&L: ₹{status['total_return']:+,.2f} ({status['total_return_pct']:+.2f}%)\n"
                f"Trades: {active_session.total_trades} (W: {active_session.winning_trades}, L: {active_session.losing_trades})\n\n"
            )
            
            trades = await trading_service.get_trade_history(active_session.id, limit)

            if not trades:
                message += (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"*CLOSED TRADES*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📭 No trades yet.\n\n"
                    f"Trades will appear here once positions are closed."
                )
            else:
                message += (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"*CLOSED TRADES* (Last {len(trades)})\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                )
                
                for i, trade in enumerate(trades, 1):
                    pnl_emoji = "🟢" if trade.is_winner else "🔴"
                    exit_emoji = {
                        'TARGET_HIT': '🎯',
                        'STOP_LOSS': '🛡️',
                        'TRAILING_STOP': '📉',
                        'SELL_SIGNAL': '🔴',
                        'SESSION_STOPPED': '🔚',
                        'MANUAL': '✋'
                    }.get(trade.exit_reason, '❓')

                    message += (
                        f"{i}. {pnl_emoji} *{trade.symbol}*\n"
                        f"Entry: ₹{trade.entry_price:.2f} on {trade.entry_date.strftime('%b %d')}\n"
                        f"Exit: ₹{trade.exit_price:.2f} on {trade.exit_date.strftime('%b %d')}\n"
                        f"P&L: ₹{trade.pnl:,.0f} ({trade.pnl_pct:+.1f}%)\n"
                        f"Exit: {exit_emoji} {trade.exit_reason.replace('_', ' ')}\n"
                        f"Hold: {trade.days_held} days | R: {trade.r_multiple:.1f}R\n\n"
                    )

            # Add navigation keyboard
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Status", callback_data="papertrade_status")],
                [InlineKeyboardButton("📈 Performance", callback_data="papertrade_performance")],
                [InlineKeyboardButton("◀️ Back to Menu", callback_data="papertrade_menu")],
            ])

            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error getting trade history: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to get history: {str(e)}"),
            parse_mode='Markdown'
        )


async def paper_trade_performance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed performance metrics"""
    user_id = update.effective_user.id

    try:
        with get_db_context() as db:
            trading_service = get_paper_trading_service(db)
            analysis_service = get_paper_trade_analysis_service(db)

            active_session = await trading_service.get_active_session(user_id)

            if not active_session:
                await update.message.reply_text(
                    format_error("No active session."),
                    parse_mode='Markdown'
                )
                return

            # Get analysis
            winners = analysis_service.analyze_winning_trades(active_session)
            losers = analysis_service.analyze_losing_trades(active_session)

            status = await trading_service.get_session_status(active_session.id)

            message = (
                f"📈 *PERFORMANCE ANALYSIS*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"*OVERALL METRICS*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Total Trades: {status['total_trades']}\n"
                f"Win Rate: {status['win_rate_pct']:.1f}%\n"
                f"Profit Factor: {status['profit_factor']:.2f}\n\n"
            )

            if winners.get('total_winners', 0) > 0:
                message += (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"*WINNING TRADES*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Total Winners: {winners['total_winners']}\n"
                    f"Avg Win: {winners.get('avg_win_pct', 0):.1f}%\n"
                    f"Avg R: {winners.get('avg_r_multiple', 0):.2f}R\n"
                    f"Avg Hold: {winners.get('avg_hold_days', 0):.1f} days\n\n"
                )

            if losers.get('total_losers', 0) > 0:
                message += (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"*LOSING TRADES*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Total Losers: {losers['total_losers']}\n"
                    f"Avg Loss: {losers.get('avg_loss_pct', 0):.1f}%\n"
                    f"Avg Hold: {losers.get('avg_hold_days', 0):.1f} days\n\n"
                )

            await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error getting performance: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to get performance: {str(e)}"),
            parse_mode='Markdown'
        )


async def paper_trade_insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show system improvement recommendations"""
    user_id = update.effective_user.id

    try:
        with get_db_context() as db:
            trading_service = get_paper_trading_service(db)
            analysis_service = get_paper_trade_analysis_service(db)

            active_session = await trading_service.get_active_session(user_id)

            if not active_session or active_session.total_trades < 10:
                await update.message.reply_text(
                    format_error(
                        "Insufficient data for insights.\n"
                        "Complete at least 10 trades to generate recommendations."
                    ),
                    parse_mode='Markdown'
                )
                return

            recommendations = analysis_service.generate_improvement_recommendations(active_session)

            if not recommendations:
                await update.message.reply_text("No recommendations available yet.")
                return

            message = "🎯 *SYSTEM IMPROVEMENT RECOMMENDATIONS*\n\n"

            # Group by priority
            high_priority = [r for r in recommendations if r.get('priority') == 'HIGH']
            medium_priority = [r for r in recommendations if r.get('priority') == 'MEDIUM']
            low_priority = [r for r in recommendations if r.get('priority') == 'LOW']

            if high_priority:
                message += "═══ *HIGH PRIORITY* ═══\n\n"
                for i, rec in enumerate(high_priority, 1):
                    message += (
                        f"{i}. {rec.get('recommendation', 'N/A')}\n"
                        f"   Category: {rec.get('category', 'N/A')}\n"
                        f"   Why: {rec.get('rationale', 'N/A')}\n"
                        f"   Impact: {rec.get('expected_impact', 'N/A')}\n\n"
                    )

            if medium_priority:
                message += "═══ *MEDIUM PRIORITY* ═══\n\n"
                for i, rec in enumerate(medium_priority, 1):
                    message += (
                        f"{i}. {rec.get('recommendation', 'N/A')}\n"
                        f"   Impact: {rec.get('expected_impact', 'N/A')}\n\n"
                    )

            if low_priority:
                message += "═══ *LOW PRIORITY* ═══\n\n"
                for i, rec in enumerate(low_priority, 1):
                    message += f"{i}. {rec.get('recommendation', 'N/A')}\n\n"

            await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error getting insights: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to get insights: {str(e)}"),
            parse_mode='Markdown'
        )


async def paper_trade_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset paper trading session (with confirmation)"""
    user_id = update.effective_user.id

    try:
        with get_db_context() as db:
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)

            if not active_session:
                await update.message.reply_text(
                    format_error("No active session to reset."),
                    parse_mode='Markdown'
                )
                return

            # Show current performance
            status = await trading_service.get_session_status(active_session.id)

            await update.message.reply_text(
                f"⚠️ *Reset Paper Trading Session?*\n\n"
                f"Current Performance:\n"
                f"• Total Return: ₹{status['total_return']:+,.2f} ({status['total_return_pct']:+.2f}%)\n"
                f"• Total Trades: {status['total_trades']}\n"
                f"• Win Rate: {status['win_rate_pct']:.1f}%\n\n"
                f"This will close the current session and start a new one.\n\n"
                f"To confirm, reply with: `/papertrade reset confirm`",
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error resetting session: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to reset: {str(e)}"),
            parse_mode='Markdown'
        )


async def paper_trade_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Configure paper trading settings"""
    user_id = update.effective_user.id

    try:
        with get_db_context() as db:
            user = get_or_create_user(db, user_id)
            settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()

            if not settings:
                await update.message.reply_text(
                    format_error("Settings not found."),
                    parse_mode='Markdown'
                )
                return

            await update.message.reply_text(
                f"⚙️ *Paper Trading Settings*\n\n"
                f"Virtual Capital: ₹{settings.paper_trading_capital:,.2f}\n"
                f"Max Positions: {settings.paper_trading_max_positions}\n"
                f"Risk Per Trade: {settings.paper_trading_risk_per_trade_pct}%\n"
                f"Enabled: {'Yes' if settings.paper_trading_enabled else 'No'}\n\n"
                f"_Settings can be modified via database or admin panel._",
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error getting settings: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to get settings: {str(e)}"),
            parse_mode='Markdown'
        )

