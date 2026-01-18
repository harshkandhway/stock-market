"""
Settings Management Handlers

Enhanced with comprehensive guides and tooltips for the best user experience.
Every setting has contextual help to make investing accessible to everyone.

Author: Harsh Kandhway
"""

import logging
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from ..database.db import (
    get_db_context,
    get_or_create_user,
    get_user_settings,
    update_user_settings
)
from ..utils.formatters import format_success, format_error, format_warning
from ..utils.keyboards import (
    create_settings_menu_keyboard, create_risk_mode_keyboard,
    create_horizon_keyboard,
    create_capital_preset_keyboard,
    create_daily_buy_alerts_keyboard
)
from ..utils.validators import validate_mode, validate_timeframe, parse_command_args
from ..config import RiskMode, Timeframe, DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)


async def safe_edit_message(query, text: str, reply_markup=None, parse_mode='Markdown'):
    """
    Safely edit a message, handling BadRequest when content is unchanged.
    
    Args:
        query: CallbackQuery object
        text: Message text
        reply_markup: Optional keyboard markup
        parse_mode: Parse mode (default: 'Markdown')
    """
    try:
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except BadRequest as e:
        # Message content is the same - this is fine, just acknowledge
        if "not modified" in str(e).lower() or "exactly the same" in str(e).lower():
            await query.answer()  # Just acknowledge the callback
            logger.debug(f"Message not modified (same content) for user {query.from_user.id}")
        else:
            # Some other BadRequest error - log and re-raise
            logger.warning(f"BadRequest when editing message: {e}")
            await query.answer("⚠️ Could not update message. Please try again.")
            raise
    except Exception as e:
        logger.error(f"Error editing message: {e}", exc_info=True)
        await query.answer("⚠️ An error occurred. Please try again.")
        raise

# =============================================================================
# INVESTMENT HORIZON CONFIGURATIONS WITH DETAILED GUIDES
# =============================================================================

HORIZON_INFO = {
    '1week': {
        'name': 'Quick Trade',
        'display': '1 Week',
        'risk': 'HIGH',
        'risk_emoji': '🔴',
        'emoji': '⚡',
        'description': 'Very short-term trades for experienced traders',
        'suitable_for': 'Day traders & experienced investors',
        'not_for': 'Beginners or risk-averse investors',
        'expected_return': '2-5% potential (highly variable)',
        'guide': """
*⚡ 1 WEEK - Quick Trade*

*What this means:*
You plan to buy and sell within 7 days.

*Best for:*
• Experienced traders
• People who can monitor markets daily
• Those comfortable with high volatility

*Risks:*
• Prices can swing wildly in short periods
• Requires quick decision-making
• Higher chance of loss if market moves against you
• Transaction costs eat into small gains

*Our Recommendation:*
🔴 HIGH RISK - Only choose this if you have trading experience and can afford potential losses.

*Tip:* Set strict stop-losses and don't invest money you can't afford to lose.
""",
    },
    '2weeks': {
        'name': 'Swing Trade',
        'display': '2 Weeks',
        'risk': 'MEDIUM-HIGH',
        'risk_emoji': '🟠',
        'emoji': '🔄',
        'description': 'Short-term swing trading',
        'suitable_for': 'Active investors with some experience',
        'not_for': 'Complete beginners',
        'expected_return': '3-8% potential',
        'guide': """
*🔄 2 WEEKS - Swing Trade*

*What this means:*
You plan to hold for about 10-14 trading days, capturing price "swings."

*Best for:*
• Active investors
• People with basic market knowledge
• Those who check investments few times a week

*Risks:*
• Market can be unpredictable in short term
• News events can cause sudden drops
• Requires attention to market trends

*Our Recommendation:*
🟠 MEDIUM-HIGH RISK - Suitable if you understand basic technical analysis.

*Tip:* Look for stocks with clear trend patterns and good volume.
""",
    },
    '1month': {
        'name': 'Short Position',
        'display': '1 Month',
        'risk': 'MEDIUM',
        'risk_emoji': '🟡',
        'emoji': '📅',
        'description': 'Monthly positions for regular investors',
        'suitable_for': 'Regular investors',
        'not_for': 'Very conservative investors',
        'expected_return': '5-12% potential',
        'guide': """
*📅 1 MONTH - Short Position*

*What this means:*
You plan to hold for about 20-25 trading days.

*Best for:*
• Regular investors
• People who can wait for trends to develop
• Those comfortable with moderate fluctuations

*Risks:*
• Stock may not reach target in time
• Monthly market cycles affect prices
• May need to extend holding period

*Our Recommendation:*
🟡 MEDIUM RISK - Good balance of risk and opportunity.

*Tip:* Choose stocks with upcoming positive catalysts (results, news).
""",
    },
    '3months': {
        'name': 'Medium Position',
        'display': '3 Months',
        'risk': 'MEDIUM-LOW',
        'risk_emoji': '🟢',
        'emoji': '📊',
        'description': 'Recommended for most investors',
        'suitable_for': 'Most investors including beginners',
        'not_for': 'Impatient traders',
        'expected_return': '10-20% potential',
        'guide': """
*📊 3 MONTHS - Medium Position* ⭐ RECOMMENDED

*What this means:*
You plan to hold for about 60-65 trading days (one quarter).

*Best for:*
• Most investors including beginners
• People who want meaningful returns
• Those who can be patient

*Why we recommend this:*
✅ Gives enough time for trends to play out
✅ Reduces impact of daily volatility
✅ Aligns with company quarterly results
✅ Good balance of risk and reward

*Our Recommendation:*
🟢 MEDIUM-LOW RISK - Ideal starting point for building wealth.

*Tip:* Review your investment once a month, not daily!
""",
    },
    '6months': {
        'name': 'Long Position',
        'display': '6 Months',
        'risk': 'LOW',
        'risk_emoji': '🟢',
        'emoji': '🎯',
        'description': 'Ideal for patient investors and beginners',
        'suitable_for': 'Patient investors, beginners, retirement planning',
        'not_for': 'Those needing quick returns',
        'expected_return': '15-30% potential',
        'guide': """
*🎯 6 MONTHS - Long Position* ⭐ BEGINNER FRIENDLY

*What this means:*
You plan to hold for about 125 trading days (two quarters).

*Best for:*
• Beginners learning to invest
• Patient investors
• Building long-term wealth
• Those who don't want to check daily

*Why beginners should consider this:*
✅ Short-term noise doesn't affect you
✅ Time to recover from temporary dips
✅ Less stressful - no daily monitoring
✅ Better tax treatment (in many countries)

*Our Recommendation:*
🟢 LOW RISK - Excellent for beginners and steady wealth building.

*Tip:* Invest regularly (SIP approach) for even better results!
""",
    },
    '1year': {
        'name': 'Long-Term Investment',
        'display': '1 Year',
        'risk': 'VERY LOW',
        'risk_emoji': '🟢',
        'emoji': '💎',
        'description': 'Best for wealth creation and retirement',
        'suitable_for': 'Long-term wealth builders, retirement planning',
        'not_for': 'Those needing money soon',
        'expected_return': '20-40%+ potential',
        'guide': """
*💎 1 YEAR - Long-Term Investment* ⭐ WEALTH BUILDING

*What this means:*
You plan to hold for 250+ trading days (full year).

*Best for:*
• Serious wealth building
• Retirement planning
• Those who believe in company's future
• Tax-efficient investing

*Why long-term wins:*
✅ Historically, markets always grow over time
✅ Compounding works magic over years
✅ Lowest stress - minimal monitoring
✅ Best tax treatment
✅ Ride out any market corrections

*Our Recommendation:*
🟢 VERY LOW RISK - The safest and most proven way to build wealth.

*Tip:* Choose fundamentally strong companies and forget about daily prices!
""",
    },
}

# =============================================================================
# RISK MODE CONFIGURATIONS WITH DETAILED GUIDES
# =============================================================================

RISK_MODE_INFO = {
    'conservative': {
        'name': 'Conservative',
        'emoji': '🛡️',
        'risk_level': 'LOW',
        'description': 'Safety first approach',
        'guide': """
*🛡️ CONSERVATIVE MODE*

*How it works:*
• Shows only the SAFEST opportunities
• Applies strict filters (blocks risky setups)
• Smaller position sizes (1% risk per trade)
• Higher profit targets required
• Fewer but higher-quality signals

*Best for:*
• Risk-averse investors
• Beginners learning the market
• Those who can't afford losses
• Retirement savings

*Trade-off:*
You'll see fewer opportunities, but each one has a higher chance of success.

*Our Recommendation:*
If you're new to investing or value capital preservation over growth, choose this.
""",
    },
    'balanced': {
        'name': 'Balanced',
        'emoji': '⚖️',
        'risk_level': 'MEDIUM',
        'description': 'Best of both worlds',
        'guide': """
*⚖️ BALANCED MODE* ⭐ RECOMMENDED

*How it works:*
• Balances safety with opportunity
• Moderate filters (catches good setups)
• Standard position sizes (1.5% risk per trade)
• Reasonable profit targets
• Good number of quality signals

*Best for:*
• Most investors
• Those with basic market understanding
• People seeking growth with manageable risk

*Why we recommend this:*
✅ Not too aggressive, not too cautious
✅ Captures most good opportunities
✅ Reasonable risk management
✅ Works well in most market conditions

*Our Recommendation:*
The best starting point for most investors. Adjust later based on experience.
""",
    },
    'aggressive': {
        'name': 'Aggressive',
        'emoji': '🚀',
        'risk_level': 'HIGH',
        'description': 'Maximum opportunity approach',
        'guide': """
*🚀 AGGRESSIVE MODE*

*How it works:*
• Relaxed filters (more opportunities)
• Larger position sizes (2% risk per trade)
• Lower entry thresholds
• More signals, including speculative ones

*Best for:*
• Experienced traders
• Those who can afford losses
• People seeking high growth
• Active market participants

*Risks:*
⚠️ More false signals
⚠️ Higher chance of losses
⚠️ Requires active monitoring
⚠️ Not for beginners

*Our Recommendation:*
Only choose this if you have experience and can handle volatility.
""",
    },
}

# =============================================================================
# CAPITAL GUIDE
# =============================================================================

CAPITAL_GUIDE = """
*💰 SETTING YOUR INVESTMENT CAPITAL*

Your capital setting helps us calculate:
• How many shares to buy
• Position sizes for proper risk management
• Potential profit/loss in rupees
• Portfolio allocation suggestions

*Guidelines for setting capital:*

📌 *Only use money you can afford to lose*
   Never invest emergency funds or borrowed money.

📌 *Start small if you're new*
   Rs 25,000 - Rs 50,000 is a good starting point.

📌 *Be realistic*
   Enter your actual investment amount, not aspirational.

📌 *Update regularly*
   As your capital grows, update this setting.

*How position sizing works:*
We use the "1% Rule" - never risk more than 1-2% of capital per trade. This protects you from big losses.

*Example:*
Capital: Rs 1,00,000
Risk per trade: 1% = Rs 1,000
If stop loss is 5% away, we recommend buying Rs 20,000 worth.

*Choose a preset or enter custom amount:*
"""

# =============================================================================
# REPORT STYLE GUIDE
# =============================================================================

# =============================================================================
# COMMAND HANDLERS
# =============================================================================

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /settings command.
    Shows current settings and provides inline buttons to modify them.
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        settings = get_user_settings(db, user_id)
        
        # Get horizon info
        horizon_key = getattr(settings, 'investment_horizon', '3months') or '3months'
        horizon = HORIZON_INFO.get(horizon_key, HORIZON_INFO['3months'])
        
        # Get mode info
        mode_key = settings.risk_mode or 'balanced'
        mode = RISK_MODE_INFO.get(mode_key, RISK_MODE_INFO['balanced'])
        
        # Format settings message with quick overview
        message = f"""
*⚙️ YOUR SETTINGS*
━━━━━━━━━━━━━━━━━━━━

*📅 Investment Period:* {horizon['display']}
   {horizon['emoji']} {horizon['name']} • {horizon['risk_emoji']} {horizon['risk']} risk

*🎯 Risk Mode:* {mode['emoji']} {mode['name']}
   {mode['description']}

*💰 Analysis Capital:* Rs {settings.default_capital or 100000:,.0f}
   For position sizing calculations

━━━━━━━━━━━━━━━━━━━━

*📊 PAPER TRADING SETTINGS*
━━━━━━━━━━━━━━━━━━━━

*Enable Paper Trading:* {'✅ ON' if getattr(settings, 'paper_trading_enabled', True) else '❌ OFF'}
*Default Capital:* ₹{getattr(settings, 'paper_trading_default_capital', 500000):,.0f}
*Max Positions:* {getattr(settings, 'paper_trading_max_positions', 15)}
*Risk per Trade:* {getattr(settings, 'paper_trading_risk_percentage', 1.0)}%
*Monitor Interval:* {getattr(settings, 'paper_trading_monitor_interval_seconds', 300)//60} min
*Max Position Size:* {getattr(settings, 'paper_trading_max_position_size_pct', 20.0)}%
*Buy Execution:* {getattr(settings, 'paper_trading_buy_execution_time', '09:20')} IST
*Daily Summary:* {getattr(settings, 'paper_trading_daily_summary_time', '16:00')} IST
*Weekly Summary:* {getattr(settings, 'paper_trading_weekly_summary_time', '18:00')} IST
*Rebalance:* {getattr(settings, 'paper_trading_position_rebalance_time', '11:00')} IST
*Price Tolerance:* {getattr(settings, 'paper_trading_entry_price_tolerance_pct', 3.0)}%

━━━━━━━━━━━━━━━━━━━━

*Tap any button below to customize:*
_(Each option has a helpful guide)_
"""
        
        daily_buy_enabled = getattr(settings, 'daily_buy_alerts_enabled', False) or False
        keyboard = create_settings_menu_keyboard(daily_buy_enabled)
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def setmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setmode command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    args = parse_command_args(update.message.text)
    
    if not args:
        message = """
*🎯 SET RISK MODE*

Choose how aggressive you want the analysis to be:

`/setmode conservative` - Safety first, fewer signals
`/setmode balanced` - Best of both worlds ⭐
`/setmode aggressive` - More opportunities, higher risk

*Or use* `/settings` *for interactive selection with guides.*
"""
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    mode = args[0].lower()
    
    is_valid, error_msg = validate_mode(mode)
    if not is_valid:
        await update.message.reply_text(format_error(error_msg))
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        update_user_settings(db, user_id, risk_mode=mode)
        
        mode_info = RISK_MODE_INFO[mode]
        
        await update.message.reply_text(
            f"✅ *Risk mode updated!*\n\n"
            f"{mode_info['emoji']} *{mode_info['name'].upper()}*\n"
            f"{mode_info['description']}\n\n"
            f"Your analysis will now use {mode} filters.",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} changed risk mode to {mode}")


async def sethorizon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sethorizon command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    args = parse_command_args(update.message.text)
    
    if not args:
        message = """
*📅 SET INVESTMENT HORIZON*

How long do you plan to hold investments?

`/sethorizon 1week` - Quick trade (High risk)
`/sethorizon 2weeks` - Swing trade
`/sethorizon 1month` - Short position
`/sethorizon 3months` - Recommended ⭐
`/sethorizon 6months` - Beginner friendly ⭐
`/sethorizon 1year` - Long-term wealth

*Or use* `/settings` *for interactive selection with detailed guides.*
"""
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    horizon = args[0].lower()
    
    if horizon not in HORIZON_INFO:
        await update.message.reply_text(
            format_error(f"Invalid horizon. Use: {', '.join(HORIZON_INFO.keys())}")
        )
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        update_user_settings(db, user_id, investment_horizon=horizon)
        
        info = HORIZON_INFO[horizon]
        
        await update.message.reply_text(
            f"✅ *Investment horizon updated!*\n\n"
            f"{info['emoji']} *{info['display']} - {info['name']}*\n"
            f"Risk Level: {info['risk_emoji']} {info['risk']}\n\n"
            f"_{info['description']}_",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} changed horizon to {horizon}")


async def settimeframe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settimeframe command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    args = parse_command_args(update.message.text)
    
    if not args:
        await update.message.reply_text(
            "*📊 SET ANALYSIS TIMEFRAME*\n\n"
            "`/settimeframe short` - 1-4 weeks analysis\n"
            "`/settimeframe medium` - 1-3 months analysis\n\n"
            "*Or use* `/settings` *for interactive menu.*",
            parse_mode='Markdown'
        )
        return
    
    timeframe = args[0].lower()
    
    if timeframe not in ['short', 'medium']:
        await update.message.reply_text(
            format_error("Invalid timeframe. Use 'short' or 'medium'")
        )
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        update_user_settings(db, user_id, timeframe=timeframe)
        
        await update.message.reply_text(
            f"✅ *Analysis timeframe updated to {timeframe.upper()}*",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} changed timeframe to {timeframe}")


async def setcapital_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setcapital command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    args = parse_command_args(update.message.text)
    
    if not args:
        await update.message.reply_text(
            "*💰 SET YOUR INVESTMENT CAPITAL*\n\n"
            "Example: `/setcapital 100000` for Rs 1,00,000\n\n"
            "This helps calculate:\n"
            "• Position sizes\n"
            "• Potential profit/loss\n"
            "• Risk management\n\n"
            "*Or use* `/settings` *for preset options with guide.*",
            parse_mode='Markdown'
        )
        return
    
    try:
        capital = float(args[0].replace(',', ''))
    except ValueError:
        await update.message.reply_text(format_error("Please enter a valid number"))
        return
    
    if capital < 10000:
        await update.message.reply_text(format_error("Minimum capital is Rs 10,000"))
        return
    
    if capital > 100000000:
        await update.message.reply_text(format_error("Maximum capital is Rs 10 crore"))
        return
    
    with get_db_context() as db:
        user = get_or_create_user(db, user_id, username)
        update_user_settings(db, user_id, default_capital=capital)
        
        await update.message.reply_text(
            f"✅ *Capital updated to Rs {capital:,.0f}*\n\n"
            f"Position sizes will now be calculated based on this amount.",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} changed capital to {capital}")


async def reset_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resetsettings command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Reset", callback_data="confirm_reset:settings"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset:settings"),
        ]
    ])
    
    await update.message.reply_text(
        "*⚠️ RESET ALL SETTINGS?*\n\n"
        "This will restore defaults:\n"
        "• Investment Period: 3 Months\n"
        "• Risk Mode: Balanced\n"
        "• Capital: Rs 1,00,000\n"
        "• Report Style: Beginner-Friendly\n\n"
        "Are you sure?",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def confirm_settings_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and execute settings reset."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    with get_db_context() as db:
        update_user_settings(
            db,
            user_id,
            risk_mode='balanced',
            timeframe='medium',
            investment_horizon='3months',
            default_capital=100000.0
        )
        
        await safe_edit_message(
            query,
            "✅ *Settings reset to defaults!*\n\n"
            "• Investment Period: 3 Months\n"
            "• Risk Mode: Balanced\n"
            "• Capital: Rs 1,00,000\n\n"
            "Use /settings to customize."
        )
        logger.info(f"User {user_id} reset settings to defaults")
    

# =============================================================================
# CALLBACK HANDLERS FOR SETTINGS BUTTONS
# =============================================================================

async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings-related callback queries from inline buttons."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check authorization (if admin IDs are configured, only allow admins)
    # If TELEGRAM_ADMIN_IDS is empty, allow everyone (public bot)
    from ..config import TELEGRAM_ADMIN_IDS
    if TELEGRAM_ADMIN_IDS:  # Only check if admin IDs are configured
        if user_id not in TELEGRAM_ADMIN_IDS:
            await query.answer(
                "⛔ You are not authorized to use this bot.",
                show_alert=True
            )
            logger.warning(f"Unauthorized settings callback attempt by user {user_id}: {query.data}")
            return
    
    await query.answer()
    
    data = query.data
    
    with get_db_context() as db:
        settings = get_user_settings(db, user_id)
        
        # =====================================================================
        # MAIN SETTINGS MENU
        # =====================================================================
        if data == "settings_menu":
            horizon_key = getattr(settings, 'investment_horizon', '3months') or '3months'
            horizon = HORIZON_INFO.get(horizon_key, HORIZON_INFO['3months'])
            mode_key = settings.risk_mode or 'balanced'
            mode = RISK_MODE_INFO.get(mode_key, RISK_MODE_INFO['balanced'])
            
            message = f"""
*⚙️ YOUR SETTINGS*
━━━━━━━━━━━━━━━━━━━━

*📅 Investment Period:* {horizon['display']}
   {horizon['emoji']} {horizon['name']} • {horizon['risk_emoji']} {horizon['risk']} risk

*🎯 Risk Mode:* {mode['emoji']} {mode['name']}
   {mode['description']}

*💰 Capital:* Rs {settings.default_capital or 100000:,.0f}

━━━━━━━━━━━━━━━━━━━━

*Tap any button below to customize:*
"""
            daily_buy_enabled = getattr(settings, 'daily_buy_alerts_enabled', False) or False
            keyboard = create_settings_menu_keyboard(daily_buy_enabled)
            await safe_edit_message(query, message, reply_markup=keyboard)
        
        # =====================================================================
        # DAILY BUY ALERTS SUBSCRIPTION
        # =====================================================================
        elif data == "settings_daily_buy_alerts":
            is_enabled = getattr(settings, 'daily_buy_alerts_enabled', False) or False
            alert_time = getattr(settings, 'daily_buy_alert_time', '09:00') or '09:00'
            
            status_text = "✅ Enabled" if is_enabled else "❌ Disabled"
            message = f"""
*🔔 DAILY BUY ALERTS*
━━━━━━━━━━━━━━━━━━━━

*Status:* {status_text}
*Alert Time:* {alert_time} (your timezone)

*What you'll receive:*
• Daily analysis of all stocks (4000+)
• Only BUY signals filtered out
• Complete analysis report for each BUY
• Delivered at your preferred time

*How it works:*
1. We analyze all stocks daily
2. Filter only BUY signals
3. Save to database
4. Send you formatted reports at your time

━━━━━━━━━━━━━━━━━━━━

*Tap buttons below to manage:*
"""
            keyboard = create_daily_buy_alerts_keyboard(is_enabled)
            await safe_edit_message(query, message, reply_markup=keyboard)
        
        elif data == "daily_buy_alerts_toggle":
            is_enabled = getattr(settings, 'daily_buy_alerts_enabled', False) or False
            new_status = not is_enabled
            
            update_user_settings(db, user_id, daily_buy_alerts_enabled=new_status)
            
            status_text = "enabled" if new_status else "disabled"
            emoji = "✅" if new_status else "❌"
            
            message = f"""
{emoji} *Daily BUY Alerts {status_text.upper()}!*

{"You'll now receive daily BUY signals at your preferred time." if new_status else "Daily BUY alerts have been disabled."}

{"Use the buttons below to set your preferred alert time." if new_status else "Use /settings to enable again anytime."}
"""
            keyboard = create_daily_buy_alerts_keyboard(new_status)
            await safe_edit_message(query, message, reply_markup=keyboard)
            logger.info(f"User {user_id} {'enabled' if new_status else 'disabled'} daily BUY alerts")
        
        elif data.startswith("daily_buy_alert_time:"):
            time_str = data.split(":", 1)[1]
            
            if time_str == "custom":
                context.user_data['awaiting_alert_time_input'] = True
                user_timezone = getattr(settings, 'timezone', None) or DEFAULT_TIMEZONE
                await safe_edit_message(
                    query,
                    f"*🕐 SET CUSTOM ALERT TIME*\n\n"
                    f"Enter your preferred time in HH:MM format:\n\n"
                    f"Examples:\n"
                    f"• `09:00` for 9:00 AM\n"
                    f"• `14:30` for 2:30 PM\n"
                    f"• `18:00` for 6:00 PM\n\n"
                    f"Time is in your timezone: {user_timezone}\n\n"
                    f"_Just type the time and send (HH:MM format)_",
                    parse_mode='Markdown'
                )
            else:
                # Validate time format
                try:
                    hour, minute = map(int, time_str.split(':'))
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        update_user_settings(db, user_id, daily_buy_alert_time=time_str)
                        await safe_edit_message(
                            query,
                            f"✅ *Alert time set to {time_str}*\n\n"
                            f"You'll receive daily BUY alerts at {time_str} ({settings.timezone}).\n\n"
                            f"Use /settings to make more changes."
                        )
                        logger.info(f"User {user_id} set daily BUY alert time to {time_str}")
                    else:
                        await query.answer("Invalid time format. Use HH:MM (e.g., 09:00)", show_alert=True)
                except ValueError:
                    await query.answer("Invalid time format. Use HH:MM (e.g., 09:00)", show_alert=True)
        
        elif data == "daily_buy_alerts_info":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back", callback_data="settings_daily_buy_alerts")]
            ])
            
            await safe_edit_message(
                query,
                """
*ℹ️ ABOUT DAILY BUY ALERTS*
━━━━━━━━━━━━━━━━━━━━

*What are Daily BUY Alerts?*
Every day, we analyze all 4000+ stocks from our database and filter out only those showing BUY signals. You'll receive a comprehensive analysis report for each BUY opportunity.

*What you'll get:*
✅ Complete technical analysis
✅ Risk/reward ratios
✅ Entry, target, and stop loss prices
✅ Confidence scores
✅ Safety ratings
✅ Position sizing guidance

*When do alerts run?*
• Analysis runs once daily (early morning)
• Alerts sent at your preferred time
• Only active BUY signals included
• No spam - only quality opportunities

*How many alerts?*
The number varies based on market conditions. Typically 5-50 BUY signals per day from 4000+ stocks.

*Best practices:*
• Review alerts when you receive them
• Don't buy everything - be selective
• Use your risk management settings
• Combine with your own research

*Privacy:*
Your subscription is private. We never share your data.

━━━━━━━━━━━━━━━━━━━━
""",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        # =====================================================================
        # PAPER TRADING SETTINGS MENU
        # =====================================================================
        elif data == "settings_paper_trading":
            from ..utils.keyboards import create_paper_trading_settings_keyboard

            message = """
*📊 PAPER TRADING SETTINGS*
━━━━━━━━━━━━━━━━━━━━

Customize how your automated paper trading works:

*⚙️ Core Settings:*
• Enable/disable paper trading
• Set default capital for new sessions
• Configure maximum concurrent positions

*💰 Risk Management:*
• Risk percentage per trade (recommended: 1-2%)
• Maximum position size as % of capital
• Price tolerance for signal execution

*⏰ Timing & Automation:*
• When pending trades execute (market open)
• Daily/weekly performance summaries
• Position monitoring frequency
• Automatic rebalancing schedule

━━━━━━━━━━━━━━━━━━━━

*Select any setting below to customize:*
"""

            keyboard = create_paper_trading_settings_keyboard()
            await safe_edit_message(query, message, reply_markup=keyboard)

        # =====================================================================
        # PAPER TRADING INDIVIDUAL SETTINGS
        # =====================================================================
        elif data == "settings_paper_trading_enabled":
            current = getattr(settings, 'paper_trading_enabled', True)
            status = "✅ ENABLED" if current else "❌ DISABLED"

            message = f"""
*🔄 PAPER TRADING ENABLE/DISABLE*
━━━━━━━━━━━━━━━━━━━━

*Current Status:* {status}

*What this does:*
• When **enabled**: Automatically execute BUY signals as paper trades
• When **disabled**: Only receive signal notifications (no trading)

*Note:* You can still manually paper trade with `/papertrade` even when disabled.

━━━━━━━━━━━━━━━━━━━━

Choose new status:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Enable Paper Trading", callback_data="settings_paper_trading_enabled:enable")],
                [InlineKeyboardButton("❌ Disable Paper Trading", callback_data="settings_paper_trading_enabled:disable")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_enabled:"):
            action = data.split(":")[1]
            new_value = action == "enable"

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_enabled=new_value)

            status = "✅ ENABLED" if new_value else "❌ DISABLED"
            await safe_edit_message(
                query,
                f"✅ *Paper trading {action}d!*\n\n"
                f"Status: {status}\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_capital":
            current = getattr(settings, 'paper_trading_default_capital', 500000)

            message = f"""
*💰 PAPER TRADING DEFAULT CAPITAL*
━━━━━━━━━━━━━━━━━━━━

*Current:* ₹{current:,.0f}

*What this is:*
This is the virtual capital amount used for new paper trading sessions.

━━━━━━━━━━━━━━━━━━━━

Choose new capital amount:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("₹1,00,000", callback_data="settings_paper_trading_capital:100000")],
                [InlineKeyboardButton("₹2,50,000", callback_data="settings_paper_trading_capital:250000")],
                [InlineKeyboardButton("₹5,00,000", callback_data="settings_paper_trading_capital:500000")],
                [InlineKeyboardButton("₹10,00,000", callback_data="settings_paper_trading_capital:1000000")],
                [InlineKeyboardButton("💰 Custom Amount", callback_data="settings_paper_trading_capital:custom")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_capital:"):
            value = data.split(":")[1]

            if value == "custom":
                context.user_data['awaiting_paper_trading_capital_input'] = True

                await safe_edit_message(
                    query,
                    "*💰 ENTER CUSTOM CAPITAL AMOUNT*\n\n"
                    "Type your paper trading capital amount:\n\n"
                    "Examples:\n"
                    "• `75000` for Rs 75,000\n"
                    "• `150000` for Rs 1,50,000\n"
                    "• `300000` for Rs 3,00,000\n\n"
                    "Minimum: Rs 10,000\n"
                    "Maximum: Rs 1,00,00,000\n\n"
                    "_Just type the number and send_",
                    parse_mode='Markdown'
                )
            else:
                amount = int(value)
                with get_db_context() as db:
                    update_user_settings(db, user_id, paper_trading_default_capital=amount)

                await safe_edit_message(
                    query,
                    f"✅ *Capital updated!*\n\n"
                    f"Paper trading capital: ₹{amount:,.0f}\n\n"
                    f"Use `/settings` to see all your settings.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                    ])
                )

        elif data == "settings_paper_trading_max_positions":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data.startswith("settings_paper_trading_max_positions:"):
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_risk":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data.startswith("settings_paper_trading_risk:"):
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_monitor":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data.startswith("settings_paper_trading_monitor:"):
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_max_size":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data.startswith("settings_paper_trading_max_size:"):
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_buy_time":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data.startswith("settings_paper_trading_buy_time:"):
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_daily_time":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data.startswith("settings_paper_trading_daily_time:"):
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_weekly_time":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data.startswith("settings_paper_trading_weekly_time:"):
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_rebalance_time":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data.startswith("settings_paper_trading_rebalance_time:"):
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_tolerance":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data.startswith("settings_paper_trading_tolerance:"):
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_reset":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_reset:confirm":
            await safe_edit_message(
                query,
                "*Feature Coming Soon!*\n\n"
                "This paper trading setting is under development.\n\n"
                "Use `/settings` to see all your current settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        # =====================================================================
        # INVESTMENT HORIZON SELECTION
        # =====================================================================
        # PAPER TRADING INDIVIDUAL SETTINGS
        # =====================================================================
        elif data == "settings_paper_trading_enabled":
            current = getattr(settings, 'paper_trading_enabled', True)
            status = "✅ ENABLED" if current else "❌ DISABLED"

            message = f"""
*🔄 PAPER TRADING ENABLE/DISABLE*
━━━━━━━━━━━━━━━━━━━━

*Current Status:* {status}

*What this does:*
• When **enabled**: Automatically execute BUY signals as paper trades
• When **disabled**: Only receive signal notifications (no trading)

*Note:* You can still manually paper trade with `/papertrade` even when disabled.

━━━━━━━━━━━━━━━━━━━━

Choose new status:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Enable Paper Trading", callback_data="settings_paper_trading_enabled:enable")],
                [InlineKeyboardButton("❌ Disable Paper Trading", callback_data="settings_paper_trading_enabled:disable")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_enabled:"):
            action = data.split(":")[1]
            new_value = action == "enable"

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_enabled=new_value)

            status = "✅ ENABLED" if new_value else "❌ DISABLED"
            await safe_edit_message(
                query,
                f"✅ *Paper trading {action}d!*\n\n"
                f"Status: {status}\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        # =====================================================================
        # INVESTMENT HORIZON SELECTION
        # =====================================================================
        # PAPER TRADING INDIVIDUAL SETTINGS
        # =====================================================================
        elif data == "settings_paper_trading_enabled":
            current = getattr(settings, 'paper_trading_enabled', True)
            status = "✅ ENABLED" if current else "❌ DISABLED"

            message = f"""
*🔄 PAPER TRADING ENABLE/DISABLE*
━━━━━━━━━━━━━━━━━━━━

*Current Status:* {status}

*What this does:*
• When **enabled**: Automatically execute BUY signals as paper trades
• When **disabled**: Only receive signal notifications (no trading)

*Note:* You can still manually paper trade with `/papertrade` even when disabled.

━━━━━━━━━━━━━━━━━━━━

Choose new status:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Enable Paper Trading", callback_data="settings_paper_trading_enabled:enable")],
                [InlineKeyboardButton("❌ Disable Paper Trading", callback_data="settings_paper_trading_enabled:disable")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_enabled:"):
            action = data.split(":")[1]
            new_value = action == "enable"

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_enabled=new_value)

            status = "✅ ENABLED" if new_value else "❌ DISABLED"
            await safe_edit_message(
                query,
                f"✅ *Paper trading {action}d!*\n\n"
                f"Status: {status}\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_capital":
            current = getattr(settings, 'paper_trading_default_capital', 500000)

            message = f"""
*💰 PAPER TRADING DEFAULT CAPITAL*
━━━━━━━━━━━━━━━━━━━━

*Current:* ₹{current:,.0f}

*What this is:*
This is the virtual capital amount used for new paper trading sessions.

*When it's used:*
• When you start paper trading without an active session
• For calculating position sizes and risk management
• For P&L calculations and performance tracking

━━━━━━━━━━━━━━━━━━━━

Choose new capital amount:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("₹1,00,000", callback_data="settings_paper_trading_capital:100000")],
                [InlineKeyboardButton("₹2,50,000", callback_data="settings_paper_trading_capital:250000")],
                [InlineKeyboardButton("₹5,00,000", callback_data="settings_paper_trading_capital:500000")],
                [InlineKeyboardButton("₹10,00,000", callback_data="settings_paper_trading_capital:1000000")],
                [InlineKeyboardButton("💰 Custom Amount", callback_data="settings_paper_trading_capital:custom")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_capital:"):
            value = data.split(":")[1]

            if value == "custom":
                context.user_data['awaiting_paper_trading_capital_input'] = True

                await safe_edit_message(
                    query,
                    "*💰 ENTER CUSTOM CAPITAL AMOUNT*\n\n"
                    "Type your paper trading capital amount:\n\n"
                    "Examples:\n"
                    "• `75000` for Rs 75,000\n"
                    "• `150000` for Rs 1,50,000\n"
                    "• `300000` for Rs 3,00,000\n\n"
                    "Minimum: Rs 10,000\n"
                    "Maximum: Rs 1,00,00,000\n\n"
                    "_Just type the number and send_",
                    parse_mode='Markdown'
                )
            else:
                amount = int(value)
                with get_db_context() as db:
                    update_user_settings(db, user_id, paper_trading_default_capital=amount)

                await safe_edit_message(
                    query,
                    f"✅ *Capital updated!*\n\n"
                    f"Paper trading capital: ₹{amount:,.0f}\n\n"
                    f"Use `/settings` to see all your settings.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                    ])
                )

        elif data == "settings_paper_trading_max_positions":
            current = getattr(settings, 'paper_trading_max_positions', 15)

            message = f"""
*🎯 MAXIMUM CONCURRENT POSITIONS*
━━━━━━━━━━━━━━━━━━━━

*Current:* {current} positions

*What this controls:*
Maximum number of stocks you can hold simultaneously in paper trading.

*Guidelines:*
• **5-10**: Conservative (experienced traders)
• **10-15**: Balanced (most traders)
• **15-25**: Aggressive (portfolio managers)

━━━━━━━━━━━━━━━━━━━━

Choose maximum positions:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("5 Positions", callback_data="settings_paper_trading_max_positions:5")],
                [InlineKeyboardButton("10 Positions", callback_data="settings_paper_trading_max_positions:10")],
                [InlineKeyboardButton("15 Positions ⭐", callback_data="settings_paper_trading_max_positions:15")],
                [InlineKeyboardButton("20 Positions", callback_data="settings_paper_trading_max_positions:20")],
                [InlineKeyboardButton("25 Positions", callback_data="settings_paper_trading_max_positions:25")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_max_positions:"):
            value = int(data.split(":")[1])

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_max_positions=value)

            await safe_edit_message(
                query,
                f"✅ *Max positions updated!*\n\n"
                f"Maximum concurrent positions: {value}\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_risk":
            current = getattr(settings, 'paper_trading_risk_percentage', 1.0)

            message = f"""
*⚠️ RISK PER TRADE PERCENTAGE*
━━━━━━━━━━━━━━━━━━━━

*Current:* {current}%

*What this is:*
Maximum percentage of your capital to risk on any single trade.

*Professional Guidelines:*
• **0.5-1%**: Conservative (recommended for most)
• **1-2%**: Balanced (experienced traders)
• **2-5%**: Aggressive (high risk tolerance)

━━━━━━━━━━━━━━━━━━━━

Choose risk percentage:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("0.5% (Conservative)", callback_data="settings_paper_trading_risk:0.5")],
                [InlineKeyboardButton("1.0% (Recommended)", callback_data="settings_paper_trading_risk:1.0")],
                [InlineKeyboardButton("1.5% (Balanced)", callback_data="settings_paper_trading_risk:1.5")],
                [InlineKeyboardButton("2.0% (Experienced)", callback_data="settings_paper_trading_risk:2.0")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_risk:"):
            value = float(data.split(":")[1])

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_risk_percentage=value)

            await safe_edit_message(
                query,
                f"✅ *Risk percentage updated!*\n\n"
                f"Risk per trade: {value}%\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_monitor":
            current_seconds = getattr(settings, 'paper_trading_monitor_interval_seconds', 300)
            current_minutes = current_seconds // 60

            message = f"""
*⏱️ MONITORING INTERVAL*
━━━━━━━━━━━━━━━━━━━━

*Current:* {current_minutes} minutes

*What this controls:*
How often the system checks for:
• Price updates for P&L calculations
• Stop loss triggers
• Take profit levels

*Guidelines:*
• **1-2 min**: Very frequent (resource intensive)
• **5 min**: Balanced (recommended)
• **10-15 min**: Less frequent (saves resources)

━━━━━━━━━━━━━━━━━━━━

Choose monitoring interval:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("1 minute", callback_data="settings_paper_trading_monitor:60")],
                [InlineKeyboardButton("2 minutes", callback_data="settings_paper_trading_monitor:120")],
                [InlineKeyboardButton("5 minutes ⭐", callback_data="settings_paper_trading_monitor:300")],
                [InlineKeyboardButton("10 minutes", callback_data="settings_paper_trading_monitor:600")],
                [InlineKeyboardButton("15 minutes", callback_data="settings_paper_trading_monitor:900")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_monitor:"):
            seconds = int(data.split(":")[1])

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_monitor_interval_seconds=seconds)

            minutes = seconds // 60
            await safe_edit_message(
                query,
                f"✅ *Monitoring interval updated!*\n\n"
                f"Check every: {minutes} minutes\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_max_size":
            current = getattr(settings, 'paper_trading_max_position_size_pct', 20.0)

            message = f"""
*📏 MAX POSITION SIZE PERCENTAGE*
━━━━━━━━━━━━━━━━━━━━

*Current:* {current}%

*What this is:*
Maximum percentage of your total capital that can be invested in a single stock.

*Guidelines:*
• **5-10%**: Very conservative
• **10-20%**: Balanced (recommended)
• **20-30%**: Aggressive

━━━━━━━━━━━━━━━━━━━━

Choose max position size:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("5% (Conservative)", callback_data="settings_paper_trading_max_size:5.0")],
                [InlineKeyboardButton("10% (Safe)", callback_data="settings_paper_trading_max_size:10.0")],
                [InlineKeyboardButton("20% (Recommended)", callback_data="settings_paper_trading_max_size:20.0")],
                [InlineKeyboardButton("30% (Aggressive)", callback_data="settings_paper_trading_max_size:30.0")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_max_size:"):
            value = float(data.split(":")[1])

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_max_position_size_pct=value)

            await safe_edit_message(
                query,
                f"✅ *Max position size updated!*\n\n"
                f"Maximum per position: {value}%\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_buy_time":
            current = getattr(settings, 'paper_trading_buy_execution_time', '09:15')

            message = f"""
*🕘 BUY EXECUTION TIME*
━━━━━━━━━━━━━━━━━━━━

*Current:* {current} IST

*What this is:*
When pending BUY orders are executed during market hours.

*Important Notes:*
• Must be during market hours (9:15 AM - 3:30 PM IST)
• Orders execute at the specified time if signal conditions are met
• If market is closed, orders wait for next trading day

━━━━━━━━━━━━━━━━━━━━

Choose execution time:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("9:15 AM (Market Open)", callback_data="settings_paper_trading_buy_time:09:15")],
                [InlineKeyboardButton("9:30 AM", callback_data="settings_paper_trading_buy_time:09:30")],
                [InlineKeyboardButton("10:00 AM", callback_data="settings_paper_trading_buy_time:10:00")],
                [InlineKeyboardButton("11:00 AM", callback_data="settings_paper_trading_buy_time:11:00")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_buy_time:"):
            time_value = data.split(":")[1] + ":" + data.split(":")[2]

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_buy_execution_time=time_value)

            await safe_edit_message(
                query,
                f"✅ *Buy execution time updated!*\n\n"
                f"Execute buys at: {time_value} IST\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_daily_time":
            current = getattr(settings, 'paper_trading_daily_summary_time', '18:00')

            message = f"""
*📊 DAILY SUMMARY TIME*
━━━━━━━━━━━━━━━━━━━━

*Current:* {current} IST

*What this does:*
Sends daily performance summary every day at this time.

*Summary includes:*
• Today's P&L
• Active positions
• Pending orders
• Performance statistics

━━━━━━━━━━━━━━━━━━━━

Choose daily summary time:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("4:00 PM", callback_data="settings_paper_trading_daily_time:16:00")],
                [InlineKeyboardButton("6:00 PM ⭐", callback_data="settings_paper_trading_daily_time:18:00")],
                [InlineKeyboardButton("8:00 PM", callback_data="settings_paper_trading_daily_time:20:00")],
                [InlineKeyboardButton("9:00 PM", callback_data="settings_paper_trading_daily_time:21:00")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_daily_time:"):
            time_value = data.split(":")[1] + ":" + data.split(":")[2]

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_daily_summary_time=time_value)

            await safe_edit_message(
                query,
                f"✅ *Daily summary time updated!*\n\n"
                f"Send summary at: {time_value} IST\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_weekly_time":
            current = getattr(settings, 'paper_trading_weekly_summary_time', '18:00')

            message = f"""
*📅 WEEKLY SUMMARY TIME*
━━━━━━━━━━━━━━━━━━━━

*Current:* {current} IST

*What this does:*
Sends weekly performance summary every Sunday at this time.

*Summary includes:*
• Weekly P&L
• Best/worst performers
• Portfolio allocation
• Risk metrics

━━━━━━━━━━━━━━━━━━━━

Choose weekly summary time:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("4:00 PM", callback_data="settings_paper_trading_weekly_time:16:00")],
                [InlineKeyboardButton("6:00 PM ⭐", callback_data="settings_paper_trading_weekly_time:18:00")],
                [InlineKeyboardButton("8:00 PM", callback_data="settings_paper_trading_weekly_time:20:00")],
                [InlineKeyboardButton("9:00 PM", callback_data="settings_paper_trading_weekly_time:21:00")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_weekly_time:"):
            time_value = data.split(":")[1] + ":" + data.split(":")[2]

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_weekly_summary_time=time_value)

            await safe_edit_message(
                query,
                f"✅ *Weekly summary time updated!*\n\n"
                f"Send summary at: {time_value} IST\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_rebalance_time":
            current = getattr(settings, 'paper_trading_position_rebalance_time', '15:30')

            message = f"""
*🔄 POSITION REBALANCE TIME*
━━━━━━━━━━━━━━━━━━━━

*Current:* {current} IST

*What this does:*
Time when the system checks and rebalances portfolio positions.

*Rebalancing includes:*
• Adjusting position sizes based on performance
• Closing underperforming positions
• Opening new positions for winners

━━━━━━━━━━━━━━━━━━━━

Choose rebalance time:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("2:00 PM", callback_data="settings_paper_trading_rebalance_time:14:00")],
                [InlineKeyboardButton("3:00 PM", callback_data="settings_paper_trading_rebalance_time:15:00")],
                [InlineKeyboardButton("3:30 PM ⭐", callback_data="settings_paper_trading_rebalance_time:15:30")],
                [InlineKeyboardButton("4:00 PM", callback_data="settings_paper_trading_rebalance_time:16:00")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_rebalance_time:"):
            time_value = data.split(":")[1] + ":" + data.split(":")[2]

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_position_rebalance_time=time_value)

            await safe_edit_message(
                query,
                f"✅ *Rebalance time updated!*\n\n"
                f"Rebalance at: {time_value} IST\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_tolerance":
            current = getattr(settings, 'paper_trading_entry_price_tolerance_pct', 3.0)

            message = f"""
*🎯 ENTRY PRICE TOLERANCE*
━━━━━━━━━━━━━━━━━━━━

*Current:* {current}%

*What this is:*
Maximum price slippage allowed when executing buy orders.

*How it works:*
• If signal price is ₹100
• Tolerance 2% = Buy if price ≤ ₹102
• Tolerance 5% = Buy if price ≤ ₹105

*Guidelines:*
• **1-2%**: Tight (may miss opportunities)
• **2-5%**: Balanced (recommended)
• **5-10%**: Loose (easier execution)

━━━━━━━━━━━━━━━━━━━━

Choose price tolerance:
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("1.0% (Tight)", callback_data="settings_paper_trading_tolerance:1.0")],
                [InlineKeyboardButton("2.0% (Conservative)", callback_data="settings_paper_trading_tolerance:2.0")],
                [InlineKeyboardButton("3.0% (Recommended)", callback_data="settings_paper_trading_tolerance:3.0")],
                [InlineKeyboardButton("5.0% (Balanced)", callback_data="settings_paper_trading_tolerance:5.0")],
                [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data.startswith("settings_paper_trading_tolerance:"):
            value = float(data.split(":")[1])

            with get_db_context() as db:
                update_user_settings(db, user_id, paper_trading_entry_price_tolerance_pct=value)

            await safe_edit_message(
                query,
                f"✅ *Price tolerance updated!*\n\n"
                f"Entry tolerance: {value}%\n\n"
                f"Use `/settings` to see all your settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        elif data == "settings_paper_trading_reset":
            message = """
*🔄 RESET PAPER TRADING SETTINGS*
━━━━━━━━━━━━━━━━━━━━

*This will reset ALL paper trading settings to defaults:*

• Enable Paper Trading: ✅ ON
• Default Capital: ₹5,00,000
• Max Positions: 15
• Risk per Trade: 1.0%
• Monitor Interval: 5 minutes
• Max Position Size: 20%
• Buy Execution: 09:20 IST
• Daily Summary: 18:00 IST
• Weekly Summary: 18:00 IST
• Rebalance: 15:30 IST
• Price Tolerance: 3.0%

━━━━━━━━━━━━━━━━━━━━

Are you sure you want to reset?
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Reset All", callback_data="settings_paper_trading_reset:confirm")],
                [InlineKeyboardButton("❌ Cancel", callback_data="settings_paper_trading")]
            ])

            await safe_edit_message(query, message, reply_markup=keyboard)

        elif data == "settings_paper_trading_reset:confirm":
            # Reset all paper trading settings to defaults
            with get_db_context() as db:
                update_user_settings(db, user_id,
                    paper_trading_enabled=True,
                    paper_trading_default_capital=500000.0,
                    paper_trading_max_positions=15,
                    paper_trading_risk_percentage=1.0,
                    paper_trading_monitor_interval_seconds=300,
                    paper_trading_max_position_size_pct=20.0,
                    paper_trading_buy_execution_time='09:15',
                    paper_trading_daily_summary_time='18:00',
                    paper_trading_weekly_summary_time='18:00',
                    paper_trading_position_rebalance_time='15:30',
                    paper_trading_entry_price_tolerance_pct=3.0
                )

            await safe_edit_message(
                query,
                "✅ *All paper trading settings reset to defaults!*\n\n"
                "Use `/settings` to see your updated settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="settings_paper_trading")]
                ])
            )

        # =====================================================================
        # INVESTMENT HORIZON SELECTION
        # =====================================================================
        elif data == "settings_horizon":
            current = getattr(settings, 'investment_horizon', '3months') or '3months'
            
            message = """
*📅 SELECT INVESTMENT PERIOD*
━━━━━━━━━━━━━━━━━━━━

*How long do you plan to hold investments?*

This affects:
• Target price calculations
• Risk assessments
• Expected timeline estimates
• Trading recommendations

━━━━━━━━━━━━━━━━━━━━

⭐ = Recommended for beginners
🔴 = Higher risk | 🟢 = Lower risk

*Tap an option to see detailed guide:*
"""
            keyboard = create_horizon_keyboard(current)
            await safe_edit_message(query, message, reply_markup=keyboard)
        
        elif data.startswith("settings_horizon:"):
            horizon = data.split(":")[1]
            
            if horizon.startswith("info_"):
                # Show detailed guide for this horizon
                horizon_key = horizon.replace("info_", "")
                info = HORIZON_INFO.get(horizon_key, HORIZON_INFO['3months'])
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        f"✅ Select {info['display']}", 
                        callback_data=f"settings_horizon:select_{horizon_key}"
                    )],
                    [InlineKeyboardButton("◀️ Back to Options", callback_data="settings_horizon")]
                ])
                
                await safe_edit_message(
                    query,
                    info['guide'],
                    reply_markup=keyboard
                )
            
            elif horizon.startswith("select_"):
                # Actually set the horizon
                horizon_key = horizon.replace("select_", "")
                if horizon_key in HORIZON_INFO:
                    update_user_settings(db, user_id, investment_horizon=horizon_key)
                    info = HORIZON_INFO[horizon_key]
                    
                    await safe_edit_message(
                        query,
                        f"✅ *Investment period set to {info['display']}!*\n\n"
                        f"{info['emoji']} *{info['name']}*\n"
                        f"Risk Level: {info['risk_emoji']} {info['risk']}\n\n"
                        f"_{info['description']}_\n\n"
                        f"Use /settings to make more changes."
                    )
                    logger.info(f"User {user_id} changed horizon to {horizon_key}")
            
            elif horizon in HORIZON_INFO:
                # Direct selection (from keyboard)
                update_user_settings(db, user_id, investment_horizon=horizon)
                info = HORIZON_INFO[horizon]
                
                await safe_edit_message(
                    query,
                    f"✅ *Investment period set to {info['display']}!*\n\n"
                    f"{info['emoji']} *{info['name']}*\n"
                    f"Risk Level: {info['risk_emoji']} {info['risk']}\n\n"
                    f"_{info['description']}_\n\n"
                    f"Use /settings to make more changes."
                )
                logger.info(f"User {user_id} changed horizon to {horizon}")
        
        # =====================================================================
        # RISK MODE SELECTION
        # =====================================================================
        elif data == "settings_risk_mode":
            current = settings.risk_mode or 'balanced'
            
            message = """
*🎯 SELECT RISK MODE*
━━━━━━━━━━━━━━━━━━━━

*How much risk are you comfortable with?*

This affects:
• Filter strictness
• Signal sensitivity  
• Position sizing recommendations
• Number of opportunities shown

━━━━━━━━━━━━━━━━━━━━

*Tap an option to see detailed guide:*
"""
            keyboard = create_risk_mode_keyboard(current)
            await safe_edit_message(query, message, reply_markup=keyboard)
        
        elif data.startswith("settings_risk_mode:"):
            mode = data.split(":")[1]
            
            if mode.startswith("info_"):
                # Show detailed guide
                mode_key = mode.replace("info_", "")
                info = RISK_MODE_INFO.get(mode_key, RISK_MODE_INFO['balanced'])
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        f"✅ Select {info['name']}", 
                        callback_data=f"settings_risk_mode:select_{mode_key}"
                    )],
                    [InlineKeyboardButton("◀️ Back to Options", callback_data="settings_risk_mode")]
                ])
                
                await safe_edit_message(
                    query,
                    info['guide'],
                    reply_markup=keyboard
                )
            
            elif mode.startswith("select_"):
                # Actually set the mode
                mode_key = mode.replace("select_", "")
                if mode_key in RISK_MODE_INFO:
                    update_user_settings(db, user_id, risk_mode=mode_key)
                    info = RISK_MODE_INFO[mode_key]
                    
                    await safe_edit_message(
                        query,
                        f"✅ *Risk mode set to {info['name']}!*\n\n"
                        f"{info['emoji']} {info['description']}\n\n"
                        f"Use /settings to make more changes."
                    )
                    logger.info(f"User {user_id} changed risk mode to {mode_key}")
            
            elif mode in RISK_MODE_INFO:
                # Direct selection
                update_user_settings(db, user_id, risk_mode=mode)
                info = RISK_MODE_INFO[mode]
                
                await safe_edit_message(
                    query,
                    f"✅ *Risk mode set to {info['name']}!*\n\n"
                    f"{info['emoji']} {info['description']}\n\n"
                    f"Use /settings to make more changes."
                )
                logger.info(f"User {user_id} changed risk mode to {mode}")
        
        # =====================================================================
        # CAPITAL SELECTION
        # =====================================================================
        elif data == "settings_capital":
            keyboard = create_capital_preset_keyboard()
            
            await safe_edit_message(
                query,
                CAPITAL_GUIDE,
                reply_markup=keyboard
            )
        
        elif data.startswith("settings_capital:"):
            value = data.split(":")[1]
            
            if value == "custom":
                context.user_data['awaiting_capital_input'] = True
                
                await safe_edit_message(
                    query,
                    "*💰 ENTER CUSTOM AMOUNT*\n\n"
                    "Type your investment capital amount:\n\n"
                    "Examples:\n"
                    "• `75000` for Rs 75,000\n"
                    "• `150000` for Rs 1,50,000\n"
                    "• `300000` for Rs 3,00,000\n\n"
                    "Minimum: Rs 10,000\n"
                    "Maximum: Rs 10,00,00,000\n\n"
                    "_Just type the number and send_",
                    parse_mode='Markdown'
                )
            elif value == "guide":
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Presets", callback_data="settings_capital")]
                ])
                
                await safe_edit_message(
                    query,
                    """
*💰 CAPITAL GUIDE - WHY IT MATTERS*
━━━━━━━━━━━━━━━━━━━━

*What is this setting?*
This is the amount you plan to invest. We use it to calculate safe position sizes.

*The 1% Rule (Professional Risk Management)*
Never risk more than 1-2% of your total capital on a single trade.

*Example:*
Capital: Rs 1,00,000
Maximum risk per trade: Rs 1,000-2,000

If a stock has 5% stop loss:
Position size = Rs 1,000 ÷ 5% = Rs 20,000

This means you'd buy Rs 20,000 worth of that stock.

*Why this protects you:*
Even if you have 10 losing trades in a row (unlikely), you'd only lose 10-20% of capital - enough to recover!

*Tips:*
✅ Only invest money you won't need soon
✅ Start with a smaller amount if new
✅ Never borrow to invest
✅ Update this as your capital grows
""",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                try:
                    capital = float(value)
                    update_user_settings(db, user_id, default_capital=capital)
                    
                    await safe_edit_message(
                        query,
                        f"✅ *Capital set to Rs {capital:,.0f}*\n\n"
                        f"Position sizes will now be calculated based on this amount.\n\n"
                        f"*Quick math:*\n"
                        f"• 1% risk = Rs {capital * 0.01:,.0f} max loss per trade\n"
                        f"• 2% risk = Rs {capital * 0.02:,.0f} max loss per trade\n\n"
                        f"Use /settings to make more changes."
                    )
                    logger.info(f"User {user_id} changed capital to {capital}")
                except ValueError:
                    pass
        
        # =====================================================================
        # LEGACY REPORT STYLE CALLBACKS (Deprecated - handled gracefully)
        # =====================================================================
        elif data == "settings_report_style" or data.startswith("settings_report_style:"):
            # Report style is now unified - all users get the same comprehensive format
            await safe_edit_message(
                query,
                "ℹ️ *Report Style Update*\n\n"
                "We now use a unified comprehensive analysis format for all users.\n"
                "This format includes all the information you need:\n\n"
                "• Clear BUY/HOLD/AVOID recommendations\n"
                "• Technical indicators (RSI, MACD, ADX)\n"
                "• Safety ratings and risk assessment\n"
                "• Target prices and stop losses\n"
                "• Investment guidance\n\n"
                "All analysis now includes everything!\n\n"
                "Use /settings to view your other settings.",
                parse_mode='Markdown'
            )
            logger.info(f"User {user_id} accessed deprecated report style setting")
        
        # =====================================================================
        # VIEW ALL SETTINGS
        # =====================================================================
        elif data == "settings_show":
            horizon_key = getattr(settings, 'investment_horizon', '3months') or '3months'
            horizon = HORIZON_INFO.get(horizon_key, HORIZON_INFO['3months'])
            mode_key = settings.risk_mode or 'balanced'
            mode = RISK_MODE_INFO.get(mode_key, RISK_MODE_INFO['balanced'])
            
            daily_buy_enabled = getattr(settings, 'daily_buy_alerts_enabled', False) or False
            daily_buy_alert_time = getattr(settings, 'daily_buy_alert_time', '09:00') or '09:00'
            
            message = f"""
*📋 ALL YOUR SETTINGS*
━━━━━━━━━━━━━━━━━━━━

*📅 INVESTMENT PERIOD*
   {horizon['emoji']} {horizon['display']} ({horizon['name']})
   Risk: {horizon['risk_emoji']} {horizon['risk']}
   _{horizon['description']}_

*🎯 RISK MODE*
   {mode['emoji']} {mode['name']}
   _{mode['description']}_

*📊 ANALYSIS TIMEFRAME*
   {settings.timeframe.upper() if settings.timeframe else 'MEDIUM'}

*💰 INVESTMENT CAPITAL*
   Rs {(settings.default_capital or 100000):,.0f}
   (1% risk = Rs {(settings.default_capital or 100000) * 0.01:,.0f} per trade)

*🔔 NOTIFICATIONS*
   {'Enabled' if settings.notifications_enabled else 'Disabled'}

*📈 DAILY BUY ALERTS*
   {'✅ Enabled' if daily_buy_enabled else '❌ Disabled'}
   {f'Alert Time: {daily_buy_alert_time} ({settings.timezone})' if daily_buy_enabled else ''}

*🌍 TIMEZONE*
   {settings.timezone}

━━━━━━━━━━━━━━━━━━━━
"""
            
            keyboard = create_settings_menu_keyboard(daily_buy_enabled)
            await safe_edit_message(query, message, reply_markup=keyboard)
        
        # =====================================================================
        # RESET CONFIRMATION
        # =====================================================================
        elif data == "confirm_reset:settings":
            update_user_settings(
                db,
                user_id,
                risk_mode='balanced',
                timeframe='medium',
                investment_horizon='3months',
                default_capital=100000.0
            )
            
            await safe_edit_message(
                query,
                "✅ *Settings reset to defaults!*\n\n"
                "• Investment Period: 3 Months\n"
                "• Risk Mode: Balanced\n"
                "• Capital: Rs 1,00,000\n\n"
                "Use /settings to customize."
            )
            logger.info(f"User {user_id} reset settings")
        
        elif data == "cancel_reset:settings":
            await safe_edit_message(
                query,
                "❌ *Reset cancelled*\n\n"
                "Your settings remain unchanged.\n"
                "Use /settings to view or change settings."
            )


async def handle_alert_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle custom alert time input from user."""
    if not context.user_data.get('awaiting_alert_time_input'):
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Validate time format HH:MM
    try:
        hour, minute = map(int, text.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid hour or minute")
        
        time_str = f"{hour:02d}:{minute:02d}"
        
        with get_db_context() as db:
            settings = get_user_settings(db, user_id)
            user_timezone = getattr(settings, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
            update_user_settings(db, user_id, daily_buy_alert_time=time_str)
        
        context.user_data.pop('awaiting_alert_time_input', None)
        
        await update.message.reply_text(
            f"✅ *Alert time set to {time_str}*\n\n"
            f"You'll receive daily BUY alerts at {time_str} ({user_timezone}).\n\n"
            f"Use /settings to make more changes.",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} set daily BUY alert time to {time_str}")
        
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "⚠️ *Invalid time format*\n\n"
            "Please enter time in HH:MM format:\n\n"
            "Examples:\n"
            "• `09:00` for 9:00 AM\n"
            "• `14:30` for 2:30 PM\n"
            "• `18:00` for 6:00 PM\n\n"
            "_Hour: 00-23, Minute: 00-59_",
            parse_mode='Markdown'
        )


async def handle_capital_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle custom capital input from user."""
    if not context.user_data.get('awaiting_capital_input'):
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Clean the input
    text = text.replace(',', '').replace('₹', '').replace('Rs', '').replace('rs', '').replace('RS', '').strip()
    
    try:
        capital = float(text)
        
        if capital < 10000:
            await update.message.reply_text(
                "⚠️ *Minimum capital is Rs 10,000*\n\n"
                "Please enter a higher amount.\n"
                "_Tip: Start with at least Rs 25,000 for meaningful diversification._",
                parse_mode='Markdown'
            )
            return
        
        if capital > 100000000:
            await update.message.reply_text(
                "⚠️ *Maximum capital is Rs 10 crore*\n\n"
                "Please enter a lower amount.",
                parse_mode='Markdown'
            )
            return
        
        with get_db_context() as db:
            update_user_settings(db, user_id, default_capital=capital)
        
        context.user_data.pop('awaiting_capital_input', None)
        
        await update.message.reply_text(
            f"✅ *Capital set to Rs {capital:,.0f}*\n\n"
            f"*Quick reference:*\n"
            f"• 1% risk per trade = Rs {capital * 0.01:,.0f}\n"
            f"• 2% risk per trade = Rs {capital * 0.02:,.0f}\n"
            f"• 5% of capital = Rs {capital * 0.05:,.0f}\n\n"
            f"Use /settings to make more changes.",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} changed capital to {capital}")
        
    except ValueError:
        await update.message.reply_text(
            "⚠️ *Please enter a valid number*\n\n"
            "Examples:\n"
            "• `100000` for Rs 1,00,000\n"
            "• `250000` for Rs 2,50,000\n\n"
            "_Just type the number without commas or symbols._",
            parse_mode='Markdown'
        )
