"""
Analyze Command Handler
Handles /analyze command for stock analysis
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.config import EMOJI, ERROR_MESSAGES
from src.bot.services.analysis_service import analyze_stock
from src.bot.utils.formatters import format_analysis_full, format_error, chunk_message
from src.bot.utils.keyboards import create_analysis_action_keyboard
from src.bot.utils.validators import validate_stock_symbol, parse_command_args
from src.bot.database.db import get_user_settings, get_db_context

logger = logging.getLogger(__name__)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /analyze command - Analyze a stock
    
    Usage: /analyze SYMBOL
    Example: /analyze RELIANCE.NS
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    
    try:
        # Parse arguments
        args = parse_command_args(update.message.text, 'analyze')
        
        if not args:
            await update.message.reply_text(
                f"{EMOJI['warning']} Please provide a stock symbol.\n\n"
                f"Usage: `/analyze RELIANCE.NS`\n"
                f"Example: `/analyze TCS.NS`",
                parse_mode='Markdown'
            )
            return
        
        symbol = args[0].upper()
        
        # Validate symbol
        is_valid, error_msg = validate_stock_symbol(symbol)
        if not is_valid:
            await update.message.reply_text(
                format_error(error_msg, f"/analyze {symbol}"),
                parse_mode='Markdown'
            )
            return
        
        # Send "analyzing" message
        analyzing_msg = await update.message.reply_text(
            f"{EMOJI['loading']} Analyzing **{symbol}**...\n\n"
            f"This may take a few seconds.",
            parse_mode='Markdown'
        )
        
        # Get user settings (mode and timeframe)
        mode = 'balanced'
        timeframe = 'medium'
        
        try:
            with get_db_context() as db:
                settings = get_user_settings(db, user_id)
                if settings:
                    mode = settings.risk_mode
                    timeframe = settings.timeframe
        except Exception as e:
            logger.warning(f"Could not fetch user settings: {e}")
        
        # Perform analysis
        try:
            analysis = analyze_stock(symbol, mode=mode, timeframe=timeframe)
        except ValueError as e:
            await analyzing_msg.edit_text(
                format_error(str(e), f"/analyze {symbol}"),
                parse_mode='Markdown'
            )
            logger.error(f"Analysis failed for {symbol}: {e}")
            return
        except Exception as e:
            await analyzing_msg.edit_text(
                format_error(
                    "An unexpected error occurred during analysis. Please try again later.",
                    f"/analyze {symbol}"
                ),
                parse_mode='Markdown'
            )
            logger.error(f"Unexpected error analyzing {symbol}: {e}", exc_info=True)
            return
        
        # Format analysis result
        try:
            formatted_result = format_analysis_full(analysis)
        except Exception as e:
            logger.error(f"Error formatting analysis: {e}")
            formatted_result = f"{EMOJI['error']} Error formatting results. Please try again."
        
        # Split message if too long
        messages = chunk_message(formatted_result)
        
        # Delete "analyzing" message
        try:
            await analyzing_msg.delete()
        except Exception:
            pass
        
        # Send analysis results
        keyboard = create_analysis_action_keyboard(symbol)
        
        for i, msg in enumerate(messages):
            if i == len(messages) - 1:
                # Last message gets the keyboard
                await update.message.reply_text(
                    msg,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    msg,
                    parse_mode='Markdown'
                )
        
        logger.info(f"User {user_id} analyzed {symbol} (mode={mode}, timeframe={timeframe})")
        
    except Exception as e:
        logger.error(f"Error in analyze_command: {e}", exc_info=True)
        await update.message.reply_text(
            f"{EMOJI['error']} An unexpected error occurred. Please try again later."
        )


async def quick_analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /quick command - Quick analysis summary
    
    Usage: /quick SYMBOL
    Example: /quick RELIANCE.NS
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    
    try:
        # Parse arguments
        args = parse_command_args(update.message.text, 'quick')
        
        if not args:
            await update.message.reply_text(
                f"{EMOJI['warning']} Please provide a stock symbol.\n\n"
                f"Usage: `/quick RELIANCE.NS`",
                parse_mode='Markdown'
            )
            return
        
        symbol = args[0].upper()
        
        # Validate symbol
        is_valid, error_msg = validate_stock_symbol(symbol)
        if not is_valid:
            await update.message.reply_text(
                format_error(error_msg, f"/quick {symbol}"),
                parse_mode='Markdown'
            )
            return
        
        # Send "analyzing" message
        analyzing_msg = await update.message.reply_text(
            f"{EMOJI['loading']} Quick analysis for **{symbol}**...",
            parse_mode='Markdown'
        )
        
        # Get user settings
        mode = 'balanced'
        timeframe = 'medium'
        
        try:
            with get_db_context() as db:
                settings = get_user_settings(db, user_id)
                if settings:
                    mode = settings.risk_mode
                    timeframe = settings.timeframe
        except Exception as e:
            logger.warning(f"Could not fetch user settings: {e}")
        
        # Perform analysis
        try:
            analysis = analyze_stock(symbol, mode=mode, timeframe=timeframe)
        except Exception as e:
            await analyzing_msg.edit_text(
                format_error(str(e), f"/quick {symbol}"),
                parse_mode='Markdown'
            )
            return
        
        # Format quick summary
        from src.bot.utils.formatters import format_analysis_summary
        summary = format_analysis_summary(analysis)
        
        # Create keyboard
        keyboard = create_analysis_action_keyboard(symbol)
        
        # Send result
        await analyzing_msg.edit_text(
            summary,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        logger.info(f"User {user_id} quick analyzed {symbol}")
        
    except Exception as e:
        logger.error(f"Error in quick_analyze_command: {e}", exc_info=True)
        await update.message.reply_text(
            f"{EMOJI['error']} An unexpected error occurred. Please try again later."
        )
