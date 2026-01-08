"""
Start and Help Command Handlers
Handles /start, /help, and /about commands
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.config import WELCOME_MESSAGE, HELP_MESSAGE, ABOUT_MESSAGE, EMOJI
from src.bot.utils.keyboards import create_main_menu_keyboard
from src.bot.database.db import get_or_create_user, get_db_context

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command - Welcome new users
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    user = update.effective_user
    
    try:
        # Register/update user in database
        with get_db_context() as db:
            get_or_create_user(
                db,
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code
            )
        
        # Send welcome message with main menu keyboard
        keyboard = create_main_menu_keyboard()
        
        await update.message.reply_text(
            WELCOME_MESSAGE,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        logger.info(f"User {user.id} ({user.username}) started the bot")
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text(
            f"{EMOJI['error']} An error occurred. Please try again later."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command - Show available commands
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    try:
        await update.message.reply_text(
            HELP_MESSAGE,
            parse_mode='Markdown'
        )
        
        logger.info(f"User {update.effective_user.id} requested help")
        
    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await update.message.reply_text(
            f"{EMOJI['error']} An error occurred. Please try again."
        )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /about command - Show bot information
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    try:
        await update.message.reply_text(
            ABOUT_MESSAGE,
            parse_mode='Markdown'
        )
        
        logger.info(f"User {update.effective_user.id} requested about info")
        
    except Exception as e:
        logger.error(f"Error in about_command: {e}")
        await update.message.reply_text(
            f"{EMOJI['error']} An error occurred. Please try again."
        )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /menu command - Show main menu
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    try:
        keyboard = create_main_menu_keyboard()
        
        await update.message.reply_text(
            f"{EMOJI['menu']} **Main Menu**\n\nSelect an option below:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        logger.info(f"User {update.effective_user.id} requested menu")
        
    except Exception as e:
        logger.error(f"Error in menu_command: {e}")
        await update.message.reply_text(
            f"{EMOJI['error']} An error occurred. Please try again."
        )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle unknown commands
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    await update.message.reply_text(
        f"{EMOJI['warning']} Unknown command.\n\n"
        f"Use /help to see available commands."
    )
