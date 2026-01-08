"""
Keyboard Builders for Telegram Bot
Creates inline keyboards for interactive bot navigation
"""

from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from src.bot.config import (
    MAIN_MENU_BUTTONS, ANALYSIS_ACTION_BUTTONS, WATCHLIST_MENU_BUTTONS,
    ALERT_MENU_BUTTONS, PORTFOLIO_MENU_BUTTONS, SETTINGS_MENU_BUTTONS
)


def create_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Create main menu keyboard with persistent buttons
    
    Returns:
        ReplyKeyboardMarkup with main menu buttons
    """
    keyboard = [[KeyboardButton(text) for text in row] for row in MAIN_MENU_BUTTONS]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def create_analysis_action_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for actions after analysis
    
    Args:
        symbol: Stock symbol
    
    Returns:
        InlineKeyboardMarkup with action buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("⭐ Add to Watchlist", callback_data=f"watchlist_add:{symbol}"),
            InlineKeyboardButton("🔔 Set Alert", callback_data=f"alert_menu:{symbol}"),
        ],
        [
            InlineKeyboardButton("💼 Add to Portfolio", callback_data=f"portfolio_add:{symbol}"),
            InlineKeyboardButton("📊 View Chart", callback_data=f"chart:{symbol}"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Analysis", callback_data=f"analyze:{symbol}"),
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_watchlist_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for watchlist menu
    
    Returns:
        InlineKeyboardMarkup with watchlist options
    """
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Stock", callback_data="watchlist_add_prompt"),
            InlineKeyboardButton("➖ Remove Stock", callback_data="watchlist_remove_prompt"),
        ],
        [
            InlineKeyboardButton("📋 View Watchlist", callback_data="watchlist_show"),
            InlineKeyboardButton("📊 Analyze All", callback_data="watchlist_analyze"),
        ],
        [
            InlineKeyboardButton("🗑️ Clear Watchlist", callback_data="watchlist_clear_confirm"),
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_watchlist_item_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for individual watchlist item
    
    Args:
        symbol: Stock symbol
    
    Returns:
        InlineKeyboardMarkup with item actions
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Analyze", callback_data=f"analyze:{symbol}"),
            InlineKeyboardButton("🔔 Set Alert", callback_data=f"alert_menu:{symbol}"),
        ],
        [
            InlineKeyboardButton("➖ Remove", callback_data=f"watchlist_remove:{symbol}"),
            InlineKeyboardButton("◀️ Back", callback_data="watchlist_show"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_alert_type_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for selecting alert type
    
    Args:
        symbol: Stock symbol
    
    Returns:
        InlineKeyboardMarkup with alert type options
    """
    keyboard = [
        [
            InlineKeyboardButton("💰 Price Alert", callback_data=f"alert_price:{symbol}"),
            InlineKeyboardButton("📈 RSI Alert", callback_data=f"alert_rsi:{symbol}"),
        ],
        [
            InlineKeyboardButton("🔔 Signal Change", callback_data=f"alert_signal:{symbol}"),
            InlineKeyboardButton("📊 Breakout Alert", callback_data=f"alert_breakout:{symbol}"),
        ],
        [
            InlineKeyboardButton("⚡ Divergence Alert", callback_data=f"alert_divergence:{symbol}"),
        ],
        [
            InlineKeyboardButton("◀️ Back", callback_data=f"analyze:{symbol}"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_alert_list_keyboard(alerts: List[dict]) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for alert list with actions
    
    Args:
        alerts: List of alert dictionaries
    
    Returns:
        InlineKeyboardMarkup with alert management buttons
    """
    keyboard = []
    
    # Add buttons for each alert (max 5)
    for alert in alerts[:5]:
        alert_id = alert['id']
        symbol = alert['symbol']
        alert_type = alert['alert_type']
        is_active = alert['is_active']
        
        status = "✅" if is_active else "⏸️"
        label = f"{status} {symbol} - {alert_type}"
        
        keyboard.append([
            InlineKeyboardButton(label, callback_data=f"alert_view:{alert_id}"),
        ])
    
    # Add general actions
    keyboard.append([
        InlineKeyboardButton("➕ Add New Alert", callback_data="alert_add_prompt"),
        InlineKeyboardButton("🗑️ Clear All", callback_data="alert_clear_all_confirm"),
    ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_alert_action_keyboard(alert_id: int) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for alert actions
    
    Args:
        alert_id: Alert ID
    
    Returns:
        InlineKeyboardMarkup with alert action buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("⏸️ Disable", callback_data=f"alert_disable:{alert_id}"),
            InlineKeyboardButton("▶️ Enable", callback_data=f"alert_enable:{alert_id}"),
        ],
        [
            InlineKeyboardButton("🗑️ Delete", callback_data=f"alert_delete:{alert_id}"),
            InlineKeyboardButton("◀️ Back to List", callback_data="alert_list"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_portfolio_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for portfolio menu
    
    Returns:
        InlineKeyboardMarkup with portfolio options
    """
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Position", callback_data="portfolio_add_prompt"),
            InlineKeyboardButton("➖ Remove Position", callback_data="portfolio_remove_prompt"),
        ],
        [
            InlineKeyboardButton("📊 Performance", callback_data="portfolio_performance"),
            InlineKeyboardButton("📋 View Portfolio", callback_data="portfolio_show"),
        ],
        [
            InlineKeyboardButton("📈 Charts", callback_data="portfolio_charts"),
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_portfolio_item_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for portfolio item actions
    
    Args:
        symbol: Stock symbol
    
    Returns:
        InlineKeyboardMarkup with item action buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Analyze", callback_data=f"analyze:{symbol}"),
            InlineKeyboardButton("➕ Add Shares", callback_data=f"portfolio_add_shares:{symbol}"),
        ],
        [
            InlineKeyboardButton("➖ Remove Position", callback_data=f"portfolio_remove:{symbol}"),
            InlineKeyboardButton("◀️ Back", callback_data="portfolio_show"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_settings_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for settings menu
    
    Returns:
        InlineKeyboardMarkup with settings options
    """
    keyboard = [
        [
            InlineKeyboardButton("⚙️ Risk Mode", callback_data="settings_risk_mode"),
            InlineKeyboardButton("⏱️ Timeframe", callback_data="settings_timeframe"),
        ],
        [
            InlineKeyboardButton("💰 Set Capital", callback_data="settings_capital"),
            InlineKeyboardButton("🌍 Timezone", callback_data="settings_timezone"),
        ],
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications"),
            InlineKeyboardButton("📋 View Settings", callback_data="settings_show"),
        ],
        [
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_risk_mode_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for risk mode selection
    
    Args:
        current_mode: Current risk mode
    
    Returns:
        InlineKeyboardMarkup with risk mode options
    """
    modes = ['conservative', 'balanced', 'aggressive']
    keyboard = []
    
    for mode in modes:
        is_current = "✅ " if mode == current_mode else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{is_current}{mode.title()}",
                callback_data=f"settings_risk_mode:{mode}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ Back to Settings", callback_data="settings_menu"),
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_timeframe_keyboard(current_timeframe: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for timeframe selection
    
    Args:
        current_timeframe: Current timeframe
    
    Returns:
        InlineKeyboardMarkup with timeframe options
    """
    timeframes = [
        ('short', 'Short-term (1-4 weeks)'),
        ('medium', 'Medium-term (1-3 months)'),
    ]
    keyboard = []
    
    for tf, label in timeframes:
        is_current = "✅ " if tf == current_timeframe else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{is_current}{label}",
                callback_data=f"settings_timeframe:{tf}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ Back to Settings", callback_data="settings_menu"),
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_confirmation_keyboard(action: str, data: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for confirmation dialogs
    
    Args:
        action: Action to confirm
        data: Data for the action
    
    Returns:
        InlineKeyboardMarkup with yes/no buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm:{action}:{data}"),
            InlineKeyboardButton("❌ No", callback_data=f"cancel:{action}:{data}"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_comparison_keyboard(symbols: List[str]) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for stock comparison results
    
    Args:
        symbols: List of stock symbols
    
    Returns:
        InlineKeyboardMarkup with action buttons
    """
    keyboard = []
    
    # Add analyze button for each stock (max 5)
    for symbol in symbols[:5]:
        keyboard.append([
            InlineKeyboardButton(f"📊 Analyze {symbol}", callback_data=f"analyze:{symbol}"),
        ])
    
    # Add comparison options
    keyboard.append([
        InlineKeyboardButton("🔄 Compare Again", callback_data="compare_prompt"),
        InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_schedule_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for scheduled reports menu
    
    Returns:
        InlineKeyboardMarkup with schedule options
    """
    keyboard = [
        [
            InlineKeyboardButton("📅 Daily Report", callback_data="schedule_daily"),
            InlineKeyboardButton("📅 Weekly Report", callback_data="schedule_weekly"),
        ],
        [
            InlineKeyboardButton("📋 View Schedules", callback_data="schedule_list"),
            InlineKeyboardButton("🗑️ Clear All", callback_data="schedule_clear_all"),
        ],
        [
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for pagination
    
    Args:
        current_page: Current page number (0-indexed)
        total_pages: Total number of pages
        callback_prefix: Prefix for callback data
    
    Returns:
        InlineKeyboardMarkup with pagination buttons
    """
    keyboard = []
    
    nav_buttons = []
    
    # Previous button
    if current_page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Previous", callback_data=f"{callback_prefix}:page:{current_page-1}")
        )
    
    # Page indicator
    nav_buttons.append(
        InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="noop")
    )
    
    # Next button
    if current_page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("Next ▶️", callback_data=f"{callback_prefix}:page:{current_page+1}")
        )
    
    keyboard.append(nav_buttons)
    
    # Back button
    keyboard.append([
        InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_back_button(callback_data: str = "main_menu", label: str = "◀️ Back to Menu") -> InlineKeyboardMarkup:
    """
    Create simple keyboard with just a back button
    
    Args:
        callback_data: Callback data for back button
        label: Button label
    
    Returns:
        InlineKeyboardMarkup with back button
    """
    keyboard = [[InlineKeyboardButton(label, callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)


def remove_keyboard() -> dict:
    """
    Create reply markup to remove keyboard
    
    Returns:
        Dictionary for ReplyKeyboardRemove
    """
    return {"remove_keyboard": True}
