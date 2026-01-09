"""
Signal Generation Module for Stock Analyzer Pro
Handles signal scoring, hard filters, and confidence calculation

Author: Harsh Kandhway
"""

from typing import Dict, List, Tuple, Optional
from .config import (
    SIGNAL_WEIGHTS, HARD_FILTERS, RECOMMENDATION_THRESHOLDS,
    CONFIDENCE_LEVELS, RISK_MODES
)


def check_hard_filters(indicators: Dict, direction: str) -> Tuple[bool, List[str]]:
    """
    Check if any hard filters are triggered that block the trade
    
    Args:
        indicators: Dictionary of calculated indicators
        direction: 'buy' or 'sell'
    
    Returns:
        Tuple of (is_blocked, list_of_reasons)
    """
    filters = HARD_FILTERS.get(f'block_{direction}', [])
    triggered_filters = []
    
    for filter_rule in filters:
        indicator_name = filter_rule['indicator']
        operator = filter_rule['operator']
        threshold = filter_rule['value']
        reason = filter_rule['reason']
        
        # Get indicator value
        indicator_value = indicators.get(indicator_name)
        
        if indicator_value is None:
            continue
        
        # Check condition
        triggered = False
        if operator == '>' and indicator_value > threshold:
            triggered = True
        elif operator == '<' and indicator_value < threshold:
            triggered = True
        elif operator == '>=' and indicator_value >= threshold:
            triggered = True
        elif operator == '<=' and indicator_value <= threshold:
            triggered = True
        elif operator == '==' and indicator_value == threshold:
            triggered = True
        elif operator == '!=' and indicator_value != threshold:
            triggered = True
        
        if triggered:
            triggered_filters.append(reason)
    
    is_blocked = len(triggered_filters) > 0
    return is_blocked, triggered_filters


def calculate_trend_signals(indicators: Dict, mode: str) -> Dict[str, Tuple[float, str]]:
    """
    Calculate trend-based signals (40% of total weight)
    
    Returns:
        Dict of signal_name: (score, signal_direction)
        score: 0-100 normalized for this signal's weight
        signal_direction: 'bullish', 'bearish', 'neutral'
    """
    mode_config = RISK_MODES[mode]
    multiplier = mode_config['weight_multipliers']['trend']
    
    signals = {}
    
    # Price vs Trend EMA (200/100 EMA) - 15 points max
    weight = SIGNAL_WEIGHTS['price_vs_trend_ema']
    if indicators['price_vs_trend_ema'] == 'above':
        signals['price_vs_trend_ema'] = (weight * multiplier, 'bullish')
    else:
        signals['price_vs_trend_ema'] = (-weight * multiplier, 'bearish')
    
    # Price vs Medium EMA (50 EMA) - 10 points max
    weight = SIGNAL_WEIGHTS['price_vs_medium_ema']
    if indicators['price_vs_medium_ema'] == 'above':
        signals['price_vs_medium_ema'] = (weight * multiplier, 'bullish')
    else:
        signals['price_vs_medium_ema'] = (-weight * multiplier, 'bearish')
    
    # EMA Alignment - 10 points max
    weight = SIGNAL_WEIGHTS['ema_alignment']
    alignment = indicators['ema_alignment']
    if alignment == 'strong_bullish':
        signals['ema_alignment'] = (weight * multiplier, 'bullish')
    elif alignment == 'bullish':
        signals['ema_alignment'] = (weight * 0.7 * multiplier, 'bullish')
    elif alignment == 'strong_bearish':
        signals['ema_alignment'] = (-weight * multiplier, 'bearish')
    elif alignment == 'bearish':
        signals['ema_alignment'] = (-weight * 0.7 * multiplier, 'bearish')
    else:
        signals['ema_alignment'] = (0, 'neutral')
    
    # ADX Strength - 5 points max
    weight = SIGNAL_WEIGHTS['adx_strength']
    min_adx = mode_config['min_adx_trend']
    if indicators['adx'] >= min_adx:
        # Trend exists, give points based on direction
        if indicators['adx_trend_direction'] == 'bullish':
            signals['adx_strength'] = (weight * multiplier, 'bullish')
        elif indicators['adx_trend_direction'] == 'bearish':
            signals['adx_strength'] = (-weight * multiplier, 'bearish')
        else:
            signals['adx_strength'] = (0, 'neutral')
    else:
        # No trend - neutral but slightly negative for trend-following
        signals['adx_strength'] = (-weight * 0.3 * multiplier, 'neutral')
    
    return signals


def calculate_momentum_signals(indicators: Dict, mode: str) -> Dict[str, Tuple[float, str]]:
    """
    Calculate momentum-based signals (35% of total weight)
    """
    mode_config = RISK_MODES[mode]
    multiplier = mode_config['weight_multipliers']['momentum']
    
    signals = {}
    
    # RSI Zone - 12 points max
    weight = SIGNAL_WEIGHTS['rsi_zone']
    rsi = indicators['rsi']
    rsi_zone = indicators['rsi_zone']
    
    if rsi_zone == 'extremely_oversold':
        signals['rsi_zone'] = (weight * multiplier, 'bullish')  # Strong buy signal
    elif rsi_zone == 'oversold':
        signals['rsi_zone'] = (weight * 0.8 * multiplier, 'bullish')
    elif rsi_zone == 'slightly_oversold':
        signals['rsi_zone'] = (weight * 0.5 * multiplier, 'bullish')
    elif rsi_zone == 'extremely_overbought':
        signals['rsi_zone'] = (-weight * multiplier, 'bearish')  # Strong sell signal
    elif rsi_zone == 'overbought':
        signals['rsi_zone'] = (-weight * 0.8 * multiplier, 'bearish')
    elif rsi_zone == 'slightly_overbought':
        signals['rsi_zone'] = (-weight * 0.5 * multiplier, 'bearish')
    else:
        signals['rsi_zone'] = (0, 'neutral')
    
    # RSI Direction - 3 points max
    weight = SIGNAL_WEIGHTS['rsi_direction']
    if indicators['rsi_direction'] == 'rising':
        signals['rsi_direction'] = (weight * multiplier, 'bullish')
    elif indicators['rsi_direction'] == 'falling':
        signals['rsi_direction'] = (-weight * multiplier, 'bearish')
    else:
        signals['rsi_direction'] = (0, 'neutral')
    
    # MACD Signal - 8 points max
    weight = SIGNAL_WEIGHTS['macd_signal']
    if indicators['macd_crossover'] == 'bullish':
        signals['macd_signal'] = (weight * multiplier, 'bullish')
    elif indicators['macd_crossover'] == 'bearish':
        signals['macd_signal'] = (-weight * multiplier, 'bearish')
    elif indicators['macd_above_signal']:
        signals['macd_signal'] = (weight * 0.5 * multiplier, 'bullish')
    else:
        signals['macd_signal'] = (-weight * 0.5 * multiplier, 'bearish')
    
    # MACD Histogram Direction - 4 points max
    weight = SIGNAL_WEIGHTS['macd_histogram']
    if indicators['hist_direction'] == 'expanding' and indicators['macd_hist'] > 0:
        signals['macd_histogram'] = (weight * multiplier, 'bullish')
    elif indicators['hist_direction'] == 'expanding' and indicators['macd_hist'] < 0:
        signals['macd_histogram'] = (-weight * multiplier, 'bearish')
    elif indicators['hist_direction'] == 'contracting' and indicators['macd_hist'] > 0:
        signals['macd_histogram'] = (weight * 0.3 * multiplier, 'bullish')
    elif indicators['hist_direction'] == 'contracting' and indicators['macd_hist'] < 0:
        signals['macd_histogram'] = (-weight * 0.3 * multiplier, 'bearish')
    else:
        signals['macd_histogram'] = (0, 'neutral')
    
    # MACD Zero Line - 3 points max
    weight = SIGNAL_WEIGHTS['macd_zero_line']
    if indicators['macd_above_zero']:
        signals['macd_zero_line'] = (weight * multiplier, 'bullish')
    else:
        signals['macd_zero_line'] = (-weight * multiplier, 'bearish')
    
    # Divergence - 5 points max (IMPORTANT for reversals)
    weight = SIGNAL_WEIGHTS['divergence']
    if indicators['divergence'] == 'bullish':
        signals['divergence'] = (weight * multiplier, 'bullish')
    elif indicators['divergence'] == 'bearish':
        signals['divergence'] = (-weight * multiplier, 'bearish')
    else:
        signals['divergence'] = (0, 'neutral')
    
    return signals


def calculate_confirmation_signals(indicators: Dict, mode: str) -> Dict[str, Tuple[float, str]]:
    """
    Calculate confirmation signals (25% of total weight)
    """
    mode_config = RISK_MODES[mode]
    multiplier = mode_config['weight_multipliers']['confirmation']
    
    signals = {}
    
    # Volume Confirmation - 8 points max
    weight = SIGNAL_WEIGHTS['volume_confirmation']
    volume_ratio = indicators['volume_ratio']
    momentum_dir = indicators['momentum_direction']
    
    if volume_ratio >= 1.5:
        # High volume - confirms the move
        if momentum_dir in ['strong_up', 'up']:
            signals['volume_confirmation'] = (weight * multiplier, 'bullish')
        elif momentum_dir in ['strong_down', 'down']:
            signals['volume_confirmation'] = (-weight * multiplier, 'bearish')
        else:
            signals['volume_confirmation'] = (0, 'neutral')
    elif volume_ratio < 0.5:
        # Low volume - weakens the signal
        signals['volume_confirmation'] = (-weight * 0.3 * multiplier, 'neutral')
    else:
        signals['volume_confirmation'] = (0, 'neutral')
    
    # Volume Trend (OBV) - 4 points max
    weight = SIGNAL_WEIGHTS['volume_trend']
    if indicators['obv_trend'] == 'rising':
        signals['volume_trend'] = (weight * multiplier, 'bullish')
    elif indicators['obv_trend'] == 'falling':
        signals['volume_trend'] = (-weight * multiplier, 'bearish')
    else:
        signals['volume_trend'] = (0, 'neutral')
    
    # Bollinger Band Position - 6 points max
    weight = SIGNAL_WEIGHTS['bollinger_position']
    bb_position = indicators['bb_position']
    bb_percent = indicators['bb_percent']
    
    if bb_position == 'below_lower':
        # Oversold - potential buy (mean reversion)
        signals['bollinger_position'] = (weight * multiplier, 'bullish')
    elif bb_position == 'above_upper':
        # Overbought - potential sell
        signals['bollinger_position'] = (-weight * multiplier, 'bearish')
    elif bb_position == 'upper_half' and bb_percent > 0.8:
        # Near upper band
        signals['bollinger_position'] = (-weight * 0.4 * multiplier, 'bearish')
    elif bb_position == 'lower_half' and bb_percent < 0.2:
        # Near lower band
        signals['bollinger_position'] = (weight * 0.4 * multiplier, 'bullish')
    else:
        signals['bollinger_position'] = (0, 'neutral')
    
    # Support/Resistance Proximity - 7 points max
    weight = SIGNAL_WEIGHTS['support_resistance']
    support_prox = indicators['support_proximity']
    resistance_prox = indicators['resistance_proximity']
    
    if support_prox == 'very_close':
        # At support - good buy zone
        signals['support_resistance'] = (weight * multiplier, 'bullish')
    elif support_prox == 'close':
        signals['support_resistance'] = (weight * 0.5 * multiplier, 'bullish')
    elif resistance_prox == 'very_close':
        # At resistance - caution for buys
        signals['support_resistance'] = (-weight * 0.7 * multiplier, 'bearish')
    elif resistance_prox == 'close':
        signals['support_resistance'] = (-weight * 0.3 * multiplier, 'bearish')
    else:
        signals['support_resistance'] = (0, 'neutral')
    
    return signals


def calculate_pattern_signals(indicators: Dict, mode: str) -> Dict[str, Tuple[float, str]]:
    """
    Calculate pattern-based signals (15% of total weight)
    Uses candlestick and chart pattern detection
    """
    mode_config = RISK_MODES[mode]
    multiplier = mode_config['weight_multipliers'].get('pattern', 1.0)
    
    signals = {}
    
    # Pattern weight - 15 points max total
    pattern_weight = 15
    
    # Get pattern data
    pattern_bias = indicators.get('pattern_bias', 'neutral')
    bullish_score = indicators.get('pattern_bullish_score', 0)
    bearish_score = indicators.get('pattern_bearish_score', 0)
    strongest_pattern = indicators.get('strongest_pattern')
    
    # Pattern bias signal
    if pattern_bias == 'bullish':
        # Scale based on difference between bullish and bearish scores
        score_diff = bullish_score - bearish_score
        normalized_score = min(pattern_weight * multiplier, (score_diff / 100) * pattern_weight * multiplier)
        signals['pattern_bias'] = (normalized_score, 'bullish')
    elif pattern_bias == 'bearish':
        score_diff = bearish_score - bullish_score
        normalized_score = min(pattern_weight * multiplier, (score_diff / 100) * pattern_weight * multiplier)
        signals['pattern_bias'] = (-normalized_score, 'bearish')
    else:
        signals['pattern_bias'] = (0, 'neutral')
    
    # Strongest pattern signal (additional weight for strong patterns)
    if strongest_pattern:
        from .patterns import PatternType, PatternStrength
        
        strength_multiplier = {
            PatternStrength.STRONG: 1.0,
            PatternStrength.MODERATE: 0.6,
            PatternStrength.WEAK: 0.3,
        }.get(strongest_pattern.strength, 0.5)
        
        bonus_weight = 5 * strength_multiplier * multiplier
        
        if strongest_pattern.type == PatternType.BULLISH:
            signals['strongest_pattern'] = (bonus_weight, 'bullish')
        elif strongest_pattern.type == PatternType.BEARISH:
            signals['strongest_pattern'] = (-bonus_weight, 'bearish')
        else:
            signals['strongest_pattern'] = (0, 'neutral')
    else:
        signals['strongest_pattern'] = (0, 'neutral')
    
    return signals


def calculate_all_signals(indicators: Dict, mode: str = 'balanced') -> Dict:
    """
    Calculate all signals and aggregate scores
    
    Returns:
        Dictionary with all signals, scores, and breakdown
    """
    # Calculate signals by category
    trend_signals = calculate_trend_signals(indicators, mode)
    momentum_signals = calculate_momentum_signals(indicators, mode)
    confirmation_signals = calculate_confirmation_signals(indicators, mode)
    pattern_signals = calculate_pattern_signals(indicators, mode)
    
    # Aggregate all signals
    all_signals = {
        **trend_signals,
        **momentum_signals,
        **confirmation_signals,
        **pattern_signals,
    }
    
    # Calculate totals
    bullish_score = sum(score for score, direction in all_signals.values() if score > 0)
    bearish_score = abs(sum(score for score, direction in all_signals.values() if score < 0))
    
    # Count signals by direction
    bullish_count = sum(1 for _, direction in all_signals.values() if direction == 'bullish')
    bearish_count = sum(1 for _, direction in all_signals.values() if direction == 'bearish')
    neutral_count = sum(1 for _, direction in all_signals.values() if direction == 'neutral')
    
    # Net score
    net_score = bullish_score - bearish_score
    
    # Normalize to 0-100 scale
    # Max possible score is roughly sum of all weights (100) + pattern weights (20)
    max_score = sum(SIGNAL_WEIGHTS.values()) + 20  # Added pattern weight
    
    # Convert net score to confidence percentage
    # net_score ranges from -max_score to +max_score
    # Map to 0-100 where 50 is neutral
    confidence = 50 + (net_score / max_score) * 50
    confidence = max(0, min(100, confidence))  # Clamp to 0-100
    
    return {
        'signals': all_signals,
        'trend_signals': trend_signals,
        'momentum_signals': momentum_signals,
        'confirmation_signals': confirmation_signals,
        'pattern_signals': pattern_signals,
        'bullish_score': bullish_score,
        'bearish_score': bearish_score,
        'net_score': net_score,
        'bullish_count': bullish_count,
        'bearish_count': bearish_count,
        'neutral_count': neutral_count,
        'confidence': confidence,
    }


def get_confidence_level(confidence: float) -> str:
    """Get confidence level string from confidence percentage"""
    for (low, high), level in CONFIDENCE_LEVELS.items():
        if low <= confidence <= high:
            return level
    return 'UNKNOWN'


def determine_recommendation(
    confidence: float,
    is_buy_blocked: bool,
    is_sell_blocked: bool,
    mode: str = 'balanced'
) -> Tuple[str, str]:
    """
    Determine the recommendation based on confidence and filters
    
    Returns:
        Tuple of (recommendation, recommendation_type)
        recommendation_type: 'BUY', 'SELL', 'HOLD', 'BLOCKED'
    """
    thresholds = RECOMMENDATION_THRESHOLDS[mode]
    
    # Check if buy is blocked
    if confidence >= 50 and is_buy_blocked:
        return 'AVOID - BUY BLOCKED', 'BLOCKED'
    
    # Check if sell is blocked
    if confidence < 50 and is_sell_blocked:
        return 'AVOID - SELL BLOCKED', 'BLOCKED'
    
    # Determine recommendation based on confidence
    if confidence >= thresholds['STRONG_BUY']:
        return 'STRONG BUY', 'BUY'
    elif confidence >= thresholds['BUY']:
        return 'BUY', 'BUY'
    elif confidence >= thresholds['WEAK_BUY']:
        return 'WEAK BUY', 'BUY'
    elif confidence >= thresholds['HOLD_UPPER']:
        return 'HOLD', 'HOLD'
    elif confidence >= thresholds['HOLD_LOWER']:
        return 'HOLD', 'HOLD'
    elif confidence >= thresholds['WEAK_SELL']:
        return 'WEAK SELL', 'SELL'
    elif confidence >= thresholds['SELL']:
        return 'SELL', 'SELL'
    elif confidence >= thresholds['STRONG_SELL']:
        return 'STRONG SELL', 'SELL'
    else:
        return 'STRONG SELL', 'SELL'


def generate_reasoning(
    indicators: Dict,
    signal_data: Dict,
    is_buy_blocked: bool,
    buy_block_reasons: List[str],
    is_sell_blocked: bool,
    sell_block_reasons: List[str],
    recommendation: str
) -> List[str]:
    """
    Generate human-readable reasoning for the recommendation
    """
    reasoning = []
    
    # Hard filter warnings first
    if is_buy_blocked:
        for reason in buy_block_reasons:
            reasoning.append(f"WARNING: {reason}")
    if is_sell_blocked:
        for reason in sell_block_reasons:
            reasoning.append(f"WARNING: {reason}")
    
    # Market phase
    phase = indicators['market_phase']
    if phase == 'strong_uptrend':
        reasoning.append("Strong uptrend: Price above all EMAs with strong momentum")
    elif phase == 'uptrend':
        reasoning.append("Uptrend: Price above trend EMA with confirmed trend")
    elif phase == 'weak_uptrend':
        reasoning.append("Weak uptrend: Price above trend EMA but trend not confirmed (ADX < 25)")
    elif phase == 'strong_downtrend':
        reasoning.append("Strong downtrend: Price below all EMAs with strong momentum")
    elif phase == 'downtrend':
        reasoning.append("Downtrend: Price below trend EMA with confirmed trend")
    elif phase == 'weak_downtrend':
        reasoning.append("Weak downtrend: Price below trend EMA but trend not confirmed")
    else:
        reasoning.append("Consolidation: No clear trend, market moving sideways")
    
    # RSI condition
    rsi = indicators['rsi']
    rsi_zone = indicators['rsi_zone']
    if 'overbought' in rsi_zone:
        reasoning.append(f"RSI at {rsi:.1f} indicates overbought conditions - reversal risk")
    elif 'oversold' in rsi_zone:
        reasoning.append(f"RSI at {rsi:.1f} indicates oversold conditions - bounce potential")
    
    # MACD
    if indicators['macd_crossover'] == 'bullish':
        reasoning.append("Bullish MACD crossover detected - positive momentum shift")
    elif indicators['macd_crossover'] == 'bearish':
        reasoning.append("Bearish MACD crossover detected - negative momentum shift")
    
    # Divergence (important!)
    if indicators['divergence'] == 'bearish':
        reasoning.append("BEARISH DIVERGENCE: Price making higher highs but momentum weakening")
    elif indicators['divergence'] == 'bullish':
        reasoning.append("BULLISH DIVERGENCE: Price making lower lows but momentum strengthening")
    
    # Volume
    volume_ratio = indicators['volume_ratio']
    if volume_ratio >= 1.5:
        reasoning.append(f"High volume ({volume_ratio:.1f}x average) confirms the move")
    elif volume_ratio < 0.5:
        reasoning.append(f"Low volume ({volume_ratio:.1f}x average) - move may lack conviction")
    
    # Support/Resistance
    if indicators['support_proximity'] == 'very_close':
        reasoning.append(f"Price near support at ₹{indicators['support']:.2f} - potential bounce zone")
    elif indicators['resistance_proximity'] == 'very_close':
        reasoning.append(f"Price near resistance at ₹{indicators['resistance']:.2f} - breakout or rejection likely")
    
    return reasoning


def generate_action_plan(
    recommendation: str,
    recommendation_type: str,
    indicators: Dict,
    is_blocked: bool
) -> Dict[str, str]:
    """
    Generate specific action plans for different investor types
    """
    current_price = indicators['current_price']
    support = indicators['support']
    resistance = indicators['resistance']
    ema_medium = indicators['ema_medium']
    
    actions = {}
    
    if is_blocked or recommendation_type == 'BLOCKED':
        actions['new_investors'] = f"DO NOT BUY - Wait for better entry conditions"
        actions['existing_holders'] = f"Consider taking partial profits. Set tight stop loss."
        actions['traders'] = f"Watch for reversal signals. Potential short opportunity if breakdown occurs."
    elif recommendation_type == 'BUY':
        if 'STRONG' in recommendation:
            actions['new_investors'] = f"Good entry opportunity. Consider building position."
            actions['existing_holders'] = f"Can add to position on pullbacks to ₹{ema_medium:.2f}"
            actions['traders'] = f"Enter long with stop below ₹{support:.2f}"
        else:
            actions['new_investors'] = f"Wait for pullback to ₹{ema_medium:.2f} for better entry"
            actions['existing_holders'] = f"Hold position. Add only on confirmed breakout above ₹{resistance:.2f}"
            actions['traders'] = f"Scale into position gradually. Use tight stops."
    elif recommendation_type == 'SELL':
        actions['new_investors'] = f"Avoid buying. Wait for trend reversal."
        actions['existing_holders'] = f"Consider reducing position. Set stop loss at ₹{support:.2f}"
        actions['traders'] = f"Look for short opportunities on rallies to ₹{ema_medium:.2f}"
    else:  # HOLD
        actions['new_investors'] = f"Wait for clearer signal. No rush to enter."
        actions['existing_holders'] = f"Hold current position. Monitor for breakout/breakdown."
        actions['traders'] = f"Stay on sidelines. Wait for volatility expansion."
    
    return actions
