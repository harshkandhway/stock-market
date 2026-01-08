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
    """
    Fetch historical data from Yahoo Finance
    
    Args:
        symbol: Stock ticker symbol (e.g., 'RELIANCE.NS')
        period: Data period ('1y', '3mo', etc.)
    
    Returns:
        DataFrame with OHLCV data, or empty DataFrame on error
    """
    if not symbol or not isinstance(symbol, str):
        print(f"  Error: Invalid symbol '{symbol}'")
        return pd.DataFrame()
    
    try:
        ticker = Ticker(symbol)
        df = ticker.history(period=period, interval='1d')
        
        # Check for error message (yahooquery sometimes returns strings)
        if isinstance(df, str):
            print(f"  Error fetching {symbol}: {df}")
            return pd.DataFrame()
        
        # Validate DataFrame structure
        if not isinstance(df, pd.DataFrame):
            print(f"  Error: Unexpected data type for {symbol}")
            return pd.DataFrame()
        
        if df.empty:
            print(f"  Warning: No data available for {symbol} (period: {period})")
            return pd.DataFrame()
        
        # Check required columns
        required_columns = ['close', 'high', 'low', 'open']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"  Error: Missing required columns for {symbol}: {missing_columns}")
            return pd.DataFrame()
        
        # Validate data quality
        if len(df) < 50:
            print(f"  Warning: Insufficient data for {symbol} ({len(df)} rows, need at least 50)")
        
        # Check for NaN values in critical columns
        if df['close'].isna().all():
            print(f"  Error: No valid price data for {symbol}")
            return pd.DataFrame()
        
        # Flatten multi-index if present
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index(level=0, drop=True)
        
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except (ValueError, TypeError):
                print(f"  Warning: Could not convert index to datetime for {symbol}")
        
        return df
        
    except KeyError as e:
        print(f"  Error: Invalid period '{period}' for {symbol}: {e}")
        return pd.DataFrame()
    except AttributeError as e:
        print(f"  Error: Invalid symbol format '{symbol}': {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"  Error fetching {symbol}: {type(e).__name__}: {e}")
        return pd.DataFrame()


def analyze_stock(
    symbol: str,
    df: pd.DataFrame,
    mode: str = 'balanced',
    timeframe: str = 'medium'
) -> Dict:
    """
    Perform complete technical analysis on a stock
    
    Args:
        symbol: Stock ticker symbol
        df: DataFrame with OHLCV data
        mode: Risk mode ('conservative', 'balanced', 'aggressive')
        timeframe: Timeframe ('short' or 'medium')
    
    Returns:
        Comprehensive analysis dictionary
    
    Raises:
        ValueError: If inputs are invalid or analysis cannot be performed
    """
    # Validate inputs
    if not symbol or not isinstance(symbol, str):
        raise ValueError(f"Invalid symbol: {symbol}")
    
    if df is None or df.empty:
        raise ValueError(f"Invalid or empty DataFrame for {symbol}")
    
    if mode not in RISK_MODES:
        raise ValueError(f"Invalid mode: {mode}. Must be one of {list(RISK_MODES.keys())}")
    
    if timeframe not in TIMEFRAME_CONFIGS:
        raise ValueError(f"Invalid timeframe: {timeframe}. Must be 'short' or 'medium'")
    
    # Get configurations
    tf_config = TIMEFRAME_CONFIGS[timeframe]
    mode_config = RISK_MODES[mode]
    
    # Calculate all indicators (may raise ValueError)
    try:
        indicators = calculate_all_indicators(df, timeframe)
    except ValueError as e:
        raise ValueError(f"Indicator calculation failed for {symbol}: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error calculating indicators for {symbol}: {e}")
    
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
    """
    Get capital from user interactively with validation
    
    Returns:
        Capital amount as float, or None if cancelled/invalid
    """
    try:
        response = input("\n  Would you like to calculate position sizes? (y/n): ").strip().lower()
        if response not in ['y', 'yes']:
            return None
        
        max_attempts = 3
        for attempt in range(max_attempts):
            capital_str = input(f"  Enter your capital ({CURRENCY_SYMBOL}): ").strip()
            
            if not capital_str:
                print("  Error: Capital cannot be empty")
                continue
            
            # Clean input: remove commas, currency symbols, whitespace
            capital_str = capital_str.replace(',', '').replace(CURRENCY_SYMBOL, '').strip()
            
            try:
                capital = float(capital_str)
                
                # Validate capital amount
                if capital <= 0:
                    print(f"  Error: Capital must be greater than 0")
                    continue
                
                if capital < 1000:
                    print(f"  Warning: Capital ({CURRENCY_SYMBOL}{capital:,.2f}) is very low")
                    confirm = input("  Continue anyway? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes']:
                        return None
                
                if capital > 1e12:  # 1 trillion
                    print(f"  Error: Capital amount seems unreasonably high")
                    continue
                
                return capital
                
            except ValueError:
                print(f"  Error: Invalid number format. Please enter a valid amount (attempt {attempt + 1}/{max_attempts})")
                if attempt == max_attempts - 1:
                    print("  Maximum attempts reached. Skipping position sizing.")
                    return None
                continue
        
        return None
        
    except EOFError:
        print("\n  Input cancelled (EOF)")
        return None
    except KeyboardInterrupt:
        print("\n  Input cancelled by user")
        return None
    except Exception as e:
        print(f"  Unexpected error getting capital: {e}")
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
    
    # Validate symbols
    if not args.symbols:
        print("\n  Error: No symbols provided for analysis")
        return
    
    # Analyze each stock
    analyses = []
    
    for symbol in args.symbols:
        # Validate symbol format
        if not symbol or not isinstance(symbol, str) or len(symbol.strip()) == 0:
            print(f"  Warning: Skipping invalid symbol '{symbol}'")
            continue
        
        symbol = symbol.strip().upper()
        print(f"\n  Fetching data for {symbol}...")
        df = fetch_data(symbol, data_period)
        
        if df.empty:
            print(f"  Skipping {symbol} - no data available")
            continue
        
        print(f"  Analyzing {symbol}...")
        try:
            analysis = analyze_stock(symbol, df, args.mode, args.timeframe)
            analyses.append(analysis)
        except ValueError as e:
            print(f"  Error analyzing {symbol}: {e}")
            continue
        except Exception as e:
            print(f"  Unexpected error analyzing {symbol}: {type(e).__name__}: {e}")
            continue
    
    if not analyses:
        print("\n  No stocks could be analyzed. Please check your symbols.")
        return
    
    # Get capital if not provided via CLI
    capital = args.capital
    if capital is not None:
        # Validate CLI-provided capital
        if capital <= 0:
            print(f"\n  Error: Invalid capital amount: {capital}")
            capital = None
        elif capital < 1000:
            print(f"\n  Warning: Capital ({CURRENCY_SYMBOL}{capital:,.2f}) is very low")
    
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
