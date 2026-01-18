"""
Scheduled Reports Handler

This module handles the /schedule command for managing scheduled reports.
"""

import logging
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..database.db import (
    get_db_context,
    get_or_create_user,
    get_user_scheduled_reports,
    create_scheduled_report,
    delete_scheduled_report,
    update_scheduled_report_status
)
from ..utils.formatters import format_success, format_error
from ..utils.validators import parse_command_args, validate_time
from ..config import EMOJI, MAX_SCHEDULED_REPORTS

logger = logging.getLogger(__name__)


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /schedule command.
    
    Usage:
        /schedule - View all scheduled reports
        /schedule add TYPE TIME - Create schedule (e.g., "watchlist 09:00", "portfolio 09:00", "combined 09:00")
        /schedule remove ID - Delete schedule
    """
    user_id = update.effective_user.id
    
    # Parse arguments
    args = parse_command_args(update.message.text, 'schedule')
    
    if not args:
        # Show all scheduled reports
        await show_scheduled_reports(update, context)
        return
    
    subcommand = args[0].lower()
    
    if subcommand == "add":
        await schedule_add(update, context, args[1:])
    elif subcommand == "remove":
        await schedule_remove(update, context, args[1:])
    elif subcommand == "toggle":
        await schedule_toggle(update, context, args[1:])
    else:
        await update.message.reply_text(
            format_error(
                f"Unknown subcommand: {subcommand}\n\n"
                f"Available commands:\n"
                f"• /schedule - View all reports\n"
                f"• /schedule add TYPE TIME - Add schedule\n"
                f"• /schedule remove ID - Remove schedule\n"
                f"• /schedule toggle ID - Toggle schedule on/off"
            )
        )


async def show_scheduled_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all scheduled reports for the user."""
    user_id = update.effective_user.id
    
    with get_db_context() as db:
        get_or_create_user(db, user_id, update.effective_user.username)
        reports = get_user_scheduled_reports(db, user_id, active_only=False)
        
        if not reports:
            await update.message.reply_text(
                f"{EMOJI['schedule']} *Scheduled Reports*\n\n"
                "You have no scheduled reports.\n\n"
                "Create one using:\n"
                "`/schedule add watchlist 09:00`\n"
                "`/schedule add portfolio 09:00`\n"
                "`/schedule add combined 09:00`",
                parse_mode='Markdown'
            )
            return
        
        message = f"{EMOJI['schedule']} *Your Scheduled Reports*\n\n"
        
        for report in reports:
            status = "✅ Active" if report.is_active else "⏸️ Paused"
            message += f"*Report #{report.id}*\n"
            message += f"Type: {report.report_type}\n"
            message += f"Frequency: {report.frequency}\n"
            message += f"Status: {status}\n"
            if report.last_sent:
                message += f"Last sent: {report.last_sent.strftime('%Y-%m-%d %H:%M')}\n"
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')


async def schedule_add(update: Update, context: ContextTypes.DEFAULT_TYPE, args: List[str]) -> None:
    """Add a new scheduled report."""
    user_id = update.effective_user.id
    
    if len(args) < 2:
        await update.message.reply_text(
            format_error(
                "Invalid format. Usage:\n"
                "`/schedule add TYPE TIME`\n\n"
                "Types: watchlist, portfolio, combined\n"
                "Time: HH:MM (e.g., 09:00)\n\n"
                "Examples:\n"
                "`/schedule add watchlist 09:00`\n"
                "`/schedule add portfolio 18:00`",
                parse_mode='Markdown'
            )
        )
        return
    
    report_type = args[0].lower()
    time_str = args[1]
    
    # Validate report type
    valid_types = ['watchlist', 'portfolio', 'combined']
    if report_type not in valid_types:
        await update.message.reply_text(
            format_error(
                f"Invalid report type: {report_type}\n\n"
                f"Valid types: {', '.join(valid_types)}"
            )
        )
        return
    
    # Validate time
    is_valid_time, formatted_time, time_error = validate_time(time_str)
    if not is_valid_time:
        await update.message.reply_text(format_error(time_error))
        return
    
    try:
        with get_db_context() as db:
            # Check limit
            existing_reports = get_user_scheduled_reports(db, user_id, active_only=False)
            if len(existing_reports) >= MAX_SCHEDULED_REPORTS:
                await update.message.reply_text(
                    format_error(
                        f"You have reached the maximum of {MAX_SCHEDULED_REPORTS} scheduled reports.\n"
                        "Please remove some before adding new ones."
                    )
                )
                return
            
            # Create report
            report = create_scheduled_report(
                db, user_id, report_type, formatted_time
            )
            
            if report:
                await update.message.reply_text(
                    format_success(
                        f"✓ Scheduled report created!\n\n"
                        f"Type: {report_type}\n"
                        f"Time: {formatted_time}\n\n"
                        f"Note: Reports will be sent automatically at the scheduled time."
                    )
                )
            else:
                await update.message.reply_text(
                    format_error("Failed to create scheduled report")
                )
                
    except Exception as e:
        logger.error(f"Error creating scheduled report: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to create schedule: {str(e)}")
        )


async def schedule_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, args: List[str]) -> None:
    """Remove a scheduled report."""
    user_id = update.effective_user.id
    
    if not args:
        await update.message.reply_text(
            format_error(
                "Please specify a report ID to remove.\n\n"
                "Usage: `/schedule remove ID`\n\n"
                "Use `/schedule` to see your report IDs.",
                parse_mode='Markdown'
            )
        )
        return
    
    try:
        report_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            format_error("Invalid report ID. Please provide a number.")
        )
        return
    
    try:
        with get_db_context() as db:
            success = delete_scheduled_report(db, user_id, report_id)
            
            if success:
                await update.message.reply_text(
                    format_success(f"✓ Scheduled report #{report_id} removed")
                )
            else:
                await update.message.reply_text(
                    format_error(f"Report #{report_id} not found")
                )
                
    except Exception as e:
        logger.error(f"Error removing scheduled report: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to remove schedule: {str(e)}")
        )


async def schedule_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, args: List[str]) -> None:
    """Toggle a scheduled report on/off."""
    user_id = update.effective_user.id
    
    if not args:
        await update.message.reply_text(
            format_error(
                "Please specify a report ID to toggle.\n\n"
                "Usage: `/schedule toggle ID`",
                parse_mode='Markdown'
            )
        )
        return
    
    try:
        report_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            format_error("Invalid report ID. Please provide a number.")
        )
        return
    
    try:
        with get_db_context() as db:
            reports = get_user_scheduled_reports(db, user_id, active_only=False)
            report = next((r for r in reports if r.id == report_id), None)
            
            if not report:
                await update.message.reply_text(
                    format_error(f"Report #{report_id} not found")
                )
                return
            
            new_status = not report.is_active
            success = update_scheduled_report_status(db, report_id, new_status)
            
            if success:
                status_text = "activated" if new_status else "paused"
                await update.message.reply_text(
                    format_success(f"✓ Scheduled report #{report_id} {status_text}")
                )
            else:
                await update.message.reply_text(
                    format_error("Failed to update report status")
                )
                
    except Exception as e:
        logger.error(f"Error toggling scheduled report: {e}", exc_info=True)
        await update.message.reply_text(
            format_error(f"Failed to toggle schedule: {str(e)}")
        )



