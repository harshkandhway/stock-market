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
import json
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
        
        # Route to appropriate handler
        # Paper trading handlers (check early - they handle their own callback answers)
        paper_trading_actions = [
            "papertrade_stock", "papertrade_stock_confirm", "papertrade_stock_history",
            "papertrade_buy_signals", "papertrade_buy_signals_confirm", "papertrade_watchlist", "papertrade_watchlist_confirm",
            "papertrade_menu", "papertrade_start", "papertrade_stop", "papertrade_status",
            "papertrade_history", "papertrade_performance", "papertrade_insights",
            "papertrade_settings", "papertrade_info", "papertrade_buy_signals_info",
            "papertrade_watchlist_info", "papertrade_view_signals"
        ]
        
        if action in paper_trading_actions:
            # Paper trading handlers handle their own callback answers
            if action == "papertrade_stock":
                await handle_papertrade_stock(query, context, params)
            elif action == "papertrade_stock_confirm":
                await handle_papertrade_stock_confirm(query, context, params)
            elif action == "papertrade_stock_history":
                await handle_papertrade_stock_history(query, context, params)
            elif action == "papertrade_buy_signals":
                await handle_papertrade_buy_signals(query, context)
            elif action == "papertrade_buy_signals_confirm":
                await handle_papertrade_buy_signals_confirm(query, context)
            elif action == "papertrade_watchlist":
                await handle_papertrade_watchlist(query, context)
            elif action == "papertrade_watchlist_confirm":
                await handle_papertrade_watchlist_confirm(query, context)
            elif action == "papertrade_menu":
                await handle_papertrade_menu(query, context)
            elif action == "papertrade_start":
                await handle_papertrade_start(query, context)
            elif action == "papertrade_stop":
                await handle_papertrade_stop(query, context)
            elif action == "papertrade_status":
                await handle_papertrade_status(query, context)
            elif action == "papertrade_history":
                await handle_papertrade_history(query, context)
            elif action == "papertrade_performance":
                await handle_papertrade_performance(query, context)
            elif action == "papertrade_insights":
                await handle_papertrade_insights(query, context)
            elif action == "papertrade_settings":
                await handle_papertrade_settings(query, context)
            elif action == "papertrade_info":
                await handle_papertrade_info(query, context)
            elif action == "papertrade_buy_signals_info":
                await handle_papertrade_buy_signals_info(query, context)
            elif action == "papertrade_watchlist_info":
                await handle_papertrade_watchlist_info(query, context)
            elif action == "papertrade_view_signals":
                await handle_papertrade_view_signals(query, context)
        else:
            # Acknowledge callbacks for other handlers
            await query.answer()
            
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


# =============================================================================
# PAPER TRADING CALLBACK HANDLERS
# =============================================================================

async def handle_papertrade_stock(query, context, params: list) -> None:
    """Show paper trading options for a specific stock."""
    from ..utils.keyboards import create_paper_trade_stock_keyboard
    
    try:
        if not params:
            await query.answer("❌ No symbol provided", show_alert=True)
            return
        
        symbol = params[0]
        
        logger.info(f"Paper trade stock requested: {symbol} by user {query.from_user.id}")
        
        try:
            await query.edit_message_text(
                f"📈 *Paper Trade {symbol}*\n\n"
                f"Would you like to paper trade this stock?\n\n"
                f"⚠️ *Requirements:*\n"
                f"• Active paper trading session\n"
                f"• Available capital\n"
                f"• Position limit not exceeded\n\n"
                f"Click the button below to confirm.",
                parse_mode='Markdown',
                reply_markup=create_paper_trade_stock_keyboard(symbol)
            )
        except Exception as edit_error:
            # If edit fails (e.g., message too old), send a new message
            logger.warning(f"Could not edit message for papertrade_stock, sending new: {edit_error}")
            try:
                await query.message.reply_text(
                    f"📈 *Paper Trade {symbol}*\n\n"
                    f"Would you like to paper trade this stock?\n\n"
                    f"⚠️ *Requirements:*\n"
                    f"• Active paper trading session\n"
                    f"• Available capital\n"
                    f"• Position limit not exceeded\n\n"
                    f"Click the button below to confirm.",
                    parse_mode='Markdown',
                    reply_markup=create_paper_trade_stock_keyboard(symbol)
                )
            except Exception as reply_error:
                logger.error(f"Could not send new message either: {reply_error}")
                await query.answer("❌ Error showing paper trade options", show_alert=True)
    except Exception as e:
        logger.error(f"Error in handle_papertrade_stock: {e}", exc_info=True)
        await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)


async def handle_papertrade_stock_confirm(query, context, params: list) -> None:
    """Execute paper trade for a specific stock."""
    from ..services.paper_trading_service import get_paper_trading_service
    from ..services.analysis_service import analyze_stock
    from ..database.models import DailyBuySignal
    from datetime import datetime
    
    if not params:
        await query.answer("❌ No symbol provided", show_alert=True)
        return
    
    symbol = params[0]
    user_id = query.from_user.id
    
    logger.info(f"Paper trade confirm requested: {symbol} by user {user_id}")
    
    # Acknowledge callback immediately
    try:
        await query.answer("⏳ Processing trade...", show_alert=False)
    except Exception as answer_err:
        logger.warning(f"Could not answer callback: {answer_err}")
    
    try:
        # Update message immediately to show we're processing
        try:
            await query.edit_message_text(
                f"⏳ *Processing Paper Trade*\n\n"
                f"Symbol: *{symbol}*\n"
                f"Status: Analyzing stock...",
                parse_mode='Markdown'
            )
        except Exception as edit_err:
            logger.warning(f"Could not edit message initially: {edit_err}")
            # Try to send a new message instead
            try:
                await query.message.reply_text(
                    f"⏳ Processing paper trade for {symbol}...",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        with get_db_context() as db:
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)
            
            if not active_session:
                await query.answer(
                    "❌ No active session. Use /papertrade start first!",
                    show_alert=True
                )
                return
            
            # Check if stock is already in positions
            from ..database.models import PaperPosition
            existing = db.query(PaperPosition).filter(
                PaperPosition.session_id == active_session.id,
                PaperPosition.symbol == symbol,
                PaperPosition.is_open == True
            ).first()
            
            if existing:
                await query.answer(
                    f"⚠️ Already have open position in {symbol}",
                    show_alert=True
                )
                return
            
            # Analyze the stock to get current signal
            try:
                await query.edit_message_text(
                    f"⏳ *Analyzing Stock*\n\n"
                    f"Symbol: *{symbol}*\n"
                    f"Status: Fetching data and analyzing...\n\n"
                    f"This may take 10-30 seconds.",
                    parse_mode='Markdown'
                )
            except Exception as edit_err:
                logger.warning(f"Could not edit message: {edit_err}")
            
            try:
                logger.info(f"Analyzing {symbol} for paper trade...")
                
                # Check market hours - queue if closed
                from ..services.market_hours_service import get_market_hours_service
                market_hours = get_market_hours_service()
                is_market_open = market_hours.is_market_open()
                
                if not is_market_open:
                    logger.info(f"Market is closed - queueing trade for {symbol} to execute when market opens")
                    # Queue the trade instead of executing immediately
                    await _queue_paper_trade_for_market_open(query, context, symbol, active_session, user_id, db)
                    return
                
                # Market is open - proceed with normal execution
                
                try:
                    # Add timeout for analysis (30 seconds)
                    import asyncio
                    from functools import partial
                    logger.info(f"Starting analysis for {symbol} (timeout: 30s)...")
                    
                    # Create partial function for executor
                    analyze_func = partial(
                        analyze_stock,
                        symbol=symbol,
                        mode='balanced',
                        timeframe='medium',
                        use_cache=False
                    )
                    
                    loop = asyncio.get_event_loop()
                    analysis = await asyncio.wait_for(
                        loop.run_in_executor(None, analyze_func),
                        timeout=30.0
                    )
                    logger.info(f"Analysis complete for {symbol}: {analysis.get('recommendation_type', 'UNKNOWN')}")
                except asyncio.TimeoutError:
                    logger.error(f"Analysis timeout for {symbol} after 30 seconds")
                    await query.edit_message_text(
                        f"❌ *Analysis Timeout*\n\n"
                        f"Could not analyze {symbol} within 30 seconds.\n\n"
                        f"Please try again later.",
                        parse_mode='Markdown'
                    )
                    return
                except Exception as analysis_error:
                    logger.error(f"Analysis failed for {symbol}: {analysis_error}", exc_info=True)
                    await query.edit_message_text(
                        f"❌ *Analysis Failed*\n\n"
                        f"Could not analyze {symbol}.\n\n"
                        f"Error: {str(analysis_error)[:150]}\n\n"
                        f"Please try again later.",
                        parse_mode='Markdown'
                    )
                    return
                
                # Check if it's a BUY signal
                rec_type = analysis.get('recommendation_type', '')
                logger.info(f"Recommendation type for {symbol}: {rec_type}")
                
                if rec_type not in ['STRONG BUY', 'BUY', 'WEAK BUY']:
                    logger.warning(f"Cannot paper trade {symbol}: recommendation is {rec_type}")
                    try:
                        await query.edit_message_text(
                            f"❌ *Cannot Paper Trade {symbol}*\n\n"
                            f"Current recommendation: *{rec_type}*\n\n"
                            f"Only BUY signals can be paper traded.\n"
                            f"Use `/analyze {symbol}` to see full analysis.",
                            parse_mode='Markdown'
                        )
                    except Exception as edit_err:
                        logger.error(f"Could not edit message: {edit_err}")
                        await query.answer(
                            f"❌ Cannot trade {symbol}: {rec_type}",
                            show_alert=True
                        )
                    return
                
                # Create a temporary DailyBuySignal for execution
                from ..database.models import DailyBuySignal
                signal = DailyBuySignal(
                    symbol=symbol,
                    analysis_date=datetime.utcnow(),
                    recommendation=analysis.get('recommendation', ''),
                    recommendation_type=rec_type,
                    current_price=analysis.get('current_price', 0.0),
                    target=analysis.get('target_data', {}).get('recommended_target'),
                    stop_loss=analysis.get('stop_data', {}).get('recommended_stop'),
                    risk_reward=analysis.get('risk_reward', 0.0),
                    confidence=analysis.get('confidence', 0.0),
                    overall_score_pct=analysis.get('overall_score_pct', 50.0),
                    analysis_data=str(analysis)
                )
                db.add(signal)
                db.flush()
                
                # Execute the trade (use the execution service directly)
                from ..services.paper_trade_execution_service import get_paper_trade_execution_service
                execution_service = get_paper_trade_execution_service(db)
                
                # Get current price (with timeout)
                import asyncio
                logger.info(f"Fetching current price for {symbol}...")
                try:
                    await query.edit_message_text(
                        f"⏳ *Preparing Trade*\n\n"
                        f"Symbol: *{symbol}*\n"
                        f"Status: Fetching current price...",
                        parse_mode='Markdown'
                    )
                except:
                    pass
                
                try:
                    loop = asyncio.get_event_loop()
                    # Add timeout for price fetch (10 seconds)
                    current_price = await asyncio.wait_for(
                        loop.run_in_executor(None, get_current_price, symbol),
                        timeout=10.0
                    )
                    logger.info(f"Current price for {symbol}: {current_price}")
                    
                    if current_price is None:
                        logger.warning(f"Could not get current price for {symbol}, using signal price")
                        current_price = signal.current_price
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout fetching price for {symbol}, using signal price")
                    current_price = signal.current_price
                except Exception as price_error:
                    logger.error(f"Error fetching price for {symbol}: {price_error}", exc_info=True)
                    current_price = signal.current_price
                    logger.info(f"Using signal price as fallback: {current_price}")
                
                # Validate entry
                logger.info(f"Validating entry for {symbol}...")
                try:
                    await query.edit_message_text(
                        f"⏳ *Validating Trade*\n\n"
                        f"Symbol: *{symbol}*\n"
                        f"Status: Checking capital and position limits...",
                        parse_mode='Markdown'
                    )
                except:
                    pass
                
                is_valid, error_msg = execution_service.validate_entry(active_session, signal, current_price)
                
                if not is_valid:
                    logger.warning(f"Entry validation failed for {symbol}: {error_msg}")
                    try:
                        await query.edit_message_text(
                            f"❌ *Cannot Trade {symbol}*\n\n"
                            f"Reason: *{error_msg}*\n\n"
                            f"Check:\n"
                            f"• Position limits\n"
                            f"• Capital availability\n"
                            f"• Market hours",
                            parse_mode='Markdown'
                        )
                    except Exception as edit_err:
                        logger.error(f"Could not edit message: {edit_err}")
                        await query.answer(
                            f"❌ Cannot trade: {error_msg[:50]}",
                            show_alert=True
                        )
                    return
                
                # Enter position
                logger.info(f"Entering position for {symbol}...")
                try:
                    await query.edit_message_text(
                        f"⏳ *Executing Trade*\n\n"
                        f"Symbol: *{symbol}*\n"
                        f"Status: Opening position...",
                        parse_mode='Markdown'
                    )
                except:
                    pass
                
                position = await execution_service.enter_position(
                    active_session,
                    signal,
                    current_price
                )
                
                if position:
                    logger.info(f"Position opened successfully for {symbol}: {position.id}")
                    try:
                        await query.edit_message_text(
                            f"✅ *Paper Trade Executed!*\n\n"
                            f"*{symbol}*\n"
                            f"Entry: ₹{position.entry_price:.2f}\n"
                            f"Shares: {position.shares:.2f}\n"
                            f"Value: ₹{position.position_value:,.2f}\n\n"
                            f"Target: ₹{position.target_price:.2f}\n"
                            f"Stop Loss: ₹{position.stop_loss_price:.2f}\n\n"
                            f"Use `/papertrade status` to monitor.",
                            parse_mode='Markdown'
                        )
                    except Exception as edit_err:
                        await query.message.reply_text(
                            f"✅ *Paper Trade Executed!*\n\n"
                            f"*{symbol}*\n"
                            f"Entry: ₹{position.entry_price:.2f}\n"
                            f"Shares: {position.shares:.2f}\n"
                            f"Value: ₹{position.position_value:,.2f}\n\n"
                            f"Target: ₹{position.target_price:.2f}\n"
                            f"Stop Loss: ₹{position.stop_loss_price:.2f}",
                            parse_mode='Markdown'
                        )
                else:
                    logger.warning(f"Position entry returned None for {symbol}")
                    try:
                        await query.edit_message_text(
                            f"❌ *Trade Failed*\n\n"
                            f"*{symbol}*\n\n"
                            f"Could not open position.\n\n"
                            f"Check:\n"
                            f"• Available capital\n"
                            f"• Position limits\n"
                            f"• Market hours",
                            parse_mode='Markdown'
                        )
                    except Exception as edit_err:
                        await query.message.reply_text(
                            f"❌ *Trade Failed*\n\n"
                            f"Could not open position for {symbol}",
                            parse_mode='Markdown'
                        )
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol} for paper trade: {e}", exc_info=True)
                error_msg = str(e)
                logger.error(f"Full error details: {error_msg}", exc_info=True)
                
                try:
                    await query.edit_message_text(
                        f"❌ *Analysis Failed*\n\n"
                        f"Could not analyze {symbol}.\n\n"
                        f"Error: {error_msg[:150]}\n\n"
                        f"Please try again later.\n\n"
                        f"💡 Tip: Market may be closed or data unavailable.",
                        parse_mode='Markdown'
                    )
                except Exception as edit_err:
                    logger.error(f"Could not edit message: {edit_err}")
                    try:
                        await query.message.reply_text(
                            f"❌ Analysis failed for {symbol}\n\n"
                            f"Error: {error_msg[:150]}\n\n"
                            f"Market may be closed or data unavailable.",
                            parse_mode='Markdown'
                        )
                    except Exception as reply_err:
                        logger.error(f"Could not send reply either: {reply_err}")
                        await query.answer(f"❌ Error: {error_msg[:50]}", show_alert=True)
                
    except Exception as e:
        logger.error(f"Error in paper trade stock confirm: {e}", exc_info=True)
        try:
            await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)
        except:
            pass
        try:
            await query.message.reply_text(
                f"❌ *Error Executing Trade*\n\n"
                f"An error occurred: {str(e)[:200]}\n\n"
                f"Check logs for details.",
                parse_mode='Markdown'
            )
        except:
            pass


async def _queue_paper_trade_for_market_open(
    query,
    context,
    symbol: str,
    session,
    user_id: int,
    db
) -> None:
    """Queue a paper trade to execute when market opens"""
    from ..database.models import PendingPaperTrade
    from ..services.market_hours_service import get_market_hours_service
    from datetime import datetime
    import asyncio
    from functools import partial
    
    try:
        # Show immediate feedback
        try:
            await query.edit_message_text(
                f"⏳ *Queueing Trade*\n\n"
                f"Symbol: *{symbol}*\n"
                f"Status: Preparing...",
                parse_mode='Markdown'
            )
        except Exception as edit_err:
            logger.warning(f"Could not edit message: {edit_err}")
            # Try reply as fallback
            try:
                await query.message.reply_text(
                    f"⏳ Queueing trade for {symbol}...",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        # Check if already queued FIRST (fast check, no analysis needed)
        existing = db.query(PendingPaperTrade).filter(
            PendingPaperTrade.session_id == session.id,
            PendingPaperTrade.symbol == symbol,
            PendingPaperTrade.status == 'PENDING'
        ).first()
        
        if existing:
            market_hours = get_market_hours_service()
            next_open = market_hours.get_next_market_open()
            try:
                await query.edit_message_text(
                    f"⚠️ *Already Queued*\n\n"
                    f"Trade for *{symbol}* is already queued.\n\n"
                    f"📅 *Scheduled for:*\n"
                    f"{next_open.strftime('%Y-%m-%d %H:%M IST')}\n\n"
                    f"Will execute when market opens.",
                    parse_mode='Markdown'
                )
            except Exception as edit_err:
                await query.message.reply_text(
                    f"⚠️ Trade for {symbol} is already queued.\n"
                    f"Scheduled: {next_open.strftime('%Y-%m-%d %H:%M IST')}",
                    parse_mode='Markdown'
                )
            return
        
        # Prepare signal data (will be updated with analysis if available)
        signal_data = {
            'symbol': symbol,
            'recommendation_type': 'BUY',  # Default - will be validated when market opens
            'queued_at': datetime.utcnow().isoformat(),
            'analysis_pending': True  # Flag to indicate analysis needed at market open
        }
        
        # Try quick analysis (optional - won't block if it fails)
        # Use shorter timeout and cache for faster response
        try:
            try:
                await query.edit_message_text(
                    f"⏳ *Queueing Trade*\n\n"
                    f"Symbol: *{symbol}*\n"
                    f"Status: Quick analysis (optional)...",
                    parse_mode='Markdown'
                )
            except:
                pass
            
            from ..services.analysis_service import analyze_stock
            
            analyze_func = partial(
                analyze_stock,
                symbol=symbol,
                mode='balanced',
                timeframe='medium',
                use_cache=True  # Use cache for faster response
            )
            
            loop = asyncio.get_event_loop()
            # Shorter timeout for queuing (15 seconds max)
            analysis = await asyncio.wait_for(
                loop.run_in_executor(None, analyze_func),
                timeout=15.0
            )
            
            rec_type = analysis.get('recommendation_type', '')
            
            # Only queue if it's a BUY signal
            if rec_type not in ['STRONG BUY', 'BUY', 'WEAK BUY']:
                try:
                    await query.edit_message_text(
                        f"❌ *Cannot Queue Trade*\n\n"
                        f"Current recommendation: *{rec_type}*\n\n"
                        f"Only BUY signals can be paper traded.\n\n"
                        f"Use `/analyze {symbol}` to see full analysis.",
                        parse_mode='Markdown'
                    )
                except Exception as edit_err:
                    await query.message.reply_text(
                        f"❌ Cannot queue {symbol}: {rec_type}\n"
                        f"Only BUY signals can be paper traded.",
                        parse_mode='Markdown'
                    )
                return
            
            # Update signal data with analysis
            signal_data.update({
                'recommendation_type': rec_type,
                'recommendation': analysis.get('recommendation', ''),
                'current_price': analysis.get('current_price', 0.0),
                'target': analysis.get('target_data', {}).get('recommended_target'),
                'stop_loss': analysis.get('stop_data', {}).get('recommended_stop'),
                'risk_reward': analysis.get('risk_reward', 0.0),
                'confidence': analysis.get('confidence', 0.0),
                'overall_score_pct': analysis.get('overall_score_pct', 50.0),
                'analysis': analysis,
                'analysis_pending': False
            })
            
        except asyncio.TimeoutError:
            logger.warning(f"Analysis timeout for {symbol} during queuing - will analyze when market opens")
            # Continue without analysis - we'll analyze when market opens
        except Exception as analysis_error:
            logger.warning(f"Analysis failed for {symbol} during queuing: {analysis_error} - will analyze when market opens")
            # Continue without analysis - we'll analyze when market opens
        
        # Create pending trade (with or without analysis)
        try:
            pending_trade = PendingPaperTrade(
                session_id=session.id,
                symbol=symbol,
                requested_by_user_id=user_id,
                signal_data=json.dumps(signal_data, default=str),
                status='PENDING'
            )
            db.add(pending_trade)
            db.commit()
            
            # Get next market open time
            market_hours = get_market_hours_service()
            next_open = market_hours.get_next_market_open()
            
            # Show success message
            rec_display = signal_data.get('recommendation_type', 'BUY')
            try:
                await query.edit_message_text(
                    f"✅ *Trade Queued!*\n\n"
                    f"*{symbol}* - {rec_display}\n\n"
                    f"📅 *Scheduled for:*\n"
                    f"{next_open.strftime('%Y-%m-%d %H:%M IST')}\n\n"
                    f"Trade will execute automatically when market opens.\n\n"
                    f"Use `/papertrade status` to check pending trades.",
                    parse_mode='Markdown'
                )
            except Exception as edit_err:
                await query.message.reply_text(
                    f"✅ *Trade Queued!*\n\n"
                    f"*{symbol}* - {rec_display}\n\n"
                    f"📅 Scheduled: {next_open.strftime('%Y-%m-%d %H:%M IST')}\n\n"
                    f"Will execute when market opens.",
                    parse_mode='Markdown'
                )
            
            logger.info(f"Queued paper trade for {symbol} - will execute at {next_open}")
            
        except Exception as db_error:
            logger.error(f"Error creating pending trade for {symbol}: {db_error}", exc_info=True)
            try:
                await query.edit_message_text(
                    f"❌ *Failed to Queue Trade*\n\n"
                    f"Database error occurred.\n\n"
                    f"Please try again later.",
                    parse_mode='Markdown'
                )
            except Exception as edit_err:
                await query.message.reply_text(
                    f"❌ Failed to queue trade for {symbol}.\n"
                    f"Please try again later.",
                    parse_mode='Markdown'
                )
            
    except Exception as e:
        logger.error(f"Error queuing paper trade for {symbol}: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                f"❌ *Failed to Queue Trade*\n\n"
                f"An error occurred: {str(e)[:150]}\n\n"
                f"Please try again later.",
                parse_mode='Markdown'
            )
        except Exception as edit_err:
            try:
                await query.message.reply_text(
                    f"❌ Failed to queue trade for {symbol}.\n"
                    f"Error: {str(e)[:100]}\n\n"
                    f"Please try again later.",
                    parse_mode='Markdown'
                )
            except:
                # Last resort - answer callback
                try:
                    await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)
                except:
                    pass
async def handle_papertrade_stock_history(query, context, params: list) -> None:
    """Show trade history for a specific stock."""
    from ..database.models import PaperPosition, PaperTrade, PendingPaperTrade, PaperTradingSession
    from ..services.paper_trading_service import get_paper_trading_service
    from ..services.market_hours_service import get_market_hours_service
    from datetime import datetime
    import json
    
    symbol = None
    try:
        logger.info(f"handle_papertrade_stock_history called with params: {params}")
        
        if not params:
            logger.warning("handle_papertrade_stock_history: No params provided")
            await query.answer("❌ No symbol provided", show_alert=True)
            return
        
        symbol = params[0]
        user_id = query.from_user.id
        
        logger.info(f"Paper trade history requested for {symbol} by user {user_id}")
        
        # Acknowledge callback
        try:
            await query.answer("⏳ Loading trade history...", show_alert=False)
        except:
            pass
        
        with get_db_context() as db:
            # Get active session
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)
            
            if not active_session:
                # Create keyboard with back button and start session button
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("▶️ Start Paper Trading Session", callback_data="papertrade_start"),
                    ],
                    [
                        InlineKeyboardButton("◀️ Back to Paper Trade Menu", callback_data=f"papertrade_stock:{symbol}"),
                    ],
                    [
                        InlineKeyboardButton("📊 View Analysis", callback_data=f"analyze:{symbol}"),
                    ],
                ])
                
                await query.edit_message_text(
                    f"📜 *Trade History for {symbol}*\n\n"
                    f"❌ No active paper trading session found.\n\n"
                    f"Use `/papertrade start` to begin paper trading.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                return
            
            # Query open positions
            open_positions = db.query(PaperPosition).filter(
                PaperPosition.session_id == active_session.id,
                PaperPosition.symbol == symbol,
                PaperPosition.is_open == True
            ).order_by(PaperPosition.entry_date.desc()).all()
            
            # Query pending trades
            pending_trades = db.query(PendingPaperTrade).filter(
                PendingPaperTrade.session_id == active_session.id,
                PendingPaperTrade.symbol == symbol,
                PendingPaperTrade.status == 'PENDING'
            ).order_by(PendingPaperTrade.requested_at.desc()).all()
            
            # Query closed trades (history)
            closed_trades = db.query(PaperTrade).filter(
                PaperTrade.session_id == active_session.id,
                PaperTrade.symbol == symbol
            ).order_by(PaperTrade.exit_date.desc()).limit(20).all()
            
            # Build message
            message = f"📜 *Trade History for {symbol}*\n\n"
            
            has_any_data = False
            
            # Open Positions
            if open_positions:
                has_any_data = True
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                message += f"*OPEN POSITIONS ({len(open_positions)})*\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                
                for pos in open_positions:
                    # Calculate current P&L (unrealized) - use stored unrealized_pnl if available
                    try:
                        # Try to use stored unrealized_pnl first (updated by scheduler)
                        if hasattr(pos, 'unrealized_pnl') and pos.unrealized_pnl is not None:
                            unrealized_pnl = pos.unrealized_pnl
                            unrealized_pnl_pct = pos.unrealized_pnl_pct if hasattr(pos, 'unrealized_pnl_pct') else 0.0
                            pnl_sign = "📈" if unrealized_pnl >= 0 else "📉"
                            message += (
                                f"{pnl_sign} *Entry:* ₹{pos.entry_price:.2f}\n"
                                f"   *P&L:* ₹{unrealized_pnl:,.2f} ({unrealized_pnl_pct:+.2f}%)\n"
                                f"   *Shares:* {pos.shares:.2f}\n"
                                f"   *Target:* ₹{pos.target_price:.2f}\n"
                                f"   *Stop Loss:* ₹{pos.stop_loss_price:.2f}\n"
                                f"   *Entry Date:* {pos.entry_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                            )
                        else:
                            # Fallback: show without current price (scheduler will update it)
                            message += (
                                f"📊 *Entry:* ₹{pos.entry_price:.2f}\n"
                                f"   *Shares:* {pos.shares:.2f}\n"
                                f"   *Target:* ₹{pos.target_price:.2f}\n"
                                f"   *Stop Loss:* ₹{pos.stop_loss_price:.2f}\n"
                                f"   *Entry Date:* {pos.entry_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                            )
                    except Exception as e:
                        logger.warning(f"Error formatting position for {symbol}: {e}")
                        message += (
                            f"📊 *Entry:* ₹{pos.entry_price:.2f}\n"
                            f"   *Shares:* {pos.shares:.2f}\n"
                            f"   *Target:* ₹{pos.target_price:.2f}\n"
                            f"   *Stop Loss:* ₹{pos.stop_loss_price:.2f}\n"
                            f"   *Entry Date:* {pos.entry_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                        )
            
            # Pending Trades
            if pending_trades:
                has_any_data = True
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                message += f"*PENDING TRADES ({len(pending_trades)})*\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                
                market_hours = get_market_hours_service()
                next_open = market_hours.get_next_market_open()
                
                for pending in pending_trades:
                    try:
                        signal_data = json.loads(pending.signal_data) if pending.signal_data else {}
                        rec_type = signal_data.get('recommendation_type', 'BUY')
                        message += (
                            f"⏳ *{rec_type}*\n"
                            f"   *Requested:* {pending.requested_at.strftime('%Y-%m-%d %H:%M')}\n"
                            f"   *Will Execute:* {next_open.strftime('%Y-%m-%d %H:%M IST')}\n\n"
                        )
                    except:
                        message += (
                            f"⏳ *Pending*\n"
                            f"   *Requested:* {pending.requested_at.strftime('%Y-%m-%d %H:%M')}\n"
                            f"   *Will Execute:* {next_open.strftime('%Y-%m-%d %H:%M IST')}\n\n"
                        )
            
            # Closed Trades (History)
            if closed_trades:
                has_any_data = True
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                message += f"*CLOSED TRADES ({len(closed_trades)})*\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                
                for trade in closed_trades[:10]:  # Show last 10
                    pnl = trade.realized_pnl
                    pnl_sign = "✅" if pnl >= 0 else "❌"
                    pnl_pct = trade.r_multiple * 100 if trade.r_multiple else 0
                    
                    message += (
                        f"{pnl_sign} *{trade.exit_reason.replace('_', ' ').title()}*\n"
                        f"   *Entry:* ₹{trade.entry_price:.2f} ({trade.entry_date.strftime('%Y-%m-%d')})\n"
                        f"   *Exit:* ₹{trade.exit_price:.2f} ({trade.exit_date.strftime('%Y-%m-%d')})\n"
                        f"   *Shares:* {trade.shares:.2f}\n"
                        f"   *P&L:* ₹{pnl:,.2f} ({pnl_pct:+.1f}%)\n"
                        f"   *R-Multiple:* {trade.r_multiple:.2f}x\n\n"
                    )
                
                if len(closed_trades) > 10:
                    message += f"... and {len(closed_trades) - 10} more closed trades\n\n"
            
            # No data message
            if not has_any_data:
                message += (
                    f"📭 *No Trade History*\n\n"
                    f"No paper trades found for *{symbol}*.\n\n"
                    f"• No open positions\n"
                    f"• No pending trades\n"
                    f"• No closed trades\n\n"
                    f"Click *✅ Paper Trade This Stock* to start trading this stock."
                )
            
            # Create keyboard with back button
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("◀️ Back to Paper Trade Menu", callback_data=f"papertrade_stock:{symbol}"),
                ],
                [
                    InlineKeyboardButton("📊 View Analysis", callback_data=f"analyze:{symbol}"),
                    InlineKeyboardButton("✅ Paper Trade This Stock", callback_data=f"papertrade_stock_confirm:{symbol}"),
                ],
            ])
            
            try:
                await query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except Exception as edit_err:
                # If message is too long, chunk it
                from src.core.formatters import chunk_message
                chunks = chunk_message(message, max_length=4000)
                for i, chunk in enumerate(chunks):
                    # Show keyboard on the last chunk
                    show_keyboard = keyboard if i == len(chunks) - 1 else None
                    if i == 0:
                        try:
                            await query.edit_message_text(
                                chunk,
                                parse_mode='Markdown',
                                reply_markup=show_keyboard
                            )
                        except:
                            await query.message.reply_text(
                                chunk,
                                parse_mode='Markdown',
                                reply_markup=show_keyboard
                            )
                    else:
                        await query.message.reply_text(
                            chunk,
                            parse_mode='Markdown',
                            reply_markup=show_keyboard
                        )
    
    except Exception as e:
        symbol_str = symbol if symbol else "unknown"
        logger.error(f"Error showing trade history for {symbol_str}: {e}", exc_info=True)
        logger.error(f"Full traceback for trade history error:", exc_info=True)
        try:
            await query.edit_message_text(
                f"❌ *Error Loading History*\n\n"
                f"Could not load trade history for {symbol_str}.\n\n"
                f"Error: {str(e)[:150]}",
                parse_mode='Markdown'
            )
        except Exception as edit_err:
            logger.error(f"Could not edit message in error handler: {edit_err}")
            try:
                await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)
            except Exception as answer_err:
                logger.error(f"Could not answer callback in error handler: {answer_err}")


async def handle_papertrade_buy_signals(query, context) -> None:
    """Show menu for trading all BUY signals."""
    from ..utils.keyboards import create_paper_trade_buy_signals_keyboard
    
    await query.edit_message_text(
        "📈 *Trade All BUY Signals*\n\n"
        "This will execute paper trades for all stocks with BUY signals from today's analysis.\n\n"
        "⚠️ *Note:*\n"
        "• Only executes during market hours\n"
        "• Respects position limits\n"
        "• Uses available capital\n\n"
        "Click below to confirm or view signals first.",
        parse_mode='Markdown',
        reply_markup=create_paper_trade_buy_signals_keyboard()
    )


async def handle_papertrade_buy_signals_confirm(query, context) -> None:
    """Execute trades for all BUY signals."""
    from ..services.paper_trading_service import get_paper_trading_service
    from ..database.models import DailyBuySignal
    from datetime import datetime
    
    user_id = query.from_user.id
    
    try:
        with get_db_context() as db:
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)
            
            if not active_session:
                await query.answer(
                    "❌ No active session. Use /papertrade start first!",
                    show_alert=True
                )
                return
            
            await query.edit_message_text("⏳ Executing trades for all BUY signals...")
            
            # Get today's BUY signals
            today = datetime.utcnow().replace(hour=0, minute=0, second=0)
            signals = db.query(DailyBuySignal).filter(
                DailyBuySignal.analysis_date >= today,
                DailyBuySignal.recommendation_type.in_(['STRONG BUY', 'BUY', 'WEAK BUY'])
            ).all()
            
            if not signals:
                await query.edit_message_text(
                    "❌ *No BUY Signals Found*\n\n"
                    "No BUY signals available for today.\n\n"
                    "Run daily analysis first or wait for scheduled analysis.",
                    parse_mode='Markdown'
                )
                return
            
            # Execute trades
            result = await trading_service.execute_buy_signals(active_session.id)
            
            await query.edit_message_text(
                f"✅ *BUY Signals Execution Complete*\n\n"
                f"Sessions processed: {result['sessions_processed']}\n"
                f"Signals found: {result['signals_found']}\n"
                f"Positions opened: {result['positions_opened']}\n"
                f"Skipped: {result['skipped']}\n\n"
                f"Use `/papertrade status` to view positions.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error executing BUY signals: {e}", exc_info=True)
        await query.answer("❌ Error executing trades", show_alert=True)


async def handle_papertrade_watchlist(query, context) -> None:
    """Show menu for trading all watchlist stocks."""
    from ..utils.keyboards import create_paper_trade_watchlist_keyboard
    
    await query.edit_message_text(
        "⭐ *Trade All Watchlist Stocks*\n\n"
        "This will analyze and paper trade all stocks in your watchlist.\n\n"
        "⚠️ *Note:*\n"
        "• Only stocks with BUY signals will be traded\n"
        "• Respects position limits\n"
        "• Uses available capital\n\n"
        "Click below to confirm or view watchlist first.",
        parse_mode='Markdown',
        reply_markup=create_paper_trade_watchlist_keyboard()
    )


async def handle_papertrade_watchlist_confirm(query, context) -> None:
    """Execute trades for all watchlist stocks."""
    from ..services.paper_trading_service import get_paper_trading_service
    from ..services.analysis_service import analyze_stock
    from ..database.models import DailyBuySignal
    from datetime import datetime
    
    user_id = query.from_user.id
    
    try:
        with get_db_context() as db:
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)
            
            if not active_session:
                await query.answer(
                    "❌ No active session. Use /papertrade start first!",
                    show_alert=True
                )
                return
            
            # Get watchlist
            watchlist = get_user_watchlist(db, user_id)
            
            if not watchlist:
                await query.edit_message_text(
                    "❌ *Watchlist is Empty*\n\n"
                    "Add stocks to your watchlist first using `/watchlist add SYMBOL`",
                    parse_mode='Markdown'
                )
                return
            
            await query.edit_message_text(f"⏳ Analyzing {len(watchlist)} watchlist stocks...")
            
            traded = 0
            skipped = 0
            errors = []
            
            for symbol in watchlist:
                try:
                    # Check if already in positions
                    from ..database.models import PaperPosition
                    existing = db.query(PaperPosition).filter(
                        PaperPosition.session_id == active_session.id,
                        PaperPosition.symbol == symbol,
                        PaperPosition.is_open == True
                    ).first()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    # Analyze stock
                    analysis = analyze_stock(symbol, mode='balanced', timeframe='medium', use_cache=False)
                    rec_type = analysis.get('recommendation_type', '')
                    
                    if rec_type not in ['STRONG BUY', 'BUY', 'WEAK BUY']:
                        skipped += 1
                        continue
                    
                    # Create signal and execute
                    signal = DailyBuySignal(
                        symbol=symbol,
                        analysis_date=datetime.utcnow(),
                        recommendation=analysis.get('recommendation', ''),
                        recommendation_type=rec_type,
                        current_price=analysis.get('current_price', 0.0),
                        target=analysis.get('target_data', {}).get('recommended_target'),
                        stop_loss=analysis.get('stop_data', {}).get('recommended_stop'),
                        risk_reward=analysis.get('risk_reward', 0.0),
                        confidence=analysis.get('confidence', 0.0),
                        overall_score_pct=analysis.get('overall_score_pct', 50.0),
                        analysis_data=str(analysis)
                    )
                    db.add(signal)
                    db.flush()
                    
                    # Execute trade using execution service
                    from ..services.paper_trade_execution_service import get_paper_trade_execution_service
                    execution_service = get_paper_trade_execution_service(db)
                    
                    # Get current price
                    import asyncio
                    loop = asyncio.get_event_loop()
                    current_price = await loop.run_in_executor(None, get_current_price, symbol)
                    
                    if current_price is None:
                        current_price = signal.current_price
                    
                    # Validate and execute
                    is_valid, error_msg = execution_service.validate_entry(active_session, signal, current_price)
                    
                    if is_valid:
                        position = await execution_service.enter_position(active_session, signal, current_price)
                        if position:
                            traded += 1
                        else:
                            skipped += 1
                    else:
                        skipped += 1
                        
                except Exception as e:
                    errors.append(symbol)
                    logger.error(f"Error trading {symbol} from watchlist: {e}")
            
            db.commit()
            
            message = (
                f"✅ *Watchlist Trading Complete*\n\n"
                f"Traded: {traded}\n"
                f"Skipped: {skipped}\n"
            )
            
            if errors:
                message += f"\nErrors: {len(errors)}\n"
            
            message += "\nUse `/papertrade status` to view positions."
            
            await query.edit_message_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error trading watchlist: {e}", exc_info=True)
        await query.answer("❌ Error executing trades", show_alert=True)


async def handle_papertrade_menu(query, context) -> None:
    """Show paper trading main menu."""
    from ..utils.keyboards import create_paper_trading_main_keyboard
    
    await query.edit_message_text(
        "📈 *Paper Trading Menu*\n\n"
        "Manage your paper trading session:\n\n"
        "• Start/Stop session\n"
        "• View status and history\n"
        "• Trade BUY signals or watchlist\n"
        "• View performance and insights",
        parse_mode='Markdown',
        reply_markup=create_paper_trading_main_keyboard()
    )


async def handle_papertrade_start(query, context) -> None:
    """Start paper trading session via callback."""
    from ..services.paper_trading_service import get_paper_trading_service
    from ..database.models import UserSettings
    from ..database.db import get_db_context, get_or_create_user
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    user_id = query.from_user.id
    
    try:
        # Acknowledge callback
        await query.answer("⏳ Starting session...", show_alert=False)
        
        with get_db_context() as db:
            user = get_or_create_user(db, user_id)
            settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
            
            # Check if already active
            trading_service = get_paper_trading_service(db)
            active_session = await trading_service.get_active_session(user_id)
            
            if active_session:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Status", callback_data="papertrade_status")],
                    [InlineKeyboardButton("⏹️ Stop Session", callback_data="papertrade_stop")],
                    [InlineKeyboardButton("◀️ Back to Menu", callback_data="papertrade_menu")],
                ])
                await query.edit_message_text(
                    f"⚠️ *Paper Trading Session Already Active!*\n\n"
                    f"Started: {active_session.session_start.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Current Capital: ₹{active_session.current_capital:,.2f}\n"
                    f"P&L: ₹{active_session.current_capital - active_session.initial_capital:+,.2f}\n\n"
                    f"Use `/papertrade stop` to end current session.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                return
            
            # Get settings
            initial_capital = settings.paper_trading_capital if settings else 500000.0
            max_positions = settings.paper_trading_max_positions if settings else 15
            risk_per_trade = settings.paper_trading_risk_per_trade_pct if settings else 1.0
            
            # Start session
            session = await trading_service.start_session(user_id, initial_capital, max_positions)
            
            # Create keyboard with back button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Status", callback_data="papertrade_status")],
                [InlineKeyboardButton("📜 History", callback_data="papertrade_history")],
                [InlineKeyboardButton("📈 Performance", callback_data="papertrade_performance")],
                [InlineKeyboardButton("◀️ Back to Menu", callback_data="papertrade_menu")],
            ])
            
            await query.edit_message_text(
                f"🟢 *Paper Trading Session Started!*\n\n"
                f"Initial Capital: ₹{session.initial_capital:,.2f}\n"
                f"Max Positions: {session.max_positions}\n"
                f"Risk Per Trade: {risk_per_trade}%\n\n"
                f"System will automatically:\n"
                f"• Execute BUY signals at 9:20 AM IST\n"
                f"• Monitor positions every 5 minutes during market hours\n"
                f"• Send daily summary at 4:00 PM IST\n"
                f"• Send weekly summary on Sundays\n\n"
                f"Use `/papertrade status` to check positions anytime.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    
    except Exception as e:
        logger.error(f"Error starting paper trading session via callback: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                f"❌ *Failed to Start Session*\n\n"
                f"Error: {str(e)[:200]}\n\n"
                f"Please try again or use `/papertrade start`",
                parse_mode='Markdown'
            )
        except:
            await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)


async def handle_papertrade_stop(query, context) -> None:
    """Stop paper trading session via callback."""
    from telegram import Update
    from ..handlers.paper_trading import paper_trade_stop_command
    
    fake_update = Update(update_id=0, message=query.message)
    await paper_trade_stop_command(fake_update, context)


async def handle_papertrade_status(query, context) -> None:
    """Show paper trading status via callback."""
    from telegram import Update
    from ..handlers.paper_trading import paper_trade_status_command
    
    fake_update = Update(update_id=0, message=query.message)
    await paper_trade_status_command(fake_update, context)


async def handle_papertrade_history(query, context) -> None:
    """Show paper trading history via callback."""
    from telegram import Update
    from ..handlers.paper_trading import paper_trade_history_command
    
    fake_update = Update(update_id=0, message=query.message)
    await paper_trade_history_command(fake_update, context, [])


async def handle_papertrade_performance(query, context) -> None:
    """Show paper trading performance via callback."""
    from telegram import Update
    from ..handlers.paper_trading import paper_trade_performance_command
    
    fake_update = Update(update_id=0, message=query.message)
    await paper_trade_performance_command(fake_update, context)


async def handle_papertrade_insights(query, context) -> None:
    """Show paper trading insights via callback."""
    from telegram import Update
    from ..handlers.paper_trading import paper_trade_insights_command
    
    fake_update = Update(update_id=0, message=query.message)
    await paper_trade_insights_command(fake_update, context)


async def handle_papertrade_settings(query, context) -> None:
    """Show paper trading settings via callback."""
    from telegram import Update
    from ..handlers.paper_trading import paper_trade_settings_command
    
    fake_update = Update(update_id=0, message=query.message)
    await paper_trade_settings_command(fake_update, context)


async def handle_papertrade_info(query, context) -> None:
    """Show paper trading information."""
    await query.edit_message_text(
        "ℹ️ *About Paper Trading*\n\n"
        "Paper trading lets you practice trading with virtual money.\n\n"
        "**Features:**\n"
        "• Virtual capital (₹5,00,000 default)\n"
        "• Real-time position tracking\n"
        "• Stop-loss and target management\n"
        "• Performance analytics\n"
        "• System improvement recommendations\n\n"
        "**Use `/papertrade start` to begin!**",
        parse_mode='Markdown'
    )


async def handle_papertrade_buy_signals_info(query, context) -> None:
    """Show information about BUY signals trading."""
    await query.edit_message_text(
        "ℹ️ *Trading All BUY Signals*\n\n"
        "This feature automatically trades all stocks with BUY signals from today's daily analysis.\n\n"
        "**How it works:**\n"
        "• Uses signals from daily analysis (4:15 AM IST)\n"
        "• Only trades STRONG BUY, BUY, WEAK BUY\n"
        "• Respects position limits and capital\n"
        "• Executes during market hours\n\n"
        "**Requirements:**\n"
        "• Active paper trading session\n"
        "• Daily analysis must be run first\n"
        "• Available capital",
        parse_mode='Markdown'
    )


async def handle_papertrade_watchlist_info(query, context) -> None:
    """Show information about watchlist trading."""
    await query.edit_message_text(
        "ℹ️ *Trading Watchlist Stocks*\n\n"
        "This feature analyzes and trades all stocks in your watchlist.\n\n"
        "**How it works:**\n"
        "• Analyzes each stock in your watchlist\n"
        "• Only trades stocks with BUY signals\n"
        "• Skips stocks already in positions\n"
        "• Respects position limits\n\n"
        "**Requirements:**\n"
        "• Active paper trading session\n"
        "• Non-empty watchlist\n"
        "• Available capital",
        parse_mode='Markdown'
    )


async def handle_papertrade_view_signals(query, context) -> None:
    """View available BUY signals."""
    from ..database.models import DailyBuySignal
    from datetime import datetime
    
    try:
        with get_db_context() as db:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0)
            signals = db.query(DailyBuySignal).filter(
                DailyBuySignal.analysis_date >= today,
                DailyBuySignal.recommendation_type.in_(['STRONG BUY', 'BUY', 'WEAK BUY'])
            ).order_by(DailyBuySignal.confidence.desc()).limit(10).all()
            
            if not signals:
                await query.edit_message_text(
                    "❌ *No BUY Signals*\n\n"
                    "No BUY signals available for today.\n\n"
                    "Run daily analysis first.",
                    parse_mode='Markdown'
                )
                return
            
            message = "📊 *Today's BUY Signals*\n\n"
            for i, signal in enumerate(signals, 1):
                message += (
                    f"{i}. {signal.symbol} - {signal.recommendation_type}\n"
                    f"   Price: ₹{signal.current_price:.2f} | "
                    f"Conf: {signal.confidence:.0f}%\n\n"
                )
            
            message += f"Total: {len(signals)} signals\n\n"
            message += "Click 'Trade All BUY Signals' to execute."
            
            await query.edit_message_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error viewing signals: {e}", exc_info=True)
        await query.answer("❌ Error loading signals", show_alert=True)
