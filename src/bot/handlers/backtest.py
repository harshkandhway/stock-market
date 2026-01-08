"""
Backtest Handler

This module handles the /backtest command for strategy backtesting.
"""

import logging
from typing import List
from telegram import Update
from telegram.ext import ContextTypes

from ..database.db import (
    get_db_context,
    get_or_create_user,
    get_user_settings
)
from ..services.backtest_service import backtest_strategy
from ..utils.formatters import format_success, format_error, format_number, format_percentage
from ..utils.validators import parse_command_args, validate_stock_symbol, validate_days
from ..config import CURRENCY_SYMBOL, EMOJI, MAX_BACKTEST_DAYS

logger = logging.getLogger(__name__)


async def backtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /backtest command.
    
    Usage:
        /backtest SYMBOL DAYS - Backtest strategy for symbol over N days
    """
    user_id = update.effective_user.id
    
    # Parse arguments
    args = parse_command_args(update.message.text, 'backtest')
    
    if len(args) < 2:
        await update.message.reply_text(
            format_error(
                "Invalid format. Usage:\n"
                "`/backtest SYMBOL DAYS`\n\n"
                "Example: `/backtest RELIANCE.NS 90`\n\n"
                f"Maximum days: {MAX_BACKTEST_DAYS}",
                parse_mode='Markdown'
            )
        )
        return
    
    symbol = args[0].upper()
    days_str = args[1]
    
    # Validate inputs
    is_valid_symbol, symbol_error = validate_stock_symbol(symbol)
    if not is_valid_symbol:
        await update.message.reply_text(format_error(symbol_error))
        return
    
    is_valid_days, days, days_error = validate_days(days_str)
    if not is_valid_days:
        await update.message.reply_text(format_error(days_error))
        return
    
    if days > MAX_BACKTEST_DAYS:
        await update.message.reply_text(
            format_error(f"Maximum {MAX_BACKTEST_DAYS} days allowed for backtesting")
        )
        return
    
    # Show processing message
    processing_msg = await update.message.reply_text(
        f"{EMOJI['backtest']} Running backtest for {symbol} over {days} days...\n\n"
        "This may take a moment..."
    )
    
    try:
        with get_db_context() as db:
            get_or_create_user(db, user_id, update.effective_user.username)
            settings = get_user_settings(db, user_id)
            
            # Run backtest
            results = backtest_strategy(
                symbol=symbol,
                days=days,
                mode=settings.risk_mode,
                timeframe=settings.timeframe,
                initial_capital=settings.default_capital
            )
            
            # Format results
            message = f"{EMOJI['backtest']} *Backtest Results*\n\n"
            message += f"*Symbol:* {symbol}\n"
            message += f"*Period:* {days} days\n"
            message += f"*Mode:* {settings.risk_mode}\n\n"
            
            message += f"*Performance:*\n"
            message += f"• Initial Capital: {CURRENCY_SYMBOL}{format_number(results['initial_capital'])}\n"
            message += f"• Final Capital: {CURRENCY_SYMBOL}{format_number(results['final_capital'])}\n"
            
            total_return = results['total_return']
            return_emoji = EMOJI['profit'] if total_return >= 0 else EMOJI['loss']
            message += f"• Total Return: {return_emoji} {format_percentage(total_return)}\n"
            message += f"• Max Drawdown: {format_percentage(results['max_drawdown'])}\n\n"
            
            message += f"*Trading Statistics:*\n"
            message += f"• Total Trades: {results['total_trades']}\n"
            message += f"• Winning Trades: {results['winning_trades']}\n"
            message += f"• Losing Trades: {results['losing_trades']}\n"
            message += f"• Win Rate: {format_percentage(results['win_rate'])}\n"
            message += f"• Avg Win: {CURRENCY_SYMBOL}{format_number(results['avg_win'])}\n"
            message += f"• Avg Loss: {CURRENCY_SYMBOL}{format_number(results['avg_loss'])}\n\n"
            
            if results['best_trade']:
                best = results['best_trade']
                message += f"*Best Trade:*\n"
                message += f"  Entry: {CURRENCY_SYMBOL}{format_number(best['entry_price'])}\n"
                message += f"  Exit: {CURRENCY_SYMBOL}{format_number(best['exit_price'])}\n"
                message += f"  P&L: {CURRENCY_SYMBOL}{format_number(best['pnl'])} "
                message += f"({format_percentage(best['pnl_percent'])})\n\n"
            
            if results['worst_trade']:
                worst = results['worst_trade']
                message += f"*Worst Trade:*\n"
                message += f"  Entry: {CURRENCY_SYMBOL}{format_number(worst['entry_price'])}\n"
                message += f"  Exit: {CURRENCY_SYMBOL}{format_number(worst['exit_price'])}\n"
                message += f"  P&L: {CURRENCY_SYMBOL}{format_number(worst['pnl'])} "
                message += f"({format_percentage(worst['pnl_percent'])})\n"
            
            await processing_msg.edit_text(message, parse_mode='Markdown')
            
            logger.info(f"User {user_id} ran backtest for {symbol} over {days} days")
            
    except Exception as e:
        logger.error(f"Error in backtest_command: {e}", exc_info=True)
        await processing_msg.edit_text(
            format_error(f"Backtest failed: {str(e)}")
        )

