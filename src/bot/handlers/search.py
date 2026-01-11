"""
Stock Symbol Search Handler

This module handles the /search command for finding stock symbols by keyword.
"""

import logging
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..utils.formatters import format_success, format_error
from ..utils.validators import parse_command_args
from ..services.analysis_service import search_symbol

logger = logging.getLogger(__name__)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /search command.
    
    Searches for stock symbols by keyword.
    
    Usage:
        /search KEYWORD - Search for stocks matching keyword
    """
    user_id = update.effective_user.id
    
    # Parse arguments
    args = parse_command_args(update.message.text, 'search')
    
    if not args:
        await update.message.reply_text(
            format_error(
                "Please provide a search keyword.\n\n"
                "Usage: `/search KEYWORD`\n\n"
                "Example: `/search reliance`"
            ),
            parse_mode='Markdown'
        )
        return
    
    keyword = ' '.join(args)
    
    # Show searching message
    searching_msg = await update.message.reply_text(
        f"🔍 Searching for '{keyword}'..."
    )
    
    try:
        # Search for symbols
        results = search_symbol(keyword, limit=10)
        
        if not results:
            await searching_msg.edit_text(
                format_error(
                    f"No stocks found matching '{keyword}'.\n\n"
                    "Try a different keyword or check the symbol format."
                )
            )
            return
        
        # Format results
        message = f"🔍 *Search Results for '{keyword}'*\n\n"
        
        keyboard_buttons = []
        for i, result in enumerate(results[:10], 1):
            symbol = result.get('symbol', 'N/A')
            name = result.get('name', '')
            exchange = result.get('exchange', result.get('market', ''))
            
            message += f"{i}. `{symbol}`"
            if name:
                message += f" - {name}"
            if exchange:
                message += f" ({exchange})"
            message += "\n"
            
            # Add button to analyze this symbol
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"📊 Analyze {symbol}",
                    callback_data=f"analyze_quick:{symbol}"
                )
            ])
        
        # Add back button
        keyboard_buttons.append([
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await searching_msg.edit_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        logger.info(f"User {user_id} searched for '{keyword}', found {len(results)} results")
        
    except Exception as e:
        logger.error(f"Error in search_command: {e}", exc_info=True)
        await searching_msg.edit_text(
            format_error(f"Search failed: {str(e)}")
        )

