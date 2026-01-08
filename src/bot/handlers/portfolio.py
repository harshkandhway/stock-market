"""
Portfolio Management Handlers

This module handles all portfolio-related commands:
- /portfolio - View portfolio with current P&L
- /portfolio add SYMBOL SHARES PRICE - Add position
- /portfolio remove SYMBOL - Remove position
- /portfolio update SYMBOL SHARES PRICE - Update position
"""

import logging
from typing import List
from telegram import Update
from telegram.ext import ContextTypes

from ..database.db import (
    get_db_context,
    get_or_create_user,
    add_portfolio_position,
    remove_portfolio_position,
    update_portfolio_position
)
from ..services.portfolio_service import calculate_portfolio_summary
from ..config import CURRENCY_SYMBOL, EMOJI
from ..utils.formatters import (
    format_success, format_error, format_warning,
    format_number, format_percentage
)
from ..utils.validators import (
    validate_stock_symbol, validate_shares, validate_price, parse_command_args
)

logger = logging.getLogger(__name__)


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /portfolio command.
    
    Shows user's portfolio with current P&L.
    
    Usage:
        /portfolio - View portfolio
        /portfolio add SYMBOL SHARES PRICE - Add position
        /portfolio remove SYMBOL - Remove position
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Parse subcommand
    args = parse_command_args(update.message.text, 'portfolio')
    
    if not args:
        # Show portfolio
        await show_portfolio(update, context)
        return
    
    subcommand = args[0].lower()
    
    if subcommand == "add":
        await portfolio_add(update, context, args[1:])
    elif subcommand == "remove":
        await portfolio_remove(update, context, args[1:])
    elif subcommand == "update":
        await portfolio_update(update, context, args[1:])
    else:
        await update.message.reply_text(
            format_error(
                f"Unknown subcommand: {subcommand}\n\n"
                f"Available commands:\n"
                f"• /portfolio - View portfolio\n"
                f"• /portfolio add SYMBOL SHARES PRICE\n"
                f"• /portfolio remove SYMBOL"
            )
        )


async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's portfolio with P&L."""
    user_id = update.effective_user.id
    
    # Show loading message
    loading_msg = await update.message.reply_text("💼 Loading portfolio...")
    
    try:
        with get_db_context() as db:
            portfolio_summary = calculate_portfolio_summary(db, user_id)
            
            if portfolio_summary['total_positions'] == 0:
                await loading_msg.edit_text(
                    f"{EMOJI['portfolio']} *Your Portfolio*\n\n"
                    "Your portfolio is empty.\n\n"
                    "Add positions using:\n"
                    "`/portfolio add SYMBOL SHARES PRICE`\n\n"
                    "Example: `/portfolio add RELIANCE.NS 10 2500`",
                    parse_mode='Markdown'
                )
                return
            
            # Format portfolio message
            message = f"{EMOJI['portfolio']} *Your Portfolio*\n\n"
            message += f"*Summary:*\n"
            message += f"• Positions: {portfolio_summary['total_positions']}\n"
            message += f"• Total Invested: {CURRENCY_SYMBOL}{format_number(portfolio_summary['total_invested'])}\n"
            message += f"• Current Value: {CURRENCY_SYMBOL}{format_number(portfolio_summary['total_current_value'])}\n"
            
            pnl = portfolio_summary['total_pnl']
            pnl_percent = portfolio_summary['total_pnl_percent']
            pnl_emoji = EMOJI['profit'] if pnl >= 0 else EMOJI['loss']
            
            message += f"• Total P&L: {pnl_emoji} {CURRENCY_SYMBOL}{format_number(pnl)} "
            message += f"({format_percentage(pnl_percent)})\n\n"
            
            message += "*Positions:*\n"
            for pos in portfolio_summary['positions']:
                pos_pnl_emoji = EMOJI['profit'] if pos['pnl'] >= 0 else EMOJI['loss']
                message += f"\n*{pos['symbol']}*\n"
                message += f"  Shares: {format_number(pos['shares'], 2)}\n"
                message += f"  Avg Price: {CURRENCY_SYMBOL}{format_number(pos['avg_buy_price'])}\n"
                message += f"  Current: {CURRENCY_SYMBOL}{format_number(pos['current_price'])}\n"
                message += f"  Invested: {CURRENCY_SYMBOL}{format_number(pos['invested_value'])}\n"
                message += f"  Value: {CURRENCY_SYMBOL}{format_number(pos['current_value'])}\n"
                message += f"  P&L: {pos_pnl_emoji} {CURRENCY_SYMBOL}{format_number(pos['pnl'])} "
                message += f"({format_percentage(pos['pnl_percent'])})\n"
            
            await loading_msg.edit_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error showing portfolio: {e}", exc_info=True)
        await loading_msg.edit_text(
            format_error(f"Failed to load portfolio: {str(e)}")
        )


async def portfolio_add(update: Update, context: ContextTypes.DEFAULT_TYPE, args: List[str]) -> None:
    """Add position to portfolio."""
    user_id = update.effective_user.id
    
    if len(args) < 3:
        await update.message.reply_text(
            format_error(
                "Invalid format. Usage:\n"
                "`/portfolio add SYMBOL SHARES PRICE`\n\n"
                "Example: `/portfolio add RELIANCE.NS 10 2500`",
                parse_mode='Markdown'
            )
        )
        return
    
    symbol = args[0].upper()
    shares_str = args[1]
    price_str = args[2]
    
    # Validate inputs
    is_valid_symbol, symbol_error = validate_stock_symbol(symbol)
    if not is_valid_symbol:
        await update.message.reply_text(format_error(symbol_error))
        return
    
    is_valid_shares, shares, shares_error = validate_shares(shares_str)
    if not is_valid_shares:
        await update.message.reply_text(format_error(shares_error))
        return
    
    is_valid_price, price, price_error = validate_price(price_str)
    if not is_valid_price:
        await update.message.reply_text(format_error(price_error))
        return
    
    try:
        with get_db_context() as db:
            get_or_create_user(db, user_id, update.effective_user.username)
            
            position = add_portfolio_position(
                db, user_id, symbol, shares, price
            )
            
            if position:
                await update.message.reply_text(
                    format_success(
                        f"✓ Position added!\n\n"
                        f"Symbol: {symbol}\n"
                        f"Shares: {format_number(shares, 2)}\n"
                        f"Avg Price: {CURRENCY_SYMBOL}{format_number(price)}\n"
                        f"Investment: {CURRENCY_SYMBOL}{format_number(shares * price)}"
                    )
                )
            else:
                await update.message.reply_text(
                    format_error("Failed to add position")
                )
                
    except Exception as e:
        logger.error(f"Error adding portfolio position: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to add position: {str(e)}")
        )


async def portfolio_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, args: List[str]) -> None:
    """Remove position from portfolio."""
    user_id = update.effective_user.id
    
    if not args:
        await update.message.reply_text(
            format_error(
                "Please specify a symbol to remove.\n\n"
                "Usage: `/portfolio remove SYMBOL`\n\n"
                "Example: `/portfolio remove RELIANCE.NS`",
                parse_mode='Markdown'
            )
        )
        return
    
    symbol = args[0].upper()
    
    # Validate symbol
    is_valid, error_msg = validate_stock_symbol(symbol)
    if not is_valid:
        await update.message.reply_text(format_error(error_msg))
        return
    
    try:
        with get_db_context() as db:
            success = remove_portfolio_position(db, user_id, symbol)
            
            if success:
                await update.message.reply_text(
                    format_success(f"✓ Removed {symbol} from portfolio")
                )
            else:
                await update.message.reply_text(
                    format_error(f"Position {symbol} not found in portfolio")
                )
                
    except Exception as e:
        logger.error(f"Error removing portfolio position: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to remove position: {str(e)}")
        )


async def portfolio_update(update: Update, context: ContextTypes.DEFAULT_TYPE, args: List[str]) -> None:
    """Update position in portfolio."""
    user_id = update.effective_user.id
    
    if len(args) < 3:
        await update.message.reply_text(
            format_error(
                "Invalid format. Usage:\n"
                "`/portfolio update SYMBOL SHARES PRICE`\n\n"
                "Example: `/portfolio update RELIANCE.NS 15 2600`",
                parse_mode='Markdown'
            )
        )
        return
    
    symbol = args[0].upper()
    shares_str = args[1]
    price_str = args[2]
    
    # Validate inputs
    is_valid_symbol, symbol_error = validate_stock_symbol(symbol)
    if not is_valid_symbol:
        await update.message.reply_text(format_error(symbol_error))
        return
    
    is_valid_shares, shares, shares_error = validate_shares(shares_str)
    if not is_valid_shares:
        await update.message.reply_text(format_error(shares_error))
        return
    
    is_valid_price, price, price_error = validate_price(price_str)
    if not is_valid_price:
        await update.message.reply_text(format_error(price_error))
        return
    
    try:
        with get_db_context() as db:
            position = update_portfolio_position(
                db, user_id, symbol, shares=shares, avg_buy_price=price
            )
            
            if position:
                await update.message.reply_text(
                    format_success(
                        f"✓ Position updated!\n\n"
                        f"Symbol: {symbol}\n"
                        f"Shares: {format_number(shares, 2)}\n"
                        f"Avg Price: {CURRENCY_SYMBOL}{format_number(price)}\n"
                        f"Investment: {CURRENCY_SYMBOL}{format_number(shares * price)}"
                    )
                )
            else:
                await update.message.reply_text(
                    format_error(f"Position {symbol} not found. Use /portfolio add to create it.")
                )
                
    except Exception as e:
        logger.error(f"Error updating portfolio position: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to update position: {str(e)}")
        )
