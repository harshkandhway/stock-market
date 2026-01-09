"""
Analysis Service for Telegram Bot
Wraps core analysis modules and provides bot-friendly interface

Author: Harsh Kandhway
"""

import sys
import os
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.core.config import TIMEFRAME_CONFIGS, RISK_MODES
from src.core.indicators import calculate_all_indicators
from src.core.signals import (
    check_hard_filters, calculate_all_signals, get_confidence_level,
    determine_recommendation, generate_reasoning, generate_action_plan
)
from src.core.risk_management import (
    calculate_targets, calculate_stoploss, validate_risk_reward,
    calculate_trailing_stops, estimate_time_to_target, calculate_safety_score
)

from src.bot.config import ENABLE_ANALYSIS_CACHE, CACHE_EXPIRY_MINUTES
from src.bot.database.db import get_db_context
from src.bot.database.models import AnalysisCache


def fetch_stock_data(symbol: str, period: str = '1y') -> pd.DataFrame:
    """
    Fetch historical stock data from Yahoo Finance
    
    Args:
        symbol: Stock ticker symbol
        period: Data period
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        from yahooquery import Ticker
        
        ticker = Ticker(symbol)
        df = ticker.history(period=period, interval='1d')
        
        # Check for errors
        if isinstance(df, str):
            raise ValueError(f"Error fetching data: {df}")
        
        if not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError("No data returned")
        
        # Flatten multi-index if present
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index(level=0, drop=True)
        
        # Handle timezone issues - convert to naive datetime
        # If index is already DatetimeIndex with timezone, convert to UTC then remove tz
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is not None:
                df.index = df.index.tz_convert('UTC').tz_localize(None)
        else:
            # Convert to datetime, handling timezone-aware values
            try:
                df.index = pd.to_datetime(df.index, utc=True)
                # If conversion succeeded with UTC, remove timezone
                if df.index.tz is not None:
                    df.index = df.index.tz_convert('UTC').tz_localize(None)
            except (ValueError, TypeError):
                # If UTC conversion fails, try without timezone
                df.index = pd.to_datetime(df.index, utc=False)
        
        return df
        
    except Exception as e:
        raise ValueError(f"Failed to fetch data for {symbol}: {str(e)}")


def get_cached_analysis(symbol: str, mode: str, timeframe: str) -> Optional[Dict]:
    """
    Get cached analysis if available and not expired
    
    Args:
        symbol: Stock symbol
        mode: Risk mode
        timeframe: Timeframe
    
    Returns:
        Cached analysis dict or None
    """
    if not ENABLE_ANALYSIS_CACHE:
        return None
    
    try:
        with get_db_context() as db:
            cache = db.query(AnalysisCache).filter(
                AnalysisCache.symbol == symbol,
                AnalysisCache.mode == mode,
                AnalysisCache.timeframe == timeframe,
                AnalysisCache.expires_at > datetime.utcnow()
            ).first()
            
            if cache and not cache.is_expired():
                return cache.data
            
            return None
            
    except Exception:
        return None


def save_analysis_cache(symbol: str, mode: str, timeframe: str, analysis: Dict):
    """
    Save analysis to cache
    
    Args:
        symbol: Stock symbol
        mode: Risk mode
        timeframe: Timeframe
        analysis: Analysis dictionary
    """
    if not ENABLE_ANALYSIS_CACHE:
        return
    
    try:
        with get_db_context() as db:
            # Delete old cache for this symbol/mode/timeframe
            db.query(AnalysisCache).filter(
                AnalysisCache.symbol == symbol,
                AnalysisCache.mode == mode,
                AnalysisCache.timeframe == timeframe
            ).delete()
            
            # Create new cache entry
            expires_at = datetime.utcnow() + timedelta(minutes=CACHE_EXPIRY_MINUTES)
            
            cache = AnalysisCache(
                symbol=symbol,
                mode=mode,
                timeframe=timeframe,
                expires_at=expires_at
            )
            cache.data = analysis  # Uses property setter
            
            db.add(cache)
            db.commit()
            
    except Exception as e:
        # Cache failure shouldn't break analysis
        print(f"Warning: Failed to cache analysis: {e}")


def analyze_stock(
    symbol: str,
    mode: str = 'balanced',
    timeframe: str = 'medium',
    horizon: str = '3months',
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Analyze a stock with technical indicators
    
    Args:
        symbol: Stock ticker symbol
        mode: Risk mode (conservative, balanced, aggressive)
        timeframe: Analysis timeframe (short, medium)
        horizon: Investment horizon (1week, 2weeks, 1month, 3months, 6months, 1year)
        use_cache: Whether to use cached results
    
    Returns:
        Analysis dictionary with all results
    
    Raises:
        ValueError: If symbol is invalid or analysis fails
    """
    # Validate inputs
    symbol = symbol.strip().upper()
    
    if not symbol:
        raise ValueError("Symbol cannot be empty")
    
    if mode not in RISK_MODES:
        raise ValueError(f"Invalid mode: {mode}")
    
    if timeframe not in TIMEFRAME_CONFIGS:
        raise ValueError(f"Invalid timeframe: {timeframe}")
    
    # Check cache first
    if use_cache:
        cached = get_cached_analysis(symbol, mode, timeframe)
        if cached:
            return cached
    
    # Get configuration
    tf_config = TIMEFRAME_CONFIGS[timeframe]
    data_period = tf_config['data_period']
    
    # Fetch data
    try:
        df = fetch_stock_data(symbol, data_period)
    except Exception as e:
        raise ValueError(f"Data fetch failed: {str(e)}")
    
    if df.empty or len(df) < 50:
        raise ValueError(f"Insufficient data for {symbol}")
    
    # Calculate indicators
    try:
        indicators = calculate_all_indicators(df, timeframe)
    except Exception as e:
        raise ValueError(f"Indicator calculation failed: {str(e)}")
    
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
    
    # Get price and key indicators
    current_price = indicators['current_price']
    atr = indicators['atr']
    support = indicators['support']
    resistance = indicators['resistance']
    fib_extensions = indicators['fib_extensions']
    
    # Always calculate long targets for beginners
    direction = 'long'
    
    # Get strongest pattern for pattern-based target calculation
    strongest_pattern = indicators.get('strongest_pattern')
    
    # Calculate targets (with horizon for multi-timeframe targets + pattern integration)
    target_data = calculate_targets(
        current_price, atr, resistance, support,
        fib_extensions, mode, direction, horizon,
        strongest_pattern  # NEW: Pass pattern for measured move integration
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
    
    # Calculate safety score
    safety_score = calculate_safety_score(
        confidence,
        risk_reward,
        indicators['adx'],
        indicators['rsi'],
        is_blocked,
        horizon
    )
    
    # Compile analysis result
    analysis = {
        'symbol': symbol,
        'mode': mode,
        'timeframe': tf_config['name'],
        'horizon': horizon,
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
        'analyzed_at': datetime.utcnow().isoformat(),
    }
    
    # Cache the result
    save_analysis_cache(symbol, mode, timeframe, analysis)
    
    return analysis


def analyze_multiple_stocks(
    symbols: List[str],
    mode: str = 'balanced',
    timeframe: str = 'medium'
) -> List[Dict[str, Any]]:
    """
    Analyze multiple stocks
    
    Args:
        symbols: List of stock symbols
        mode: Risk mode
        timeframe: Timeframe
    
    Returns:
        List of analysis dictionaries
    """
    results = []
    
    for symbol in symbols:
        try:
            analysis = analyze_stock(symbol, mode, timeframe)
            results.append(analysis)
        except Exception as e:
            # Include error in results
            results.append({
                'symbol': symbol,
                'error': True,
                'error_message': str(e)
            })
    
    return results


def get_current_price(symbol: str) -> Optional[float]:
    """
    Get current price for a symbol (quick fetch)
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Current price or None if fetch fails
    """
    try:
        df = fetch_stock_data(symbol, period='5d')
        if not df.empty:
            return float(df['close'].iloc[-1])
        return None
    except Exception:
        return None


def get_multiple_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Get current prices for multiple symbols
    
    Args:
        symbols: List of stock symbols
    
    Returns:
        Dictionary of symbol -> price
    """
    prices = {}
    
    for symbol in symbols:
        price = get_current_price(symbol)
        if price:
            prices[symbol] = price
    
    return prices


def search_symbol(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Search for stock symbols by name or ticker
    
    Uses yahooquery to search for symbols and get company information.
    
    Args:
        query: Search query (can be company name or ticker)
        limit: Maximum results
    
    Returns:
        List of matching stocks with symbol, name, and exchange
    """
    from yahooquery import Ticker
    
    query = query.strip().upper()
    results = []
    
    # First, try to read from stock_tickers.csv if available (faster)
    try:
        import csv
        tickers_file = os.path.join(os.path.dirname(__file__), '../../../data/stock_tickers.csv')
        
        if os.path.exists(tickers_file):
            with open(tickers_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticker = row.get('ticker', '').upper()
                    name = row.get('name', '').upper()
                    market = row.get('market', '')
                    
                    # Check if query matches ticker or name
                    if query in ticker or (name and query in name):
                        # Try to get company info from yahooquery
                        try:
                            ticker_obj = Ticker(ticker)
                            quote = ticker_obj.quote_type
                            
                            if quote and ticker in quote:
                                company_info = quote[ticker]
                                full_name = company_info.get('longName', company_info.get('shortName', name))
                                exchange = company_info.get('exchange', market)
                                
                                results.append({
                                    'symbol': ticker,
                                    'name': full_name,
                                    'exchange': exchange or market or 'Unknown'
                                })
                            else:
                                # Fallback to CSV data
                                results.append({
                                    'symbol': ticker,
                                    'name': row.get('name', ''),
                                    'exchange': market or 'Unknown'
                                })
                        except Exception:
                            # Fallback to CSV data
                            results.append({
                                'symbol': ticker,
                                'name': row.get('name', ''),
                                'exchange': market or 'Unknown'
                            })
                        
                        if len(results) >= limit:
                            break
    except Exception as e:
        logger.warning(f"Error reading tickers file: {e}")
    
    # If no results from CSV, try direct yahooquery lookup
    if not results:
        # Try common suffixes for Indian stocks
        suffixes = ['.NS', '.BO', '']
        for suffix in suffixes:
            test_symbol = query + suffix if suffix else query
            try:
                ticker_obj = Ticker(test_symbol)
                quote = ticker_obj.quote_type
                
                if quote and test_symbol in quote:
                    company_info = quote[test_symbol]
                    full_name = company_info.get('longName', company_info.get('shortName', ''))
                    exchange = company_info.get('exchange', 'Unknown')
                    
                    results.append({
                        'symbol': test_symbol,
                        'name': full_name,
                        'exchange': exchange
                    })
                    break
            except Exception:
                continue
    
    return results[:limit]


def validate_symbol(symbol: str) -> bool:
    """
    Validate that a symbol exists and has data
    
    Args:
        symbol: Stock symbol
    
    Returns:
        True if valid, False otherwise
    """
    try:
        df = fetch_stock_data(symbol, period='5d')
        return not df.empty
    except Exception:
        return False
