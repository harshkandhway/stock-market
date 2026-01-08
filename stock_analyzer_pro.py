#!/usr/bin/env python3
"""
Stock Analyzer Pro - Professional Technical Analysis Tool
=========================================================

A professional-grade stock analysis tool using industry-standard technical
indicators and risk management practices used by top 0.1% traders.

Features:
- 14+ technical indicators with proper weighting
- Hard filters to block dangerous trades
- Confidence-based recommendations (0-100%)
- 3 risk modes: Conservative, Balanced, Aggressive
- 2 timeframe modes: Short-term (1-4 weeks), Medium-term (1-3 months)
- Professional position sizing calculator
- Trailing stop strategies
- Portfolio ranking and allocation

Usage:
    python3 stock_analyzer_pro.py SYMBOL1 SYMBOL2 ...
    python3 stock_analyzer_pro.py RELIANCE.NS --mode conservative --timeframe short
    python3 stock_analyzer_pro.py TCS.NS INFY.NS --capital 100000 --rank --allocate

Author: Stock Analyzer Pro
Version: 2.0
"""

import sys
import argparse
from typing import Dict, List, Optional

import pandas as pd
from yahooquery import Ticker

from config import (
    DEFAULT_MODE, DEFAULT_TIMEFRAME, DEFAULT_TICKERS,
    TIMEFRAME_CONFIGS, RISK_MODES, CURRENCY_SYMBOL
)
from indicators import calculate_all_indicators
from signals import (
    check_hard_filters, calculate_all_signals, get_confidence_level,
    determine_recommendation, generate_reasoning, generate_action_plan
)
from risk_management import (
    calculate_targets, calculate_stoploss, validate_risk_reward,
    calculate_trailing_stops, calculate_position_size,
    generate_no_trade_explanation, calculate_portfolio_allocation
)
from output import (
    print_full_report, print_summary_table, print_portfolio_ranking,
    print_portfolio_allocation, print_disclaimer
)


def fetch_data(symbol: str, period: str = '1y') -> pd.DataFrame:
    """Fetch historical data from Yahoo Finance"""
    try:
        ticker = Ticker(symbol)
        df = ticker.history(period=period, interval='1d')
        
        if isinstance(df, str):
            print(f"  Error fetching {symbol}: {df}")
            return pd.DataFrame()
        
        if df.empty or 'close' not in df.columns:
            print(f"  No data available for {symbol}")
            return pd.DataFrame()
        
        # Flatten multi-index if present
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index(level=0, drop=True)
        
        return df
    except Exception as e:
        print(f"  Error fetching {symbol}: {e}")
        return pd.DataFrame()


def analyze_stock(
    symbol: str,
    df: pd.DataFrame,
    mode: str = 'balanced',
    timeframe: str = 'medium'
) -> Dict:
    """
    Perform complete technical analysis on a stock
    
    Returns comprehensive analysis dictionary
    """
    # Get configurations
    tf_config = TIMEFRAME_CONFIGS[timeframe]
    mode_config = RISK_MODES[mode]
    
    # Calculate all indicators
    indicators = calculate_all_indicators(df, timeframe)
    
    # Check hard filters
    is_buy_blocked, buy_block_reasons = check_hard_filters(indicators, 'buy')
    is_sell_blocked, sell_block_reasons = check_hard_filters(indicators, 'sell')
    
    # Calculate signals and confidence
    signal_data = calculate_all_signals(indicators, mode)
    confidence = signal_data['confidence']
    confidence_level = get_confidence_level(confidence)
    
    # Determine recommendation
    recommendation, recommendation_type = determine_recommendation(
        confidence, is_buy_blocked, is_sell_blocked, mode
    )
    
    # Calculate targets and stop loss
    current_price = indicators['current_price']
    atr = indicators['atr']
    support = indicators['support']
    resistance = indicators['resistance']
    fib_extensions = indicators['fib_extensions']
    
    # Direction based on recommendation
    direction = 'long' if recommendation_type in ['BUY', 'HOLD'] else 'short'
    
    target_data = calculate_targets(
        current_price, atr, resistance, support,
        fib_extensions, mode, direction
    )
    
    stop_data = calculate_stoploss(
        current_price, atr, support, resistance, mode, direction
    )
    
    # Validate risk/reward
    risk_reward, rr_valid, rr_explanation = validate_risk_reward(
        current_price,
        target_data['recommended_target'],
        stop_data['recommended_stop'],
        mode
    )
    
    # Generate reasoning
    reasoning = generate_reasoning(
        indicators, signal_data,
        is_buy_blocked, buy_block_reasons,
        is_sell_blocked, sell_block_reasons,
        recommendation
    )
    
    # Generate action plan
    is_blocked = is_buy_blocked or is_sell_blocked
    actions = generate_action_plan(
        recommendation, recommendation_type,
        indicators, is_blocked
    )
    
    # Calculate trailing stops
    trailing_data = calculate_trailing_stops(current_price, atr, mode)
    
    return {
        'symbol': symbol,
        'mode': mode,
        'timeframe': tf_config['name'],
        'current_price': current_price,
        'indicators': indicators,
        'signal_data': signal_data,
        'confidence': confidence,
        'confidence_level': confidence_level,
        'recommendation': recommendation,
        'recommendation_type': recommendation_type,
        'is_buy_blocked': is_buy_blocked,
        'buy_block_reasons': buy_block_reasons,
        'is_sell_blocked': is_sell_blocked,
        'sell_block_reasons': sell_block_reasons,
        'target_data': target_data,
        'stop_data': stop_data,
        'target': target_data['recommended_target'],
        'stop_loss': stop_data['recommended_stop'],
        'risk_reward': risk_reward,
        'rr_valid': rr_valid,
        'rr_explanation': rr_explanation,
        'reasoning': reasoning,
        'actions': actions,
        'trailing_data': trailing_data,
    }


def get_capital_interactive() -> Optional[float]:
    """Get capital from user interactively"""
    try:
        response = input("\n  Would you like to calculate position sizes? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            capital_str = input(f"  Enter your capital ({CURRENCY_SYMBOL}): ").strip()
            capital_str = capital_str.replace(',', '').replace(CURRENCY_SYMBOL, '')
            return float(capital_str)
    except (ValueError, EOFError, KeyboardInterrupt):
        pass
    return None


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Stock Analyzer Pro - Professional Technical Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 stock_analyzer_pro.py SILVERBEES.NS GOLDBEES.NS
  python3 stock_analyzer_pro.py RELIANCE.NS --mode conservative
  python3 stock_analyzer_pro.py TCS.NS --timeframe short --capital 100000
  python3 stock_analyzer_pro.py INFY.NS WIPRO.NS --rank --allocate --capital 500000
        """
    )
    
    parser.add_argument(
        'symbols',
        nargs='*',
        default=DEFAULT_TICKERS,
        help='Stock symbols to analyze (e.g., RELIANCE.NS TCS.NS)'
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['conservative', 'balanced', 'aggressive'],
        default=DEFAULT_MODE,
        help='Risk mode (default: balanced)'
    )
    
    parser.add_argument(
        '--timeframe', '-t',
        choices=['short', 'medium'],
        default=DEFAULT_TIMEFRAME,
        help='Timeframe: short (1-4 weeks) or medium (1-3 months)'
    )
    
    parser.add_argument(
        '--capital', '-c',
        type=float,
        default=None,
        help='Your capital for position sizing'
    )
    
    parser.add_argument(
        '--rank', '-r',
        action='store_true',
        help='Show stocks ranked by confidence'
    )
    
    parser.add_argument(
        '--allocate', '-a',
        action='store_true',
        help='Show suggested portfolio allocation'
    )
    
    args = parser.parse_args()
    
    # Print header
    print("\n" + "=" * 80)
    print("  STOCK ANALYZER PRO - Professional Technical Analysis")
    print(f"  Mode: {args.mode.upper()} | Timeframe: {args.timeframe.upper()}")
    print("=" * 80)
    
    # Get timeframe config for data period
    tf_config = TIMEFRAME_CONFIGS[args.timeframe]
    data_period = tf_config['data_period']
    
    # Analyze each stock
    analyses = []
    
    for symbol in args.symbols:
        print(f"\n  Fetching data for {symbol}...")
        df = fetch_data(symbol, data_period)
        
        if df.empty:
            print(f"  Skipping {symbol} - no data available")
            continue
        
        print(f"  Analyzing {symbol}...")
        analysis = analyze_stock(symbol, df, args.mode, args.timeframe)
        analyses.append(analysis)
    
    if not analyses:
        print("\n  No stocks could be analyzed. Please check your symbols.")
        return
    
    # Get capital if not provided via CLI
    capital = args.capital
    if capital is None and (args.allocate or len(analyses) == 1):
        capital = get_capital_interactive()
    
    # Print full reports for each stock
    for analysis in analyses:
        position_data = None
        
        if capital and analysis['recommendation_type'] == 'BUY' and analysis['rr_valid']:
            position_data = calculate_position_size(
                capital,
                analysis['current_price'],
                analysis['stop_loss'],
                args.mode
            )
        elif capital and (analysis['is_buy_blocked'] or not analysis['rr_valid']):
            # Generate no-trade explanation
            wait_conditions = []
            if analysis['is_buy_blocked']:
                wait_conditions.append("Hard filter conditions to clear (e.g., RSI < 70)")
            if not analysis['rr_valid']:
                wait_conditions.append(f"Risk/Reward to improve to {RISK_MODES[args.mode]['min_risk_reward']}:1 or better")
            wait_conditions.append("Price pullback to support level")
            
            position_data = {
                'error': False,
                'explanation': generate_no_trade_explanation(
                    analysis['recommendation'],
                    wait_conditions
                )
            }
        
        print_full_report(analysis, position_data)
    
    # Print summary table for multiple stocks
    if len(analyses) > 1:
        print_summary_table(analyses)
    
    # Print ranking if requested
    if args.rank and len(analyses) > 1:
        print_portfolio_ranking(analyses)
    
    # Print allocation if requested
    if args.allocate and capital and len(analyses) > 1:
        allocation_data = calculate_portfolio_allocation(analyses, capital, args.mode)
        print_portfolio_allocation(allocation_data, capital)
    
    # Print disclaimer
    print_disclaimer()


if __name__ == '__main__':
    main()
