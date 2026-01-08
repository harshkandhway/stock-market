"""
Callback Query Handlers for Inline Button Interactions

This module handles all callback queries triggered by inline keyboard buttons.
Callback data format: "action:parameter" or "action:param1:param2"

Examples:
    - "watchlist_add:RELIANCE.NS"
    - "alert_menu:TCS.NS"
    - "analyze_quick:INFY.NS"
    - "settings_mode:conservative"
"""

import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..database.db import (
    get_db_context,
    get_or_create_user,
    get_user_settings,
    update_user_settings,
    add_to_watchlist,
    remove_from_watchlist,
    get_user_watchlist,
    create_alert,
    get_user_alerts,
    delete_alert
)
from ..services.analysis_service import analyze_stock, get_current_price
from ..utils.formatters import (
    format_analysis_summary,
    format_success,
    format_error,
    format_watchlist,
    format_alert
)
from ..utils.keyboards import (
    create_watchlist_menu_keyboard,
    create_alert_type_keyboard,
    create_settings_menu_keyboard,
    create_back_button
)
from ..utils.validators import validate_stock_symbol, validate_price
from ..config import RiskMode, Timeframe

logger = logging.getLogger(__name__)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main callback query router.
    
    Routes callback queries to appropriate handlers based on the action prefix.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"Callback from user {user_id}: {callback_data}")
    
    try:
        # Parse callback data
        parts = callback_data.split(':')
        action = parts[0]
        params = parts[1:] if len(parts) > 1 else []
        
        # Route to appropriate handler
        if action == "watchlist_add":
            await handle_watchlist_add(query, context, params)
        elif action == "watchlist_remove":
            await handle_watchlist_remove(query, context, params)
        elif action == "watchlist_menu":
            await handle_watchlist_menu(query, context, params)
        elif action == "alert_menu":
            await handle_alert_menu(query, context, params)
        elif action == "alert_price":
            await handle_alert_price_setup(query, context, params)
        elif action == "alert_rsi":
            await handle_alert_rsi_setup(query, context, params)
        elif action == "alert_signal":
            await handle_alert_signal_setup(query, context, params)
        elif action == "alert_delete":
            await handle_alert_delete(query, context, params)
        elif action == "settings_menu":
            await handle_settings_menu(query, context)
        elif action == "settings_mode":
            await handle_settings_mode(query, context, params)
        elif action == "settings_timeframe":
            await handle_settings_timeframe(query, context, params)
        elif action == "analyze_quick":
            await handle_analyze_quick(query, context, params)
        elif action == "analyze_full":
            await handle_analyze_full(query, context, params)
        elif action == "back":
            await handle_back(query, context, params)
        elif action == "close":
            await handle_close(query, context)
        else:
            await query.edit_message_text(
                format_error(f"Unknown action: {action}")
            )
    
    except Exception as e:
        logger.error(f"Error handling callback {callback_data}: {e}", exc_info=True)
        await query.edit_message_text(
            format_error(f"An error occurred: {str(e)}")
        )


# ============================================================================
# WATCHLIST CALLBACKS
# ============================================================================

async def handle_watchlist_add(query, context, params: list) -> None:
    """Add a stock to watchlist."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    symbol = params[0]
    user_id = query.from_user.id
    
    # Validate symbol
    is_valid, error_msg = validate_stock_symbol(symbol)
    if not is_valid:
        await query.edit_message_text(format_error(error_msg))
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, query.from_user.username)
        
        # Check if already in watchlist
        watchlist = get_user_watchlist(db, user_id)
        if any(w.symbol == symbol for w in watchlist):
            await query.edit_message_text(
                format_error(f"✓ {symbol} is already in your watchlist")
            )
            return
        
        # Add to watchlist
        success = add_to_watchlist(db, user_id, symbol)
        
        if success:
            await query.edit_message_text(
                format_success(
                    f"✓ Added {symbol} to your watchlist!\n\n"
                    f"Use /watchlist to view all stocks."
                )
            )
        else:
            await query.edit_message_text(
                format_error(f"Failed to add {symbol} to watchlist")
            )


async def handle_watchlist_remove(query, context, params: list) -> None:
    """Remove a stock from watchlist."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    symbol = params[0]
    user_id = query.from_user.id
    
    with get_db_context() as db:
        success = remove_from_watchlist(db, user_id, symbol)
        
        if success:
            await query.edit_message_text(
                format_success(f"✓ Removed {symbol} from your watchlist")
            )
        else:
            await query.edit_message_text(
                format_error(f"Failed to remove {symbol} from watchlist")
            )


async def handle_watchlist_menu(query, context, params: list) -> None:
    """Show watchlist menu."""
    user_id = query.from_user.id
    
    with get_db_context() as db:
        watchlist = get_user_watchlist(db, user_id)
        
        if not watchlist:
            await query.edit_message_text(
                "📋 *Your Watchlist is Empty*\n\n"
                "Add stocks using:\n"
                "• /analyze SYMBOL (then click 'Add to Watchlist')\n"
                "• /watchlist add SYMBOL",
                parse_mode='Markdown'
            )
            return
        
        message = format_watchlist(watchlist)
        keyboard = create_watchlist_menu_keyboard([w.symbol for w in watchlist])
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


# ============================================================================
# ALERT CALLBACKS
# ============================================================================

async def handle_alert_menu(query, context, params: list) -> None:
    """Show alert type selection menu."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    symbol = params[0]
    
    keyboard = create_alert_type_keyboard(symbol)
    
    await query.edit_message_text(
        f"🔔 *Set Alert for {symbol}*\n\n"
        f"Choose the type of alert you want to set:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_alert_price_setup(query, context, params: list) -> None:
    """Set up price alert (requires user to send price in next message)."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    symbol = params[0]
    user_id = query.from_user.id
    
    # Get current price for reference
    try:
        current_price = get_current_price(symbol)
        price_info = f"\n\nℹ️ Current price: ₹{current_price:.2f}"
    except Exception as e:
        logger.warning(f"Could not fetch current price: {e}")
        price_info = ""
    
    # Store symbol in user context for next message
    context.user_data['awaiting_price_alert'] = symbol
    
    await query.edit_message_text(
        f"🔔 *Price Alert for {symbol}*{price_info}\n\n"
        f"Send me the target price (e.g., `2500` or `2500.50`):\n\n"
        f"I'll notify you when the price reaches this level.",
        parse_mode='Markdown'
    )


async def handle_alert_rsi_setup(query, context, params: list) -> None:
    """Set up RSI alert."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    symbol = params[0]
    user_id = query.from_user.id
    
    # Create overbought (RSI > 70) and oversold (RSI < 30) alerts
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, query.from_user.username)
        
        # Create oversold alert (RSI < 30)
        alert_oversold = create_alert(
            db=db,
            user_id=user_id,
            symbol=symbol,
            alert_type='rsi',
            condition={'operator': '<', 'value': 30},
            message=f"RSI oversold for {symbol} (< 30)"
        )
        
        # Create overbought alert (RSI > 70)
        alert_overbought = create_alert(
            db=db,
            user_id=user_id,
            symbol=symbol,
            alert_type='rsi',
            condition={'operator': '>', 'value': 70},
            message=f"RSI overbought for {symbol} (> 70)"
        )
        
        if alert_oversold and alert_overbought:
            await query.edit_message_text(
                format_success(
                    f"✓ RSI alerts set for {symbol}!\n\n"
                    f"• Alert when RSI < 30 (Oversold)\n"
                    f"• Alert when RSI > 70 (Overbought)\n\n"
                    f"Use /alerts to manage your alerts."
                )
            )
        else:
            await query.edit_message_text(
                format_error("Failed to create RSI alerts")
            )


async def handle_alert_signal_setup(query, context, params: list) -> None:
    """Set up signal change alert."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    symbol = params[0]
    user_id = query.from_user.id
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, query.from_user.username)
        
        # Create signal change alert
        alert = create_alert(
            db=db,
            user_id=user_id,
            symbol=symbol,
            alert_type='signal_change',
            condition={},
            message=f"Signal changed for {symbol}"
        )
        
        if alert:
            await query.edit_message_text(
                format_success(
                    f"✓ Signal change alert set for {symbol}!\n\n"
                    f"You'll be notified when the recommendation changes.\n\n"
                    f"Use /alerts to manage your alerts."
                )
            )
        else:
            await query.edit_message_text(
                format_error("Failed to create signal change alert")
            )


async def handle_alert_delete(query, context, params: list) -> None:
    """Delete an alert."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    alert_id = int(params[0])
    user_id = query.from_user.id
    
    with get_db_context() as db:
        success = delete_alert(db, alert_id, user_id)
        
        if success:
            await query.edit_message_text(
                format_success("✓ Alert deleted successfully")
            )
        else:
            await query.edit_message_text(
                format_error("Failed to delete alert")
            )


# ============================================================================
# SETTINGS CALLBACKS
# ============================================================================

async def handle_settings_menu(query, context) -> None:
    """Show settings menu."""
    user_id = query.from_user.id
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, query.from_user.username)
        settings = get_user_settings(db, user_id)
        
        message = (
            "⚙️ *Your Settings*\n\n"
            f"🎯 Risk Mode: `{settings.risk_mode}`\n"
            f"📊 Timeframe: `{settings.timeframe}`\n"
            f"💰 Capital: `₹{settings.default_capital:,.0f}`\n\n"
            f"Select a setting to change:"
        )
        
        keyboard = create_settings_menu_keyboard()
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def handle_settings_mode(query, context, params: list) -> None:
    """Change risk mode setting."""
    if not params:
        # Show mode selection
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡️ Conservative", callback_data="settings_mode:conservative")],
            [InlineKeyboardButton("⚖️ Moderate", callback_data="settings_mode:moderate")],
            [InlineKeyboardButton("🚀 Aggressive", callback_data="settings_mode:aggressive")],
            [InlineKeyboardButton("◀️ Back", callback_data="settings_menu")]
        ])
        
        await query.edit_message_text(
            "🎯 *Select Risk Mode*\n\n"
            "• Conservative: Lower risk, strict filters\n"
            "• Moderate: Balanced approach\n"
            "• Aggressive: Higher risk, more opportunities",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    mode = params[0]
    user_id = query.from_user.id
    
    # Validate mode
    if mode not in ['conservative', 'moderate', 'aggressive']:
        await query.edit_message_text(format_error("Invalid risk mode"))
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, query.from_user.username)
        update_user_settings(db, user_id, risk_mode=mode)
        
        await query.edit_message_text(
            format_success(f"✓ Risk mode changed to: {mode.upper()}")
        )


async def handle_settings_timeframe(query, context, params: list) -> None:
    """Change timeframe setting."""
    if not params:
        # Show timeframe selection
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Day", callback_data="settings_timeframe:1d")],
            [InlineKeyboardButton("1 Week", callback_data="settings_timeframe:1wk")],
            [InlineKeyboardButton("1 Month", callback_data="settings_timeframe:1mo")],
            [InlineKeyboardButton("◀️ Back", callback_data="settings_menu")]
        ])
        
        await query.edit_message_text(
            "📊 *Select Timeframe*\n\n"
            "Choose the default timeframe for analysis:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    timeframe = params[0]
    user_id = query.from_user.id
    
    # Validate timeframe
    if timeframe not in ['1d', '1wk', '1mo']:
        await query.edit_message_text(format_error("Invalid timeframe"))
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, query.from_user.username)
        update_user_settings(db, user_id, timeframe=timeframe)
        
        await query.edit_message_text(
            format_success(f"✓ Timeframe changed to: {timeframe}")
        )


# ============================================================================
# ANALYSIS CALLBACKS
# ============================================================================

async def handle_analyze_quick(query, context, params: list) -> None:
    """Perform quick analysis from callback."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    symbol = params[0]
    user_id = query.from_user.id
    
    # Show analyzing message
    await query.edit_message_text(f"🔍 Analyzing {symbol}...")
    
    try:
        with get_db_context() as db:
            user = get_or_create_user(db, user_id, query.from_user.username)
            settings = get_user_settings(db, user_id)
            
            # Perform analysis
            result = analyze_stock(
                symbol=symbol,
                mode=settings.risk_mode,
                timeframe=settings.timeframe
            )
            
            if result['status'] == 'success':
                message = format_analysis_summary(result['data'])
                await query.edit_message_text(message, parse_mode='Markdown')
            else:
                await query.edit_message_text(
                    format_error(result.get('message', 'Analysis failed'))
                )
    
    except Exception as e:
        logger.error(f"Error in quick analysis: {e}", exc_info=True)
        await query.edit_message_text(
            format_error(f"Analysis error: {str(e)}")
        )


async def handle_analyze_full(query, context, params: list) -> None:
    """Perform full analysis from callback."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    symbol = params[0]
    
    # Redirect to analyze command
    await query.edit_message_text(
        f"💡 Use `/analyze {symbol}` for full analysis"
    )


# ============================================================================
# UTILITY CALLBACKS
# ============================================================================

async def handle_back(query, context, params: list) -> None:
    """Handle back button - go to previous menu."""
    if not params:
        await query.edit_message_text("Use /menu to see the main menu")
        return
    
    destination = params[0]
    
    if destination == "watchlist":
        await handle_watchlist_menu(query, context, [])
    elif destination == "settings":
        await handle_settings_menu(query, context)
    else:
        await query.edit_message_text("Use /menu to see the main menu")


async def handle_close(query, context) -> None:
    """Close/delete the message."""
    await query.message.delete()
