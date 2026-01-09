"""
Bot Configuration Module
Contains all bot-specific settings and constants
"""

import os
from typing import Dict, Any, Literal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# TELEGRAM BOT SETTINGS
# =============================================================================

# Bot Token from BotFather
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Admin User IDs (comma-separated in .env)
TELEGRAM_ADMIN_IDS_STR = os.getenv('TELEGRAM_ADMIN_IDS', '')
TELEGRAM_ADMIN_IDS = [
    int(uid.strip()) for uid in TELEGRAM_ADMIN_IDS_STR.split(',') 
    if uid.strip().isdigit()
]

# Bot Info
BOT_NAME = os.getenv('BOT_NAME', 'Stock Analyzer Pro Bot')
BOT_VERSION = os.getenv('BOT_VERSION', '1.0.0')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# =============================================================================
# DATABASE SETTINGS
# =============================================================================

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/bot.db')

# =============================================================================
# RATE LIMITING
# =============================================================================

ENABLE_RATE_LIMITING = os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
MAX_REQUESTS_PER_HOUR = int(os.getenv('MAX_REQUESTS_PER_HOUR', '50'))

# Rate limits for specific commands (calls per hour)
RATE_LIMITS: Dict[str, Dict[str, int]] = {
    'analyze': {'max_calls': 10, 'per_minutes': 60},
    'compare': {'max_calls': 5, 'per_minutes': 60},
    'watchlist_analyze': {'max_calls': 3, 'per_minutes': 60},
    'backtest': {'max_calls': 5, 'per_minutes': 1440},  # 5 per day
    'chart': {'max_calls': 15, 'per_minutes': 60},
    'portfolio': {'max_calls': 20, 'per_minutes': 60},
    'global': {'max_calls': MAX_REQUESTS_PER_HOUR, 'per_minutes': 60},
}

# =============================================================================
# ALERT SYSTEM
# =============================================================================

ALERT_CHECK_INTERVAL = int(os.getenv('ALERT_CHECK_INTERVAL', '300'))  # 5 minutes (seconds)
ALERT_CHECK_INTERVAL_MINUTES = ALERT_CHECK_INTERVAL // 60  # Convert to minutes for scheduler
MAX_ALERTS_PER_USER = int(os.getenv('MAX_ALERTS_PER_USER', '20'))
ALERT_COOLDOWN_MINUTES = int(os.getenv('ALERT_COOLDOWN_MINUTES', '60'))  # 1 hour between same alert triggers

# =============================================================================
# CACHE SETTINGS
# =============================================================================

CACHE_EXPIRY_MINUTES = int(os.getenv('CACHE_EXPIRY_MINUTES', '15'))
ENABLE_ANALYSIS_CACHE = os.getenv('ENABLE_ANALYSIS_CACHE', 'true').lower() == 'true'

# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/bot.log')

# =============================================================================
# TIMEZONE
# =============================================================================

DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'Asia/Kolkata')

# =============================================================================
# LIMITS & CONSTRAINTS
# =============================================================================

# Maximum number of stocks that can be compared at once
MAX_COMPARE_STOCKS = 5

# Maximum watchlist size per user
MAX_WATCHLIST_SIZE = 50

# Maximum portfolio positions per user
MAX_PORTFOLIO_POSITIONS = 100

# Maximum scheduled reports per user
MAX_SCHEDULED_REPORTS = 10

# Maximum backtest days
MAX_BACKTEST_DAYS = 365

# Message length limits (Telegram's limit is 4096)
MAX_MESSAGE_LENGTH = 4000

# Currency symbol for display (default: ₹ for Indian Rupee)
# Note: Using 'Rs ' for Windows console compatibility
CURRENCY_SYMBOL = os.getenv('CURRENCY_SYMBOL', 'Rs ')

# Type aliases for settings
RiskMode = Literal['conservative', 'moderate', 'aggressive', 'balanced']
Timeframe = Literal['1d', '1wk', '1mo', 'short', 'medium']

# =============================================================================
# TELEGRAM MESSAGE FORMATTING
# =============================================================================

# Emojis for visual appeal
EMOJI = {
    # Status
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'loading': '⏳',
    
    # Actions
    'analyze': '🔍',
    'chart': '📊',
    'compare': '📈',
    'portfolio': '💼',
    'watchlist': '⭐',
    'alert': '🔔',
    'settings': '⚙️',
    'help': '❓',
    'schedule': '📅',
    'backtest': '🔬',
    
    # Recommendations
    'buy': '🟢',
    'sell': '🔴',
    'hold': '🟡',
    'blocked': '⛔',
    
    # Money
    'money': '💰',
    'profit': '📈',
    'loss': '📉',
    'target': '🎯',
    'stop': '🛡️',
    
    # Trends
    'up': '📈',
    'down': '📉',
    'neutral': '➡️',
    
    # Menu
    'menu': '📋',
    'back': '◀️',
    'forward': '▶️',
    'add': '➕',
    'remove': '➖',
    'edit': '✏️',
    'delete': '🗑️',
    'refresh': '🔄',
}

# =============================================================================
# KEYBOARD BUTTON LABELS
# =============================================================================

MAIN_MENU_BUTTONS = [
    ['📊 Analyze Stock', '📈 Compare Stocks'],
    ['⭐ Watchlist', '🔔 Alerts'],
    ['💼 Portfolio', '📅 Schedule Reports'],
    ['⚙️ Settings', 'ℹ️ Help'],
]

ANALYSIS_ACTION_BUTTONS = [
    ['⭐ Add to Watchlist', '🔔 Set Alert'],
    ['💼 Add to Portfolio', '📊 View Chart'],
    ['🔄 Refresh Analysis', '◀️ Back to Menu'],
]

WATCHLIST_MENU_BUTTONS = [
    ['➕ Add Stock', '➖ Remove Stock'],
    ['📋 View Watchlist', '📊 Analyze All'],
    ['🗑️ Clear Watchlist', '◀️ Back to Menu'],
]

ALERT_MENU_BUTTONS = [
    ['📊 Price Alert', '📈 Technical Alert'],
    ['🔔 Signal Alert', '📋 View Alerts'],
    ['◀️ Back to Menu'],
]

PORTFOLIO_MENU_BUTTONS = [
    ['➕ Add Position', '➖ Remove Position'],
    ['📊 Performance', '📋 View Portfolio'],
    ['◀️ Back to Menu'],
]

SETTINGS_MENU_BUTTONS = [
    ['⚙️ Risk Mode', '⏱️ Timeframe'],
    ['💰 Set Capital', '🌍 Timezone'],
    ['◀️ Back to Menu'],
]

# =============================================================================
# WELCOME & HELP MESSAGES
# =============================================================================

WELCOME_MESSAGE = f"""
👋 Welcome to **{BOT_NAME}**!

I'm your professional stock analysis assistant powered by advanced technical indicators and risk management strategies.

**What I can do:**
• 📊 Analyze stocks with 14+ technical indicators
• 📈 Compare multiple stocks side-by-side
• ⭐ Manage your watchlist
• 🔔 Set smart price and technical alerts
• 💼 Track your portfolio performance
• 📅 Schedule daily/weekly reports
• 📊 Generate beautiful charts
• 🔬 Quick backtesting

**Getting Started:**
Try analyzing a stock: `/analyze RELIANCE.NS`
Or use the menu below to explore all features!

💡 **Tip:** Use `/help` anytime to see all available commands.
"""

HELP_MESSAGE = """
**📋 Available Commands:**

**📊 Analysis:**
• `/analyze SYMBOL` - Full technical analysis
• `/quick SYMBOL` - Quick summary
• `/compare SYM1 SYM2 ...` - Compare stocks (max 5)

**⭐ Watchlist:**
• `/watchlist` - View your watchlist
• `/watchlist add SYMBOL` - Add stock
• `/watchlist remove SYMBOL` - Remove stock
• `/watchlist analyze` - Analyze all stocks
• `/watchlist clear` - Clear watchlist

**🔔 Alerts:**
• `/alerts` - View all active alerts
• `/alert SYMBOL` - Create alert for stock
• `/deletealert ID` - Delete specific alert
• `/clearalerts` - Clear all alerts

**💼 Portfolio:**
• `/portfolio` - View portfolio
• `/portfolio add SYMBOL SHARES PRICE` - Add position
• `/portfolio remove SYMBOL` - Remove position

**⚙️ Settings:**
• `/settings` - View/change settings
• `/setmode MODE` - Set risk mode (conservative/moderate/aggressive)
• `/settimeframe TF` - Set timeframe (1d/1wk/1mo)
• `/setcapital AMOUNT` - Set default capital
• `/resetsettings` - Reset to defaults

**🔬 Advanced:**
• `/backtest SYMBOL DAYS` - Backtest strategy (max 90 days)
• `/search KEYWORD` - Search stock ticker
• `/schedule` - Manage scheduled reports

**ℹ️ Help:**
• `/help` - This message
• `/about` - Bot information
• `/menu` - Show main menu

💡 **Tip:** Most commands also have interactive buttons!
"""

ABOUT_MESSAGE = f"""
**{BOT_NAME}**
Version: {BOT_VERSION}

**🔬 Technical Indicators:**
• Trend: EMAs (9/21/50/100/200), ADX
• Momentum: RSI, MACD, Stochastic
• Volatility: ATR, Bollinger Bands
• Volume: OBV, Volume Ratio
• Support/Resistance + Fibonacci

**🎯 Risk Management:**
• 3 Risk Modes (Conservative/Balanced/Aggressive)
• Professional position sizing (1% rule)
• Smart stop loss & targets
• Risk/Reward validation
• Trailing stop strategies

**📊 Features:**
• Real-time analysis
• Multi-timeframe support
• Advanced alert system
• Portfolio tracking
• Chart generation
• Backtesting

**⚠️ Disclaimer:**
This bot is for educational purposes only. Always do your own research and consult a financial advisor before making investment decisions.

**Data Source:** Yahoo Finance
**Built with:** Python, python-telegram-bot, TA-Lib
"""

# =============================================================================
# ERROR MESSAGES
# =============================================================================

ERROR_MESSAGES = {
    'invalid_symbol': '❌ Invalid stock symbol. Please use format: RELIANCE.NS (NSE) or RELIANCE.BO (BSE)',
    'no_data': '❌ No data available for this symbol. Please check the ticker.',
    'analysis_failed': '❌ Analysis failed. Please try again later.',
    'rate_limit': '⚠️ Rate limit exceeded. Please try again in {minutes} minutes.',
    'unauthorized': '⛔ You are not authorized to use this bot.',
    'invalid_command': '❌ Invalid command format. Use /help for usage instructions.',
    'database_error': '❌ Database error occurred. Please try again later.',
    'watchlist_full': f'⚠️ Watchlist is full (max {MAX_WATCHLIST_SIZE} stocks). Remove some stocks first.',
    'portfolio_full': f'⚠️ Portfolio is full (max {MAX_PORTFOLIO_POSITIONS} positions).',
    'alert_limit': f'⚠️ Maximum {MAX_ALERTS_PER_USER} alerts per user.',
    'invalid_number': '❌ Invalid number format. Please enter a valid number.',
}

# =============================================================================
# VALIDATION
# =============================================================================

def validate_config() -> bool:
    """Validate that all required configuration is present"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is not set")
    
    if not TELEGRAM_ADMIN_IDS:
        errors.append("TELEGRAM_ADMIN_IDS is not set")
    
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


def get_config_summary() -> str:
    """Get a summary of current configuration"""
    return f"""
Bot Configuration:
==================
Bot Name: {BOT_NAME}
Version: {BOT_VERSION}
Environment: {ENVIRONMENT}
Admin IDs: {len(TELEGRAM_ADMIN_IDS)} configured
Database: {DATABASE_URL}
Rate Limiting: {'Enabled' if ENABLE_RATE_LIMITING else 'Disabled'}
Alert Check Interval: {ALERT_CHECK_INTERVAL}s
Cache Enabled: {ENABLE_ANALYSIS_CACHE}
Log Level: {LOG_LEVEL}
Timezone: {DEFAULT_TIMEZONE}
"""


if __name__ == '__main__':
    # Test configuration
    print(get_config_summary())
    if validate_config():
        print("\n✅ Configuration is valid!")
    else:
        print("\n❌ Configuration has errors!")
