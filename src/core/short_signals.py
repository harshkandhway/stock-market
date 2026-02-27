"""
Short Signal Generation Module for Stock Analyzer Pro (Twin Short Engine)
=========================================================================
Dedicated bearish signal scoring, short-specific hard filters, and short
recommendation logic. Does NOT import from signals.py — completely independent.

Reuses indicator outputs from indicators.py (direction-neutral math).

Author: Harsh Kandhway
"""

from typing import Dict, List, Tuple, Optional
from .config import (
    SHORT_SIGNAL_WEIGHTS, SHORT_HARD_FILTERS, SHORT_RECOMMENDATION_THRESHOLDS,
    CONFIDENCE_LEVELS, RISK_MODES
)


def check_short_hard_filters(indicators: Dict) -> Tuple[bool, List[str]]:
    """
    Check if any hard filters block opening a SHORT position.

    Blocks shorting when the stock is already deeply oversold (bounce risk).
    """
    filters = SHORT_HARD_FILTERS.get('block_short', [])
    triggered = []

    for rule in filters:
        ind_name = rule['indicator']
        operator = rule['operator']
        threshold = rule['value']
        reason = rule['reason']

        value = indicators.get(ind_name)
        if value is None:
            continue

        hit = False
        if operator == '>' and value > threshold:
            hit = True
        elif operator == '<' and value < threshold:
            hit = True
        elif operator == '>=' and value >= threshold:
            hit = True
        elif operator == '<=' and value <= threshold:
            hit = True
        elif operator == '==' and value == threshold:
            hit = True
        elif operator == '!=' and value != threshold:
            hit = True

        if hit:
            triggered.append(reason)

    return (len(triggered) > 0, triggered)


# -------------------------------------------------------------------------
# Signal calculation functions — bearish conditions score POSITIVE
# -------------------------------------------------------------------------

def calculate_short_trend_signals(indicators: Dict, mode: str) -> Dict[str, Tuple[float, str]]:
    """
    Calculate trend signals for SHORT direction (45% weight).
    Bearish conditions = positive score (good for shorts).
    """
    mode_config = RISK_MODES[mode]
    multiplier = mode_config['weight_multipliers']['trend']
    signals = {}

    # Price vs Trend EMA — below = bearish = good for short
    weight = SHORT_SIGNAL_WEIGHTS['price_vs_trend_ema']
    if indicators['price_vs_trend_ema'] == 'below':
        signals['price_vs_trend_ema'] = (weight * multiplier, 'bearish')
    else:
        signals['price_vs_trend_ema'] = (-weight * multiplier, 'bullish')

    # Price vs Medium EMA
    weight = SHORT_SIGNAL_WEIGHTS['price_vs_medium_ema']
    if indicators['price_vs_medium_ema'] == 'below':
        signals['price_vs_medium_ema'] = (weight * multiplier, 'bearish')
    else:
        signals['price_vs_medium_ema'] = (-weight * multiplier, 'bullish')

    # EMA Alignment — bearish alignment = good for short
    weight = SHORT_SIGNAL_WEIGHTS['ema_alignment']
    alignment = indicators['ema_alignment']
    if alignment == 'strong_bearish':
        signals['ema_alignment'] = (weight * multiplier, 'bearish')
    elif alignment == 'bearish':
        signals['ema_alignment'] = (weight * 0.7 * multiplier, 'bearish')
    elif alignment == 'strong_bullish':
        signals['ema_alignment'] = (-weight * multiplier, 'bullish')
    elif alignment == 'bullish':
        signals['ema_alignment'] = (-weight * 0.7 * multiplier, 'bullish')
    else:
        signals['ema_alignment'] = (0, 'neutral')

    # ADX Strength — strong bearish trend = good for short
    weight = SHORT_SIGNAL_WEIGHTS['adx_strength']
    min_adx = mode_config['min_adx_trend']
    if indicators['adx'] >= min_adx:
        if indicators['adx_trend_direction'] == 'bearish':
            signals['adx_strength'] = (weight * multiplier, 'bearish')
        elif indicators['adx_trend_direction'] == 'bullish':
            signals['adx_strength'] = (-weight * multiplier, 'bullish')
        else:
            signals['adx_strength'] = (0, 'neutral')
    else:
        # No trend — slightly negative for trend-following shorts
        signals['adx_strength'] = (-weight * 0.3 * multiplier, 'neutral')

    return signals


def calculate_short_momentum_signals(indicators: Dict, mode: str) -> Dict[str, Tuple[float, str]]:
    """
    Calculate momentum signals for SHORT direction (35% weight).

    Key difference from long engine:
    - RSI 35-60 is the "sweet spot" for shorts (weakness confirmed, not yet exhausted)
    - RSI < 30 is NEGATIVE (oversold bounce risk)
    - RSI > 65 is slightly negative (still too strong)
    - MACD bearish = positive score
    """
    mode_config = RISK_MODES[mode]
    multiplier = mode_config['weight_multipliers']['momentum']
    signals = {}

    # RSI Zone — SHORT-SPECIFIC interpretation
    weight = SHORT_SIGNAL_WEIGHTS['rsi_zone']
    rsi_zone = indicators['rsi_zone']

    if rsi_zone == 'slightly_oversold':
        # RSI 30-40: Good short zone — weakness confirmed
        signals['rsi_zone'] = (weight * 0.8 * multiplier, 'bearish')
    elif rsi_zone == 'neutral':
        # RSI 40-60: OK for shorts, developing weakness
        rsi = indicators['rsi']
        if rsi <= 50:
            signals['rsi_zone'] = (weight * 0.6 * multiplier, 'bearish')
        else:
            signals['rsi_zone'] = (weight * 0.2 * multiplier, 'bearish')
    elif rsi_zone == 'slightly_overbought':
        # RSI 60-70: Becoming overbought — reversal SHORT candidate
        signals['rsi_zone'] = (weight * 0.5 * multiplier, 'bearish')
    elif rsi_zone == 'overbought':
        # RSI 70-80: Overbought — good reversal SHORT zone
        signals['rsi_zone'] = (weight * 0.7 * multiplier, 'bearish')
    elif rsi_zone == 'extremely_overbought':
        # RSI > 80: Very overbought — strong reversal SHORT candidate
        signals['rsi_zone'] = (weight * multiplier, 'bearish')
    elif rsi_zone == 'oversold':
        # RSI 20-30: Oversold — bounce risk, avoid short
        signals['rsi_zone'] = (-weight * 0.7 * multiplier, 'bullish')
    elif rsi_zone == 'extremely_oversold':
        # RSI < 20: DO NOT SHORT — high bounce probability
        signals['rsi_zone'] = (-weight * multiplier, 'bullish')
    else:
        signals['rsi_zone'] = (0, 'neutral')

    # RSI Direction — falling = good for short
    weight = SHORT_SIGNAL_WEIGHTS['rsi_direction']
    if indicators['rsi_direction'] == 'falling':
        signals['rsi_direction'] = (weight * multiplier, 'bearish')
    elif indicators['rsi_direction'] == 'rising':
        signals['rsi_direction'] = (-weight * multiplier, 'bullish')
    else:
        signals['rsi_direction'] = (0, 'neutral')

    # MACD Signal — bearish crossover = good for short
    weight = SHORT_SIGNAL_WEIGHTS['macd_signal']
    if indicators['macd_crossover'] == 'bearish':
        signals['macd_signal'] = (weight * multiplier, 'bearish')
    elif indicators['macd_crossover'] == 'bullish':
        signals['macd_signal'] = (-weight * multiplier, 'bullish')
    elif not indicators['macd_above_signal']:
        # MACD below signal line
        signals['macd_signal'] = (weight * 0.5 * multiplier, 'bearish')
    else:
        signals['macd_signal'] = (-weight * 0.5 * multiplier, 'bullish')

    # MACD Histogram — expanding negative = strong short
    weight = SHORT_SIGNAL_WEIGHTS['macd_histogram']
    if indicators['hist_direction'] == 'expanding' and indicators['macd_hist'] < 0:
        signals['macd_histogram'] = (weight * multiplier, 'bearish')
    elif indicators['hist_direction'] == 'expanding' and indicators['macd_hist'] > 0:
        signals['macd_histogram'] = (-weight * multiplier, 'bullish')
    elif indicators['hist_direction'] == 'contracting' and indicators['macd_hist'] < 0:
        signals['macd_histogram'] = (weight * 0.3 * multiplier, 'bearish')
    elif indicators['hist_direction'] == 'contracting' and indicators['macd_hist'] > 0:
        signals['macd_histogram'] = (-weight * 0.3 * multiplier, 'bullish')
    else:
        signals['macd_histogram'] = (0, 'neutral')

    # MACD Zero Line — below zero = good for short
    weight = SHORT_SIGNAL_WEIGHTS['macd_zero_line']
    if not indicators['macd_above_zero']:
        signals['macd_zero_line'] = (weight * multiplier, 'bearish')
    else:
        signals['macd_zero_line'] = (-weight * multiplier, 'bullish')

    # Divergence — bearish divergence = good for short
    weight = SHORT_SIGNAL_WEIGHTS['divergence']
    if indicators['divergence'] == 'bearish':
        signals['divergence'] = (weight * multiplier, 'bearish')
    elif indicators['divergence'] == 'bullish':
        signals['divergence'] = (-weight * multiplier, 'bullish')
    else:
        signals['divergence'] = (0, 'neutral')

    return signals


def calculate_short_confirmation_signals(indicators: Dict, mode: str) -> Dict[str, Tuple[float, str]]:
    """
    Calculate confirmation signals for SHORT direction (20% weight).
    Volume on down-moves, breaking support, BB position.
    """
    mode_config = RISK_MODES[mode]
    multiplier = mode_config['weight_multipliers']['confirmation']
    signals = {}

    # Volume Confirmation — high volume on down move = confirms short
    weight = SHORT_SIGNAL_WEIGHTS['volume_confirmation']
    volume_ratio = indicators['volume_ratio']
    momentum_dir = indicators['momentum_direction']

    if volume_ratio >= 1.5:
        if momentum_dir in ['strong_down', 'down']:
            signals['volume_confirmation'] = (weight * multiplier, 'bearish')
        elif momentum_dir in ['strong_up', 'up']:
            signals['volume_confirmation'] = (-weight * multiplier, 'bullish')
        else:
            signals['volume_confirmation'] = (0, 'neutral')
    elif volume_ratio < 0.5:
        signals['volume_confirmation'] = (-weight * 0.3 * multiplier, 'neutral')
    else:
        signals['volume_confirmation'] = (0, 'neutral')

    # Volume Trend (OBV) — falling = good for short
    weight = SHORT_SIGNAL_WEIGHTS['volume_trend']
    if indicators['obv_trend'] == 'falling':
        signals['volume_trend'] = (weight * multiplier, 'bearish')
    elif indicators['obv_trend'] == 'rising':
        signals['volume_trend'] = (-weight * multiplier, 'bullish')
    else:
        signals['volume_trend'] = (0, 'neutral')

    # Bollinger Band Position — above upper band = reversal SHORT candidate
    weight = SHORT_SIGNAL_WEIGHTS['bollinger_position']
    bb_position = indicators['bb_position']
    bb_percent = indicators['bb_percent']

    if bb_position == 'above_upper':
        # Overbought — mean reversion short
        signals['bollinger_position'] = (weight * multiplier, 'bearish')
    elif bb_position == 'below_lower':
        # Already oversold — avoid short
        signals['bollinger_position'] = (-weight * multiplier, 'bullish')
    elif bb_position == 'upper_half' and bb_percent > 0.8:
        signals['bollinger_position'] = (weight * 0.4 * multiplier, 'bearish')
    elif bb_position == 'lower_half' and bb_percent < 0.2:
        signals['bollinger_position'] = (-weight * 0.4 * multiplier, 'bullish')
    else:
        signals['bollinger_position'] = (0, 'neutral')

    # Support/Resistance — breaking below support = strong short; near resistance = caution
    weight = SHORT_SIGNAL_WEIGHTS['support_resistance']
    support_prox = indicators['support_proximity']
    resistance_prox = indicators['resistance_proximity']

    if support_prox == 'very_close':
        # Near support — could bounce OR break. Slightly positive for shorts
        # expecting a break. But risky.
        signals['support_resistance'] = (weight * 0.3 * multiplier, 'bearish')
    elif resistance_prox == 'very_close':
        # Near resistance — less room to fall from here
        signals['support_resistance'] = (-weight * 0.5 * multiplier, 'bullish')
    elif resistance_prox == 'close':
        signals['support_resistance'] = (-weight * 0.2 * multiplier, 'bullish')
    else:
        signals['support_resistance'] = (0, 'neutral')

    return signals


def calculate_short_pattern_signals(indicators: Dict, mode: str) -> Dict[str, Tuple[float, str]]:
    """
    Calculate pattern signals for SHORT direction.
    Bearish patterns = positive score.
    """
    mode_config = RISK_MODES[mode]
    multiplier = mode_config['weight_multipliers'].get('pattern', 1.0)
    signals = {}

    pattern_weight = 15
    pattern_bias = indicators.get('pattern_bias', 'neutral')
    bullish_score = indicators.get('pattern_bullish_score', 0)
    bearish_score = indicators.get('pattern_bearish_score', 0)
    strongest_pattern = indicators.get('strongest_pattern')

    # Pattern bias — bearish = positive for shorts
    if pattern_bias == 'bearish':
        score_diff = bearish_score - bullish_score
        normalized = min(pattern_weight * multiplier, (score_diff / 100) * pattern_weight * multiplier)
        signals['pattern_bias'] = (normalized, 'bearish')
    elif pattern_bias == 'bullish':
        score_diff = bullish_score - bearish_score
        normalized = min(pattern_weight * multiplier, (score_diff / 100) * pattern_weight * multiplier)
        signals['pattern_bias'] = (-normalized, 'bullish')
    else:
        signals['pattern_bias'] = (0, 'neutral')

    # Strongest pattern bonus — bearish patterns
    if strongest_pattern:
        from .patterns import PatternType, PatternStrength

        strength_multiplier = {
            PatternStrength.STRONG: 1.0,
            PatternStrength.MODERATE: 0.6,
            PatternStrength.WEAK: 0.3,
        }.get(strongest_pattern.strength, 0.5)

        bonus_weight = 5 * strength_multiplier * multiplier

        if strongest_pattern.type == PatternType.BEARISH:
            signals['strongest_pattern'] = (bonus_weight, 'bearish')
        elif strongest_pattern.type == PatternType.BULLISH:
            signals['strongest_pattern'] = (-bonus_weight, 'bullish')
        else:
            signals['strongest_pattern'] = (0, 'neutral')
    else:
        signals['strongest_pattern'] = (0, 'neutral')

    return signals


# -------------------------------------------------------------------------
# Aggregate
# -------------------------------------------------------------------------

def calculate_all_short_signals(indicators: Dict, mode: str = 'balanced', market_regime: Optional[str] = None) -> Dict:
    """
    Calculate all short signals and aggregate scores.

    Confidence formula (inverted from long engine):
      confidence = 50 + (bearish_score - bullish_score) / max_score * 50

    High confidence = strong short opportunity.
    """
    trend_signals = calculate_short_trend_signals(indicators, mode)
    momentum_signals = calculate_short_momentum_signals(indicators, mode)
    confirmation_signals = calculate_short_confirmation_signals(indicators, mode)
    pattern_signals = calculate_short_pattern_signals(indicators, mode)

    all_signals = {
        **trend_signals,
        **momentum_signals,
        **confirmation_signals,
        **pattern_signals,
    }

    # Positive scores = bearish (good for short), Negative = bullish (bad for short)
    bearish_score = sum(s for s, _ in all_signals.values() if s > 0)
    bullish_score = abs(sum(s for s, _ in all_signals.values() if s < 0))

    bearish_count = sum(1 for _, d in all_signals.values() if d == 'bearish')
    bullish_count = sum(1 for _, d in all_signals.values() if d == 'bullish')
    neutral_count = sum(1 for _, d in all_signals.values() if d == 'neutral')

    net_score = bearish_score - bullish_score
    max_score = sum(SHORT_SIGNAL_WEIGHTS.values()) + 20  # pattern weight

    # Confidence: 50 = neutral, >50 = short opportunity, <50 = avoid short
    confidence = 50 + (net_score / max_score) * 50

    total_signals = bearish_count + bullish_count + neutral_count
    if total_signals > 0:
        bearish_ratio = bearish_count / total_signals
        # Penalty: if less than 40% of signals are bearish, reduce confidence
        if bearish_ratio < 0.4 and confidence > 50:
            confidence = 50 + (confidence - 50) * bearish_ratio * 1.5

    # --- Layer 4: Regime-Aware Signal Penalties ---
    if market_regime == 'bearish':
        confidence += 5.0
    elif market_regime == 'bullish':
        confidence -= 15.0

    confidence = max(0, min(100, confidence))

    return {
        'signals': all_signals,
        'trend_signals': trend_signals,
        'momentum_signals': momentum_signals,
        'confirmation_signals': confirmation_signals,
        'pattern_signals': pattern_signals,
        'bearish_score': bearish_score,
        'bullish_score': bullish_score,
        'net_score': net_score,
        'bearish_count': bearish_count,
        'bullish_count': bullish_count,
        'neutral_count': neutral_count,
        'confidence': confidence,
    }


def get_short_confidence_level(confidence: float) -> str:
    """Map confidence percentage to text level."""
    for (low, high), level in CONFIDENCE_LEVELS.items():
        if low <= confidence <= high:
            return level
    return 'UNKNOWN'


def determine_short_recommendation(
    confidence: float,
    is_short_blocked: bool,
    mode: str = 'balanced',
    rr_valid: bool = True,
    overall_score_pct: float = 50.0,
    risk_reward: float = 0.0,
    min_rr: float = 2.0,
    adx: float = 0.0,
    bearish_indicators_count: int = 0,
    pattern_confidence: float = 0.0,
    pattern_type: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Determine SHORT recommendation based on confidence, filters, and R:R.

    Returns:
        Tuple of (recommendation_str, recommendation_type)
        Types: 'SHORT', 'NEUTRAL', 'BLOCKED'
    """
    thresholds = SHORT_RECOMMENDATION_THRESHOLDS[mode]

    # Blocked by hard filters (oversold extremes)
    if is_short_blocked:
        return 'AVOID SHORT - BLOCKED (Oversold / Bounce Risk)', 'BLOCKED'

    # --- STRONG SHORT check ---
    if confidence >= thresholds['STRONG_SHORT'] and overall_score_pct >= 65:
        if risk_reward >= min_rr:
            return 'STRONG SHORT', 'SHORT'
        elif risk_reward >= 1.5:
            return 'STRONG SHORT - R:R SLIGHTLY BELOW MIN', 'SHORT'
        else:
            if overall_score_pct >= 65 and confidence >= 70:
                return 'SHORT - R:R BELOW MINIMUM', 'SHORT'
            return 'NEUTRAL - R:R TOO LOW FOR SHORT', 'NEUTRAL'

    # --- R:R gate ---
    if not rr_valid and confidence >= thresholds['WEAK_SHORT']:
        if risk_reward >= 1.5 and overall_score_pct >= 60 and confidence >= 60:
            return 'WEAK SHORT - R:R BELOW MINIMUM (CAUTION)', 'SHORT'
        return 'NEUTRAL - R:R BELOW MINIMUM', 'NEUTRAL'

    # --- Low overall score penalty ---
    if overall_score_pct < 35 and confidence >= thresholds['WEAK_SHORT']:
        return 'NEUTRAL - WEAK BEARISH SIGNALS', 'NEUTRAL'

    # --- Standard flow ---
    if confidence >= thresholds['STRONG_SHORT']:
        return 'STRONG SHORT', 'SHORT'
    elif confidence >= thresholds['SHORT']:
        return 'SHORT', 'SHORT'
    elif confidence >= thresholds['WEAK_SHORT']:
        return 'WEAK SHORT', 'SHORT'
    elif confidence >= thresholds['NEUTRAL_UPPER']:
        return 'NEUTRAL', 'NEUTRAL'
    elif confidence >= thresholds['NEUTRAL_LOWER']:
        return 'NEUTRAL', 'NEUTRAL'
    else:
        # Check for bearish pattern contradiction
        pattern_type_str = None
        if pattern_type:
            if hasattr(pattern_type, 'value'):
                pattern_type_str = pattern_type.value.lower()
            elif isinstance(pattern_type, str):
                pattern_type_str = pattern_type.lower()
            else:
                pattern_type_str = str(pattern_type).lower().replace('patterntype.', '')

        if pattern_type_str == 'bearish' and pattern_confidence >= 75:
            return 'WEAK SHORT - BEARISH PATTERN OVERRIDE', 'SHORT'

        return 'AVOID SHORT', 'BLOCKED'


def generate_short_reasoning(
    indicators: Dict,
    signal_data: Dict,
    is_short_blocked: bool,
    block_reasons: List[str],
    recommendation: str,
) -> List[str]:
    """Generate human-readable reasoning for the short recommendation."""
    reasoning = []

    if is_short_blocked:
        for reason in block_reasons:
            reasoning.append(f"WARNING: {reason}")

    phase = indicators['market_phase']
    if phase == 'strong_downtrend':
        reasoning.append("Strong downtrend: Price below all EMAs — ideal short environment")
    elif phase == 'downtrend':
        reasoning.append("Downtrend: Price below trend EMA with confirmed trend")
    elif phase == 'weak_downtrend':
        reasoning.append("Weak downtrend: Price below trend EMA but trend not confirmed")
    elif 'uptrend' in phase:
        reasoning.append(f"Uptrend detected ({phase}) — shorting against the trend is risky")
    else:
        reasoning.append("Consolidation: No clear trend — wait for breakdown confirmation")

    rsi = indicators['rsi']
    rsi_zone = indicators['rsi_zone']
    if 'oversold' in rsi_zone:
        reasoning.append(f"RSI at {rsi:.1f} — oversold, bounce risk! Caution for shorts")
    elif 'overbought' in rsi_zone:
        reasoning.append(f"RSI at {rsi:.1f} — overbought, reversal short candidate")
    elif rsi <= 50:
        reasoning.append(f"RSI at {rsi:.1f} — below 50, bearish momentum confirmed")

    if indicators['macd_crossover'] == 'bearish':
        reasoning.append("Bearish MACD crossover — negative momentum shift (short signal)")
    elif indicators['macd_crossover'] == 'bullish':
        reasoning.append("Bullish MACD crossover — caution for shorts")

    if indicators['divergence'] == 'bearish':
        reasoning.append("BEARISH DIVERGENCE: Momentum weakening — supports short thesis")
    elif indicators['divergence'] == 'bullish':
        reasoning.append("BULLISH DIVERGENCE: Momentum strengthening — risky to short")

    volume_ratio = indicators['volume_ratio']
    if volume_ratio >= 1.5:
        reasoning.append(f"High volume ({volume_ratio:.1f}x average) confirms the move")
    elif volume_ratio < 0.5:
        reasoning.append(f"Low volume ({volume_ratio:.1f}x average) — move may lack conviction")

    if indicators['support_proximity'] == 'very_close':
        reasoning.append(f"Price near support at {indicators['support']:.2f} — potential bounce zone, watch closely")

    return reasoning
