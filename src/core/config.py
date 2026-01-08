"""
Configuration module for Stock Analyzer Pro
Contains all configurable parameters, thresholds, and mode settings

Author: Harsh Kandhway
"""

from typing import Dict, List, Tuple, Any

# =============================================================================
# TIMEFRAME CONFIGURATIONS
# =============================================================================

TIMEFRAME_CONFIGS = {
    'short': {
        'name': 'SHORT-TERM',
        'description': 'Optimized for swing trades lasting 1-4 weeks',
        'data_period': '3mo',
        'ema_fast': 9,
        'ema_medium': 21,
        'ema_slow': 50,
        'ema_trend': 100,  # For trend filter in short-term
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
        'ema_trend': 200,  # Primary trend filter
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
        'STRONG_BUY': 80,
        'BUY': 65,
        'WEAK_BUY': 55,
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
DEFAULT_TICKERS = ['SILVERBEES.NS', 'GOLDBEES.NS']

# =============================================================================
# DISPLAY SETTINGS
# =============================================================================

CURRENCY_SYMBOL = '₹'
REPORT_WIDTH = 80
