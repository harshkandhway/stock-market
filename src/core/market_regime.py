"""
Market Regime Detection Module
==============================
Detects broad market regime (bullish/neutral/bearish) using Nifty50 index data.
Shared between backtest and live trading for consistent regime detection.

Regime rules:
  - 'bearish': 3+ consecutive days below EMA-21 AND RSI-14 <= 60
  - 'neutral':  Below EMA-21 but < 3 days, or RSI between 55-65
  - 'bullish':  Above EMA-21 OR RSI > 65

Author: Harsh Kandhway
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI on a price series."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def detect_market_regime(
    nifty_df: pd.DataFrame,
    ema_period: int = 50,
    rsi_period: int = 14,
    distance_top_threshold: float = 0.02,
    distance_panic_threshold: float = -0.015,
) -> Dict:
    """
    Detect market regime from Nifty50 data using V3 Institutional Elasticity.

    Parameters
    ----------
    nifty_df : pd.DataFrame
        Must have a DatetimeIndex and a 'close' column.
    ema_period : int
        EMA period to measure elasticity against (default 50).
    rsi_period : int
        RSI period (default 14).

    Returns
    -------
    dict
        Mapping of date -> {
            'close': float,
            'ema50': float,
            'rsi14': float,
            'distance': float,
            'regime': 'bearish' | 'neutral' | 'bullish',
            'short_allowed': bool,
        }
    """
    df = nifty_df.copy()

    # Ensure we have 'close' column
    if 'close' not in df.columns:
        raise ValueError("nifty_df must have a 'close' column")

    # Compute EMA and RSI
    df['ema'] = df['close'].ewm(span=ema_period, adjust=False).mean()
    df['rsi'] = _compute_rsi(df['close'], rsi_period)
    
    # Compute Elasticity (Distance)
    df['distance'] = (df['close'] - df['ema']) / df['ema']

    # Determine regime
    regime_data = {}
    for i in range(len(df)):
        date = df.index[i]
        close = df['close'].iloc[i]
        ema_val = df['ema'].iloc[i]
        rsi_val = df['rsi'].iloc[i] if not np.isnan(df['rsi'].iloc[i]) else 50.0
        distance = df['distance'].iloc[i]

        # V3 Regime classification
        if distance > distance_top_threshold or rsi_val > 70.0:
            regime = 'bearish'  # Good for shorts (Overextended top)
            short_allowed = True
        elif distance < distance_panic_threshold or rsi_val < 45.0:
            regime = 'bullish'  # Bad for shorts (Capitulation panic / V-Bounce risk)
            short_allowed = False
        else:
            regime = 'neutral'  # Chopping around the mean
            short_allowed = True

        # Strip timezone for consistent dict keys
        if hasattr(date, 'tz') and date.tz is not None:
            date = date.tz_localize(None)

        regime_data[date] = {
            'close': close,
            'ema50': ema_val,
            'rsi14': rsi_val,
            'distance': distance,
            'regime': regime,
            'short_allowed': short_allowed,
        }

    return regime_data


def get_regime_for_date(
    regime_data: Dict,
    date: pd.Timestamp,
) -> Optional[Dict]:
    """
    Look up regime info for a specific date.
    Handles timezone-aware/naive mismatches by stripping tz.
    """
    if hasattr(date, 'tz') and date.tz is not None:
        date = date.tz_localize(None)

    # Exact match
    if date in regime_data:
        return regime_data[date]

    # Try normalizing to midnight
    date_normalized = pd.Timestamp(date.date())
    if date_normalized in regime_data:
        return regime_data[date_normalized]

    return None


def get_regime_summary(regime_data: Dict) -> str:
    """Print a summary of regime periods for debugging."""
    lines = []
    dates = sorted(regime_data.keys())
    if not dates:
        return "No regime data"

    current_regime = None
    regime_start = None

    for d in dates:
        r = regime_data[d]['regime']
        if r != current_regime:
            if current_regime is not None:
                lines.append(f"  {str(regime_start)[:10]} -> {str(d)[:10]}: {current_regime.upper()}")
            current_regime = r
            regime_start = d

    if current_regime is not None:
        lines.append(f"  {str(regime_start)[:10]} -> {str(dates[-1])[:10]}: {current_regime.upper()}")

    return "\n".join(lines)
