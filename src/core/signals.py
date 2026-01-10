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
    # Use more conservative mapping - require stronger signals for higher confidence
    confidence = 50 + (net_score / max_score) * 50
    
    # Apply penalty if most signals are bearish (more conservative)
    bullish_count = sum(1 for _, direction in all_signals.values() if direction == 'bullish')
    bearish_count = sum(1 for _, direction in all_signals.values() if direction == 'bearish')
    total_signals = bullish_count + bearish_count + neutral_count
    
    if total_signals > 0:
        bullish_ratio = bullish_count / total_signals
        # If less than 40% of signals are bullish, reduce confidence
        if bullish_ratio < 0.4 and confidence > 50:
            confidence = 50 + (confidence - 50) * bullish_ratio * 1.5  # Penalty for low bullish ratio
    
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
    mode: str = 'balanced',
    rr_valid: bool = True,
    overall_score_pct: float = 50.0,
    risk_reward: float = 0.0,
    min_rr: float = 2.0,
    adx: float = 0.0,
    bullish_indicators_count: int = 0,
    pattern_confidence: float = 0.0,
    pattern_type: Optional[str] = None
) -> Tuple[str, str]:
    """
    Determine the recommendation based on confidence, filters, risk/reward, and overall score
    Following professional tool standards (Bloomberg, Zacks, TipRanks, TradingView, MetaTrader)
    
    Args:
        confidence: Confidence percentage (0-100)
        is_buy_blocked: Whether buy is blocked by hard filters
        is_sell_blocked: Whether sell is blocked by hard filters
        mode: Risk mode (conservative, balanced, aggressive)
        rr_valid: Whether risk/reward ratio meets minimum requirement
        overall_score_pct: Overall bullish score percentage (0-100)
        risk_reward: Actual risk/reward ratio (for fine-grained exception logic)
        min_rr: Minimum required R:R for the mode
        adx: ADX value (for trend strength validation)
        bullish_indicators_count: Number of bullish indicators (for confirmation)
        pattern_confidence: Pattern confidence percentage (0-100) - for contradiction detection
        pattern_type: Pattern type ('bullish', 'bearish', None) - for contradiction detection
    
    Returns:
        Tuple of (recommendation, recommendation_type)
        recommendation_type: 'BUY', 'SELL', 'HOLD', 'BLOCKED'
    """
    thresholds = RECOMMENDATION_THRESHOLDS[mode]
    
    # Check if buy is blocked
    # PROFESSIONAL STANDARD: Divergence is a significant warning signal
    # Professional tools (Bloomberg, Zacks, TipRanks) treat divergence seriously
    # EXCEPTION: Only override in EXTREMELY RARE cases with exceptional signals
    # This prevents false positives while allowing genuine exceptional setups
    if confidence >= 50 and is_buy_blocked:
        # Professional practice: Override divergence ONLY if ALL conditions are exceptional:
        # 1. Overall score is EXCEPTIONAL (>=90%) - near-perfect technical setup
        # 2. R:R is EXCEPTIONAL (>=4.0:1) - outstanding risk/reward
        # 3. Bullish pattern is VERY high confidence (>=85%) - very strong pattern
        # 4. ADX shows VERY strong trend (>=35) - very reliable trend
        # 5. Confidence is high enough (>=65%) to support the override
        
        # This is EXTREMELY strict - only triggers in rare exceptional cases
        # Matches professional practice: Don't override divergence unless signals are truly exceptional
        has_exceptional_score = overall_score_pct >= 90
        has_exceptional_rr = risk_reward >= 4.0
        has_very_strong_pattern = pattern_confidence >= 85 and pattern_type and pattern_type.lower() == 'bullish'
        has_very_strong_trend = adx >= 35
        has_sufficient_confidence = confidence >= 65
        
        # Override ONLY if ALL 5 conditions are met (extremely rare)
        # This ensures we don't override divergence for marginal cases
        can_override = (
            has_exceptional_score and
            has_exceptional_rr and
            has_very_strong_pattern and
            has_very_strong_trend and
            has_sufficient_confidence
        )
        
        if can_override:
            # Override the block but add clear warning about divergence
            # Professional standard: Always disclose the warning prominently
            # Downgrade confidence to reflect the risk (15 point penalty)
            adjusted_confidence = max(confidence - 15, thresholds['WEAK_BUY'])
            
            # Build condition string for transparency
            conditions = [
                f"score {overall_score_pct:.1f}%",
                f"R:R {risk_reward:.2f}:1",
                f"pattern {pattern_confidence:.0f}%",
                f"ADX {adx:.1f}"
            ]
            conditions_str = ", ".join(conditions)
            
            if adjusted_confidence >= thresholds['BUY']:
                return f'BUY - DIVERGENCE WARNING (EXCEPTIONAL SETUP: {conditions_str})', 'BUY'
            else:
                return f'WEAK BUY - DIVERGENCE WARNING (EXCEPTIONAL SETUP: {conditions_str})', 'BUY'
        else:
            # Standard block - divergence warning is significant
            # Professional standard: Respect divergence when signals aren't truly exceptional
            return 'AVOID - BUY BLOCKED', 'BLOCKED'
    
    # Check if sell is blocked
    if confidence < 50 and is_sell_blocked:
        return 'AVOID - SELL BLOCKED', 'BLOCKED'
    
    # =====================================================================
    # PROFESSIONAL STANDARD: Check STRONG BUY eligibility FIRST
    # This matches Bloomberg, Zacks, TipRanks, TradingView, MetaTrader
    # =====================================================================
    if confidence >= thresholds['STRONG_BUY'] and overall_score_pct >= 70:
        # STRONG BUY eligibility: confidence ≥75% and score ≥70% (professional standard)
        
        # Check R:R requirements (professional standard: 1.8:1 minimum for exceptions)
        # Professional tools (Bloomberg, Zacks, TipRanks) use 1.8:1 as standard exception
        # Check actual risk_reward value directly for precision (not just rr_valid)
        if risk_reward >= min_rr:
            # Valid R:R (≥min_rr, typically 2.0:1) - Standard STRONG BUY
            return 'STRONG BUY', 'BUY'
        elif risk_reward >= 1.8:
            # R:R in exception range (1.8-2.0:1) - Professional tools allow this (Bloomberg, Zacks, TipRanks)
            # ALWAYS show warning for transparency, even with strong ADX/confirmations (professional standard)
            # Additional validation: ADX ≥25 preferred (strong trend) - matches MetaTrader/TradingView
            # Note: Strong ADX and confirmations are already reflected in confidence and score
            return 'STRONG BUY - R:R SLIGHTLY BELOW MINIMUM', 'BUY'
        else:
            # R:R too low (<1.8:1) - Professional tools don't allow STRONG BUY below 1.8:1
            # Downgrade to BUY or WEAK BUY based on confidence and score
            if overall_score_pct >= 70 and confidence >= 75:
                return 'BUY - R:R BELOW MINIMUM', 'BUY'
            elif overall_score_pct >= 60 and confidence >= 70:
                return 'WEAK BUY - R:R BELOW MINIMUM (CAUTION)', 'BUY'
            else:
                return 'HOLD - RISK/REWARD BELOW MINIMUM', 'HOLD'
    
    # =====================================================================
    # If Risk/Reward is below minimum, apply downgrade logic
    # EXCEPTION: Only allow BUY with warning if R:R is in acceptable range (1.8-2.0:1)
    # Professional standard: Don't allow R:R < 1.8:1 even with warnings
    # =====================================================================
    if not rr_valid and confidence >= thresholds['WEAK_BUY']:
        # Risk/Reward below minimum - check if we can still recommend BUY
        if overall_score_pct < 30:
            return 'AVOID - RISK/REWARD TOO LOW', 'BLOCKED'
        elif risk_reward >= 1.8:
            # R:R in exception range (1.8-2.0:1) - Professional tools allow this
            if overall_score_pct >= 70 and confidence >= 70:
                # High score and confidence - allow WEAK BUY with R:R warning
                return 'WEAK BUY - R:R SLIGHTLY BELOW MINIMUM', 'BUY'
            elif overall_score_pct >= 60 and confidence >= 65:
                # Good score and confidence - still allow WEAK BUY but with stronger warning
                return 'WEAK BUY - R:R BELOW MINIMUM (CAUTION)', 'BUY'
            else:
                return 'HOLD - RISK/REWARD BELOW MINIMUM', 'HOLD'
        else:
            # R:R < 1.8:1 - Too low, don't allow BUY even with warnings (professional standard)
            return 'HOLD - RISK/REWARD BELOW MINIMUM', 'HOLD'
    
    # =====================================================================
    # CRITICAL: If overall score is very low (<40%), downgrade BUY recommendations
    # =====================================================================
    if overall_score_pct < 40 and confidence >= thresholds['WEAK_BUY']:
        # Very low technical score - patterns alone shouldn't drive BUY
        if confidence >= thresholds['BUY']:
            # Downgrade from BUY to WEAK BUY or HOLD
            if overall_score_pct < 30:
                return 'HOLD - WEAK TECHNICAL SIGNALS', 'HOLD'
            else:
                return 'WEAK BUY - CAUTION REQUIRED', 'BUY'
        elif confidence >= thresholds['WEAK_BUY']:
            # Downgrade WEAK BUY to HOLD if score is too low
            return 'HOLD - INSUFFICIENT BULLISH SIGNALS', 'HOLD'
    
    # =====================================================================
    # Determine recommendation based on confidence (standard flow)
    # =====================================================================
    if confidence >= thresholds['STRONG_BUY']:
        # Should have been caught above, but fallback
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
        # Check for pattern contradiction: high-confidence bullish pattern contradicts SELL
        pattern_type_str = None
        if pattern_type:
            # Handle both Enum and string types
            if hasattr(pattern_type, 'value'):
                pattern_type_str = pattern_type.value.lower()
            elif isinstance(pattern_type, str):
                pattern_type_str = pattern_type.lower()
            else:
                pattern_type_str = str(pattern_type).lower().replace('patterntype.', '')
        
        if pattern_type_str == 'bullish' and pattern_confidence >= 75:
            # High-confidence bullish pattern (>=75%) contradicts SELL - downgrade to HOLD
            # Professional standard: Don't ignore high-confidence patterns
            return 'HOLD - BULLISH PATTERN CONTRADICTS SELL SIGNAL', 'HOLD'
        return 'WEAK SELL', 'SELL'
    elif confidence >= thresholds['SELL']:
        # Check for pattern contradiction: high-confidence bullish pattern contradicts SELL
        pattern_type_str = None
        if pattern_type:
            # Handle both Enum and string types
            if hasattr(pattern_type, 'value'):
                pattern_type_str = pattern_type.value.lower()
            elif isinstance(pattern_type, str):
                pattern_type_str = pattern_type.lower()
            else:
                pattern_type_str = str(pattern_type).lower().replace('patterntype.', '')
        
        if pattern_type_str == 'bullish' and pattern_confidence >= 75:
            # High-confidence bullish pattern (>=75%) contradicts SELL - downgrade to WEAK SELL or HOLD
            # Professional standard: High-confidence patterns should influence recommendation
            if pattern_confidence >= 80:
                # Very high confidence pattern (>=80%) - downgrade to HOLD
                return 'HOLD - STRONG BULLISH PATTERN CONTRADICTS SELL', 'HOLD'
            else:
                # High confidence pattern (75-79%) - downgrade to WEAK SELL
                return 'WEAK SELL - BULLISH PATTERN CONTRADICTS', 'SELL'
        return 'SELL', 'SELL'
    elif confidence >= thresholds['STRONG_SELL']:
        # Check for pattern contradiction: high-confidence bullish pattern contradicts STRONG SELL
        pattern_type_str = None
        if pattern_type:
            # Handle both Enum and string types
            if hasattr(pattern_type, 'value'):
                pattern_type_str = pattern_type.value.lower()
            elif isinstance(pattern_type, str):
                pattern_type_str = pattern_type.lower()
            else:
                pattern_type_str = str(pattern_type).lower().replace('patterntype.', '')
        
        if pattern_type_str == 'bullish' and pattern_confidence >= 75:
            # High-confidence bullish pattern contradicts STRONG SELL - downgrade significantly
            if pattern_confidence >= 80:
                return 'HOLD - STRONG BULLISH PATTERN CONTRADICTS SELL', 'HOLD'
            else:
                return 'WEAK SELL - BULLISH PATTERN CONTRADICTS', 'SELL'
        return 'STRONG SELL', 'SELL'
    else:
        # Check for pattern contradiction even for very low confidence
        pattern_type_str = None
        if pattern_type:
            # Handle both Enum and string types
            if hasattr(pattern_type, 'value'):
                pattern_type_str = pattern_type.value.lower()
            elif isinstance(pattern_type, str):
                pattern_type_str = pattern_type.lower()
            else:
                pattern_type_str = str(pattern_type).lower().replace('patterntype.', '')
        
        if pattern_type_str == 'bullish' and pattern_confidence >= 80:
            # Very high confidence pattern - don't allow STRONG SELL
            return 'WEAK SELL - STRONG BULLISH PATTERN CONTRADICTS', 'SELL'
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
