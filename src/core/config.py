"""
Configuration module for Stock Analyzer Pro
Contains all configurable parameters, thresholds, and mode settings

Author: Harsh Kandhway
"""

from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta

# =============================================================================
# INVESTMENT HORIZON CONFIGURATIONS (Beginner-Friendly)
# =============================================================================

INVESTMENT_HORIZONS = {
    '1week': {
        'name': 'Quick Trade',
        'display_name': '1 Week',
        'description': 'Very short-term trade for quick gains',
        'min_days': 3,
        'max_days': 7,
        'avg_days': 5,
        'data_period': '3mo',
        'timeframe_key': 'short',
        'expected_return_min': 1.5,
        'expected_return_max': 3.0,
        'risk_level': 'HIGH',
        'suitable_for': 'Experienced traders only',
        'emoji': '⚡',
    },
    '2weeks': {
        'name': 'Swing Trade',
        'display_name': '2 Weeks',
        'description': 'Short-term swing trade',
        'min_days': 7,
        'max_days': 14,
        'avg_days': 10,
        'data_period': '3mo',
        'timeframe_key': 'short',
        'expected_return_min': 2.0,
        'expected_return_max': 5.0,
        'risk_level': 'MEDIUM-HIGH',
        'suitable_for': 'Active traders',
        'emoji': '🔄',
    },
    '1month': {
        'name': 'Short Position',
        'display_name': '1 Month',
        'description': 'Hold for about a month',
        'min_days': 21,
        'max_days': 35,
        'avg_days': 28,
        'data_period': '6mo',
        'timeframe_key': 'short',
        'expected_return_min': 3.0,
        'expected_return_max': 8.0,
        'risk_level': 'MEDIUM',
        'suitable_for': 'Most investors',
        'emoji': '📅',
    },
    '3months': {
        'name': 'Medium Position',
        'display_name': '3 Months',
        'description': 'Standard investment period',
        'min_days': 60,
        'max_days': 100,
        'avg_days': 90,
        'data_period': '1y',
        'timeframe_key': 'medium',
        'expected_return_min': 5.0,
        'expected_return_max': 15.0,
        'risk_level': 'MEDIUM-LOW',
        'suitable_for': 'Recommended for beginners',
        'emoji': '📊',
    },
    '6months': {
        'name': 'Long Position',
        'display_name': '6 Months',
        'description': 'Patient investment for better returns',
        'min_days': 150,
        'max_days': 200,
        'avg_days': 180,
        'data_period': '2y',
        'timeframe_key': 'medium',
        'expected_return_min': 8.0,
        'expected_return_max': 25.0,
        'risk_level': 'LOW',
        'suitable_for': 'Ideal for beginners',
        'emoji': '🎯',
    },
    '1year': {
        'name': 'Long-Term Investment',
        'display_name': '1 Year',
        'description': 'Wealth building investment',
        'min_days': 300,
        'max_days': 400,
        'avg_days': 365,
        'data_period': '5y',
        'timeframe_key': 'medium',
        'expected_return_min': 12.0,
        'expected_return_max': 40.0,
        'risk_level': 'VERY LOW',
        'suitable_for': 'Best for wealth creation',
        'emoji': '💎',
    },
}

# =============================================================================
# TIMEFRAME CONFIGURATIONS (Technical)
# =============================================================================

TIMEFRAME_CONFIGS = {
    'short': {
        'name': 'SHORT-TERM',
        'description': 'Optimized for swing trades lasting 1-4 weeks',
        'data_period': '3mo',
        'ema_fast': 9,
        'ema_medium': 21,
        'ema_slow': 50,
        'ema_trend': 100,
        'rsi_period': 9,
        'macd_fast': 8,
        'macd_slow': 17,
        'macd_signal': 9,
        'atr_period': 10,
        'adx_period': 10,
        'bb_period': 20,
        'bb_std': 2,
        'support_lookback': 10,
        'resistance_lookback': 10,
        'momentum_period': 5,
        'divergence_lookback': 10,
        'volume_avg_period': 10,
    },
    'medium': {
        'name': 'MEDIUM-TERM',
        'description': 'Optimized for position trades lasting 1-3 months',
        'data_period': '1y',
        'ema_fast': 20,
        'ema_medium': 50,
        'ema_slow': 100,
        'ema_trend': 200,
        'rsi_period': 14,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'atr_period': 14,
        'adx_period': 14,
        'bb_period': 20,
        'bb_std': 2,
        'support_lookback': 20,
        'resistance_lookback': 20,
        'momentum_period': 10,
        'divergence_lookback': 14,
        'volume_avg_period': 20,
    }
}

# =============================================================================
# MARKET HEALTH THRESHOLDS (Beginner-Friendly Scoring)
# =============================================================================

MARKET_HEALTH_SCORES = {
    'EXCELLENT': {'min': 80, 'max': 100, 'emoji': '🟢', 'advice': 'Great time to invest!'},
    'GOOD': {'min': 65, 'max': 79, 'emoji': '🟢', 'advice': 'Good opportunity to buy'},
    'FAIR': {'min': 50, 'max': 64, 'emoji': '🟡', 'advice': 'Proceed with caution'},
    'POOR': {'min': 35, 'max': 49, 'emoji': '🟠', 'advice': 'Wait for better entry'},
    'BAD': {'min': 0, 'max': 34, 'emoji': '🔴', 'advice': 'Avoid buying now'},
}

# Safety rating for beginners
SAFETY_RATINGS = {
    'VERY_SAFE': {'min': 80, 'stars': 5, 'emoji': '⭐⭐⭐⭐⭐'},
    'SAFE': {'min': 65, 'stars': 4, 'emoji': '⭐⭐⭐⭐'},
    'MODERATE': {'min': 50, 'stars': 3, 'emoji': '⭐⭐⭐'},
    'RISKY': {'min': 35, 'stars': 2, 'emoji': '⭐⭐'},
    'VERY_RISKY': {'min': 0, 'stars': 1, 'emoji': '⭐'},
}

# =============================================================================
# RISK MODE CONFIGURATIONS
# =============================================================================

RISK_MODES = {
    'conservative': {
        'name': 'CONSERVATIVE',
        'description': 'Fewer signals, higher win rate, maximum capital protection',
        'risk_per_trade': 0.005,  # 0.5% risk per trade
        'min_risk_reward': 3.0,   # Minimum 3:1 R:R
        'atr_stop_multiplier': 2.5,
        'atr_target_multiplier': 3.0,
        'min_confidence_buy': 75,
        'min_confidence_sell': 75,
        'min_adx_trend': 30,      # Require stronger trend
        'weight_multipliers': {
            'trend': 1.5,         # Emphasize trend
            'momentum': 0.8,
            'confirmation': 1.2,
            'pattern': 1.3,       # Trust strong patterns
        }
    },
    'balanced': {
        'name': 'BALANCED',
        'description': 'Standard professional approach with good risk/reward',
        'risk_per_trade': 0.01,   # 1% risk per trade
        'min_risk_reward': 2.0,   # Minimum 2:1 R:R
        'atr_stop_multiplier': 2.0,
        'atr_target_multiplier': 2.5,
        'min_confidence_buy': 60,
        'min_confidence_sell': 60,
        'min_adx_trend': 25,
        'weight_multipliers': {
            'trend': 1.0,
            'momentum': 1.0,
            'confirmation': 1.0,
            'pattern': 1.0,       # Balanced pattern weight
        }
    },
    'aggressive': {
        'name': 'AGGRESSIVE',
        'description': 'More signals, higher risk tolerance, for experienced traders',
        'risk_per_trade': 0.02,   # 2% risk per trade
        'min_risk_reward': 1.5,   # Minimum 1.5:1 R:R
        'atr_stop_multiplier': 1.5,
        'atr_target_multiplier': 2.0,
        'min_confidence_buy': 50,
        'min_confidence_sell': 50,
        'min_adx_trend': 20,
        'weight_multipliers': {
            'trend': 0.8,
            'momentum': 1.3,
            'confirmation': 0.9,
            'pattern': 1.5,       # More aggressive on patterns
        }
    }
}

# =============================================================================
# SIGNAL WEIGHTS (Professional Standard)
# =============================================================================

# Total weights = 100
SIGNAL_WEIGHTS = {
    # TREND INDICATORS (40% total)
    'price_vs_trend_ema': 15,      # Price vs 200/100 EMA (primary trend)
    'price_vs_medium_ema': 10,     # Price vs 50 EMA
    'ema_alignment': 10,           # Fast > Medium > Slow alignment
    'adx_strength': 5,             # ADX trend strength
    
    # MOMENTUM INDICATORS (35% total)
    'rsi_zone': 12,                # RSI overbought/oversold/neutral
    'rsi_direction': 3,            # RSI trending up/down
    'macd_signal': 8,              # MACD vs signal line
    'macd_histogram': 4,           # MACD histogram direction
    'macd_zero_line': 3,           # MACD above/below zero
    'divergence': 5,               # RSI/MACD divergence
    
    # CONFIRMATION INDICATORS (25% total)
    'volume_confirmation': 8,      # Volume supports move
    'volume_trend': 4,             # OBV trend
    'bollinger_position': 6,       # Price vs Bollinger Bands
    'support_resistance': 7,       # Proximity to key levels
}

# =============================================================================
# HARD FILTERS (Block Dangerous Trades)
# =============================================================================

HARD_FILTERS = {
    'block_buy': [
        {
            'indicator': 'rsi',
            'operator': '>',
            'value': 80,
            'reason': 'RSI > 80: Extremely overbought - high reversal probability'
        },
        {
            'indicator': 'stoch_k',
            'operator': '>',
            'value': 85,
            'reason': 'Stochastic > 85: Extremely overbought'
        },
        {
            'indicator': 'bb_percent',
            'operator': '>',
            'value': 1.0,
            'reason': 'Price above upper Bollinger Band - overextended'
        },
        {
            'indicator': 'divergence',
            'operator': '==',
            'value': 'bearish',
            'reason': 'Bearish divergence detected - momentum weakening'
        },
    ],
    'block_sell': [
        {
            'indicator': 'rsi',
            'operator': '<',
            'value': 20,
            'reason': 'RSI < 20: Extremely oversold - bounce likely'
        },
        {
            'indicator': 'stoch_k',
            'operator': '<',
            'value': 15,
            'reason': 'Stochastic < 15: Extremely oversold'
        },
        {
            'indicator': 'bb_percent',
            'operator': '<',
            'value': 0.0,
            'reason': 'Price below lower Bollinger Band - oversold'
        },
        {
            'indicator': 'divergence',
            'operator': '==',
            'value': 'bullish',
            'reason': 'Bullish divergence detected - momentum strengthening'
        },
    ]
}

# =============================================================================
# RECOMMENDATION THRESHOLDS
# =============================================================================

RECOMMENDATION_THRESHOLDS = {
    'conservative': {
        'STRONG_BUY': 85,
        'BUY': 75,
        'WEAK_BUY': 65,
        'HOLD_UPPER': 55,
        'HOLD_LOWER': 45,
        'WEAK_SELL': 35,
        'SELL': 25,
        'STRONG_SELL': 15,
    },
    'balanced': {
        'STRONG_BUY': 75,  # Lowered from 80 - more realistic for real markets
        'BUY': 70,  # Increased from 65 - require higher confidence
        'WEAK_BUY': 60,  # Increased from 55 - require higher confidence
        'HOLD_UPPER': 50,
        'HOLD_LOWER': 40,
        'WEAK_SELL': 35,
        'SELL': 25,
        'STRONG_SELL': 15,
    },
    'aggressive': {
        'STRONG_BUY': 70,
        'BUY': 55,
        'WEAK_BUY': 45,
        'HOLD_UPPER': 42,
        'HOLD_LOWER': 38,
        'WEAK_SELL': 30,
        'SELL': 20,
        'STRONG_SELL': 10,
    }
}

# =============================================================================
# CONFIDENCE LEVELS
# =============================================================================

CONFIDENCE_LEVELS = {
    (90, 100): 'VERY HIGH',
    (75, 89): 'HIGH',
    (55, 74): 'MEDIUM',
    (35, 54): 'LOW',
    (0, 34): 'VERY LOW',
}

# =============================================================================
# PATTERN HORIZONS (Industry-Standard Time Expectations)
# =============================================================================

# Each pattern has empirically-observed timeframes for target achievement
# Based on technical analysis research and historical performance data
PATTERN_HORIZONS = {
    # Reversal Patterns (tend to take longer)
    'Double Bottom': {
        'min_days': 60,
        'max_days': 180,
        'recommended_horizon': '3months',
        'reliability': 0.72,  # 72% historical success rate
        'description': 'Classic bullish reversal - needs time to confirm'
    },
    'Double Top': {
        'min_days': 60,
        'max_days': 180,
        'recommended_horizon': '3months',
        'reliability': 0.70,
        'description': 'Classic bearish reversal pattern'
    },
    'Head and Shoulders': {
        'min_days': 90,
        'max_days': 365,
        'recommended_horizon': '6months',
        'reliability': 0.83,  # Most reliable chart pattern
        'description': 'Highly reliable bearish reversal'
    },
    'Head and Shoulders (forming)': {
        'min_days': 60,
        'max_days': 180,
        'recommended_horizon': '3months',
        'reliability': 0.65,
        'description': 'Developing pattern - watch for confirmation'
    },
    'Inverse Head and Shoulders': {
        'min_days': 90,
        'max_days': 365,
        'recommended_horizon': '6months',
        'reliability': 0.83,
        'description': 'Highly reliable bullish reversal'
    },
    'Inverse Head and Shoulders (forming)': {
        'min_days': 60,
        'max_days': 180,
        'recommended_horizon': '3months',
        'reliability': 0.65,
        'description': 'Developing pattern - watch for confirmation'
    },
    
    # Triangle Patterns (moderate time)
    'Ascending Triangle': {
        'min_days': 21,
        'max_days': 90,
        'recommended_horizon': '3months',
        'reliability': 0.75,
        'description': 'Bullish continuation - breakout expected'
    },
    'Ascending Triangle Breakout': {
        'min_days': 14,
        'max_days': 60,
        'recommended_horizon': '1month',
        'reliability': 0.78,
        'description': 'Confirmed breakout - target in weeks'
    },
    'Descending Triangle': {
        'min_days': 21,
        'max_days': 90,
        'recommended_horizon': '3months',
        'reliability': 0.72,
        'description': 'Bearish continuation - breakdown expected'
    },
    'Descending Triangle Breakdown': {
        'min_days': 14,
        'max_days': 60,
        'recommended_horizon': '1month',
        'reliability': 0.75,
        'description': 'Confirmed breakdown - target in weeks'
    },
    'Symmetrical Triangle': {
        'min_days': 14,
        'max_days': 60,
        'recommended_horizon': '1month',
        'reliability': 0.60,
        'description': 'Direction uncertain - wait for breakout'
    },
    'Symmetrical Triangle Bullish Breakout': {
        'min_days': 14,
        'max_days': 45,
        'recommended_horizon': '1month',
        'reliability': 0.68,
        'description': 'Bullish breakout from symmetrical'
    },
    'Symmetrical Triangle Bearish Breakdown': {
        'min_days': 14,
        'max_days': 45,
        'recommended_horizon': '1month',
        'reliability': 0.68,
        'description': 'Bearish breakdown from symmetrical'
    },
    
    # Wedge Patterns
    'Rising Wedge': {
        'min_days': 21,
        'max_days': 90,
        'recommended_horizon': '1month',
        'reliability': 0.68,
        'description': 'Bearish reversal - watch for breakdown'
    },
    'Rising Wedge Breakdown': {
        'min_days': 14,
        'max_days': 60,
        'recommended_horizon': '1month',
        'reliability': 0.72,
        'description': 'Confirmed bearish breakdown'
    },
    'Falling Wedge': {
        'min_days': 21,
        'max_days': 90,
        'recommended_horizon': '1month',
        'reliability': 0.68,
        'description': 'Bullish reversal - watch for breakout'
    },
    'Falling Wedge Breakout': {
        'min_days': 14,
        'max_days': 60,
        'recommended_horizon': '1month',
        'reliability': 0.72,
        'description': 'Confirmed bullish breakout'
    },
    
    # Flag & Pennant (short-term continuation)
    'Bull Flag': {
        'min_days': 5,
        'max_days': 21,
        'recommended_horizon': '2weeks',
        'reliability': 0.67,
        'description': 'Short-term bullish continuation'
    },
    'Bull Flag Breakout': {
        'min_days': 3,
        'max_days': 14,
        'recommended_horizon': '1week',
        'reliability': 0.70,
        'description': 'Confirmed flag breakout - quick target'
    },
    'Bear Flag': {
        'min_days': 5,
        'max_days': 21,
        'recommended_horizon': '2weeks',
        'reliability': 0.67,
        'description': 'Short-term bearish continuation'
    },
    'Bear Flag Breakdown': {
        'min_days': 3,
        'max_days': 14,
        'recommended_horizon': '1week',
        'reliability': 0.70,
        'description': 'Confirmed flag breakdown - quick target'
    },
    
    # Candlestick Patterns (short-term signals)
    'Morning Star': {
        'min_days': 3,
        'max_days': 14,
        'recommended_horizon': '2weeks',
        'reliability': 0.70,
        'description': 'Strong bullish reversal candlestick'
    },
    'Evening Star': {
        'min_days': 3,
        'max_days': 14,
        'recommended_horizon': '2weeks',
        'reliability': 0.70,
        'description': 'Strong bearish reversal candlestick'
    },
    'Bullish Engulfing': {
        'min_days': 2,
        'max_days': 10,
        'recommended_horizon': '1week',
        'reliability': 0.63,
        'description': 'Bullish reversal signal'
    },
    'Bearish Engulfing': {
        'min_days': 2,
        'max_days': 10,
        'recommended_horizon': '1week',
        'reliability': 0.63,
        'description': 'Bearish reversal signal'
    },
    'Three White Soldiers': {
        'min_days': 5,
        'max_days': 21,
        'recommended_horizon': '2weeks',
        'reliability': 0.75,
        'description': 'Very strong bullish continuation'
    },
    'Three Black Crows': {
        'min_days': 5,
        'max_days': 21,
        'recommended_horizon': '2weeks',
        'reliability': 0.75,
        'description': 'Very strong bearish continuation'
    },
    'Hammer': {
        'min_days': 2,
        'max_days': 7,
        'recommended_horizon': '1week',
        'reliability': 0.60,
        'description': 'Potential bullish reversal - needs confirmation'
    },
    'Shooting Star': {
        'min_days': 2,
        'max_days': 7,
        'recommended_horizon': '1week',
        'reliability': 0.60,
        'description': 'Potential bearish reversal - needs confirmation'
    },
}

# Default for patterns not in the list
DEFAULT_PATTERN_HORIZON = {
    'min_days': 14,
    'max_days': 60,
    'recommended_horizon': '1month',
    'reliability': 0.55,
    'description': 'Pattern detected'
}

# =============================================================================
# FIBONACCI LEVELS
# =============================================================================

FIBONACCI_RETRACEMENT = [0.236, 0.382, 0.5, 0.618, 0.786]
FIBONACCI_EXTENSION = [1.0, 1.272, 1.618, 2.0, 2.618]

# =============================================================================
# RSI ZONES
# =============================================================================

RSI_ZONES = {
    'extremely_overbought': (80, 100),
    'overbought': (70, 80),
    'slightly_overbought': (60, 70),
    'neutral': (40, 60),
    'slightly_oversold': (30, 40),
    'oversold': (20, 30),
    'extremely_oversold': (0, 20),
}

# =============================================================================
# TREND STRENGTH (ADX)
# =============================================================================

ADX_LEVELS = {
    'no_trend': (0, 20),
    'weak_trend': (20, 25),
    'trend': (25, 40),
    'strong_trend': (40, 60),
    'very_strong_trend': (60, 100),
}

# =============================================================================
# MARKET PHASES
# =============================================================================

MARKET_PHASES = {
    'strong_uptrend': 'Price > all EMAs, EMAs aligned bullish, ADX > 25',
    'uptrend': 'Price > trend EMA, ADX > 25',
    'weak_uptrend': 'Price > trend EMA, ADX < 25',
    'consolidation': 'Price near trend EMA, ADX < 20',
    'weak_downtrend': 'Price < trend EMA, ADX < 25',
    'downtrend': 'Price < trend EMA, ADX > 25',
    'strong_downtrend': 'Price < all EMAs, EMAs aligned bearish, ADX > 25',
}

# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_MODE = 'balanced'
DEFAULT_TIMEFRAME = 'medium'
DEFAULT_HORIZON = '3months'
DEFAULT_TICKERS = ['SILVERBEES.NS', 'GOLDBEES.NS']

# =============================================================================
# DISPLAY SETTINGS
# =============================================================================

CURRENCY_SYMBOL = '₹'
REPORT_WIDTH = 80

# =============================================================================
# BEGINNER-FRIENDLY EXPLANATIONS
# =============================================================================

SIMPLE_EXPLANATIONS = {
    'rsi': {
        'name': 'Momentum Check',
        'simple': 'Shows if the stock is being bought too much (overbought) or sold too much (oversold)',
        'overbought': 'Stock has been bought a lot recently - price might drop soon',
        'oversold': 'Stock has been sold a lot recently - price might rise soon',
        'neutral': 'Stock is trading normally - no extreme buying or selling',
    },
    'macd': {
        'name': 'Trend Direction',
        'simple': 'Shows if the stock price trend is going up or down',
        'bullish': 'Trend is turning positive - good sign for buyers',
        'bearish': 'Trend is turning negative - be cautious',
    },
    'adx': {
        'name': 'Trend Strength',
        'simple': 'Shows how strong the current price movement is',
        'strong': 'Price is moving strongly in one direction - trend is reliable',
        'weak': 'Price is moving slowly - no clear direction yet',
    },
    'volume': {
        'name': 'Trading Activity',
        'simple': 'Shows how many people are buying/selling this stock',
        'high': 'Many traders are active - confirms the price movement',
        'low': 'Few traders active - price movement may not last',
    },
    'support': {
        'name': 'Safety Net',
        'simple': 'Price level where the stock usually stops falling',
    },
    'resistance': {
        'name': 'Ceiling',
        'simple': 'Price level where the stock usually stops rising',
    },
}

# =============================================================================
# ACTION RECOMMENDATIONS (Plain English)
# =============================================================================

ACTION_RECOMMENDATIONS = {
    'STRONG_BUY': {
        'emoji': '🟢',
        'title': 'STRONG BUY',
        'simple': 'Excellent opportunity to invest!',
        'action': 'You can buy this stock now with confidence',
        'timing': 'Buy today or within the next 1-2 trading days',
    },
    'BUY': {
        'emoji': '🟢',
        'title': 'BUY',
        'simple': 'Good opportunity to invest',
        'action': 'Consider buying this stock',
        'timing': 'Buy within this week for best results',
    },
    'WEAK_BUY': {
        'emoji': '🟡',
        'title': 'WEAK BUY',
        'simple': 'Okay to buy, but be cautious',
        'action': 'You can buy, but start with a smaller amount',
        'timing': 'Buy on any price dip for better entry',
    },
    'HOLD': {
        'emoji': '🟡',
        'title': 'HOLD',
        'simple': 'No clear direction right now',
        'action': 'If you own it, keep it. If not, wait for a better signal',
        'timing': 'Wait 1-2 weeks for clearer signals',
    },
    'WEAK_SELL': {
        'emoji': '🟠',
        'title': 'AVOID BUYING',
        'simple': 'Not a good time to buy',
        'action': 'Do not buy now. Wait for the stock to stabilize',
        'timing': 'Check again after 1-2 weeks',
    },
    'SELL': {
        'emoji': '🔴',
        'title': 'DO NOT BUY',
        'simple': 'Bad time to invest',
        'action': 'Avoid this stock for now',
        'timing': 'Wait for trend reversal (may take weeks)',
    },
    'STRONG_SELL': {
        'emoji': '🔴',
        'title': 'DANGER - AVOID',
        'simple': 'Risky investment right now',
        'action': 'Do not invest - high risk of losses',
        'timing': 'Avoid until significant improvement',
    },
}

# =============================================================================
# TRADING DAY CALCULATIONS
# =============================================================================

TRADING_DAYS_PER_WEEK = 5
TRADING_DAYS_PER_MONTH = 22
TRADING_DAYS_PER_YEAR = 252

def get_expected_dates(horizon_key: str) -> dict:
    """Calculate expected buy/sell dates based on horizon"""
    from datetime import datetime, timedelta
    
    horizon = INVESTMENT_HORIZONS.get(horizon_key, INVESTMENT_HORIZONS['3months'])
    today = datetime.now()
    
    # Skip weekends for buy date
    buy_date = today
    if buy_date.weekday() >= 5:  # Weekend
        days_until_monday = 7 - buy_date.weekday()
        buy_date = buy_date + timedelta(days=days_until_monday)
    
    # Calculate sell dates (business days approximation)
    min_sell = buy_date + timedelta(days=int(horizon['min_days'] * 7 / 5))
    max_sell = buy_date + timedelta(days=int(horizon['max_days'] * 7 / 5))
    expected_sell = buy_date + timedelta(days=int(horizon['avg_days'] * 7 / 5))
    
    return {
        'buy_date': buy_date,
        'min_sell_date': min_sell,
        'max_sell_date': max_sell,
        'expected_sell_date': expected_sell,
        'holding_days': horizon['avg_days'],
    }
