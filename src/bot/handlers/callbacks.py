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
from src.core.formatters import (
    format_analysis_comprehensive,
    format_success,
    format_error,
    format_watchlist,
    format_alert,
    chunk_message,
    format_comparison_table,
    format_warning,
    format_position_sizing
)
from ..utils.keyboards import (
    create_watchlist_menu_keyboard,
    create_alert_type_keyboard,
    create_settings_menu_keyboard,
    create_back_button
)
from ..utils.validators import validate_stock_symbol, validate_price
from ..config import RiskMode, Timeframe, MAX_MESSAGE_LENGTH

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
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"Callback from user {user_id}: {callback_data}")
    
    # Check authorization (if admin IDs are configured, only allow admins)
    # If TELEGRAM_ADMIN_IDS is empty, allow everyone (public bot)
    from ..config import TELEGRAM_ADMIN_IDS
    if TELEGRAM_ADMIN_IDS:  # Only check if admin IDs are configured
        if user_id not in TELEGRAM_ADMIN_IDS:
            await query.answer(
                "⛔ You are not authorized to use this bot.",
                show_alert=True
            )
            logger.warning(f"Unauthorized callback attempt by user {user_id}: {callback_data}")
            return
    
    try:
        # Parse callback data
        parts = callback_data.split(':')
        action = parts[0]
        params = parts[1:] if len(parts) > 1 else []
        
        # Handle settings callbacks through the settings handler
        if callback_data.startswith("settings_") or callback_data.startswith("daily_buy_"):
            from ..handlers.settings import handle_settings_callback
            await handle_settings_callback(update, context)
            return
        
        # Acknowledge the callback for other handlers
        await query.answer()
        
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
        elif action == "analyze":
            await handle_analyze_refresh(query, context, params)
        elif action == "analyze_quick":
            await handle_analyze_quick(query, context, params)
        elif action == "analyze_full":
            await handle_analyze_full(query, context, params)
        elif action == "back":
            await handle_back(query, context, params)
        elif action == "close":
            await handle_close(query, context)
        elif action == "main_menu":
            await handle_main_menu(query, context)
        elif action == "noop":
            # No operation - just acknowledge
            pass
        elif action == "confirm":
            await handle_confirm(query, context, params)
        elif action == "cancel":
            await handle_cancel(query, context, params)
        elif action == "chart":
            await handle_chart(query, context, params)
        elif action == "portfolio_add":
            await handle_portfolio_add(query, context, params)
        elif action == "position_sizing":
            await handle_position_sizing(query, context, params)
        elif action == "watchlist_add_prompt":
            await handle_watchlist_add_prompt(query, context)
        elif action == "watchlist_remove_prompt":
            await handle_watchlist_remove_prompt(query, context)
        elif action == "watchlist_show":
            await handle_watchlist_menu(query, context, [])
        elif action == "watchlist_analyze":
            await handle_watchlist_analyze(query, context)
        elif action == "watchlist_clear_confirm":
            await handle_watchlist_clear_confirm(query, context)
        elif action == "alert_breakout":
            await handle_alert_breakout(query, context, params)
        elif action == "alert_divergence":
            await handle_alert_divergence(query, context, params)
        elif action == "alert_view":
            await handle_alert_view(query, context, params)
        elif action == "alert_add_prompt":
            await handle_alert_add_prompt(query, context)
        elif action == "alert_clear_all_confirm":
            await handle_alert_clear_all_confirm(query, context)
        elif action == "alert_disable":
            await handle_alert_disable(query, context, params)
        elif action == "alert_enable":
            await handle_alert_enable(query, context, params)
        elif action == "confirm_reset":
            await handle_confirm_reset(query, context)
        elif action == "cancel_reset":
            await handle_cancel_reset(query, context)
        elif action.startswith("schedule_"):
            await handle_schedule(query, context, action, params)
        else:
            await query.edit_message_text(
                format_error(f"Unknown action: {action}")
            )
    
    except Exception as e:
        logger.error(f"Error handling callback {callback_data}: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                format_error(f"An error occurred: {str(e)}")
            )
        except Exception:
            pass


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
            telegram_id=user_id,
            symbol=symbol,
            alert_type='rsi',
            condition_type='below',
            threshold_value=30.0,
            condition_data={'operator': '<', 'value': 30}
        )
        
        # Create overbought alert (RSI > 70)
        alert_overbought = create_alert(
            db=db,
            telegram_id=user_id,
            symbol=symbol,
            alert_type='rsi',
            condition_type='above',
            threshold_value=70.0,
            condition_data={'operator': '>', 'value': 70}
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
            telegram_id=user_id,
            symbol=symbol,
            alert_type='signal_change',
            condition_type='change',
            condition_data={}
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

async def handle_analyze_refresh(query, context, params: list) -> None:
    """Handle refresh analysis button - performs full analysis."""
    if not params:
        await query.edit_message_text(format_error("Invalid callback data"))
        return
    
    symbol = params[0]
    user_id = query.from_user.id
    
    # Show analyzing message
    await query.edit_message_text(f"🔄 Refreshing analysis for {symbol}...")
    
    try:
        from src.bot.handlers.analyze import analyze_stock_with_settings
        from src.bot.database.db import get_db_context, get_or_create_user, get_user_settings
        
        with get_db_context() as db:
            user = get_or_create_user(db, user_id, query.from_user.username)
            settings = get_user_settings(db, user_id)
            
            # Perform full analysis
            analysis = analyze_stock_with_settings(
                symbol=symbol,
                user_id=user_id,
                db=db
            )
            
            if analysis and 'error' not in analysis:
                # Get horizon from settings
                horizon = getattr(settings, 'investment_horizon', '3months')

                # Use comprehensive formatter
                message = format_analysis_comprehensive(
                    analysis,
                    output_mode='bot',
                    horizon=horizon
                )

                # Split message if too long
                messages = chunk_message(message)

                # Create action keyboard
                from src.bot.utils.keyboards import create_analysis_action_keyboard
                keyboard = create_analysis_action_keyboard(symbol)

                # Send messages
                if len(messages) == 1:
                    await query.edit_message_text(
                        messages[0],
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    # For multiple messages, delete original and send new ones
                    await query.message.delete()
                    for i, msg in enumerate(messages):
                        if i == len(messages) - 1:
                            await query.message.reply_text(
                                msg,
                                reply_markup=keyboard,
                                parse_mode='Markdown'
                            )
                        else:
                            await query.message.reply_text(
                                msg,
                                parse_mode='Markdown'
                            )
            else:
                error_msg = analysis.get('error', 'Analysis failed') if analysis else 'Analysis failed'
                
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
                    user_friendly_msg = f"Failed to analyze {symbol}: {error_msg}"
                
                await query.edit_message_text(
                    format_error(user_friendly_msg, output_mode='bot')
                )
    
    except Exception as e:
        logger.error(f"Error refreshing analysis: {e}", exc_info=True)
        await query.edit_message_text(
            format_error(f"Refresh error: {str(e)}")
        )


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
            horizon = getattr(settings, 'investment_horizon', '3months')
            result = analyze_stock(
                symbol=symbol,
                mode=settings.risk_mode,
                timeframe=settings.timeframe,
                horizon=horizon,
                use_cache=False
            )

            if result['status'] == 'success':
                message = format_analysis_comprehensive(
                    result['data'],
                    output_mode='bot',
                    horizon=horizon
                )
                messages = chunk_message(message)

                # Send messages
                if len(messages) == 1:
                    await query.edit_message_text(messages[0], parse_mode='Markdown')
                else:
                    await query.message.delete()
                    for msg in messages:
                        await query.message.reply_text(msg, parse_mode='Markdown')
            else:
                error_msg = result.get('message', 'Analysis failed')
                
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
                
                await query.edit_message_text(
                    format_error(user_friendly_msg, output_mode='bot')
                )
    
    except Exception as e:
        logger.error(f"Error in quick analysis: {e}", exc_info=True)
        await query.edit_message_text(
            format_error(f"Analysis error: {str(e)}")
        )


async def handle_analyze_full(query, context, params: list) -> None:
    """Perform full analysis from callback - redirects to /analyze command."""
    if not params:
        await query.answer("❌ Invalid symbol", show_alert=True)
        return
    
    symbol = params[0]
    
    # Validate symbol
    if not validate_stock_symbol(symbol):
        await query.answer(f"❌ Invalid symbol: {symbol}", show_alert=True)
        return
    
    # Acknowledge callback
    await query.answer("📊 Fetching full analysis...")
    
    # Get user settings and perform full analysis
    user_id = query.from_user.id
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, query.from_user.username)
        settings = get_user_settings(db, user_id)
        
        # Get user preferences
        mode = settings.risk_mode if settings and settings.risk_mode else 'balanced'
        timeframe = settings.timeframe if settings and settings.timeframe else 'medium'
        horizon = getattr(settings, 'investment_horizon', None) or '3months'
        
        # Perform analysis
        analysis_result = analyze_stock(
            symbol=symbol,
            mode=mode,
            timeframe=timeframe,
            horizon=horizon,
            use_cache=False
        )
        
        if 'error' in analysis_result:
            await query.edit_message_text(
                format_error(analysis_result['error'], 'bot'),
                parse_mode='Markdown'
            )
            return
        
        # Format comprehensive analysis
        formatted = format_analysis_comprehensive(
            analysis_result,
            output_mode='bot',
            horizon=horizon
        )
        
        # Split into chunks if needed
        chunks = chunk_message(formatted, MAX_MESSAGE_LENGTH)
        
        # Send first chunk with action buttons
        from ..utils.keyboards import create_analysis_action_keyboard
        keyboard = create_analysis_action_keyboard(symbol)
        
        await query.edit_message_text(
            chunks[0],
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        # Send remaining chunks
        for chunk in chunks[1:]:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=chunk,
                parse_mode='Markdown'
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


async def handle_main_menu(query, context) -> None:
    """Return to main menu with helpful guide."""
    await query.edit_message_text(
        """
*📊 STOCK ANALYZER PRO - MAIN MENU*
━━━━━━━━━━━━━━━━━━━━

*🔍 ANALYZE STOCKS*
`/analyze RELIANCE.NS` - Full analysis with recommendation
`/quick TCS.NS` - Quick summary

*📈 COMPARE STOCKS*
`/compare INFY.NS TCS.NS` - Side by side comparison

*⚙️ YOUR SETTINGS*
`/settings` - Customize your preferences
_(Risk level, investment period, capital)_

*⭐ TRACK FAVORITES*
`/watchlist` - Manage your stock list
`/alerts` - Set price notifications

*💼 YOUR PORTFOLIO*
`/portfolio` - Track your investments

━━━━━━━━━━━━━━━━━━━━

*💡 First time?* Start with `/settings` to configure your preferences!

Use `/help` for complete command list.
""",
        parse_mode='Markdown'
    )


async def handle_confirm(query, context, params: list) -> None:
    """Handle confirmation callbacks."""
    if not params:
        await query.edit_message_text(format_error("Invalid confirmation"))
        return
    
    action = params[0]
    data = params[1] if len(params) > 1 else None
    user_id = query.from_user.id
    
    if action == "confirm_settings_reset":
        from ..handlers.settings import confirm_settings_reset
        await confirm_settings_reset(query.message.chat_id, context)
    else:
        await query.edit_message_text(format_success(f"Action {action} confirmed"))


async def handle_cancel(query, context, params: list) -> None:
    """Handle cancellation callbacks."""
    await query.edit_message_text("❌ Operation cancelled")


# ============================================================================
# MISSING HANDLERS - Add implementations
# ============================================================================

async def handle_chart(query, context, params: list) -> None:
    """Handle chart view request."""
    if not params:
        await query.edit_message_text(format_error("Invalid symbol"))
        return
    
    symbol = params[0]
    await query.edit_message_text(
        f"📊 *Chart for {symbol}*\n\n"
        f"Chart generation coming soon!\n\n"
        f"For now, use external charting tools or visit:\n"
        f"https://in.tradingview.com/chart/?symbol=NSE:{symbol.replace('.NS', '')}",
        parse_mode='Markdown'
    )


async def handle_portfolio_add(query, context, params: list) -> None:
    """Handle add to portfolio button."""
    if not params:
        await query.edit_message_text(format_error("Invalid symbol"))
        return
    
    symbol = params[0]
    await query.edit_message_text(
        f"💼 *Add {symbol} to Portfolio*\n\n"
        f"Use the command:\n"
        f"`/portfolio add {symbol} SHARES PRICE`\n\n"
        f"Example:\n"
        f"`/portfolio add {symbol} 10 3500`",
        parse_mode='Markdown'
    )


async def handle_position_sizing(query, context, params: list) -> None:
    """Handle position sizing button - shows detailed position sizing information."""
    if not params:
        await query.edit_message_text(format_error("Invalid symbol", output_mode='bot'))
        return
    
    symbol = params[0]
    user_id = query.from_user.id
    
    # Show loading message
    await query.edit_message_text(f"💰 Calculating position sizing for {symbol}...")
    
    try:
        from src.bot.handlers.analyze import analyze_stock_with_settings
        
        with get_db_context() as db:
            user = get_or_create_user(db, user_id, query.from_user.username)
            settings = get_user_settings(db, user_id)
            
            # Get user's capital from settings
            capital = getattr(settings, 'default_capital', 100000)
            
            # Perform analysis to get current data
            analysis = analyze_stock_with_settings(
                symbol=symbol,
                user_id=user_id,
                db=db
            )
            
            if analysis and 'error' not in analysis:
                # Format position sizing details
                message = format_position_sizing(
                    analysis,
                    capital=capital,
                    output_mode='bot'
                )
                
                # Create back button
                from src.bot.utils.keyboards import create_analysis_action_keyboard
                keyboard = create_analysis_action_keyboard(symbol)
                
                await query.edit_message_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                error_msg = analysis.get('error', 'Analysis failed') if analysis else 'Analysis failed'
                await query.edit_message_text(
                    format_error(f"Failed to analyze {symbol}: {error_msg}", output_mode='bot')
                )
    
    except Exception as e:
        logger.error(f"Error calculating position sizing: {e}", exc_info=True)
        await query.edit_message_text(
            format_error(f"Error calculating position sizing: {str(e)}", output_mode='bot')
        )


async def handle_watchlist_add_prompt(query, context) -> None:
    """Prompt user to add stock to watchlist."""
    await query.edit_message_text(
        "⭐ *Add Stock to Watchlist*\n\n"
        "Send me the stock symbol:\n\n"
        "Example: `RELIANCE.NS`\n\n"
        "_Just type the symbol and send_",
        parse_mode='Markdown'
    )


async def handle_watchlist_remove_prompt(query, context) -> None:
    """Prompt user to remove stock from watchlist."""
    from src.bot.database.db import get_db_context, get_user_watchlist
    from src.bot.utils.keyboards import create_watchlist_keyboard
    
    user_id = query.from_user.id
    with get_db_context() as db:
        watchlist = get_user_watchlist(db, user_id)
        
        if not watchlist:
            await query.edit_message_text("⭐ Your watchlist is empty!")
            return
        
        keyboard = create_watchlist_keyboard([w.symbol for w in watchlist])
        await query.edit_message_text(
            "➖ *Remove Stock from Watchlist*\n\n"
            "Select a stock to remove:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def handle_watchlist_analyze(query, context) -> None:
    """Analyze all stocks in watchlist."""
    from src.bot.database.db import get_db_context, get_user_watchlist, get_user_settings
    from src.bot.services.analysis_service import analyze_multiple_stocks

    user_id = query.from_user.id
    
    with get_db_context() as db:
        watchlist = get_user_watchlist(db, user_id)
        
        if not watchlist:
            await query.edit_message_text("⭐ Your watchlist is empty!")
            return
        
        settings = get_user_settings(db, user_id)
        symbols = [w.symbol for w in watchlist]
        
        # Show progress message
        await query.edit_message_text(
            f"🔍 Analyzing {len(symbols)} stock(s) from your watchlist...\n\n"
            f"This may take a moment."
        )
        
        try:
            # Analyze all stocks
            results = analyze_multiple_stocks(
                symbols=symbols,
                mode=settings.risk_mode if settings else 'balanced',
                timeframe=settings.timeframe if settings else 'medium'
            )
            
            # Filter successful results (successful ones don't have 'error' key)
            successful_results = [r for r in results if not r.get('error', False)]
            failed_results = [r for r in results if r.get('error', False)]
            
            if not successful_results:
                await query.edit_message_text(
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
            
            # Edit message with first chunk
            await query.edit_message_text(chunks[0], parse_mode='Markdown')
            
            # Send remaining chunks as new messages
            for chunk in chunks[1:]:
                await query.message.reply_text(chunk, parse_mode='Markdown')
            
            logger.info(f"User {user_id} analyzed watchlist: {len(successful_results)} successful, {len(failed_results)} failed")
        
        except Exception as e:
            logger.error(f"Error analyzing watchlist: {e}", exc_info=True)
            await query.edit_message_text(
                format_error(f"An error occurred during analysis: {str(e)}")
            )


async def handle_watchlist_clear_confirm(query, context) -> None:
    """Confirm watchlist clear."""
    from src.bot.utils.keyboards import create_confirmation_keyboard
    
    keyboard = create_confirmation_keyboard("watchlist_clear", "")
    await query.edit_message_text(
        "🗑️ *Clear Watchlist?*\n\n"
        "Are you sure you want to remove all stocks from your watchlist?",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_alert_breakout(query, context, params: list) -> None:
    """Handle breakout alert setup."""
    if not params:
        await query.edit_message_text(format_error("Invalid symbol"))
        return
    
    symbol = params[0]
    await query.edit_message_text(
        f"📊 *Breakout Alert for {symbol}*\n\n"
        f"Use: `/alert {symbol} breakout PRICE`\n\n"
        f"Example: `/alert {symbol} breakout 3500`",
        parse_mode='Markdown'
    )


async def handle_alert_divergence(query, context, params: list) -> None:
    """Handle divergence alert setup."""
    if not params:
        await query.edit_message_text(format_error("Invalid symbol"))
        return
    
    symbol = params[0]
    await query.edit_message_text(
        f"⚡ *Divergence Alert for {symbol}*\n\n"
        f"Divergence alerts notify you when RSI or MACD shows divergence patterns.\n\n"
        f"Use: `/alert {symbol} divergence`",
        parse_mode='Markdown'
    )


async def handle_alert_view(query, context, params: list) -> None:
    """View alert details."""
    if not params:
        await query.edit_message_text(format_error("Invalid alert ID"))
        return
    
    alert_id = params[0]
    from src.bot.database.db import get_db_context, get_alert_by_id
    from src.bot.utils.keyboards import create_alert_detail_keyboard
    
    user_id = query.from_user.id
    with get_db_context() as db:
        alert = get_alert_by_id(db, alert_id)
        
        if not alert or alert.user_id != user_id:
            await query.edit_message_text(format_error("Alert not found"))
            return
        
        keyboard = create_alert_detail_keyboard(alert_id)
        status = "✅ Enabled" if alert.is_active else "⏸️ Disabled"
        
        await query.edit_message_text(
            f"🔔 *Alert Details*\n\n"
            f"Symbol: {alert.symbol}\n"
            f"Type: {alert.alert_type}\n"
            f"Condition: {alert.condition}\n"
            f"Status: {status}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def handle_alert_add_prompt(query, context) -> None:
    """Prompt to add alert."""
    await query.edit_message_text(
        "🔔 *Add Alert*\n\n"
        "Send me:\n"
        "`/alert SYMBOL TYPE VALUE`\n\n"
        "Examples:\n"
        "• `/alert RELIANCE.NS price 2500`\n"
        "• `/alert TCS.NS rsi 30`",
        parse_mode='Markdown'
    )


async def handle_alert_clear_all_confirm(query, context) -> None:
    """Confirm clear all alerts."""
    from src.bot.utils.keyboards import create_confirmation_keyboard
    
    keyboard = create_confirmation_keyboard("alert_clear_all", "")
    await query.edit_message_text(
        "🗑️ *Clear All Alerts?*\n\n"
        "Are you sure you want to delete all your alerts?",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_alert_disable(query, context, params: list) -> None:
    """Disable an alert."""
    if not params:
        await query.edit_message_text(format_error("Invalid alert ID"))
        return
    
    alert_id = params[0]
    from src.bot.database.db import get_db_context, get_alert_by_id, update_alert
    
    user_id = query.from_user.id
    with get_db_context() as db:
        alert = get_alert_by_id(db, alert_id)
        
        if not alert or alert.user_id != user_id:
            await query.edit_message_text(format_error("Alert not found"))
            return
        
        update_alert(db, alert_id, is_active=False)
        await query.edit_message_text("⏸️ Alert disabled")


async def handle_alert_enable(query, context, params: list) -> None:
    """Enable an alert."""
    if not params:
        await query.edit_message_text(format_error("Invalid alert ID"))
        return
    
    alert_id = params[0]
    from src.bot.database.db import get_db_context, get_alert_by_id, update_alert
    
    user_id = query.from_user.id
    with get_db_context() as db:
        alert = get_alert_by_id(db, alert_id)
        
        if not alert or alert.user_id != user_id:
            await query.edit_message_text(format_error("Alert not found"))
            return
        
        update_alert(db, alert_id, is_active=True)
        await query.edit_message_text("▶️ Alert enabled")


async def handle_confirm_reset(query, context) -> None:
    """Confirm settings reset."""
    from src.bot.handlers.settings import confirm_settings_reset
    
    # Create fake update
    from telegram import Update
    fake_update = Update(update_id=0, callback_query=query)
    await confirm_settings_reset(fake_update, context)


async def handle_cancel_reset(query, context) -> None:
    """Cancel settings reset."""
    await query.edit_message_text("❌ Settings reset cancelled")


async def handle_schedule(query, context, action: str, params: list) -> None:
    """Handle schedule-related callbacks."""
    await query.edit_message_text(
        "📅 *Scheduled Reports*\n\n"
        "Use commands:\n"
        "• `/schedule daily HH:MM`\n"
        "• `/schedule weekly DAY HH:MM`\n"
        "• `/schedule list`",
        parse_mode='Markdown'
    )
