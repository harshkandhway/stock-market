#!/usr/bin/env python3
"""
Stock Analyzer Pro - Beginner-Friendly Investment Analysis Tool
================================================================

A powerful yet easy-to-understand stock analysis tool designed for
investors of all experience levels.

Features:
- Clear buy/sell recommendations with simple explanations
- Expected timeline for reaching target prices
- Investment safety ratings (1-5 stars)
- Profit/loss calculator
- Clear guidance on when to buy and sell
- Support for multiple investment horizons (1 week to 1 year)

Usage:
    python stock_analyzer_pro.py SYMBOL1 SYMBOL2 ...
    python stock_analyzer_pro.py RELIANCE.NS --horizon 3months
    python stock_analyzer_pro.py TCS.NS --horizon 1month --capital 50000

Author: Harsh Kandhway
Version: 3.0 (Beginner-Friendly Edition)
"""

import sys
import os
import argparse
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
from yahooquery import Ticker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.config import (
    DEFAULT_MODE, DEFAULT_TIMEFRAME, DEFAULT_TICKERS, DEFAULT_HORIZON,
    TIMEFRAME_CONFIGS, RISK_MODES, CURRENCY_SYMBOL, INVESTMENT_HORIZONS
)
from src.core.indicators import calculate_all_indicators
from src.core.signals import (
    check_hard_filters, calculate_all_signals, get_confidence_level,
    determine_recommendation, generate_reasoning, generate_action_plan
)
from src.core.risk_management import (
    calculate_targets, calculate_stoploss, validate_risk_reward,
    calculate_trailing_stops, calculate_position_size,
    generate_no_trade_explanation, calculate_portfolio_allocation,
    estimate_time_to_target, calculate_investment_summary, calculate_safety_score
)
from src.core.output import (
    print_full_report, print_summary_table, print_portfolio_ranking,
    print_portfolio_allocation, print_disclaimer
)


def print_welcome():
    """Print welcome message"""
    print("\n" + "=" * 60)
    print("  STOCK ANALYZER PRO - Your Investment Assistant")
    print("=" * 60)
    print("  Making stock analysis simple and accessible for everyone!")
    print("=" * 60)


def fetch_data(symbol: str, period: str = '1y') -> pd.DataFrame:
    """Fetch historical data from Yahoo Finance"""
    if not symbol or not isinstance(symbol, str):
        print(f"  ❌ Error: Invalid symbol '{symbol}'")
        return pd.DataFrame()
    
    try:
        ticker = Ticker(symbol)
        df = ticker.history(period=period, interval='1d')
        
        if isinstance(df, str):
            print(f"  ❌ Error fetching {symbol}: {df}")
            return pd.DataFrame()
        
        if not isinstance(df, pd.DataFrame):
            print(f"  ❌ Error: Unexpected data type for {symbol}")
            return pd.DataFrame()
        
        if df.empty:
            print(f"  ⚠️ No data available for {symbol}")
            return pd.DataFrame()
        
        required_columns = ['close', 'high', 'low', 'open']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"  ❌ Missing data columns for {symbol}")
            return pd.DataFrame()
        
        if len(df) < 50:
            print(f"  ⚠️ Limited data for {symbol} - results may be less accurate")
        
        if df['close'].isna().all():
            print(f"  ❌ No valid price data for {symbol}")
            return pd.DataFrame()
        
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index(level=0, drop=True)
        
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except (ValueError, TypeError):
                pass
        
        return df
        
    except Exception as e:
        print(f"  ❌ Error fetching {symbol}: {e}")
        return pd.DataFrame()


def analyze_stock(
    symbol: str,
    df: pd.DataFrame,
    mode: str = 'balanced',
    timeframe: str = 'medium',
    horizon: str = '3months'
) -> Dict:
    """Perform complete technical analysis with beginner-friendly additions"""
    
    if not symbol or df is None or df.empty:
        raise ValueError(f"Invalid input for {symbol}")
    
    if mode not in RISK_MODES:
        mode = DEFAULT_MODE
    
    if timeframe not in TIMEFRAME_CONFIGS:
        timeframe = DEFAULT_TIMEFRAME
    
    if horizon not in INVESTMENT_HORIZONS:
        horizon = DEFAULT_HORIZON
    
    tf_config = TIMEFRAME_CONFIGS[timeframe]
    horizon_config = INVESTMENT_HORIZONS[horizon]
    
    try:
        indicators = calculate_all_indicators(df, timeframe)
    except ValueError as e:
        raise ValueError(f"Analysis failed for {symbol}: {e}")
    
    is_buy_blocked, buy_block_reasons = check_hard_filters(indicators, 'buy')
    is_sell_blocked, sell_block_reasons = check_hard_filters(indicators, 'sell')
    
    signal_data = calculate_all_signals(indicators, mode)
    confidence = signal_data['confidence']
    confidence_level = get_confidence_level(confidence)
    
    current_price = indicators['current_price']
    atr = indicators['atr']
    support = indicators['support']
    resistance = indicators['resistance']
    fib_extensions = indicators['fib_extensions']
    
    # For beginners, always calculate long targets (shorting is advanced)
    direction = 'long'
    
    target_data = calculate_targets(
        current_price, atr, resistance, support,
        fib_extensions, mode, direction
    )
    
    # Calculate stop loss
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
    
    # Calculate overall score percentage
    trend_signals = signal_data.get('trend_signals', {})
    momentum_signals = signal_data.get('momentum_signals', {})
    pattern_signals = signal_data.get('pattern_signals', {})
    
    trend_bullish = sum(1 for _, d in trend_signals.values() if d == 'bullish')
    trend_score = min(3, max(0, trend_bullish))
    
    momentum_bullish = sum(1 for _, d in momentum_signals.values() if d == 'bullish')
    momentum_score = min(3, max(0, momentum_bullish))
    
    vol_ratio = indicators.get('volume_ratio', 1.0)
    volume_score = 1 if (vol_ratio >= 1.5) else 0
    
    pattern_bullish = sum(1 for _, d in pattern_signals.values() if d == 'bullish')
    pattern_bias = indicators.get('pattern_bias', 'neutral')
    pattern_score = min(3, max(0, pattern_bullish + (1 if pattern_bias == 'bullish' else 0)))
    
    risk_score = 1 if rr_valid else 0
    
    total_bullish = trend_score + momentum_score + volume_score + pattern_score + risk_score
    overall_score_pct = (total_bullish / 10) * 100
    
    # Count bullish indicators for professional validation
    all_signals = signal_data.get('signals', {})
    bullish_indicators_count = sum(1 for _, direction in all_signals.values() if direction == 'bullish')
    
    # Get ADX for trend strength validation
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
    
    # Get minimum R:R for the mode
    min_rr = RISK_MODES[mode]['min_risk_reward']
    
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
    
    stop_data = calculate_stoploss(
        current_price, atr, support, resistance, mode, direction
    )
    
    risk_reward, rr_valid, rr_explanation = validate_risk_reward(
        current_price,
        target_data['recommended_target'],
        stop_data['recommended_stop'],
        mode
    )
    
    # Calculate time estimate for target
    time_estimate = estimate_time_to_target(
        current_price,
        target_data['recommended_target'],
        atr,
        indicators['atr_percent'],
        indicators['momentum'],
        indicators['adx'],
        horizon
    )
    
    # Calculate safety score for beginners
    safety_score = calculate_safety_score(
        confidence,
        risk_reward,
        indicators['adx'],
        indicators['rsi'],
        is_buy_blocked,
        horizon
    )
    
    reasoning = generate_reasoning(
        indicators, signal_data,
        is_buy_blocked, buy_block_reasons,
        is_sell_blocked, sell_block_reasons,
        recommendation
    )
    
    is_blocked = is_buy_blocked or is_sell_blocked
    actions = generate_action_plan(
        recommendation, recommendation_type,
        indicators, is_blocked
    )
    
    trailing_data = calculate_trailing_stops(current_price, atr, mode)
    
    return {
        'symbol': symbol,
        'mode': mode,
        'timeframe': tf_config['name'],
        'horizon': horizon,
        'horizon_config': horizon_config,
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
        'time_estimate': time_estimate,
        'safety_score': safety_score,
    }


def get_capital_interactive() -> Optional[float]:
    """Get capital from user interactively"""
    try:
        response = input("\n  💰 Would you like to see profit/loss calculations? (y/n): ").strip().lower()
        if response not in ['y', 'yes']:
            return None
        
        for _ in range(3):
            capital_str = input(f"  Enter your investment amount ({CURRENCY_SYMBOL}): ").strip()
            
            if not capital_str:
                print("  ⚠️ Please enter an amount")
                continue
            
            capital_str = capital_str.replace(',', '').replace(CURRENCY_SYMBOL, '').strip()
            
            try:
                capital = float(capital_str)
                
                if capital <= 0:
                    print("  ⚠️ Amount must be greater than 0")
                    continue
                
                if capital < 1000:
                    print(f"  ⚠️ {CURRENCY_SYMBOL}{capital:,.2f} is a very small amount")
                    confirm = input("  Continue anyway? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes']:
                        return None
                
                return capital
                
            except ValueError:
                print("  ⚠️ Please enter a valid number")
                continue
        
        return None
        
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled")
        return None


def select_horizon_interactive() -> str:
    """Let user select investment horizon interactively"""
    print("\n  📅 SELECT YOUR INVESTMENT TIMELINE:")
    print("  " + "─" * 40)
    
    horizons = list(INVESTMENT_HORIZONS.items())
    for i, (key, config) in enumerate(horizons, 1):
        risk_emoji = '🟢' if config['risk_level'] in ['LOW', 'VERY LOW'] else '🟡' if config['risk_level'] == 'MEDIUM' else '🔴'
        print(f"  {i}. {config['emoji']} {config['display_name']:12} - {config['name']:20} {risk_emoji} {config['risk_level']}")
        print(f"      {config['suitable_for']}")
    
    print(f"\n  💡 Recommended for beginners: 3 Months or 6 Months")
    
    try:
        choice = input(f"\n  Enter choice (1-{len(horizons)}) or press Enter for 3 Months: ").strip()
        
        if not choice:
            return '3months'
        
        choice_num = int(choice)
        if 1 <= choice_num <= len(horizons):
            return horizons[choice_num - 1][0]
        else:
            print("  ⚠️ Invalid choice, using 3 months")
            return '3months'
            
    except (ValueError, EOFError, KeyboardInterrupt):
        return '3months'


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Stock Analyzer Pro - Beginner-Friendly Investment Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python stock_analyzer_pro.py RELIANCE.NS
  python stock_analyzer_pro.py TCS.NS --horizon 3months
  python stock_analyzer_pro.py INFY.NS --horizon 1month --capital 50000
  python stock_analyzer_pro.py SILVERBEES.NS GOLDBEES.NS --compare
        """
    )
    
    parser.add_argument(
        'symbols',
        nargs='*',
        default=DEFAULT_TICKERS,
        help='Stock symbols to analyze (e.g., RELIANCE.NS TCS.NS)'
    )
    
    parser.add_argument(
        '--horizon', '-H',
        choices=list(INVESTMENT_HORIZONS.keys()),
        default=None,
        help='Investment horizon (1week, 2weeks, 1month, 3months, 6months, 1year)'
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['conservative', 'balanced', 'aggressive'],
        default=DEFAULT_MODE,
        help='Risk mode (default: balanced)'
    )
    
    parser.add_argument(
        '--capital', '-c',
        type=float,
        default=None,
        help='Your investment amount for profit/loss calculations'
    )
    
    parser.add_argument(
        '--compare', '-C',
        action='store_true',
        help='Compare multiple stocks and rank them'
    )
    
    parser.add_argument(
        '--simple', '-s',
        action='store_true',
        default=True,
        help='Show simplified beginner-friendly report (default)'
    )
    
    parser.add_argument(
        '--advanced', '-a',
        action='store_true',
        help='Show advanced technical details'
    )
    
    args = parser.parse_args()
    
    # Print welcome
    print_welcome()
    
    # Get investment horizon
    if args.horizon:
        horizon = args.horizon
    else:
        horizon = select_horizon_interactive()
    
    horizon_config = INVESTMENT_HORIZONS[horizon]
    
    print(f"\n  📊 Analyzing for: {horizon_config['emoji']} {horizon_config['display_name']} investment")
    print(f"  Risk Level: {horizon_config['risk_level']}")
    print(f"  {horizon_config['suitable_for']}")
    
    # Determine timeframe from horizon
    timeframe = horizon_config['timeframe_key']
    data_period = horizon_config['data_period']
    
    # Validate symbols
    if not args.symbols:
        print("\n  ❌ No stocks specified. Please provide stock symbols.")
        print("  Example: python stock_analyzer_pro.py RELIANCE.NS TCS.NS")
        return
    
    # Analyze each stock
    analyses = []
    
    for symbol in args.symbols:
        if not symbol or len(symbol.strip()) == 0:
            continue
        
        symbol = symbol.strip().upper()
        print(f"\n  🔍 Fetching data for {symbol}...")
        df = fetch_data(symbol, data_period)
        
        if df.empty:
            print(f"  ⚠️ Skipping {symbol} - no data available")
            continue
        
        print(f"  📈 Analyzing {symbol}...")
        try:
            analysis = analyze_stock(symbol, df, args.mode, timeframe, horizon)
            analyses.append(analysis)
        except ValueError as e:
            print(f"  ❌ Error analyzing {symbol}: {e}")
            continue
        except Exception as e:
            print(f"  ❌ Unexpected error for {symbol}: {e}")
            continue
    
    if not analyses:
        print("\n  ❌ No stocks could be analyzed. Please check your symbols.")
        print("  Tip: Add .NS suffix for NSE stocks (e.g., RELIANCE.NS)")
        return
    
    # Get capital if needed
    capital = args.capital
    if capital is None and len(analyses) >= 1:
        capital = get_capital_interactive()
    
    # Print reports
    for analysis in analyses:
        position_data = None
        if capital:
            position_data = {'capital': capital}
        
        print_full_report(analysis, position_data, horizon)
    
    # Print comparison if multiple stocks
    if len(analyses) > 1:
        print_summary_table(analyses)
        
        if args.compare:
            print_portfolio_ranking(analyses)
            
            if capital:
                allocation_data = calculate_portfolio_allocation(analyses, capital, args.mode)
                print_portfolio_allocation(allocation_data, capital)


if __name__ == '__main__':
    main()
