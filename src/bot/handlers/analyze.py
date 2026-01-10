"""
Analyze Command Handler
Handles /analyze command for stock analysis
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.config import EMOJI, ERROR_MESSAGES
from src.bot.services.analysis_service import analyze_stock
from src.core.formatters import (
    format_analysis_comprehensive,
    format_error, chunk_message
)
from src.bot.utils.keyboards import create_analysis_action_keyboard
from src.bot.utils.validators import validate_stock_symbol, parse_command_args
from src.bot.database.db import get_user_settings, get_db_context

logger = logging.getLogger(__name__)


def analyze_stock_with_settings(symbol: str, user_id: int, db) -> dict:
    """
    Analyze a stock using user settings from database.
    
    Args:
        symbol: Stock ticker symbol
        user_id: User ID to fetch settings for
        db: Database session
    
    Returns:
        Analysis dictionary with results, or dict with 'error' key if failed
    """
    try:
        # Get user settings
        settings = get_user_settings(db, user_id)
        
        # Default values
        mode = 'balanced'
        timeframe = 'medium'
        horizon = '3months'
        
        # Override with user settings if available
        if settings:
            mode = settings.risk_mode or mode
            timeframe = settings.timeframe or timeframe
            horizon = getattr(settings, 'investment_horizon', None) or horizon
        
        # Perform analysis (cache disabled by default to respect horizon changes)
        analysis = analyze_stock(symbol, mode=mode, timeframe=timeframe, horizon=horizon, use_cache=False)
        return analysis
        
    except ValueError as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        return {'error': str(e)}
    except Exception as e:
        logger.error(f"Unexpected error analyzing {symbol}: {e}", exc_info=True)
        return {'error': f"An unexpected error occurred: {str(e)}"}


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
        
        # Get user settings (mode, timeframe, horizon)
        mode = 'balanced'
        timeframe = 'medium'
        horizon = '3months'

        try:
            with get_db_context() as db:
                settings = get_user_settings(db, user_id)
                if settings:
                    mode = settings.risk_mode
                    timeframe = settings.timeframe
                    horizon = getattr(settings, 'investment_horizon', '3months') or '3months'
        except Exception as e:
            logger.warning(f"Could not fetch user settings: {e}")

        # Perform analysis (cache disabled by default to respect horizon changes)
        try:
            analysis = analyze_stock(symbol, mode=mode, timeframe=timeframe, horizon=horizon, use_cache=False)
        except ValueError as e:
            error_msg = str(e)
            
            # Provide more helpful error messages
            if 'Insufficient data' in error_msg:
                user_friendly_msg = (
                    f"⚠️ *Insufficient Data for {symbol}*\n\n"
                    f"This stock doesn't have enough historical data for analysis.\n\n"
                    f"*Possible reasons:*\n"
                    f"• Stock is newly listed (need at least 50 days of data)\n"
                    f"• Trading is suspended or halted\n"
                    f"• Symbol might be incorrect\n\n"
                    f"*Try:*\n"
                    f"• Verify the symbol is correct\n"
                    f"• Check if the stock is actively traded\n"
                    f"• Try analyzing a different stock"
                )
            else:
                user_friendly_msg = error_msg
            
            await analyzing_msg.edit_text(
                format_error(user_friendly_msg, output_mode='bot', command=f"/analyze {symbol}"),
                parse_mode='Markdown'
            )
            logger.error(f"Analysis failed for {symbol}: {e}")
            return
        except Exception as e:
            await analyzing_msg.edit_text(
                format_error(
                    "An unexpected error occurred during analysis. Please try again later.",
                    output_mode='bot',
                    command=f"/analyze {symbol}"
                ),
                parse_mode='Markdown'
            )
            logger.error(f"Unexpected error analyzing {symbol}: {e}", exc_info=True)
            return

        # Format analysis result using comprehensive formatter
        try:
            formatted_result = format_analysis_comprehensive(
                analysis,
                output_mode='bot',
                horizon=horizon
            )
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
        
        logger.info(f"User {user_id} analyzed {symbol} (mode={mode}, timeframe={timeframe}, horizon={horizon})")
        
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
        horizon = '3months'
        
        try:
            with get_db_context() as db:
                settings = get_user_settings(db, user_id)
                if settings:
                    mode = settings.risk_mode
                    timeframe = settings.timeframe
                    horizon = getattr(settings, 'investment_horizon', '3months') or '3months'
        except Exception as e:
            logger.warning(f"Could not fetch user settings: {e}")
        
        # Perform analysis (cache disabled by default to respect horizon changes)
        try:
            analysis = analyze_stock(symbol, mode=mode, timeframe=timeframe, horizon=horizon, use_cache=False)
        except ValueError as e:
            error_msg = str(e)
            
            # Provide more helpful error messages
            if 'Insufficient data' in error_msg:
                user_friendly_msg = (
                    f"⚠️ *Insufficient Data for {symbol}*\n\n"
                    f"This stock doesn't have enough historical data for analysis.\n\n"
                    f"*Possible reasons:*\n"
                    f"• Stock is newly listed (need at least 50 days of data)\n"
                    f"• Trading is suspended or halted\n"
                    f"• Symbol might be incorrect\n\n"
                    f"*Try:*\n"
                    f"• Verify the symbol is correct\n"
                    f"• Check if the stock is actively traded\n"
                    f"• Try analyzing a different stock"
                )
            else:
                user_friendly_msg = error_msg
            
            await analyzing_msg.edit_text(
                format_error(user_friendly_msg, output_mode='bot', command=f"/quick {symbol}"),
                parse_mode='Markdown'
            )
            logger.error(f"Quick analysis failed for {symbol}: {e}")
            return
        except Exception as e:
            await analyzing_msg.edit_text(
                format_error(
                    "An unexpected error occurred during analysis. Please try again later.",
                    output_mode='bot',
                    command=f"/quick {symbol}"
                ),
                parse_mode='Markdown'
            )
            logger.error(f"Unexpected error in quick analysis for {symbol}: {e}", exc_info=True)
            return

        # Format using comprehensive formatter
        try:
            formatted_result = format_analysis_comprehensive(
                analysis,
                output_mode='bot',
                horizon=horizon
            )
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

        # Create keyboard
        keyboard = create_analysis_action_keyboard(symbol)

        # Send results
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
        
        logger.info(f"User {user_id} quick analyzed {symbol}")
        
    except Exception as e:
        logger.error(f"Error in quick_analyze_command: {e}", exc_info=True)
        await update.message.reply_text(
            f"{EMOJI['error']} An unexpected error occurred. Please try again later."
        )
