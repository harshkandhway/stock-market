"""
Watchlist Management Handlers

This module handles all watchlist-related commands:
- /watchlist - View and manage watchlist
- /watchlist add SYMBOL - Add stock to watchlist
- /watchlist remove SYMBOL - Remove stock from watchlist
- /watchlist analyze - Analyze all stocks in watchlist
- /watchlist clear - Clear entire watchlist
"""

import logging
from typing import List
from telegram import Update
from telegram.ext import ContextTypes

from ..database.db import (
    get_db_context,
    get_or_create_user,
    get_user_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    get_user_settings
)
from ..services.analysis_service import analyze_stock, analyze_multiple_stocks
from ..utils.formatters import (
    format_watchlist,
    format_analysis_summary,
    format_comparison_table,
    format_success,
    format_error,
    format_warning,
    chunk_message
)
from ..utils.keyboards import create_watchlist_menu_keyboard
from ..utils.validators import validate_stock_symbol, parse_command_args

logger = logging.getLogger(__name__)


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /watchlist command.
    
    Shows the user's watchlist with inline action buttons.
    
    Usage:
        /watchlist - Show watchlist
        /watchlist add SYMBOL - Add stock
        /watchlist remove SYMBOL - Remove stock
        /watchlist analyze - Analyze all stocks
        /watchlist clear - Clear watchlist
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Handle menu button clicks (text might be "⭐ Watchlist" instead of "/watchlist")
    text = update.message.text
    if not text.startswith('/watchlist'):
        # If it's a menu button click, treat it as just "/watchlist"
        text = '/watchlist'
    
    # Parse subcommand
    args = parse_command_args(text, 'watchlist')
    
    if not args:
        # Show watchlist
        await show_watchlist(update, context)
        return
    
    subcommand = args[0].lower()
    
    if subcommand == "add":
        await watchlist_add(update, context, args[1:])
    elif subcommand == "remove":
        await watchlist_remove(update, context, args[1:])
    elif subcommand == "analyze":
        await watchlist_analyze(update, context)
    elif subcommand == "clear":
        await watchlist_clear(update, context)
    else:
        await update.message.reply_text(
            format_error(
                f"Unknown subcommand: {subcommand}\n\n"
                f"Available commands:\n"
                f"• /watchlist - Show watchlist\n"
                f"• /watchlist add SYMBOL\n"
                f"• /watchlist remove SYMBOL\n"
                f"• /watchlist analyze\n"
                f"• /watchlist clear"
            )
        )


async def show_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's watchlist."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        watchlist = get_user_watchlist(db, user_id)
        
        if not watchlist:
            await update.message.reply_text(
                "📋 *Your Watchlist is Empty*\n\n"
                "Add stocks using:\n"
                "• `/watchlist add SYMBOL`\n"
                "• `/analyze SYMBOL` (then click 'Add to Watchlist')\n\n"
                "*Examples:*\n"
                "• `/watchlist add RELIANCE.NS`\n"
                "• `/watchlist add TCS.NS`",
                parse_mode='Markdown'
            )
            return
        
        # Format watchlist
        message = format_watchlist(watchlist)
        
        # Create keyboard with action buttons
        symbols = [w.symbol for w in watchlist]
        keyboard = create_watchlist_menu_keyboard(symbols)
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def watchlist_add(update: Update, context: ContextTypes.DEFAULT_TYPE, args: List[str]) -> None:
    """Add a stock to watchlist."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    if not args:
        await update.message.reply_text(
            format_error(
                "Please provide a stock symbol.\n\n"
                "*Usage:* `/watchlist add SYMBOL`\n"
                "*Example:* `/watchlist add RELIANCE.NS`"
            ),
            parse_mode='Markdown'
        )
        return
    
    symbol = args[0].upper()
    
    # Validate symbol
    is_valid, error_msg = validate_stock_symbol(symbol)
    if not is_valid:
        await update.message.reply_text(format_error(error_msg))
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        
        # Check if already in watchlist
        watchlist = get_user_watchlist(db, user_id)
        if any(w.symbol == symbol for w in watchlist):
            await update.message.reply_text(
                format_warning(f"{symbol} is already in your watchlist.")
            )
            return
        
        # Check watchlist limit (max 20 stocks)
        if len(watchlist) >= 20:
            await update.message.reply_text(
                format_error(
                    "Watchlist limit reached (20 stocks).\n\n"
                    "Remove some stocks using:\n"
                    "`/watchlist remove SYMBOL`"
                ),
                parse_mode='Markdown'
            )
            return
        
        # Add to watchlist
        success = add_to_watchlist(db, user_id, symbol)
        
        if success:
            await update.message.reply_text(
                format_success(
                    f"✓ Added {symbol} to your watchlist!\n\n"
                    f"You now have {len(watchlist) + 1} stock(s) in your watchlist.\n\n"
                    f"Use /watchlist to view all stocks."
                )
            )
            logger.info(f"User {user_id} added {symbol} to watchlist")
        else:
            await update.message.reply_text(
                format_error(f"Failed to add {symbol} to watchlist")
            )


async def watchlist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, args: List[str]) -> None:
    """Remove a stock from watchlist."""
    user_id = update.effective_user.id
    
    if not args:
        await update.message.reply_text(
            format_error(
                "Please provide a stock symbol.\n\n"
                "*Usage:* `/watchlist remove SYMBOL`\n"
                "*Example:* `/watchlist remove RELIANCE.NS`"
            ),
            parse_mode='Markdown'
        )
        return
    
    symbol = args[0].upper()
    
    with get_db_context() as db:
        # Check if symbol exists in watchlist
        watchlist = get_user_watchlist(db, user_id)
        if not any(w.symbol == symbol for w in watchlist):
            await update.message.reply_text(
                format_warning(f"{symbol} is not in your watchlist.")
            )
            return
        
        success = remove_from_watchlist(db, user_id, symbol)
        
        if success:
            await update.message.reply_text(
                format_success(
                    f"✓ Removed {symbol} from your watchlist\n\n"
                    f"You now have {len(watchlist) - 1} stock(s) in your watchlist."
                )
            )
            logger.info(f"User {user_id} removed {symbol} from watchlist")
        else:
            await update.message.reply_text(
                format_error(f"Failed to remove {symbol} from watchlist")
            )


async def watchlist_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze all stocks in watchlist."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        watchlist = get_user_watchlist(db, user_id)
        
        if not watchlist:
            await update.message.reply_text(
                format_warning("Your watchlist is empty. Add stocks first!")
            )
            return
        
        settings = get_user_settings(db, user_id)
        symbols = [w.symbol for w in watchlist]
        
        # Show progress message
        progress_msg = await update.message.reply_text(
            f"🔍 Analyzing {len(symbols)} stock(s) from your watchlist...\n\n"
            f"This may take a moment."
        )
        
        try:
            # Analyze all stocks
            results = analyze_multiple_stocks(
                symbols=symbols,
                mode=settings.risk_mode,
                timeframe=settings.timeframe
            )
            
            # Filter successful results (successful ones don't have 'error' key)
            successful_results = [r for r in results if not r.get('error', False)]
            failed_results = [r for r in results if r.get('error', False)]
            
            if not successful_results:
                await progress_msg.edit_text(
                    format_error(
                        "Failed to analyze any stocks.\n\n"
                        "Please check if the symbols are valid and try again."
                    )
                )
                return
            
            # Format comparison table
            message = format_comparison_table(successful_results)
            
            # Add failed stocks warning if any
            if failed_results:
                failed_symbols = [r['symbol'] for r in failed_results]
                message += f"\n\n⚠️ Failed to analyze: {', '.join(failed_symbols)}"
            
            # Handle long messages
            chunks = chunk_message(message)
            
            # Edit progress message with first chunk
            await progress_msg.edit_text(chunks[0], parse_mode='Markdown')
            
            # Send remaining chunks
            for chunk in chunks[1:]:
                await update.message.reply_text(chunk, parse_mode='Markdown')
            
            logger.info(f"User {user_id} analyzed watchlist: {len(successful_results)} successful, {len(failed_results)} failed")
        
        except Exception as e:
            logger.error(f"Error analyzing watchlist: {e}", exc_info=True)
            await progress_msg.edit_text(
                format_error(f"An error occurred during analysis: {str(e)}")
            )


async def watchlist_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear entire watchlist."""
    user_id = update.effective_user.id
    
    with get_db_context() as db:
        watchlist = get_user_watchlist(db, user_id)
        
        if not watchlist:
            await update.message.reply_text(
                format_warning("Your watchlist is already empty.")
            )
            return
        
        # Confirm before clearing
        count = len(watchlist)
        
        # Store confirmation in user context
        context.user_data['awaiting_watchlist_clear_confirmation'] = True
        
        from ..utils.keyboards import create_confirmation_keyboard
        keyboard = create_confirmation_keyboard("confirm_watchlist_clear")
        
        await update.message.reply_text(
            f"⚠️ *Confirm Clear Watchlist*\n\n"
            f"Are you sure you want to remove all {count} stock(s) from your watchlist?\n\n"
            f"This action cannot be undone.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def confirm_watchlist_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and execute watchlist clear."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    with get_db_context() as db:
        watchlist = get_user_watchlist(db, user_id)
        count = len(watchlist)
        
        # Remove all watchlist items
        success_count = 0
        for item in watchlist:
            if remove_from_watchlist(db, user_id, item.symbol):
                success_count += 1
        
        if success_count == count:
            await query.edit_message_text(
                format_success(
                    f"✓ Cleared {count} stock(s) from your watchlist"
                )
            )
            logger.info(f"User {user_id} cleared watchlist ({count} stocks)")
        else:
            await query.edit_message_text(
                format_warning(
                    f"Partially cleared watchlist:\n"
                    f"• Removed: {success_count}\n"
                    f"• Failed: {count - success_count}"
                )
            )
    
    # Clear context
    context.user_data.pop('awaiting_watchlist_clear_confirmation', None)
