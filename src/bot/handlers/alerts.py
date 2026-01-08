"""
Alert Management Handlers

This module handles all alert-related commands:
- /alerts - View all active alerts
- /alert SYMBOL - Create alerts for a stock
- /deletealert ID - Delete an alert
"""

import logging
from typing import List
from telegram import Update
from telegram.ext import ContextTypes

from ..database.db import (
    get_db_context,
    get_or_create_user,
    get_user_alerts,
    create_alert,
    delete_alert,
    update_alert_status
)
from ..services.analysis_service import get_current_price
from ..utils.formatters import (
    format_alert,
    format_success,
    format_error,
    format_warning
)
from ..utils.keyboards import (
    create_alert_type_keyboard,
    create_alert_list_keyboard
)
from ..utils.validators import validate_stock_symbol, validate_price, parse_command_args

logger = logging.getLogger(__name__)


async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /alerts command.
    
    Shows all active alerts for the user.
    
    Usage:
        /alerts - View all active alerts
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        alerts = get_user_alerts(db, user_id, active_only=True)
        
        if not alerts:
            await update.message.reply_text(
                "🔔 *Your Alerts*\n\n"
                "You don't have any active alerts.\n\n"
                "*How to create alerts:*\n"
                "1. Analyze a stock: `/analyze SYMBOL`\n"
                "2. Click 'Set Alert' button\n"
                "3. Choose alert type\n\n"
                "*Alert types available:*\n"
                "• Price alerts - Get notified at target price\n"
                "• RSI alerts - Overbought/oversold levels\n"
                "• Signal alerts - Recommendation changes\n\n"
                "*Example:*\n"
                "`/analyze RELIANCE.NS`",
                parse_mode='Markdown'
            )
            return
        
        # Format alerts list
        message = f"🔔 *Your Active Alerts* ({len(alerts)})\n\n"
        
        for i, alert in enumerate(alerts, 1):
            message += format_alert(alert, index=i) + "\n\n"
        
        message += (
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 *Managing alerts:*\n"
            "• Use buttons below to delete alerts\n"
            "• Alerts auto-trigger when conditions are met\n"
            "• You'll receive a notification in this chat"
        )
        
        # Create keyboard with delete buttons
        keyboard = create_alert_list_keyboard(alerts)
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        logger.info(f"User {user_id} viewed {len(alerts)} active alerts")


async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /alert command.
    
    Quick way to create an alert for a stock.
    
    Usage:
        /alert SYMBOL - Show alert options for stock
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Parse arguments
    args = parse_command_args(update.message.text)
    
    if not args:
        await update.message.reply_text(
            "🔔 *Create Alert*\n\n"
            "*Usage:* `/alert SYMBOL`\n\n"
            "*Example:* `/alert RELIANCE.NS`\n\n"
            "This will show you alert options for the stock.\n\n"
            "*Tip:* You can also create alerts after analyzing a stock "
            "using the 'Set Alert' button.",
            parse_mode='Markdown'
        )
        return
    
    symbol = args[0].upper()
    
    # Validate symbol
    is_valid, error_msg = validate_stock_symbol(symbol)
    if not is_valid:
        await update.message.reply_text(format_error(error_msg))
        return
    
    # Show alert type selection
    keyboard = create_alert_type_keyboard(symbol)
    
    try:
        # Get current price for reference
        current_price = get_current_price(symbol)
        price_info = f"\n\nℹ️ Current price: ₹{current_price:.2f}"
    except Exception as e:
        logger.warning(f"Could not fetch current price for {symbol}: {e}")
        price_info = ""
    
    await update.message.reply_text(
        f"🔔 *Create Alert for {symbol}*{price_info}\n\n"
        f"Choose the type of alert you want to set:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def deletealert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /deletealert command.
    
    Deletes a specific alert by ID.
    
    Usage:
        /deletealert ID - Delete alert by ID
    """
    user_id = update.effective_user.id
    
    # Parse arguments
    args = parse_command_args(update.message.text)
    
    if not args:
        await update.message.reply_text(
            format_error(
                "Please provide an alert ID.\n\n"
                "*Usage:* `/deletealert ID`\n"
                "*Example:* `/deletealert 5`\n\n"
                "Use `/alerts` to see all your alerts with their IDs."
            )
        )
        return
    
    try:
        alert_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            format_error("Invalid alert ID. Please provide a number.")
        )
        return
    
    with get_db_context() as db:
        # Verify alert belongs to user before deleting
        alerts = get_user_alerts(db, user_id, active_only=False)
        alert_to_delete = next((a for a in alerts if a.id == alert_id), None)
        
        if not alert_to_delete:
            await update.message.reply_text(
                format_error(
                    f"Alert #{alert_id} not found.\n\n"
                    f"Use `/alerts` to see your active alerts."
                )
            )
            return
        
        success = delete_alert(db, alert_id, user_id)
        
        if success:
            await update.message.reply_text(
                format_success(
                    f"✓ Alert #{alert_id} deleted\n\n"
                    f"Symbol: {alert_to_delete.symbol}\n"
                    f"Type: {alert_to_delete.alert_type}"
                )
            )
            logger.info(f"User {user_id} deleted alert {alert_id}")
        else:
            await update.message.reply_text(
                format_error(f"Failed to delete alert #{alert_id}")
            )


async def handle_price_alert_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle user input for price alert value.
    
    This is called when user sends a price after clicking "Price Alert" button.
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Check if user is awaiting price alert input
    if 'awaiting_price_alert' not in context.user_data:
        return
    
    symbol = context.user_data['awaiting_price_alert']
    price_text = update.message.text.strip()
    
    # Validate price
    is_valid, price_or_error = validate_price(price_text)
    if not is_valid:
        await update.message.reply_text(
            format_error(
                f"Invalid price format: {price_or_error}\n\n"
                f"Please send a valid price (e.g., `2500` or `2500.50`)"
            )
        )
        return
    
    target_price = price_or_error
    
    try:
        # Get current price
        current_price = get_current_price(symbol)
        
        # Determine if it's above or below current price
        if target_price > current_price:
            operator = '>'
            direction = "rises above"
        elif target_price < current_price:
            operator = '<'
            direction = "falls below"
        else:
            await update.message.reply_text(
                format_warning(
                    f"Target price (₹{target_price:.2f}) is same as current price (₹{current_price:.2f}).\n\n"
                    f"Please set a different target price."
                )
            )
            return
        
        # Create alert
        with get_db_context() as db:
            user = get_or_create_user(db, user_id, username)
            
            alert = create_alert(
                db=db,
                user_id=user_id,
                symbol=symbol,
                alert_type='price',
                condition={'operator': operator, 'value': target_price},
                message=f"{symbol} {direction} ₹{target_price:.2f}"
            )
            
            if alert:
                price_change = ((target_price - current_price) / current_price) * 100
                
                await update.message.reply_text(
                    format_success(
                        f"✓ Price alert created!\n\n"
                        f"*Stock:* {symbol}\n"
                        f"*Current Price:* ₹{current_price:.2f}\n"
                        f"*Target Price:* ₹{target_price:.2f}\n"
                        f"*Change:* {price_change:+.2f}%\n\n"
                        f"You'll be notified when {symbol} {direction} ₹{target_price:.2f}"
                    )
                )
                logger.info(
                    f"User {user_id} created price alert: "
                    f"{symbol} {operator} {target_price}"
                )
            else:
                await update.message.reply_text(
                    format_error("Failed to create alert. Please try again.")
                )
    
    except Exception as e:
        logger.error(f"Error creating price alert: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"An error occurred: {str(e)}")
        )
    
    finally:
        # Clear context
        context.user_data.pop('awaiting_price_alert', None)


async def clearalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /clearalerts command.
    
    Clears all active alerts for the user.
    
    Usage:
        /clearalerts - Clear all alerts
    """
    user_id = update.effective_user.id
    
    with get_db_context() as db:
        alerts = get_user_alerts(db, user_id, active_only=True)
        
        if not alerts:
            await update.message.reply_text(
                format_warning("You don't have any active alerts to clear.")
            )
            return
        
        # Confirm before clearing
        count = len(alerts)
        
        # Store confirmation in user context
        context.user_data['awaiting_alerts_clear_confirmation'] = True
        
        from ..utils.keyboards import create_confirmation_keyboard
        keyboard = create_confirmation_keyboard("confirm_alerts_clear")
        
        await update.message.reply_text(
            f"⚠️ *Confirm Clear Alerts*\n\n"
            f"Are you sure you want to delete all {count} alert(s)?\n\n"
            f"This action cannot be undone.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def confirm_alerts_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and execute alerts clear."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    with get_db_context() as db:
        alerts = get_user_alerts(db, user_id, active_only=True)
        count = len(alerts)
        
        # Delete all alerts
        success_count = 0
        for alert in alerts:
            if delete_alert(db, alert.id, user_id):
                success_count += 1
        
        if success_count == count:
            await query.edit_message_text(
                format_success(
                    f"✓ Cleared all {count} alert(s)"
                )
            )
            logger.info(f"User {user_id} cleared all alerts ({count} alerts)")
        else:
            await query.edit_message_text(
                format_warning(
                    f"Partially cleared alerts:\n"
                    f"• Deleted: {success_count}\n"
                    f"• Failed: {count - success_count}"
                )
            )
    
    # Clear context
    context.user_data.pop('awaiting_alerts_clear_confirmation', None)
