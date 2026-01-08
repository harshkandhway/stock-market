"""
Stock Comparison Handler

This module handles the /compare command for comparing multiple stocks side-by-side.
"""

import logging
from typing import List
from telegram import Update
from telegram.ext import ContextTypes

from ..database.db import get_db_context, get_or_create_user, get_user_settings
from ..services.analysis_service import analyze_multiple_stocks
from ..utils.formatters import (
    format_comparison_table,
    format_error,
    format_warning,
    chunk_message
)
from ..utils.validators import validate_stock_symbol, parse_command_args

logger = logging.getLogger(__name__)


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /compare command.
    
    Compares multiple stocks side-by-side with key metrics and recommendations.
    
    Usage:
        /compare SYMBOL1 SYMBOL2 [SYMBOL3] ... - Compare 2-5 stocks
    
    Examples:
        /compare RELIANCE.NS TCS.NS INFY.NS
        /compare HDFCBANK.NS ICICIBANK.NS KOTAKBANK.NS AXISBANK.NS
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Parse arguments
    args = parse_command_args(update.message.text)
    
    if not args:
        await update.message.reply_text(
            "📊 *Stock Comparison*\n\n"
            "*Usage:* `/compare SYMBOL1 SYMBOL2 [SYMBOL3] ...`\n\n"
            "Compare 2-5 stocks side-by-side with key metrics.\n\n"
            "*Examples:*\n"
            "• `/compare RELIANCE.NS TCS.NS`\n"
            "• `/compare HDFCBANK.NS ICICIBANK.NS KOTAKBANK.NS`\n"
            "• `/compare INFY.NS WIPRO.NS TCS.NS TECHM.NS`\n\n"
            "*What you'll see:*\n"
            "• Price and recommendation\n"
            "• Key indicators (RSI, MACD, ADX)\n"
            "• Confidence scores\n"
            "• Target prices\n"
            "• Risk/reward ratios",
            parse_mode='Markdown'
        )
        return
    
    symbols = [arg.upper() for arg in args]
    
    # Validate number of symbols
    if len(symbols) < 2:
        await update.message.reply_text(
            format_error(
                "Please provide at least 2 stocks to compare.\n\n"
                "*Example:* `/compare RELIANCE.NS TCS.NS`"
            )
        )
        return
    
    if len(symbols) > 5:
        await update.message.reply_text(
            format_error(
                "You can compare up to 5 stocks at a time.\n\n"
                f"You provided {len(symbols)} stocks. Please reduce to 5 or fewer."
            )
        )
        return
    
    # Validate each symbol
    invalid_symbols = []
    for symbol in symbols:
        is_valid, error_msg = validate_stock_symbol(symbol)
        if not is_valid:
            invalid_symbols.append(symbol)
    
    if invalid_symbols:
        await update.message.reply_text(
            format_error(
                f"Invalid symbol(s): {', '.join(invalid_symbols)}\n\n"
                f"Please use valid stock symbols (e.g., RELIANCE.NS, TCS.NS)"
            )
        )
        return
    
    # Check for duplicates
    if len(symbols) != len(set(symbols)):
        await update.message.reply_text(
            format_warning("You provided duplicate symbols. Each symbol should be unique.")
        )
        return
    
    # Show progress message
    progress_msg = await update.message.reply_text(
        f"🔍 Comparing {len(symbols)} stocks...\n\n"
        f"Symbols: {', '.join(symbols)}\n\n"
        f"This may take a moment."
    )
    
    try:
        with get_db_context() as db:
            user = get_or_create_user(db, user_id, username)
            settings = get_user_settings(db, user_id)
            
            # Analyze all stocks
            results = analyze_multiple_stocks(
                symbols=symbols,
                mode=settings.risk_mode,
                timeframe=settings.timeframe
            )
            
            # Filter successful results
            successful_results = [r for r in results if r['status'] == 'success']
            failed_results = [r for r in results if r['status'] != 'success']
            
            if not successful_results:
                await progress_msg.edit_text(
                    format_error(
                        "Failed to analyze any of the provided stocks.\n\n"
                        "Possible reasons:\n"
                        "• Invalid symbols\n"
                        "• Network issues\n"
                        "• Data not available\n\n"
                        "Please check the symbols and try again."
                    )
                )
                return
            
            if len(successful_results) < 2:
                await progress_msg.edit_text(
                    format_warning(
                        f"Only 1 stock analyzed successfully.\n\n"
                        f"Comparison requires at least 2 stocks.\n\n"
                        f"Failed: {', '.join([r['symbol'] for r in failed_results])}"
                    )
                )
                return
            
            # Format comparison table
            message = format_comparison_table(successful_results)
            
            # Add failed stocks warning if any
            if failed_results:
                failed_symbols = [r['symbol'] for r in failed_results]
                message += f"\n\n⚠️ *Failed to analyze:* {', '.join(failed_symbols)}"
            
            # Add footer
            message += (
                f"\n\n━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 *Tip:* Use `/analyze SYMBOL` for detailed analysis of any stock."
            )
            
            # Handle long messages
            chunks = chunk_message(message)
            
            # Edit progress message with first chunk
            await progress_msg.edit_text(chunks[0], parse_mode='Markdown')
            
            # Send remaining chunks
            for chunk in chunks[1:]:
                await update.message.reply_text(chunk, parse_mode='Markdown')
            
            logger.info(
                f"User {user_id} compared {len(symbols)} stocks: "
                f"{len(successful_results)} successful, {len(failed_results)} failed"
            )
    
    except Exception as e:
        logger.error(f"Error comparing stocks: {e}", exc_info=True)
        await progress_msg.edit_text(
            format_error(f"An error occurred during comparison: {str(e)}")
        )
