"""
Technical Indicators Module for Stock Analyzer Pro
Calculates all technical indicators used in the analysis
"""

from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator, ADXIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import OnBalanceVolumeIndicator

from config import TIMEFRAME_CONFIGS, FIBONACCI_RETRACEMENT, FIBONACCI_EXTENSION


def calculate_emas(close: pd.Series, config: dict) -> Dict[str, pd.Series]:
    """Calculate all EMA indicators based on timeframe config"""
    emas = {}
    
    # Fast EMA
    ema_fast = EMAIndicator(close, window=config['ema_fast'])
    emas['ema_fast'] = ema_fast.ema_indicator()
    emas['ema_fast_period'] = config['ema_fast']
    
    # Medium EMA
    ema_medium = EMAIndicator(close, window=config['ema_medium'])
    emas['ema_medium'] = ema_medium.ema_indicator()
    emas['ema_medium_period'] = config['ema_medium']
    
    # Slow EMA
    ema_slow = EMAIndicator(close, window=config['ema_slow'])
    emas['ema_slow'] = ema_slow.ema_indicator()
    emas['ema_slow_period'] = config['ema_slow']
    
    # Trend EMA (200 or 100 depending on timeframe)
    ema_trend = EMAIndicator(close, window=config['ema_trend'])
    emas['ema_trend'] = ema_trend.ema_indicator()
    emas['ema_trend_period'] = config['ema_trend']
    
    return emas


def calculate_rsi(close: pd.Series, config: dict) -> Dict[str, any]:
    """Calculate RSI indicator"""
    rsi_indicator = RSIIndicator(close, window=config['rsi_period'])
    rsi = rsi_indicator.rsi()
    
    latest_rsi = rsi.iloc[-1] if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else 50
    
    # Determine RSI zone
    if latest_rsi >= 80:
        zone = 'extremely_overbought'
    elif latest_rsi >= 70:
        zone = 'overbought'
    elif latest_rsi >= 60:
        zone = 'slightly_overbought'
    elif latest_rsi >= 40:
        zone = 'neutral'
    elif latest_rsi >= 30:
        zone = 'slightly_oversold'
    elif latest_rsi >= 20:
        zone = 'oversold'
    else:
        zone = 'extremely_oversold'
    
    # RSI direction (trending up or down)
    rsi_direction = 'neutral'
    if len(rsi) >= 5:
        rsi_5_ago = rsi.iloc[-5] if not pd.isna(rsi.iloc[-5]) else latest_rsi
        if latest_rsi > rsi_5_ago + 5:
            rsi_direction = 'rising'
        elif latest_rsi < rsi_5_ago - 5:
            rsi_direction = 'falling'
    
    return {
        'rsi_series': rsi,
        'rsi': latest_rsi,
        'rsi_zone': zone,
        'rsi_direction': rsi_direction,
        'rsi_period': config['rsi_period']
    }


def calculate_macd(close: pd.Series, config: dict) -> Dict[str, any]:
    """Calculate MACD indicator"""
    macd_indicator = MACD(
        close,
        window_fast=config['macd_fast'],
        window_slow=config['macd_slow'],
        window_sign=config['macd_signal']
    )
    
    macd_line = macd_indicator.macd()
    signal_line = macd_indicator.macd_signal()
    histogram = macd_indicator.macd_diff()
    
    latest_macd = macd_line.iloc[-1] if len(macd_line) > 0 and not pd.isna(macd_line.iloc[-1]) else 0
    latest_signal = signal_line.iloc[-1] if len(signal_line) > 0 and not pd.isna(signal_line.iloc[-1]) else 0
    latest_hist = histogram.iloc[-1] if len(histogram) > 0 and not pd.isna(histogram.iloc[-1]) else 0
    
    # Check for crossover
    crossover = 'none'
    if len(histogram) >= 2:
        prev_hist = histogram.iloc[-2] if not pd.isna(histogram.iloc[-2]) else 0
        if latest_hist > 0 and prev_hist <= 0:
            crossover = 'bullish'
        elif latest_hist < 0 and prev_hist >= 0:
            crossover = 'bearish'
    
    # Histogram direction
    hist_direction = 'neutral'
    if len(histogram) >= 3:
        hist_3_ago = histogram.iloc[-3] if not pd.isna(histogram.iloc[-3]) else latest_hist
        if latest_hist > hist_3_ago:
            hist_direction = 'expanding'
        elif latest_hist < hist_3_ago:
            hist_direction = 'contracting'
    
    return {
        'macd_line': macd_line,
        'signal_line': signal_line,
        'histogram': histogram,
        'macd': latest_macd,
        'macd_signal': latest_signal,
        'macd_hist': latest_hist,
        'macd_crossover': crossover,
        'macd_above_zero': latest_macd > 0,
        'macd_above_signal': latest_macd > latest_signal,
        'hist_direction': hist_direction,
    }


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, config: dict) -> Dict[str, any]:
    """Calculate ADX indicator for trend strength"""
    adx_indicator = ADXIndicator(high, low, close, window=config['adx_period'])
    
    adx = adx_indicator.adx()
    plus_di = adx_indicator.adx_pos()
    minus_di = adx_indicator.adx_neg()
    
    latest_adx = adx.iloc[-1] if len(adx) > 0 and not pd.isna(adx.iloc[-1]) else 20
    latest_plus_di = plus_di.iloc[-1] if len(plus_di) > 0 and not pd.isna(plus_di.iloc[-1]) else 25
    latest_minus_di = minus_di.iloc[-1] if len(minus_di) > 0 and not pd.isna(minus_di.iloc[-1]) else 25
    
    # Determine trend strength
    if latest_adx >= 60:
        strength = 'very_strong_trend'
    elif latest_adx >= 40:
        strength = 'strong_trend'
    elif latest_adx >= 25:
        strength = 'trend'
    elif latest_adx >= 20:
        strength = 'weak_trend'
    else:
        strength = 'no_trend'
    
    # Trend direction from DI
    trend_direction = 'neutral'
    if latest_plus_di > latest_minus_di + 5:
        trend_direction = 'bullish'
    elif latest_minus_di > latest_plus_di + 5:
        trend_direction = 'bearish'
    
    return {
        'adx': latest_adx,
        'plus_di': latest_plus_di,
        'minus_di': latest_minus_di,
        'adx_strength': strength,
        'adx_trend_direction': trend_direction,
        'trend_exists': latest_adx >= 25,
    }


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, config: dict) -> Dict[str, any]:
    """Calculate ATR for volatility"""
    atr_indicator = AverageTrueRange(high, low, close, window=config['atr_period'])
    atr = atr_indicator.average_true_range()
    
    latest_atr = atr.iloc[-1] if len(atr) > 0 and not pd.isna(atr.iloc[-1]) else close.iloc[-1] * 0.02
    latest_price = close.iloc[-1]
    atr_percent = (latest_atr / latest_price) * 100
    
    # Volatility level
    if atr_percent >= 5:
        volatility = 'very_high'
    elif atr_percent >= 3:
        volatility = 'high'
    elif atr_percent >= 1.5:
        volatility = 'normal'
    elif atr_percent >= 0.75:
        volatility = 'low'
    else:
        volatility = 'very_low'
    
    return {
        'atr': latest_atr,
        'atr_percent': atr_percent,
        'volatility_level': volatility,
    }


def calculate_bollinger_bands(close: pd.Series, config: dict) -> Dict[str, any]:
    """Calculate Bollinger Bands"""
    bb = BollingerBands(close, window=config['bb_period'], window_dev=config['bb_std'])
    
    upper = bb.bollinger_hband()
    middle = bb.bollinger_mavg()
    lower = bb.bollinger_lband()
    percent_b = bb.bollinger_pband()  # %B indicator
    bandwidth = bb.bollinger_wband()
    
    latest_upper = upper.iloc[-1] if len(upper) > 0 and not pd.isna(upper.iloc[-1]) else close.iloc[-1] * 1.02
    latest_middle = middle.iloc[-1] if len(middle) > 0 and not pd.isna(middle.iloc[-1]) else close.iloc[-1]
    latest_lower = lower.iloc[-1] if len(lower) > 0 and not pd.isna(lower.iloc[-1]) else close.iloc[-1] * 0.98
    latest_percent_b = percent_b.iloc[-1] if len(percent_b) > 0 and not pd.isna(percent_b.iloc[-1]) else 0.5
    latest_bandwidth = bandwidth.iloc[-1] if len(bandwidth) > 0 and not pd.isna(bandwidth.iloc[-1]) else 0.04
    
    latest_price = close.iloc[-1]
    
    # Position within bands
    if latest_price > latest_upper:
        position = 'above_upper'
    elif latest_price > latest_middle:
        position = 'upper_half'
    elif latest_price > latest_lower:
        position = 'lower_half'
    else:
        position = 'below_lower'
    
    return {
        'bb_upper': latest_upper,
        'bb_middle': latest_middle,
        'bb_lower': latest_lower,
        'bb_percent': latest_percent_b,
        'bb_bandwidth': latest_bandwidth,
        'bb_position': position,
    }


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, config: dict) -> Dict[str, any]:
    """Calculate Stochastic Oscillator"""
    stoch = StochasticOscillator(high, low, close, window=14, smooth_window=3)
    
    stoch_k = stoch.stoch()
    stoch_d = stoch.stoch_signal()
    
    latest_k = stoch_k.iloc[-1] if len(stoch_k) > 0 and not pd.isna(stoch_k.iloc[-1]) else 50
    latest_d = stoch_d.iloc[-1] if len(stoch_d) > 0 and not pd.isna(stoch_d.iloc[-1]) else 50
    
    # Determine zone
    if latest_k >= 85:
        zone = 'extremely_overbought'
    elif latest_k >= 80:
        zone = 'overbought'
    elif latest_k <= 15:
        zone = 'extremely_oversold'
    elif latest_k <= 20:
        zone = 'oversold'
    else:
        zone = 'neutral'
    
    return {
        'stoch_k': latest_k,
        'stoch_d': latest_d,
        'stoch_zone': zone,
    }


def calculate_volume_indicators(df: pd.DataFrame, config: dict) -> Dict[str, any]:
    """Calculate volume-based indicators"""
    close = df['close']
    volume = df['volume'] if 'volume' in df.columns else pd.Series([0] * len(df))
    
    # Volume ratio
    avg_volume = volume.tail(config['volume_avg_period']).mean()
    latest_volume = volume.iloc[-1] if len(volume) > 0 else 0
    volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1
    
    # OBV
    obv_indicator = OnBalanceVolumeIndicator(close, volume)
    obv = obv_indicator.on_balance_volume()
    
    # OBV trend
    obv_trend = 'neutral'
    if len(obv) >= 10:
        obv_10_ago = obv.iloc[-10] if not pd.isna(obv.iloc[-10]) else obv.iloc[-1]
        obv_change = (obv.iloc[-1] - obv_10_ago) / abs(obv_10_ago) * 100 if obv_10_ago != 0 else 0
        if obv_change > 5:
            obv_trend = 'rising'
        elif obv_change < -5:
            obv_trend = 'falling'
    
    # Volume level
    if volume_ratio >= 2.0:
        volume_level = 'very_high'
    elif volume_ratio >= 1.5:
        volume_level = 'high'
    elif volume_ratio >= 0.7:
        volume_level = 'normal'
    elif volume_ratio >= 0.5:
        volume_level = 'low'
    else:
        volume_level = 'very_low'
    
    return {
        'volume_ratio': volume_ratio,
        'volume_level': volume_level,
        'avg_volume': avg_volume,
        'latest_volume': latest_volume,
        'obv_trend': obv_trend,
    }


def detect_divergence(
    price: pd.Series,
    indicator: pd.Series,
    lookback: int = 14
) -> str:
    """
    Detect bullish or bearish divergence between price and indicator
    
    Bullish divergence: Price makes lower low, indicator makes higher low
    Bearish divergence: Price makes higher high, indicator makes lower high
    """
    if len(price) < lookback or len(indicator) < lookback:
        return 'none'
    
    price_window = price.tail(lookback)
    indicator_window = indicator.tail(lookback)
    
    # Find recent highs and lows
    price_high_idx = price_window.idxmax()
    price_low_idx = price_window.idxmin()
    
    # Get values at those points
    price_at_high = price_window.loc[price_high_idx]
    price_at_low = price_window.loc[price_low_idx]
    
    # Compare with indicator at same points
    try:
        ind_at_price_high = indicator_window.loc[price_high_idx]
        ind_at_price_low = indicator_window.loc[price_low_idx]
    except KeyError:
        return 'none'
    
    # Check for divergence in recent data vs previous
    half_lookback = lookback // 2
    
    if len(price_window) >= lookback:
        # First half vs second half comparison
        first_half_price = price_window.iloc[:half_lookback]
        second_half_price = price_window.iloc[half_lookback:]
        first_half_ind = indicator_window.iloc[:half_lookback]
        second_half_ind = indicator_window.iloc[half_lookback:]
        
        # Bearish divergence: Price higher high, indicator lower high
        if (second_half_price.max() > first_half_price.max() and 
            second_half_ind.max() < first_half_ind.max()):
            return 'bearish'
        
        # Bullish divergence: Price lower low, indicator higher low
        if (second_half_price.min() < first_half_price.min() and 
            second_half_ind.min() > first_half_ind.min()):
            return 'bullish'
    
    return 'none'


def calculate_support_resistance(df: pd.DataFrame, config: dict) -> Dict[str, any]:
    """Calculate support and resistance levels"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    lookback = config['support_lookback']
    
    # Recent support and resistance
    recent_high = high.tail(lookback).max()
    recent_low = low.tail(lookback).min()
    
    # 52-week high/low (or available data)
    all_time_high = high.max()
    all_time_low = low.min()
    
    current_price = close.iloc[-1]
    
    # Distance to key levels
    distance_to_resistance = ((recent_high - current_price) / current_price) * 100
    distance_to_support = ((current_price - recent_low) / current_price) * 100
    
    # Proximity assessment
    if distance_to_resistance <= 2:
        resistance_proximity = 'very_close'
    elif distance_to_resistance <= 5:
        resistance_proximity = 'close'
    else:
        resistance_proximity = 'far'
    
    if distance_to_support <= 2:
        support_proximity = 'very_close'
    elif distance_to_support <= 5:
        support_proximity = 'close'
    else:
        support_proximity = 'far'
    
    return {
        'resistance': recent_high,
        'support': recent_low,
        'high_52w': all_time_high,
        'low_52w': all_time_low,
        'distance_to_resistance': distance_to_resistance,
        'distance_to_support': distance_to_support,
        'resistance_proximity': resistance_proximity,
        'support_proximity': support_proximity,
    }


def calculate_fibonacci_levels(high: float, low: float, current_price: float) -> Dict[str, any]:
    """Calculate Fibonacci retracement and extension levels"""
    price_range = high - low
    
    # Retracement levels (for pullbacks in uptrend)
    retracements = {}
    for level in FIBONACCI_RETRACEMENT:
        retracements[f'fib_{int(level*100)}'] = high - (price_range * level)
    
    # Extension levels (for targets)
    extensions = {}
    for level in FIBONACCI_EXTENSION:
        extensions[f'fib_ext_{int(level*100)}'] = low + (price_range * level)
    
    # Find nearest Fibonacci level
    all_levels = {**retracements, **extensions}
    nearest_level = min(all_levels.items(), key=lambda x: abs(x[1] - current_price))
    
    return {
        'fib_retracements': retracements,
        'fib_extensions': extensions,
        'nearest_fib_level': nearest_level[0],
        'nearest_fib_price': nearest_level[1],
    }


def calculate_momentum(close: pd.Series, config: dict) -> Dict[str, any]:
    """Calculate price momentum"""
    period = config['momentum_period']
    
    if len(close) < period:
        return {
            'momentum': 0,
            'momentum_direction': 'neutral',
        }
    
    current = close.iloc[-1]
    past = close.iloc[-period]
    
    momentum = ((current - past) / past) * 100
    
    if momentum > 5:
        direction = 'strong_up'
    elif momentum > 2:
        direction = 'up'
    elif momentum < -5:
        direction = 'strong_down'
    elif momentum < -2:
        direction = 'down'
    else:
        direction = 'neutral'
    
    return {
        'momentum': momentum,
        'momentum_direction': direction,
        'momentum_period': period,
    }


def calculate_all_indicators(df: pd.DataFrame, timeframe: str = 'medium') -> Dict[str, any]:
    """
    Calculate all technical indicators for analysis
    
    Args:
        df: DataFrame with OHLCV data
        timeframe: 'short' or 'medium'
    
    Returns:
        Dictionary containing all calculated indicators
    """
    config = TIMEFRAME_CONFIGS[timeframe]
    
    close = df['close']
    high = df['high']
    low = df['low']
    
    # Current price
    current_price = close.iloc[-1]
    
    # Calculate all indicators
    emas = calculate_emas(close, config)
    rsi_data = calculate_rsi(close, config)
    macd_data = calculate_macd(close, config)
    adx_data = calculate_adx(high, low, close, config)
    atr_data = calculate_atr(high, low, close, config)
    bb_data = calculate_bollinger_bands(close, config)
    stoch_data = calculate_stochastic(high, low, close, config)
    volume_data = calculate_volume_indicators(df, config)
    sr_data = calculate_support_resistance(df, config)
    momentum_data = calculate_momentum(close, config)
    fib_data = calculate_fibonacci_levels(sr_data['high_52w'], sr_data['low_52w'], current_price)
    
    # Detect divergences
    rsi_divergence = detect_divergence(close, rsi_data['rsi_series'], config['divergence_lookback'])
    macd_divergence = detect_divergence(close, macd_data['histogram'], config['divergence_lookback'])
    
    # Combined divergence signal
    if rsi_divergence == 'bearish' or macd_divergence == 'bearish':
        divergence = 'bearish'
    elif rsi_divergence == 'bullish' or macd_divergence == 'bullish':
        divergence = 'bullish'
    else:
        divergence = 'none'
    
    # EMA alignment check
    latest_ema_fast = emas['ema_fast'].iloc[-1] if not pd.isna(emas['ema_fast'].iloc[-1]) else current_price
    latest_ema_medium = emas['ema_medium'].iloc[-1] if not pd.isna(emas['ema_medium'].iloc[-1]) else current_price
    latest_ema_slow = emas['ema_slow'].iloc[-1] if not pd.isna(emas['ema_slow'].iloc[-1]) else current_price
    latest_ema_trend = emas['ema_trend'].iloc[-1] if len(emas['ema_trend']) > 0 and not pd.isna(emas['ema_trend'].iloc[-1]) else current_price
    
    # EMA alignment (bullish: fast > medium > slow > trend)
    if latest_ema_fast > latest_ema_medium > latest_ema_slow > latest_ema_trend:
        ema_alignment = 'strong_bullish'
    elif current_price > latest_ema_trend and latest_ema_fast > latest_ema_medium:
        ema_alignment = 'bullish'
    elif latest_ema_fast < latest_ema_medium < latest_ema_slow < latest_ema_trend:
        ema_alignment = 'strong_bearish'
    elif current_price < latest_ema_trend and latest_ema_fast < latest_ema_medium:
        ema_alignment = 'bearish'
    else:
        ema_alignment = 'neutral'
    
    # Market phase determination
    if ema_alignment == 'strong_bullish' and adx_data['trend_exists']:
        market_phase = 'strong_uptrend'
    elif current_price > latest_ema_trend and adx_data['trend_exists']:
        market_phase = 'uptrend'
    elif current_price > latest_ema_trend and not adx_data['trend_exists']:
        market_phase = 'weak_uptrend'
    elif ema_alignment == 'strong_bearish' and adx_data['trend_exists']:
        market_phase = 'strong_downtrend'
    elif current_price < latest_ema_trend and adx_data['trend_exists']:
        market_phase = 'downtrend'
    elif current_price < latest_ema_trend and not adx_data['trend_exists']:
        market_phase = 'weak_downtrend'
    else:
        market_phase = 'consolidation'
    
    # Compile all indicators
    indicators = {
        'current_price': current_price,
        'timeframe': timeframe,
        'config': config,
        
        # EMAs
        'ema_fast': latest_ema_fast,
        'ema_medium': latest_ema_medium,
        'ema_slow': latest_ema_slow,
        'ema_trend': latest_ema_trend,
        'ema_fast_period': emas['ema_fast_period'],
        'ema_medium_period': emas['ema_medium_period'],
        'ema_slow_period': emas['ema_slow_period'],
        'ema_trend_period': emas['ema_trend_period'],
        'ema_alignment': ema_alignment,
        'price_vs_trend_ema': 'above' if current_price > latest_ema_trend else 'below',
        'price_vs_medium_ema': 'above' if current_price > latest_ema_medium else 'below',
        'price_vs_fast_ema': 'above' if current_price > latest_ema_fast else 'below',
        
        # RSI
        **rsi_data,
        
        # MACD
        **macd_data,
        
        # ADX
        **adx_data,
        
        # ATR
        **atr_data,
        
        # Bollinger Bands
        **bb_data,
        
        # Stochastic
        **stoch_data,
        
        # Volume
        **volume_data,
        
        # Support/Resistance
        **sr_data,
        
        # Momentum
        **momentum_data,
        
        # Fibonacci
        **fib_data,
        
        # Divergence
        'rsi_divergence': rsi_divergence,
        'macd_divergence': macd_divergence,
        'divergence': divergence,
        
        # Market phase
        'market_phase': market_phase,
    }
    
    return indicators
