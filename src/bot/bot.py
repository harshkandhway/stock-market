"""
Main Bot Application
Initializes and runs the Telegram bot

Author: Harsh Kandhway
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.bot.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_ADMIN_IDS,
    validate_config,
    BOT_NAME,
    ALERT_CHECK_INTERVAL_MINUTES
)
from src.bot.handlers.start import (
    start_command,
    help_command,
    about_command,
    menu_command,
    unknown_command
)
from src.bot.handlers.analyze import (
    analyze_command,
    quick_analyze_command
)
from src.bot.handlers.watchlist import (
    watchlist_command
)
from src.bot.handlers.settings import (
    settings_command,
    setmode_command,
    sethorizon_command,
    settimeframe_command,
    setcapital_command,
    reset_settings_command,
    handle_settings_callback,
    handle_capital_input
)
from src.bot.handlers.compare import (
    compare_command
)
from src.bot.handlers.alerts import (
    alerts_command,
    alert_command,
    deletealert_command,
    clearalerts_command
)
from src.bot.handlers.portfolio import (
    portfolio_command
)
from src.bot.handlers.search import (
    search_command
)
from src.bot.handlers.schedule import (
    schedule_command
)
from src.bot.handlers.backtest import (
    backtest_command
)
from src.bot.handlers.paper_trading import (
    papertrade_command
)
from src.bot.handlers.callbacks import (
    handle_callback_query
)
from src.bot.handlers.on_demand_signals import (
    register_on_demand_handlers
)
from src.bot.services.alert_service import AlertService

# Configure logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Import config after path setup
from src.bot.config import LOG_FILE, LOG_LEVEL

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent.parent.parent / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)

# Set up root logger with file handler
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

# Remove existing handlers to avoid duplicates
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)

# File handler for main bot log
log_file_path = Path(__file__).parent.parent.parent / LOG_FILE
log_file_path.parent.mkdir(parents=True, exist_ok=True)
file_handler = RotatingFileHandler(
    filename=str(log_file_path),
    mode='a',
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)
logger.info(f"Logging configured - Console: INFO, File: {log_file_path} (DEBUG)")


def check_authorization(user_id: int) -> bool:
    """
    Check if user is authorized to use the bot
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        True if authorized, False otherwise
    """
    # If no admin IDs configured, allow everyone
    if not TELEGRAM_ADMIN_IDS:
        return True
    
    return user_id in TELEGRAM_ADMIN_IDS


async def authorization_filter(update, context):
    """
    Filter to check user authorization before processing commands
    """
    user_id = update.effective_user.id
    
    if not check_authorization(user_id):
        await update.message.reply_text(
            "⛔ You are not authorized to use this bot.\n\n"
            "This is a private bot. Contact the administrator for access."
        )
        logger.warning(f"Unauthorized access attempt by user {user_id}")
        return False
    
    return True


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages including main menu button clicks and custom inputs.
    Routes menu button text to appropriate commands.
    """
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Check authorization
    if not check_authorization(user_id):
        await update.message.reply_text(
            "⛔ You are not authorized to use this bot."
        )
        return
    
    # Handle custom capital input if awaiting
    if context.user_data.get('awaiting_capital_input'):
        from src.bot.handlers.settings import handle_capital_input
        await handle_capital_input(update, context)
        return
    
    # Handle custom alert time input if awaiting
    if context.user_data.get('awaiting_alert_time_input'):
        from src.bot.handlers.settings import handle_alert_time_input
        await handle_alert_time_input(update, context)
        return
    
    # Route main menu button clicks to commands
    menu_routes = {
        '📊 Analyze Stock': '/analyze',
        '📈 Compare Stocks': '/compare',
        '⭐ Watchlist': '/watchlist',
        '🔔 Alerts': '/alerts',
        '💼 Portfolio': '/portfolio',
        '📈 Paper Trading': '/papertrade',
        '📊 Scan Market': '/scanmarket',
        '📅 Schedule Reports': '/schedule',
        '⚙️ Settings': '/settings',
        'ℹ️ Help': '/help',
        '◀️ Back to Menu': '/menu',
    }
    
    if text in menu_routes:
        # Simulate the corresponding command
        command = menu_routes[text]
        logger.info(f"User {user_id} clicked menu button: {text} -> {command}")
        
        if command == '/analyze':
            await update.message.reply_text(
                "🔍 *Analyze a Stock*\n\n"
                "Send me a stock symbol to analyze:\n\n"
                "Examples:\n"
                "• `/analyze RELIANCE.NS` (NSE)\n"
                "• `/analyze TCS.NS`\n"
                "• `/analyze INFY.NS`\n\n"
                "_Just type `/analyze` followed by the symbol_",
                parse_mode='Markdown'
            )
        elif command == '/compare':
            await update.message.reply_text(
                "📈 *Compare Stocks*\n\n"
                "Compare up to 5 stocks side by side:\n\n"
                "Example:\n"
                "`/compare RELIANCE.NS TCS.NS INFY.NS`\n\n"
                "_Separate symbols with spaces_",
                parse_mode='Markdown'
            )
        elif command == '/watchlist':
            from src.bot.handlers.watchlist import watchlist_command
            await watchlist_command(update, context)
        elif command == '/alerts':
            from src.bot.handlers.alerts import alerts_command
            await alerts_command(update, context)
        elif command == '/portfolio':
            from src.bot.handlers.portfolio import portfolio_command
            await portfolio_command(update, context)
        elif command == '/papertrade':
            from src.bot.handlers.paper_trading import papertrade_command
            await papertrade_command(update, context)
        elif command == '/settings':
            from src.bot.handlers.settings import settings_command
            await settings_command(update, context)
        elif command == '/help':
            from src.bot.handlers.start import help_command
            await help_command(update, context)
        elif command == '/schedule':
            await update.message.reply_text(
                "📅 *Scheduled Reports*\n\n"
                "Set up automatic daily/weekly reports:\n\n"
                "• `/schedule daily HH:MM` - Daily report at specified time\n"
                "• `/schedule weekly DAY HH:MM` - Weekly report\n"
                "• `/schedule list` - View your schedules\n"
                "• `/schedule cancel ID` - Cancel a schedule\n\n"
                "_Example: `/schedule daily 09:00`_",
                parse_mode='Markdown'
            )
        elif command == '/menu':
            from src.bot.handlers.start import start_command
            await start_command(update, context)
        elif command == '/scanmarket':
            from src.bot.handlers.on_demand_signals import scan_market_command
            await scan_market_command(update, context)
        return
    
    # If no match, suggest using commands
    await update.message.reply_text(
        "💡 I didn't understand that.\n\n"
        "Try using these commands:\n"
        "• `/analyze SYMBOL` - Analyze a stock\n"
        "• `/settings` - Change preferences\n"
        "• `/help` - See all commands\n\n"
        "_Or tap a button from the menu below_"
    )


async def send_scheduled_reports(bot):
    """
    Send scheduled reports to users
    
    Args:
        bot: Telegram bot instance
    """
    from src.bot.database.db import get_db_context, get_all_active_scheduled_reports
    from src.bot.services.report_service import (
        generate_watchlist_report,
        generate_portfolio_report,
        generate_combined_report
    )
    from datetime import datetime, time
    
    try:
        with get_db_context() as db:
            reports = get_all_active_scheduled_reports(db)
            
            current_time = datetime.now().time()
            current_hour = current_time.hour
            current_minute = current_time.minute
            
            for report in reports:
                try:
                    # Parse frequency (simple format: "HH:MM" for daily)
                    if ':' in report.frequency:
                        parts = report.frequency.split(':')
                        if len(parts) == 2:
                            scheduled_hour = int(parts[0])
                            scheduled_minute = int(parts[1])
                            
                            # Check if it's time to send (within same hour and minute)
                            if current_hour == scheduled_hour and current_minute == scheduled_minute:
                                # Check if already sent today
                                if report.last_sent:
                                    last_sent_date = report.last_sent.date()
                                    today = datetime.now().date()
                                    if last_sent_date == today:
                                        continue  # Already sent today
                                
                                # Generate and send report
                                user = report.user
                                telegram_id = user.telegram_id
                                
                                try:
                                    if report.report_type == 'watchlist':
                                        message = generate_watchlist_report(db, telegram_id)
                                    elif report.report_type == 'portfolio':
                                        message = generate_portfolio_report(db, telegram_id)
                                    elif report.report_type == 'combined':
                                        message = generate_combined_report(db, telegram_id)
                                    else:
                                        continue
                                    
                                    # Send message
                                    await bot.send_message(
                                        chat_id=telegram_id,
                                        text=message,
                                        parse_mode='Markdown'
                                    )
                                    
                                    # Update last_sent
                                    from datetime import datetime as dt
                                    report.last_sent = dt.utcnow()
                                    db.commit()
                                except Exception as send_error:
                                    logger.error(f"Error sending report to {telegram_id}: {send_error}")
                                    continue
                                
                                logger.info(
                                    f"Sent {report.report_type} report to user {telegram_id}"
                                )
                except Exception as e:
                    logger.error(f"Error sending scheduled report {report.id}: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Error in send_scheduled_reports: {e}", exc_info=True)


async def error_handler(update, context):
    """
    Handle errors in the bot
    
    Args:
        update: Telegram update object
        context: Bot context with error info
    """
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)
    
    # Try to send error message to user
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred while processing your request.\n\n"
                "Please try again later or contact support if the problem persists."
            )
    except Exception as e:
        logger.error(f"Could not send error message to user: {e}")


def create_bot_application() -> Application:
    """
    Create and configure the bot application
    
    Returns:
        Configured Application instance
    
    Raises:
        ValueError: If configuration is invalid
    """
    # Validate configuration
    if not validate_config():
        raise ValueError("Invalid bot configuration. Check your .env file.")
    
    # Create application
    logger.info(f"Creating bot application: {BOT_NAME}")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    logger.info("Registering command handlers...")
    
    # Basic commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("menu", menu_command))
    
    # Analysis commands
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("quick", quick_analyze_command))
    application.add_handler(CommandHandler("compare", compare_command))
    
    # Watchlist commands
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    
    # Settings commands
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("setmode", setmode_command))
    application.add_handler(CommandHandler("sethorizon", sethorizon_command))
    application.add_handler(CommandHandler("settimeframe", settimeframe_command))
    application.add_handler(CommandHandler("setcapital", setcapital_command))
    application.add_handler(CommandHandler("resetsettings", reset_settings_command))
    
    # Alert commands
    application.add_handler(CommandHandler("alerts", alerts_command))
    application.add_handler(CommandHandler("alert", alert_command))
    application.add_handler(CommandHandler("deletealert", deletealert_command))
    application.add_handler(CommandHandler("clearalerts", clearalerts_command))
    
    # Portfolio commands
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    
    # Search commands
    application.add_handler(CommandHandler("search", search_command))
    
    # Schedule commands
    application.add_handler(CommandHandler("schedule", schedule_command))
    
    # Backtest commands
    application.add_handler(CommandHandler("backtest", backtest_command))
    
    # Paper trading commands
    application.add_handler(CommandHandler("papertrade", papertrade_command))
    
    # On-Demand BUY Signals - MUST be registered BEFORE general callback handler
    register_on_demand_handlers(application)
    logger.info("✅ On-demand signals handlers registered")
    
    # Callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Text message handler for main menu buttons and custom inputs
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_text_message
    ))
    
    # Unknown command handler (must be last)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info(f"Registered {len(application.handlers[0])} command handlers")
    logger.info("Bot application created successfully!")
    
    return application


async def post_init(application: Application):
    """
    Called after the bot initializes
    
    Args:
        application: Bot application
    """
    logger.info("Bot post-initialization...")
    
    # Initialize paper trading logger
    try:
        from src.bot.utils.paper_trading_logger import setup_paper_trading_logger
        pt_logger = setup_paper_trading_logger()
        logger.info("Paper trading logger initialized")
        pt_logger.info("Paper trading logger started")
    except Exception as e:
        logger.error(f"Failed to initialize paper trading logger: {e}", exc_info=True)
    
    # Initialize database
    from src.bot.database.db import init_db, test_connection
    
    try:
        logger.info("Checking database connection...")
        if not test_connection():
            logger.warning("Database connection test failed - initializing...")
            init_db()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    
    # Get bot info
    bot_info = await application.bot.get_me()
    logger.info(f"Bot @{bot_info.username} (ID: {bot_info.id}) is ready!")
    
    # Log authorized users
    if TELEGRAM_ADMIN_IDS:
        logger.info(f"Authorized users: {TELEGRAM_ADMIN_IDS}")
    else:
        logger.warning("No admin IDs configured - bot is open to everyone!")
    
    # Initialize alert service and scheduler
    try:
        logger.info("Starting alert service...")
        alert_service = AlertService(application.bot)
        alert_service.start()
        
        # Set up scheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            alert_service.check_all_alerts,
            'interval',
            minutes=ALERT_CHECK_INTERVAL_MINUTES,
            id='check_alerts',
            name='Check all alerts',
            replace_existing=True
        )
        
        # Add scheduled reports job (runs every hour to check for scheduled reports)
        scheduler.add_job(
            send_scheduled_reports,
            'interval',
            minutes=60,
            args=[application.bot],
            id='send_scheduled_reports',
            name='Send scheduled reports',
            replace_existing=True
        )
        
        scheduler.start()
        
        # Store in application context
        application.bot_data['alert_service'] = alert_service
        application.bot_data['scheduler'] = scheduler
        
        logger.info(
            f"Alert service started. Checking alerts every "
            f"{ALERT_CHECK_INTERVAL_MINUTES} minute(s)"
        )
        logger.info("Scheduled reports service started. Checking every hour.")
        
        # Start daily BUY alerts scheduler
        try:
            logger.info("Starting daily BUY alerts scheduler...")
            from src.bot.services.scheduler_service import start_scheduler
            await start_scheduler(application)
            logger.info("Daily BUY alerts scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start daily BUY alerts scheduler: {e}", exc_info=True)
            logger.warning("Bot will run without daily BUY alerts")
    except Exception as e:
        logger.error(f"Failed to start alert service: {e}", exc_info=True)
        logger.warning("Bot will run without alert notifications")


async def post_shutdown(application: Application):
    """
    Called before the bot shuts down
    
    Args:
        application: Bot application
    """
    logger.info("Bot shutting down...")
    
    # Stop alert service
    try:
        if 'alert_service' in application.bot_data:
            alert_service = application.bot_data['alert_service']
            alert_service.stop()
            logger.info("Alert service stopped")
        
        if 'scheduler' in application.bot_data:
            scheduler = application.bot_data['scheduler']
            scheduler.shutdown()
            logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping services: {e}")
    
    logger.info("Bot shutdown complete")


def run_bot():
    """
    Run the bot (blocking)
    """
    try:
        # Create application
        application = create_bot_application()
        
        # Set up post-init and post-shutdown
        application.post_init = post_init
        application.post_shutdown = post_shutdown
        
        # Run the bot
        logger.info("Starting bot polling...")
        logger.info("Press Ctrl+C to stop")
        
        application.run_polling(
            allowed_updates=['message', 'callback_query'],
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error running bot: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    run_bot()
