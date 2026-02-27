#!/usr/bin/env python3
"""
Short Analyzer Pro — Twin Short-Selling Engine
================================================
Thin orchestration wrapper that reuses:
  - indicators.py  (shared, direction-neutral)
  - short_signals.py  (new, bearish scoring)
  - risk_management.py  (existing, direction='short')

Exposes `analyze_stock_short()` for backtest consumption.

Author: Harsh Kandhway
"""

import sys
import os
from typing import Dict, Optional

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.config import (
    DEFAULT_MODE, DEFAULT_TIMEFRAME, DEFAULT_HORIZON,
    TIMEFRAME_CONFIGS, RISK_MODES, INVESTMENT_HORIZONS
)
from src.core.indicators import calculate_all_indicators
from src.core.short_signals import (
    check_short_hard_filters, calculate_all_short_signals,
    get_short_confidence_level, determine_short_recommendation,
    generate_short_reasoning
)
from src.core.risk_management import (
    calculate_targets, calculate_stoploss, validate_risk_reward
)


def analyze_stock_short(
    symbol: str,
    df: pd.DataFrame,
    mode: str = 'balanced',
    timeframe: str = 'medium',
    horizon: str = '1month',
    market_regime: Optional[str] = None,
) -> Dict:
    """
    Perform complete SHORT analysis on a stock.

    Returns a dict with:
      - recommendation: 'STRONG SHORT', 'SHORT', 'WEAK SHORT', 'NEUTRAL', 'AVOID SHORT'
      - confidence: 0-100 (high = strong short signal)
      - target: price target BELOW current price
      - stop_loss: price ABOVE current price
      - risk_reward, reasoning, etc.
    """
    if not symbol or df is None or df.empty:
        raise ValueError(f"Invalid input for {symbol}")

    if mode not in RISK_MODES:
        mode = DEFAULT_MODE
    if timeframe not in TIMEFRAME_CONFIGS:
        timeframe = DEFAULT_TIMEFRAME
    if horizon not in INVESTMENT_HORIZONS:
        horizon = DEFAULT_HORIZON

    # 1. Calculate indicators (shared, direction-neutral)
    try:
        indicators = calculate_all_indicators(df, timeframe)
    except ValueError as e:
        raise ValueError(f"Short analysis failed for {symbol}: {e}")

    # 2. Check short-specific hard filters
    is_short_blocked, block_reasons = check_short_hard_filters(indicators)

    # 3. Calculate short signals (bearish = positive score)
    signal_data = calculate_all_short_signals(indicators, mode, market_regime)
    confidence = signal_data['confidence']
    confidence_level = get_short_confidence_level(confidence)

    current_price = indicators['current_price']
    atr = indicators['atr']
    support = indicators['support']
    resistance = indicators['resistance']
    fib_extensions = indicators['fib_extensions']

    # 4. Calculate targets and stops with direction='short'
    target_data = calculate_targets(
        current_price, atr, resistance, support,
        fib_extensions, mode, direction='short', horizon=horizon,
        strongest_pattern=indicators.get('strongest_pattern')
    )

    stop_data = calculate_stoploss(
        current_price, atr, support, resistance, mode, direction='short'
    )

    # 5. Validate risk/reward (for short: reward = entry - target, risk = stop - entry)
    risk_reward, rr_valid, rr_explanation = validate_risk_reward(
        current_price,
        target_data['recommended_target'],
        stop_data['recommended_stop'],
        mode
    )

    # 6. Overall score percentage (bearish version)
    trend_signals = signal_data.get('trend_signals', {})
    momentum_signals = signal_data.get('momentum_signals', {})
    pattern_signals = signal_data.get('pattern_signals', {})

    trend_bearish = sum(1 for _, d in trend_signals.values() if d == 'bearish')
    trend_score = min(3, max(0, trend_bearish))

    momentum_bearish = sum(1 for _, d in momentum_signals.values() if d == 'bearish')
    momentum_score = min(3, max(0, momentum_bearish))

    vol_ratio = indicators.get('volume_ratio', 1.0)
    mom_dir = indicators.get('momentum_direction', '')
    volume_score = 1 if (vol_ratio >= 1.5 and mom_dir in ['strong_down', 'down']) else 0

    pattern_bearish = sum(1 for _, d in pattern_signals.values() if d == 'bearish')
    pattern_bias = indicators.get('pattern_bias', 'neutral')
    pattern_score = min(3, max(0, pattern_bearish + (1 if pattern_bias == 'bearish' else 0)))

    risk_score = 1 if rr_valid else 0

    total_bearish = trend_score + momentum_score + volume_score + pattern_score + risk_score
    overall_score_pct = (total_bearish / 10) * 100

    # 7. Pattern info
    adx = indicators.get('adx', 0.0)
    strongest_pattern = indicators.get('strongest_pattern')
    pattern_confidence = 0.0
    pattern_type = None
    if strongest_pattern:
        pattern_confidence = getattr(strongest_pattern, 'confidence', 0.0) * 100
        if hasattr(strongest_pattern, 'type'):
            pattern_type = getattr(strongest_pattern, 'type', None)
        elif hasattr(strongest_pattern, 'p_type'):
            pattern_type = getattr(strongest_pattern, 'p_type', None)

    bearish_indicators_count = sum(
        1 for _, d in signal_data.get('signals', {}).values() if d == 'bearish'
    )
    min_rr = RISK_MODES[mode]['min_risk_reward']

    # 8. Determine recommendation
    recommendation, recommendation_type = determine_short_recommendation(
        confidence, is_short_blocked, mode,
        rr_valid=rr_valid,
        overall_score_pct=overall_score_pct,
        risk_reward=risk_reward,
        min_rr=min_rr,
        adx=adx,
        bearish_indicators_count=bearish_indicators_count,
        pattern_confidence=pattern_confidence,
        pattern_type=pattern_type,
    )

    # 9. Reasoning
    reasoning = generate_short_reasoning(
        indicators, signal_data,
        is_short_blocked, block_reasons,
        recommendation
    )

    return {
        'symbol': symbol,
        'mode': mode,
        'direction': 'short',
        'horizon': horizon,
        'current_price': current_price,
        'indicators': indicators,
        'signal_data': signal_data,
        'confidence': confidence,
        'confidence_level': confidence_level,
        'recommendation': recommendation,
        'recommendation_type': recommendation_type,
        'is_short_blocked': is_short_blocked,
        'block_reasons': block_reasons,
        'target_data': target_data,
        'stop_data': stop_data,
        'target': target_data['recommended_target'],
        'stop_loss': stop_data['recommended_stop'],
        'risk_reward': risk_reward,
        'rr_valid': rr_valid,
        'rr_explanation': rr_explanation,
        'reasoning': reasoning,
        'overall_score_pct': overall_score_pct,
    }
