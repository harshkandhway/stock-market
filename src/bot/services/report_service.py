"""
Report Service for Telegram Bot
Generates scheduled reports for watchlist and portfolio

Author: Harsh Kandhway
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from ..database.db import (
    get_user_watchlist,
    get_user_settings
)
from ..services.portfolio_service import calculate_portfolio_summary
from ..services.analysis_service import get_current_price
from ..utils.formatters import format_number, format_percentage
from ..config import CURRENCY_SYMBOL, EMOJI

logger = logging.getLogger(__name__)


def generate_watchlist_report(db: Session, telegram_id: int) -> str:
    """
    Generate watchlist summary report
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
    
    Returns:
        Formatted report string
    """
    watchlist = get_user_watchlist(db, telegram_id)
    
    if not watchlist:
        return f"{EMOJI['watchlist']} *Watchlist Report*\n\nYour watchlist is empty."
    
    message = f"{EMOJI['watchlist']} *Watchlist Report*\n\n"
    message += f"*{len(watchlist)} stocks in watchlist*\n\n"
    
    for item in watchlist[:10]:  # Limit to 10 for report
        symbol = item.symbol
        try:
            current_price = get_current_price(symbol)
            if current_price:
                message += f"• *{symbol}*: {CURRENCY_SYMBOL}{format_number(current_price)}\n"
            else:
                message += f"• *{symbol}*: Price unavailable\n"
        except Exception as e:
            logger.warning(f"Could not fetch price for {symbol}: {e}")
            message += f"• *{symbol}*: Error fetching price\n"
    
    if len(watchlist) > 10:
        message += f"\n... and {len(watchlist) - 10} more stocks"
    
    message += f"\n\n_Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
    
    return message


def generate_portfolio_report(db: Session, telegram_id: int) -> str:
    """
    Generate portfolio performance report
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
    
    Returns:
        Formatted report string
    """
    portfolio_summary = calculate_portfolio_summary(db, telegram_id)
    
    if portfolio_summary['total_positions'] == 0:
        return f"{EMOJI['portfolio']} *Portfolio Report*\n\nYour portfolio is empty."
    
    message = f"{EMOJI['portfolio']} *Portfolio Performance Report*\n\n"
    message += f"*Summary:*\n"
    message += f"• Positions: {portfolio_summary['total_positions']}\n"
    message += f"• Total Invested: {CURRENCY_SYMBOL}{format_number(portfolio_summary['total_invested'])}\n"
    message += f"• Current Value: {CURRENCY_SYMBOL}{format_number(portfolio_summary['total_current_value'])}\n"
    
    pnl = portfolio_summary['total_pnl']
    pnl_percent = portfolio_summary['total_pnl_percent']
    pnl_emoji = EMOJI['profit'] if pnl >= 0 else EMOJI['loss']
    
    message += f"• Total P&L: {pnl_emoji} {CURRENCY_SYMBOL}{format_number(pnl)} "
    message += f"({format_percentage(pnl_percent)})\n\n"
    
    message += "*Top Positions:*\n"
    # Sort by absolute P&L
    sorted_positions = sorted(
        portfolio_summary['positions'],
        key=lambda x: abs(x['pnl']),
        reverse=True
    )
    
    for pos in sorted_positions[:5]:  # Top 5
        pos_pnl_emoji = EMOJI['profit'] if pos['pnl'] >= 0 else EMOJI['loss']
        message += f"\n*{pos['symbol']}*\n"
        message += f"  P&L: {pos_pnl_emoji} {CURRENCY_SYMBOL}{format_number(pos['pnl'])} "
        message += f"({format_percentage(pos['pnl_percent'])})\n"
    
    message += f"\n_Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
    
    return message


def generate_combined_report(db: Session, telegram_id: int) -> str:
    """
    Generate combined watchlist and portfolio report
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
    
    Returns:
        Formatted report string
    """
    watchlist_report = generate_watchlist_report(db, telegram_id)
    portfolio_report = generate_portfolio_report(db, telegram_id)
    
    return f"{watchlist_report}\n\n{portfolio_report}"

