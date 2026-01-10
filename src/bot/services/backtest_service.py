"""
Backtest Service for Telegram Bot
Simulates trading strategy on historical data

Author: Harsh Kandhway
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd

from ..services.analysis_service import fetch_stock_data
from src.core.indicators import calculate_all_indicators
from src.core.signals import (
    check_hard_filters, calculate_all_signals, determine_recommendation
)
from src.core.risk_management import calculate_targets, calculate_stoploss
from src.core.config import RISK_MODES

logger = logging.getLogger(__name__)


def backtest_strategy(
    symbol: str,
    days: int,
    mode: str = 'balanced',
    timeframe: str = 'medium',
    initial_capital: float = 100000.0
) -> Dict[str, Any]:
    """
    Backtest the trading strategy on historical data
    
    Simple simulation:
    - Buy when BUY signal is generated (not blocked)
    - Sell when target is hit, stop loss is hit, or SELL signal is generated
    - Track all trades and calculate performance
    
    Args:
        symbol: Stock symbol
        days: Number of days to backtest
        mode: Risk mode
        timeframe: Timeframe
        initial_capital: Starting capital
    
    Returns:
        Dictionary with backtest results
    """
    # Fetch historical data
    period_map = {
        30: '1mo',
        60: '3mo',
        90: '3mo',
        180: '6mo',
        365: '1y'
    }
    period = period_map.get(days, '1y')
    
    try:
        df = fetch_stock_data(symbol, period)
    except Exception as e:
        raise ValueError(f"Failed to fetch data: {str(e)}")
    
    if df.empty or len(df) < 50:
        raise ValueError("Insufficient data for backtesting")
    
    # Limit to requested days
    if len(df) > days:
        df = df.tail(days).copy()
    
    # Initialize tracking
    capital = initial_capital
    position = None  # {shares, entry_price, entry_date, target, stop_loss}
    trades = []
    equity_curve = []
    
    # Iterate through each day
    for i in range(50, len(df)):  # Start from day 50 to have enough data for indicators
        current_date = df.index[i]
        current_price = float(df['close'].iloc[i])
        
        # Get data up to current point
        historical_df = df.iloc[:i+1].copy()
        
        try:
            # Calculate indicators for current point
            indicators = calculate_all_indicators(historical_df, timeframe)
            
            # Check hard filters
            is_buy_blocked, _ = check_hard_filters(indicators, 'buy')
            is_sell_blocked, _ = check_hard_filters(indicators, 'sell')
            
            # Calculate signals
            signal_data = calculate_all_signals(indicators, mode)
            confidence = signal_data['confidence']
            
            # Calculate risk/reward for recommendation logic
            # Note: In backtest, we use default values - actual R:R validation happens in analysis
            rr_valid = True  # Default for backtest
            overall_score_pct = 50.0  # Default for backtest
            risk_reward = 2.0  # Default for backtest (assume valid R:R)
            
            # Determine recommendation
            # Get minimum R:R for the mode (default to balanced if not specified)
            test_mode = mode if mode else 'balanced'
            min_rr = RISK_MODES[test_mode]['min_risk_reward']
            
            # Count bullish indicators
            all_signals = signal_data.get('signals', {})
            bullish_indicators_count = sum(1 for _, direction in all_signals.values() if direction == 'bullish')
            
            # Get ADX
            adx = indicators.get('adx', 0.0)
            
            # Get pattern information for contradiction detection
            strongest_pattern = indicators.get('strongest_pattern')
            pattern_confidence = 0.0
            pattern_type = None
            if strongest_pattern:
                pattern_confidence = getattr(strongest_pattern, 'confidence', 0.0) * 100  # Convert to percentage
                if hasattr(strongest_pattern, 'type'):
                    pattern_type = getattr(strongest_pattern, 'type', None)
                elif hasattr(strongest_pattern, 'p_type'):
                    pattern_type = getattr(strongest_pattern, 'p_type', None)
            
            recommendation, recommendation_type = determine_recommendation(
                confidence, is_buy_blocked, is_sell_blocked, mode,
                rr_valid=rr_valid,
                overall_score_pct=overall_score_pct,
                risk_reward=risk_reward,
                min_rr=min_rr,
                adx=adx,
                bullish_indicators_count=bullish_indicators_count,
                pattern_confidence=pattern_confidence,
                pattern_type=pattern_type
            )
            
            # Current position logic
            if position is None:
                # No position - look for buy signal
                if recommendation_type == 'BUY' and not is_buy_blocked:
                    # Calculate position size (use 1% risk rule)
                    atr = indicators.get('atr', current_price * 0.02)
                    stop_loss = calculate_stoploss(
                        current_price, atr, 
                        indicators.get('support', current_price * 0.95),
                        indicators.get('resistance', current_price * 1.05),
                        mode, 'long'
                    )['recommended_stop']
                    
                    risk_per_trade = capital * 0.01  # 1% risk
                    risk_per_share = abs(current_price - stop_loss)
                    
                    if risk_per_share > 0:
                        shares = int(risk_per_trade / risk_per_share)
                        if shares > 0 and shares * current_price <= capital:
                            # Calculate target
                            target_data = calculate_targets(
                                current_price, atr,
                                indicators.get('resistance', current_price * 1.1),
                                indicators.get('support', current_price * 0.9),
                                indicators.get('fib_extensions', {}),
                                mode, 'long'
                            )
                            
                            position = {
                                'shares': shares,
                                'entry_price': current_price,
                                'entry_date': current_date,
                                'target': target_data['recommended_target'],
                                'stop_loss': stop_loss
                            }
                            
                            capital -= shares * current_price
            else:
                # Have position - check for exit
                should_exit = False
                exit_reason = None
                
                # Check stop loss
                if current_price <= position['stop_loss']:
                    should_exit = True
                    exit_reason = 'Stop Loss'
                
                # Check target
                elif current_price >= position['target']:
                    should_exit = True
                    exit_reason = 'Target Hit'
                
                # Check sell signal
                elif recommendation_type == 'SELL' and not is_sell_blocked:
                    should_exit = True
                    exit_reason = 'Sell Signal'
                
                if should_exit:
                    # Close position
                    exit_value = position['shares'] * current_price
                    capital += exit_value
                    
                    pnl = exit_value - (position['shares'] * position['entry_price'])
                    pnl_percent = ((current_price - position['entry_price']) / position['entry_price']) * 100
                    
                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': current_date,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'shares': position['shares'],
                        'pnl': pnl,
                        'pnl_percent': pnl_percent,
                        'exit_reason': exit_reason
                    })
                    
                    position = None
            
            # Track equity
            if position:
                current_value = capital + (position['shares'] * current_price)
            else:
                current_value = capital
            
            equity_curve.append({
                'date': current_date,
                'equity': current_value,
                'price': current_price
            })
            
        except Exception as e:
            logger.warning(f"Error processing day {current_date}: {e}")
            continue
    
    # Close any open position at the end
    if position:
        final_price = float(df['close'].iloc[-1])
        exit_value = position['shares'] * final_price
        capital += exit_value
        
        pnl = exit_value - (position['shares'] * position['entry_price'])
        pnl_percent = ((final_price - position['entry_price']) / position['entry_price']) * 100
        
        trades.append({
            'entry_date': position['entry_date'],
            'exit_date': df.index[-1],
            'entry_price': position['entry_price'],
            'exit_price': final_price,
            'shares': position['shares'],
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'exit_reason': 'End of Period'
        })
    
    # Calculate performance metrics
    final_capital = capital
    total_return = ((final_capital - initial_capital) / initial_capital) * 100
    
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]
    
    win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
    
    avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    # Calculate max drawdown
    equity_values = [e['equity'] for e in equity_curve]
    if equity_values:
        peak = equity_values[0]
        max_drawdown = 0
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    else:
        max_drawdown = 0
    
    best_trade = max(trades, key=lambda x: x['pnl']) if trades else None
    worst_trade = min(trades, key=lambda x: x['pnl']) if trades else None
    
    return {
        'symbol': symbol,
        'days': days,
        'mode': mode,
        'initial_capital': initial_capital,
        'final_capital': final_capital,
        'total_return': total_return,
        'total_trades': len(trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_drawdown': max_drawdown,
        'best_trade': best_trade,
        'worst_trade': worst_trade,
        'trades': trades[-10:],  # Last 10 trades
        'equity_curve': equity_curve[-20:]  # Last 20 points
    }

