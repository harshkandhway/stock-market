"""
Main Bot Application
Initializes and runs the Telegram bot

Author: Harsh Kandhway
"""

import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
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
    settimeframe_command,
    setcapital_command,
    reset_settings_command
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
from src.bot.handlers.callbacks import (
    handle_callback_query
)
from src.bot.services.alert_service import AlertService

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


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
    
    # Callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
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
        scheduler.start()
        
        # Store in application context
        application.bot_data['alert_service'] = alert_service
        application.bot_data['scheduler'] = scheduler
        
        logger.info(
            f"Alert service started. Checking alerts every "
            f"{ALERT_CHECK_INTERVAL_MINUTES} minute(s)"
        )
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
