"""
Settings Management Handlers

This module handles all settings-related commands:
- /settings - View and modify user settings
- /setmode MODE - Change risk mode
- /settimeframe TIMEFRAME - Change default timeframe
- /setcapital AMOUNT - Change default capital
"""

import logging
from typing import List
from telegram import Update
from telegram.ext import ContextTypes

from ..database.db import (
    get_db_context,
    get_or_create_user,
    get_user_settings,
    update_user_settings
)
from ..utils.formatters import format_success, format_error, format_warning
from ..utils.keyboards import create_settings_menu_keyboard
from ..utils.validators import validate_mode, validate_timeframe, parse_command_args
from ..config import RiskMode, Timeframe

logger = logging.getLogger(__name__)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /settings command.
    
    Shows current settings and provides inline buttons to modify them.
    
    Usage:
        /settings - Show settings menu
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        settings = get_user_settings(db, user_id)
        
        # Format settings message
        message = (
            "⚙️ *Your Settings*\n\n"
            f"🎯 *Risk Mode:* `{settings.risk_mode.upper()}`\n"
            f"   └ Determines filter strictness and position sizing\n\n"
            f"📊 *Timeframe:* `{settings.timeframe.upper()}`\n"
            f"   └ Default timeframe for analysis\n\n"
            f"💰 *Default Capital:* `₹{settings.default_capital:,.0f}`\n"
            f"   └ Used for position sizing calculations\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Quick Commands:*\n"
            f"• `/setmode [conservative|moderate|aggressive]`\n"
            f"• `/settimeframe [1d|1wk|1mo]`\n"
            f"• `/setcapital [amount]`\n\n"
            f"Or use the buttons below to modify:"
        )
        
        keyboard = create_settings_menu_keyboard()
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def setmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /setmode command.
    
    Changes the user's risk mode setting.
    
    Usage:
        /setmode conservative - Low risk, strict filters
        /setmode moderate - Balanced approach (default)
        /setmode aggressive - Higher risk, more opportunities
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Parse arguments
    args = parse_command_args(update.message.text)
    
    if not args:
        await update.message.reply_text(
            "🎯 *Set Risk Mode*\n\n"
            "*Usage:* `/setmode MODE`\n\n"
            "*Available modes:*\n"
            "• `conservative` - Lower risk, stricter filters\n"
            "• `moderate` - Balanced approach (default)\n"
            "• `aggressive` - Higher risk, more opportunities\n\n"
            "*Examples:*\n"
            "• `/setmode conservative`\n"
            "• `/setmode moderate`\n"
            "• `/setmode aggressive`",
            parse_mode='Markdown'
        )
        return
    
    mode = args[0].lower()
    
    # Validate mode
    is_valid, error_msg = validate_mode(mode)
    if not is_valid:
        await update.message.reply_text(format_error(error_msg))
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        old_settings = get_user_settings(db, user_id)
        
        # Update settings
        update_user_settings(db, user_id, risk_mode=mode)
        
        # Get mode description
        mode_descriptions = {
            'conservative': '🛡️ Conservative - Lower risk, stricter filters',
            'moderate': '⚖️ Moderate - Balanced approach',
            'aggressive': '🚀 Aggressive - Higher risk, more opportunities'
        }
        
        await update.message.reply_text(
            format_success(
                f"✓ Risk mode changed\n\n"
                f"Old: {old_settings.risk_mode.upper()}\n"
                f"New: {mode.upper()}\n\n"
                f"{mode_descriptions[mode]}"
            )
        )
        logger.info(f"User {user_id} changed risk mode: {old_settings.risk_mode} -> {mode}")


async def settimeframe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /settimeframe command.
    
    Changes the user's default timeframe setting.
    
    Usage:
        /settimeframe 1d - Daily timeframe
        /settimeframe 1wk - Weekly timeframe
        /settimeframe 1mo - Monthly timeframe
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Parse arguments
    args = parse_command_args(update.message.text)
    
    if not args:
        await update.message.reply_text(
            "📊 *Set Timeframe*\n\n"
            "*Usage:* `/settimeframe TIMEFRAME`\n\n"
            "*Available timeframes:*\n"
            "• `1d` - Daily (default)\n"
            "• `1wk` - Weekly\n"
            "• `1mo` - Monthly\n\n"
            "*Examples:*\n"
            "• `/settimeframe 1d`\n"
            "• `/settimeframe 1wk`\n"
            "• `/settimeframe 1mo`",
            parse_mode='Markdown'
        )
        return
    
    timeframe = args[0].lower()
    
    # Validate timeframe
    is_valid, error_msg = validate_timeframe(timeframe)
    if not is_valid:
        await update.message.reply_text(format_error(error_msg))
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        old_settings = get_user_settings(db, user_id)
        
        # Update settings
        update_user_settings(db, user_id, timeframe=timeframe)
        
        # Get timeframe description
        timeframe_descriptions = {
            '1d': '📈 Daily - Intraday and short-term trading',
            '1wk': '📊 Weekly - Swing trading',
            '1mo': '📉 Monthly - Long-term investing'
        }
        
        await update.message.reply_text(
            format_success(
                f"✓ Timeframe changed\n\n"
                f"Old: {old_settings.timeframe.upper()}\n"
                f"New: {timeframe.upper()}\n\n"
                f"{timeframe_descriptions[timeframe]}"
            )
        )
        logger.info(f"User {user_id} changed timeframe: {old_settings.timeframe} -> {timeframe}")


async def setcapital_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /setcapital command.
    
    Changes the user's default capital setting for position sizing.
    
    Usage:
        /setcapital 100000 - Set capital to ₹1,00,000
        /setcapital 500000 - Set capital to ₹5,00,000
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Parse arguments
    args = parse_command_args(update.message.text)
    
    if not args:
        await update.message.reply_text(
            "💰 *Set Default Capital*\n\n"
            "*Usage:* `/setcapital AMOUNT`\n\n"
            "*Examples:*\n"
            "• `/setcapital 100000` - ₹1,00,000\n"
            "• `/setcapital 500000` - ₹5,00,000\n"
            "• `/setcapital 1000000` - ₹10,00,000\n\n"
            "This amount is used for position sizing calculations.",
            parse_mode='Markdown'
        )
        return
    
    try:
        capital = float(args[0])
    except ValueError:
        await update.message.reply_text(
            format_error(
                "Invalid amount format.\n\n"
                "Please provide a number (e.g., `100000`)"
            )
        )
        return
    
    # Validate capital
    if capital < 10000:
        await update.message.reply_text(
            format_error("Minimum capital is ₹10,000")
        )
        return
    
    if capital > 100000000:  # 10 crore max
        await update.message.reply_text(
            format_error("Maximum capital is ₹10,00,00,000 (10 crore)")
        )
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        old_settings = get_user_settings(db, user_id)
        
        # Update settings
        update_user_settings(db, user_id, default_capital=capital)
        
        await update.message.reply_text(
            format_success(
                f"✓ Default capital changed\n\n"
                f"Old: ₹{old_settings.default_capital:,.0f}\n"
                f"New: ₹{capital:,.0f}\n\n"
                f"This will be used for position sizing in analysis."
            )
        )
        logger.info(f"User {user_id} changed capital: {old_settings.default_capital} -> {capital}")


async def reset_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /resetsettings command.
    
    Resets all settings to default values.
    
    Usage:
        /resetsettings - Reset to defaults
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    from ..utils.keyboards import create_confirmation_keyboard
    
    # Store confirmation in user context
    context.user_data['awaiting_settings_reset_confirmation'] = True
    
    keyboard = create_confirmation_keyboard("confirm_settings_reset")
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        settings = get_user_settings(db, user_id)
        
        await update.message.reply_text(
            f"⚠️ *Reset Settings*\n\n"
            f"*Current Settings:*\n"
            f"• Risk Mode: {settings.risk_mode.upper()}\n"
            f"• Timeframe: {settings.timeframe.upper()}\n"
            f"• Capital: ₹{settings.default_capital:,.0f}\n\n"
            f"*Default Settings:*\n"
            f"• Risk Mode: MODERATE\n"
            f"• Timeframe: 1D\n"
            f"• Capital: ₹1,00,000\n\n"
            f"Are you sure you want to reset?",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def confirm_settings_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and execute settings reset."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    with get_db_context() as db:
        # Reset to defaults
        update_user_settings(
            db,
            user_id,
            risk_mode='moderate',
            timeframe='1d',
            default_capital=100000.0
        )
        
        await query.edit_message_text(
            format_success(
                "✓ Settings reset to defaults\n\n"
                "• Risk Mode: MODERATE\n"
                "• Timeframe: 1D\n"
                "• Capital: ₹1,00,000"
            )
        )
        logger.info(f"User {user_id} reset settings to defaults")
    
    # Clear context
    context.user_data.pop('awaiting_settings_reset_confirmation', None)
