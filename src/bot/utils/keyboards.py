"""
Keyboard Builders for Telegram Bot
Creates inline keyboards for interactive bot navigation
"""

from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from src.bot.config import (
    MAIN_MENU_BUTTONS, ANALYSIS_ACTION_BUTTONS, WATCHLIST_MENU_BUTTONS,
    ALERT_MENU_BUTTONS, PORTFOLIO_MENU_BUTTONS, SETTINGS_MENU_BUTTONS,
    PAPER_TRADING_MENU_BUTTONS
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


def create_full_report_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard with button to get full report
    
    Args:
        symbol: Stock symbol
    
    Returns:
        InlineKeyboardMarkup with "Get Full Report" button
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "📊 Get Full Report",
                callback_data=f"analyze_full:{symbol}"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


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
            InlineKeyboardButton("📈 Paper Trade This", callback_data=f"papertrade_stock:{symbol}"),
            InlineKeyboardButton("💰 Position Sizing", callback_data=f"position_sizing:{symbol}"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Analysis", callback_data=f"analyze:{symbol}"),
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_watchlist_menu_keyboard(symbols: List[str] = None) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for watchlist menu
    
    Args:
        symbols: Optional list of stock symbols to show as buttons
    
    Returns:
        InlineKeyboardMarkup with watchlist options
    """
    keyboard = []
    
    # If symbols provided, create buttons for each symbol
    if symbols:
        # Add buttons for each symbol (2 per row)
        for i in range(0, len(symbols), 2):
            row = []
            row.append(InlineKeyboardButton(
                f"📊 {symbols[i]}", 
                callback_data=f"analyze:{symbols[i]}"
            ))
            if i + 1 < len(symbols):
                row.append(InlineKeyboardButton(
                    f"📊 {symbols[i + 1]}", 
                    callback_data=f"analyze:{symbols[i + 1]}"
                ))
            keyboard.append(row)
        
        # Add separator row
        keyboard.append([
            InlineKeyboardButton("📊 Analyze All", callback_data="watchlist_analyze"),
        ])
    
    # Add action buttons
    keyboard.extend([
        [
            InlineKeyboardButton("➕ Add Stock", callback_data="watchlist_add_prompt"),
            InlineKeyboardButton("➖ Remove Stock", callback_data="watchlist_remove_prompt"),
        ],
        [
            InlineKeyboardButton("📈 Paper Trade All", callback_data="papertrade_watchlist"),
            InlineKeyboardButton("🗑️ Clear Watchlist", callback_data="watchlist_clear_confirm"),
        ],
        [
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
        ],
    ])
    
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


def create_alert_list_keyboard(alerts: List) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for alert list with actions
    
    Args:
        alerts: List of alert dictionaries or Alert model objects
    
    Returns:
        InlineKeyboardMarkup with alert management buttons
    """
    keyboard = []
    
    # Add buttons for each alert (max 5)
    for alert in alerts[:5]:
        # Handle both Alert model objects and dictionaries
        if hasattr(alert, 'id'):
            # Alert model object
            alert_id = alert.id
            symbol = alert.symbol
            alert_type = alert.alert_type
            is_active = alert.is_active
        else:
            # Dictionary
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


def create_settings_menu_keyboard(daily_buy_alerts_enabled: bool = False) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for settings menu with clear labels.
    
    Args:
        daily_buy_alerts_enabled: Whether daily BUY alerts are enabled
    
    Returns:
        InlineKeyboardMarkup with settings options
    """
    alert_status = "✅ Enabled" if daily_buy_alerts_enabled else "❌ Disabled"
    keyboard = [
        [
            InlineKeyboardButton(
                "📅 How Long to Hold? (Investment Period)", 
                callback_data="settings_horizon"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎯 Risk Comfort Level", 
                callback_data="settings_risk_mode"
            ),
        ],
        [
            InlineKeyboardButton(
                "💰 My Investment Amount", 
                callback_data="settings_capital"
            ),
        ],
        [
            InlineKeyboardButton(
                f"🔔 Daily BUY Alerts ({alert_status})",
                callback_data="settings_daily_buy_alerts"
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 Paper Trading Settings",
                callback_data="settings_paper_trading"
            ),
        ],
        [
            InlineKeyboardButton(
                "📋 View All My Settings",
                callback_data="settings_show"
            ),
        ],
        [
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_risk_mode_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for risk mode selection with info buttons.
    
    Args:
        current_mode: Current risk mode
    
    Returns:
        InlineKeyboardMarkup with risk mode options and info buttons
    """
    modes = [
        ('conservative', '🛡️ Conservative', 'Safety first'),
        ('balanced', '⚖️ Balanced ⭐', 'Recommended'),
        ('aggressive', '🚀 Aggressive', 'High risk'),
    ]
    keyboard = []
    
    for mode_key, label, desc in modes:
        is_current = "✅ " if mode_key == current_mode else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{is_current}{label}",
                callback_data=f"settings_risk_mode:{mode_key}"
            ),
            InlineKeyboardButton(
                "ℹ️ Guide",
                callback_data=f"settings_risk_mode:info_{mode_key}"
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


def create_horizon_keyboard(current_horizon: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for investment horizon selection with info buttons.
    
    Args:
        current_horizon: Current investment horizon
    
    Returns:
        InlineKeyboardMarkup with horizon options and info buttons
    """
    horizons = [
        ('1week', '⚡ 1 Week', '🔴', 'Quick Trade'),
        ('2weeks', '🔄 2 Weeks', '🟠', 'Swing Trade'),
        ('1month', '📅 1 Month', '🟡', 'Short'),
        ('3months', '📊 3 Months ⭐', '🟢', 'Recommended'),
        ('6months', '🎯 6 Months ⭐', '🟢', 'Beginner'),
        ('1year', '💎 1 Year', '🟢', 'Long-Term'),
    ]
    keyboard = []
    
    for horizon_key, label, risk_emoji, desc in horizons:
        is_current = "✅ " if horizon_key == current_horizon else ""
        # Each row has: Select button + Info button
        keyboard.append([
            InlineKeyboardButton(
                f"{is_current}{label} {risk_emoji}",
                callback_data=f"settings_horizon:{horizon_key}"
            ),
            InlineKeyboardButton(
                "ℹ️ Guide",
                callback_data=f"settings_horizon:info_{horizon_key}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ Back to Settings", callback_data="settings_menu"),
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_capital_preset_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard with capital presets and guide.
    
    Returns:
        InlineKeyboardMarkup with preset capital options
    """
    keyboard = [
        [
            InlineKeyboardButton("💡 How Capital Works", callback_data="settings_capital:guide"),
        ],
        [
            InlineKeyboardButton("Rs 25,000", callback_data="settings_capital:25000"),
            InlineKeyboardButton("Rs 50,000", callback_data="settings_capital:50000"),
        ],
        [
            InlineKeyboardButton("Rs 1,00,000 ⭐", callback_data="settings_capital:100000"),
            InlineKeyboardButton("Rs 2,50,000", callback_data="settings_capital:250000"),
        ],
        [
            InlineKeyboardButton("Rs 5,00,000", callback_data="settings_capital:500000"),
            InlineKeyboardButton("Rs 10,00,000", callback_data="settings_capital:1000000"),
        ],
        [
            InlineKeyboardButton("✏️ Enter Custom Amount", callback_data="settings_capital:custom"),
        ],
        [
            InlineKeyboardButton("◀️ Back to Settings", callback_data="settings_menu"),
        ],
    ]
    
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


def create_daily_buy_alerts_keyboard(is_enabled: bool) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for daily BUY alerts subscription
    
    Args:
        is_enabled: Whether alerts are currently enabled
    
    Returns:
        InlineKeyboardMarkup with subscription options
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Enable Daily BUY Alerts" if not is_enabled else "❌ Disable Daily BUY Alerts",
                callback_data="daily_buy_alerts_toggle"
            ),
        ],
    ]
    
    if is_enabled:
        # Time selection buttons (common times)
        keyboard.append([
            InlineKeyboardButton("🕘 09:00", callback_data="daily_buy_alert_time:09:00"),
            InlineKeyboardButton("🕙 10:00", callback_data="daily_buy_alert_time:10:00"),
        ])
        keyboard.append([
            InlineKeyboardButton("🕚 11:00", callback_data="daily_buy_alert_time:11:00"),
            InlineKeyboardButton("🕛 12:00", callback_data="daily_buy_alert_time:12:00"),
        ])
        keyboard.append([
            InlineKeyboardButton("🕐 13:00", callback_data="daily_buy_alert_time:13:00"),
            InlineKeyboardButton("🕑 14:00", callback_data="daily_buy_alert_time:14:00"),
        ])
        keyboard.append([
            InlineKeyboardButton("✏️ Custom Time", callback_data="daily_buy_alert_time:custom"),
        ])
    
    keyboard.append([
        InlineKeyboardButton("ℹ️ About Daily BUY Alerts", callback_data="daily_buy_alerts_info"),
    ])
    keyboard.append([
        InlineKeyboardButton("◀️ Back to Settings", callback_data="settings_menu"),
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


def create_paper_trading_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Create main paper trading menu keyboard
    
    Returns:
        ReplyKeyboardMarkup with paper trading options
    """
    keyboard = [[KeyboardButton(text) for text in row] for row in PAPER_TRADING_MENU_BUTTONS]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def create_paper_trade_stock_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for paper trading a specific stock
    
    Args:
        symbol: Stock symbol
    
    Returns:
        InlineKeyboardMarkup with paper trading options
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Paper Trade This Stock", callback_data=f"papertrade_stock_confirm:{symbol}"),
        ],
        [
            InlineKeyboardButton("📜 Check Trade History", callback_data=f"papertrade_stock_history:{symbol}"),
        ],
        [
            InlineKeyboardButton("📊 View Analysis First", callback_data=f"analyze:{symbol}"),
            InlineKeyboardButton("ℹ️ About Paper Trading", callback_data="papertrade_info"),
        ],
        [
            InlineKeyboardButton("◀️ Back", callback_data=f"analyze:{symbol}"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_paper_trade_buy_signals_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for paper trading all BUY signals
    
    Returns:
        InlineKeyboardMarkup with confirmation options
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Trade All BUY Signals", callback_data="papertrade_buy_signals_confirm"),
        ],
        [
            InlineKeyboardButton("📊 View Signals First", callback_data="papertrade_view_signals"),
            InlineKeyboardButton("ℹ️ About BUY Signals", callback_data="papertrade_buy_signals_info"),
        ],
        [
            InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="papertrade_menu"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_paper_trade_watchlist_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for paper trading all watchlist stocks
    
    Returns:
        InlineKeyboardMarkup with confirmation options
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Trade All Watchlist Stocks", callback_data="papertrade_watchlist_confirm"),
        ],
        [
            InlineKeyboardButton("📋 View Watchlist First", callback_data="watchlist_show"),
            InlineKeyboardButton("ℹ️ About Watchlist Trading", callback_data="papertrade_watchlist_info"),
        ],
        [
            InlineKeyboardButton("◀️ Back to Watchlist", callback_data="watchlist_show"),
        ],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_paper_trading_main_keyboard(session_active: bool = False) -> InlineKeyboardMarkup:
    """
    Create main paper trading menu keyboard (Step 1).

    Args:
        session_active: Whether user has an active paper trading session

    Returns:
        InlineKeyboardMarkup with paper trading options
    """
    start_stop_label = "⏹️ Stop Session" if session_active else "▶️ Start Session"
    start_stop_callback = "papertrade_stop" if session_active else "papertrade_start"

    keyboard = [
        [
            InlineKeyboardButton(start_stop_label, callback_data=start_stop_callback),
        ],
        [
            InlineKeyboardButton("📊 Status Overview", callback_data="papertrade_status_menu"),
            InlineKeyboardButton("📈 Trade Signals", callback_data="papertrade_signals_menu"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="papertrade_settings"),
            InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def create_paper_trading_status_submenu_keyboard() -> InlineKeyboardMarkup:
    """
    Create Status Overview submenu keyboard (Step 2a).

    Returns:
        InlineKeyboardMarkup with status options
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Full Status", callback_data="papertrade_status"),
        ],
        [
            InlineKeyboardButton("📜 Trade History", callback_data="papertrade_history"),
        ],
        [
            InlineKeyboardButton("📈 Performance", callback_data="papertrade_performance"),
        ],
        [
            InlineKeyboardButton("💡 Insights", callback_data="papertrade_insights"),
        ],
        [
            InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="papertrade_main"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def create_paper_trading_signals_submenu_keyboard() -> InlineKeyboardMarkup:
    """
    Create Trade Signals submenu keyboard (Step 2b).

    Returns:
        InlineKeyboardMarkup with signal options
    """
    keyboard = [
        [
            InlineKeyboardButton("📈 Trade All BUY Signals", callback_data="papertrade_buy_signals"),
        ],
        [
            InlineKeyboardButton("⭐ Trade Watchlist", callback_data="papertrade_watchlist"),
        ],
        [
            InlineKeyboardButton("ℹ️ About Signals", callback_data="papertrade_signals_info"),
        ],
        [
            InlineKeyboardButton("◀️ Back to Paper Trading", callback_data="papertrade_main"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def remove_keyboard() -> dict:
    """
    Create reply markup to remove keyboard
    
    Returns:
        Dictionary for ReplyKeyboardRemove
    """
    return {"remove_keyboard": True}


def create_paper_trading_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for paper trading settings menu.

    Returns:
        InlineKeyboardMarkup with paper trading settings options
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 Enable/Disable Paper Trading",
                callback_data="settings_paper_trading_enabled"
            ),
        ],
        [
            InlineKeyboardButton(
                "💰 Default Capital (₹500,000)",
                callback_data="settings_paper_trading_capital"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎯 Max Positions (15)",
                callback_data="settings_paper_trading_max_positions"
            ),
        ],
        [
            InlineKeyboardButton(
                "⚠️ Risk per Trade (1.0%)",
                callback_data="settings_paper_trading_risk"
            ),
        ],
        [
            InlineKeyboardButton(
                "⏱️ Monitor Interval (5 min)",
                callback_data="settings_paper_trading_monitor"
            ),
        ],
        [
            InlineKeyboardButton(
                "📏 Max Position Size (20%)",
                callback_data="settings_paper_trading_max_size"
            ),
        ],
        [
            InlineKeyboardButton(
                "🕘 Buy Execution Time (09:20)",
                callback_data="settings_paper_trading_buy_time"
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 Daily Summary (16:00)",
                callback_data="settings_paper_trading_daily_time"
            ),
        ],
        [
            InlineKeyboardButton(
                "📅 Weekly Summary (18:00)",
                callback_data="settings_paper_trading_weekly_time"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Rebalance Time (11:00)",
                callback_data="settings_paper_trading_rebalance_time"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎯 Price Tolerance (3.0%)",
                callback_data="settings_paper_trading_tolerance"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Reset to Defaults",
                callback_data="settings_paper_trading_reset"
            ),
        ],
        [
            InlineKeyboardButton("◀️ Back to Settings", callback_data="settings_menu"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)
