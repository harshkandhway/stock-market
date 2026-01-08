"""
Portfolio Service for Telegram Bot
Handles portfolio calculations including P&L, returns, etc.

Author: Harsh Kandhway
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from ..database.db import get_user_portfolio
from ..services.analysis_service import get_current_price, get_multiple_prices

logger = logging.getLogger(__name__)


def calculate_position_pnl(
    shares: float,
    avg_buy_price: float,
    current_price: float
) -> Dict[str, float]:
    """
    Calculate P&L for a single position
    
    Args:
        shares: Number of shares
        avg_buy_price: Average buy price
        current_price: Current market price
    
    Returns:
        Dictionary with P&L metrics
    """
    invested_value = shares * avg_buy_price
    current_value = shares * current_price
    pnl = current_value - invested_value
    pnl_percent = ((current_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0
    
    return {
        'shares': shares,
        'avg_buy_price': avg_buy_price,
        'current_price': current_price,
        'invested_value': invested_value,
        'current_value': current_value,
        'pnl': pnl,
        'pnl_percent': pnl_percent
    }


def calculate_portfolio_summary(
    db: Session,
    telegram_id: int
) -> Dict[str, Any]:
    """
    Calculate portfolio summary with P&L for all positions
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
    
    Returns:
        Dictionary with portfolio summary
    """
    positions = get_user_portfolio(db, telegram_id)
    
    if not positions:
        return {
            'total_positions': 0,
            'total_invested': 0.0,
            'total_current_value': 0.0,
            'total_pnl': 0.0,
            'total_pnl_percent': 0.0,
            'positions': []
        }
    
    # Get current prices for all symbols
    symbols = [pos.symbol for pos in positions]
    current_prices = get_multiple_prices(symbols)
    
    total_invested = 0.0
    total_current_value = 0.0
    position_details = []
    
    for position in positions:
        current_price = current_prices.get(position.symbol)
        
        if current_price is None:
            # Try to fetch individually
            try:
                current_price = get_current_price(position.symbol)
            except Exception:
                logger.warning(f"Could not fetch price for {position.symbol}")
                current_price = position.avg_buy_price  # Fallback to buy price
        
        pnl_data = calculate_position_pnl(
            position.shares,
            position.avg_buy_price,
            current_price
        )
        
        total_invested += pnl_data['invested_value']
        total_current_value += pnl_data['current_value']
        
        position_details.append({
            'symbol': position.symbol,
            'shares': position.shares,
            'avg_buy_price': position.avg_buy_price,
            'current_price': current_price,
            'invested_value': pnl_data['invested_value'],
            'current_value': pnl_data['current_value'],
            'pnl': pnl_data['pnl'],
            'pnl_percent': pnl_data['pnl_percent'],
            'notes': position.notes
        })
    
    total_pnl = total_current_value - total_invested
    total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0
    
    return {
        'total_positions': len(positions),
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_pnl': total_pnl,
        'total_pnl_percent': total_pnl_percent,
        'positions': position_details
    }

