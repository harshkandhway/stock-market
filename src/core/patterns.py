"""
Chart Pattern Detection Module for Stock Analyzer Pro
======================================================

Industry-standard candlestick and chart pattern recognition.

Candlestick Patterns:
- Single candle: Doji, Hammer, Shooting Star, Spinning Top, Marubozu
- Double candle: Engulfing, Harami, Piercing, Dark Cloud, Tweezer
- Triple candle: Morning Star, Evening Star, Three Soldiers, Three Crows

Chart Patterns:
- Reversal: Head & Shoulders, Double Top/Bottom, Triple Top/Bottom
- Continuation: Triangles, Wedges, Flags, Pennants, Rectangles
- Other: Cup & Handle, Rounding Bottom/Top

Author: Harsh Kandhway
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PatternType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class PatternStrength(Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass
class PatternResult:
    """
    Result of pattern detection with industry-standard measured move data.
    
    Attributes:
        name: Pattern name (e.g., "Double Bottom", "Head and Shoulders")
        type: BULLISH, BEARISH, or NEUTRAL
        strength: STRONG, MODERATE, or WEAK
        confidence: Pattern reliability score (0-100)
        description: Human-readable pattern description
        action: Recommended action with target info
        
        # Measured Move Data (Industry Standard)
        neckline: Key level for the pattern (neckline for H&S, peak for Double Bottom)
        pattern_height: Height used for measured move calculation
        measured_target: Industry-standard price target from pattern
        invalidation_level: Price level where pattern fails (for stop loss)
        breakout_level: Price that confirmed the pattern breakout
        
        # Horizon Recommendation
        min_days: Minimum expected days to reach target
        max_days: Maximum expected days to reach target
        recommended_horizon: Suggested investment horizon (e.g., '3months')
        reliability: Historical success rate of this pattern (0.0-1.0)
    """
    name: str
    type: PatternType
    strength: PatternStrength
    confidence: float  # 0-100
    description: str
    action: str  # What to do
    
    # Measured Move Data (Industry Standard)
    neckline: Optional[float] = None
    pattern_height: Optional[float] = None
    measured_target: Optional[float] = None
    invalidation_level: Optional[float] = None
    breakout_level: Optional[float] = None
    
    # Horizon Recommendation
    min_days: Optional[int] = None
    max_days: Optional[int] = None
    recommended_horizon: Optional[str] = None
    reliability: Optional[float] = None  # Historical success rate (0.0-1.0)


def get_pattern_horizon(pattern_name: str) -> Dict:
    """
    Get horizon data for a pattern from PATTERN_HORIZONS config.
    Returns default values if pattern not found.
    """
    # Import here to avoid circular imports
    try:
        from src.core.config import PATTERN_HORIZONS, DEFAULT_PATTERN_HORIZON
    except ImportError:
        # Fallback defaults
        PATTERN_HORIZONS = {}
        DEFAULT_PATTERN_HORIZON = {
            'min_days': 14,
            'max_days': 60,
            'recommended_horizon': '1month',
            'reliability': 0.55,
            'description': 'Pattern detected'
        }
    
    return PATTERN_HORIZONS.get(pattern_name, DEFAULT_PATTERN_HORIZON)


# =============================================================================
# CANDLESTICK PATTERN DETECTION
# =============================================================================

def calculate_candle_properties(open_p: float, high: float, low: float, close: float) -> Dict:
    """Calculate properties of a single candlestick"""
    body = abs(close - open_p)
    full_range = high - low
    
    if full_range == 0:
        return {
            'body': 0, 'body_pct': 0, 'upper_shadow': 0, 'lower_shadow': 0,
            'upper_shadow_pct': 0, 'lower_shadow_pct': 0, 'is_bullish': True
        }
    
    body_pct = (body / full_range) * 100
    
    if close >= open_p:  # Bullish candle
        upper_shadow = high - close
        lower_shadow = open_p - low
        is_bullish = True
    else:  # Bearish candle
        upper_shadow = high - open_p
        lower_shadow = close - low
        is_bullish = False
    
    upper_shadow_pct = (upper_shadow / full_range) * 100 if full_range > 0 else 0
    lower_shadow_pct = (lower_shadow / full_range) * 100 if full_range > 0 else 0
    
    return {
        'body': body,
        'body_pct': body_pct,
        'upper_shadow': upper_shadow,
        'lower_shadow': lower_shadow,
        'upper_shadow_pct': upper_shadow_pct,
        'lower_shadow_pct': lower_shadow_pct,
        'is_bullish': is_bullish,
        'full_range': full_range,
    }


def detect_doji(candle: Dict, threshold: float = 10) -> Optional[PatternResult]:
    """
    Detect Doji pattern - Open and close are nearly equal
    Indicates indecision in the market
    """
    if candle['body_pct'] <= threshold:
        # Determine type of doji
        if candle['upper_shadow_pct'] > 40 and candle['lower_shadow_pct'] > 40:
            name = "Long-Legged Doji"
            desc = "Strong indecision - traders are unsure"
        elif candle['upper_shadow_pct'] > 60:
            name = "Gravestone Doji"
            desc = "Bearish signal at top of uptrend"
            return PatternResult(
                name=name, type=PatternType.BEARISH, strength=PatternStrength.MODERATE,
                confidence=70, description=desc, action="Consider selling or wait for confirmation"
            )
        elif candle['lower_shadow_pct'] > 60:
            name = "Dragonfly Doji"
            desc = "Bullish signal at bottom of downtrend"
            return PatternResult(
                name=name, type=PatternType.BULLISH, strength=PatternStrength.MODERATE,
                confidence=70, description=desc, action="Consider buying or wait for confirmation"
            )
        else:
            name = "Doji"
            desc = "Market indecision - wait for next candle"
        
        return PatternResult(
            name=name, type=PatternType.NEUTRAL, strength=PatternStrength.WEAK,
            confidence=60, description=desc, action="Wait for confirmation candle"
        )
    return None


def detect_hammer(candle: Dict, prev_trend: str) -> Optional[PatternResult]:
    """
    Detect Hammer (bullish) or Hanging Man (bearish)
    Small body at top, long lower shadow, little/no upper shadow
    """
    if (candle['body_pct'] <= 35 and 
        candle['lower_shadow_pct'] >= 50 and 
        candle['upper_shadow_pct'] <= 15):
        
        if prev_trend == 'down':
            return PatternResult(
                name="Hammer",
                type=PatternType.BULLISH,
                strength=PatternStrength.STRONG,
                confidence=75,
                description="Bullish reversal signal after downtrend. Buyers pushed price back up.",
                action="Look for buying opportunity"
            )
        elif prev_trend == 'up':
            return PatternResult(
                name="Hanging Man",
                type=PatternType.BEARISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description="Warning signal in uptrend. Selling pressure appeared.",
                action="Consider taking profits or tightening stop loss"
            )
    return None


def detect_shooting_star(candle: Dict, prev_trend: str) -> Optional[PatternResult]:
    """
    Detect Shooting Star (bearish) or Inverted Hammer (bullish)
    Small body at bottom, long upper shadow, little/no lower shadow
    """
    if (candle['body_pct'] <= 35 and 
        candle['upper_shadow_pct'] >= 50 and 
        candle['lower_shadow_pct'] <= 15):
        
        if prev_trend == 'up':
            return PatternResult(
                name="Shooting Star",
                type=PatternType.BEARISH,
                strength=PatternStrength.STRONG,
                confidence=75,
                description="Bearish reversal signal. Buyers tried to push higher but sellers took control.",
                action="Consider selling or tightening stop loss"
            )
        elif prev_trend == 'down':
            return PatternResult(
                name="Inverted Hammer",
                type=PatternType.BULLISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description="Potential bullish reversal. Buyers starting to show interest.",
                action="Wait for confirmation, then consider buying"
            )
    return None


def detect_marubozu(candle: Dict) -> Optional[PatternResult]:
    """
    Detect Marubozu - Strong candle with no/minimal shadows
    Indicates strong momentum
    """
    if candle['body_pct'] >= 85:
        if candle['is_bullish']:
            return PatternResult(
                name="Bullish Marubozu",
                type=PatternType.BULLISH,
                strength=PatternStrength.STRONG,
                confidence=80,
                description="Very strong buying pressure. Buyers dominated entire session.",
                action="Bullish signal - consider buying"
            )
        else:
            return PatternResult(
                name="Bearish Marubozu",
                type=PatternType.BEARISH,
                strength=PatternStrength.STRONG,
                confidence=80,
                description="Very strong selling pressure. Sellers dominated entire session.",
                action="Bearish signal - consider selling"
            )
    return None


def detect_spinning_top(candle: Dict) -> Optional[PatternResult]:
    """
    Detect Spinning Top - Small body with shadows on both sides
    Indicates indecision
    """
    if (15 <= candle['body_pct'] <= 35 and
        candle['upper_shadow_pct'] >= 25 and
        candle['lower_shadow_pct'] >= 25):
        
        return PatternResult(
            name="Spinning Top",
            type=PatternType.NEUTRAL,
            strength=PatternStrength.WEAK,
            confidence=55,
            description="Market indecision. Neither buyers nor sellers have control.",
            action="Wait for clearer signal"
        )
    return None


def detect_engulfing(
    curr_open: float, curr_close: float,
    prev_open: float, prev_close: float,
    prev_trend: str
) -> Optional[PatternResult]:
    """
    Detect Bullish or Bearish Engulfing pattern
    Current candle completely engulfs previous candle's body
    """
    curr_is_bullish = curr_close > curr_open
    prev_is_bullish = prev_close > prev_open
    
    curr_body = abs(curr_close - curr_open)
    prev_body = abs(prev_close - prev_open)
    
    # Bullish Engulfing: Previous bearish, current bullish and larger
    if (not prev_is_bullish and curr_is_bullish and
        curr_open <= prev_close and curr_close >= prev_open and
        curr_body > prev_body * 1.1):  # At least 10% larger
        
        strength = PatternStrength.STRONG if prev_trend == 'down' else PatternStrength.MODERATE
        return PatternResult(
            name="Bullish Engulfing",
            type=PatternType.BULLISH,
            strength=strength,
            confidence=80 if prev_trend == 'down' else 65,
            description="Strong bullish reversal. Buyers overwhelmed sellers.",
            action="Buy signal - consider entering long position"
        )
    
    # Bearish Engulfing: Previous bullish, current bearish and larger
    if (prev_is_bullish and not curr_is_bullish and
        curr_open >= prev_close and curr_close <= prev_open and
        curr_body > prev_body * 1.1):
        
        strength = PatternStrength.STRONG if prev_trend == 'up' else PatternStrength.MODERATE
        return PatternResult(
            name="Bearish Engulfing",
            type=PatternType.BEARISH,
            strength=strength,
            confidence=80 if prev_trend == 'up' else 65,
            description="Strong bearish reversal. Sellers overwhelmed buyers.",
            action="Sell signal - consider exiting or shorting"
        )
    
    return None


def detect_harami(
    curr_open: float, curr_close: float,
    prev_open: float, prev_close: float,
    prev_trend: str
) -> Optional[PatternResult]:
    """
    Detect Harami pattern (inside bar)
    Current candle is completely inside previous candle
    """
    curr_high = max(curr_open, curr_close)
    curr_low = min(curr_open, curr_close)
    prev_high = max(prev_open, prev_close)
    prev_low = min(prev_open, prev_close)
    
    prev_is_bullish = prev_close > prev_open
    
    # Current candle inside previous candle
    if curr_high < prev_high and curr_low > prev_low:
        if prev_is_bullish and prev_trend == 'up':
            return PatternResult(
                name="Bearish Harami",
                type=PatternType.BEARISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description="Potential reversal. Momentum may be slowing.",
                action="Be cautious - watch for confirmation"
            )
        elif not prev_is_bullish and prev_trend == 'down':
            return PatternResult(
                name="Bullish Harami",
                type=PatternType.BULLISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description="Potential reversal. Selling pressure may be exhausting.",
                action="Watch for buying opportunity"
            )
    
    return None


def detect_morning_evening_star(
    candles: List[Dict],
    opens: List[float],
    closes: List[float],
    prev_trend: str
) -> Optional[PatternResult]:
    """
    Detect Morning Star (bullish) or Evening Star (bearish)
    Three-candle reversal pattern
    """
    if len(candles) < 3:
        return None
    
    first = candles[-3]
    second = candles[-2]
    third = candles[-1]
    
    first_body = abs(closes[-3] - opens[-3])
    second_body = abs(closes[-2] - opens[-2])
    third_body = abs(closes[-1] - opens[-1])
    
    # Morning Star: Large bearish, small body (gap down), large bullish
    if (prev_trend == 'down' and
        not first['is_bullish'] and first['body_pct'] >= 50 and
        second['body_pct'] <= 30 and  # Small middle candle
        third['is_bullish'] and third['body_pct'] >= 50 and
        closes[-1] > (opens[-3] + closes[-3]) / 2):  # Close above midpoint of first
        
        return PatternResult(
            name="Morning Star",
            type=PatternType.BULLISH,
            strength=PatternStrength.STRONG,
            confidence=85,
            description="Strong bullish reversal pattern. Downtrend likely ending.",
            action="Strong buy signal"
        )
    
    # Evening Star: Large bullish, small body (gap up), large bearish
    if (prev_trend == 'up' and
        first['is_bullish'] and first['body_pct'] >= 50 and
        second['body_pct'] <= 30 and  # Small middle candle
        not third['is_bullish'] and third['body_pct'] >= 50 and
        closes[-1] < (opens[-3] + closes[-3]) / 2):  # Close below midpoint of first
        
        return PatternResult(
            name="Evening Star",
            type=PatternType.BEARISH,
            strength=PatternStrength.STRONG,
            confidence=85,
            description="Strong bearish reversal pattern. Uptrend likely ending.",
            action="Strong sell signal"
        )
    
    return None


def detect_three_soldiers_crows(
    candles: List[Dict],
    opens: List[float],
    closes: List[float],
    highs: List[float],
    lows: List[float]
) -> Optional[PatternResult]:
    """
    Detect Three White Soldiers (bullish) or Three Black Crows (bearish)
    Three consecutive strong candles in same direction
    """
    if len(candles) < 3:
        return None
    
    # Check if all three are bullish with good bodies
    all_bullish = all(c['is_bullish'] and c['body_pct'] >= 50 for c in candles[-3:])
    all_bearish = all(not c['is_bullish'] and c['body_pct'] >= 50 for c in candles[-3:])
    
    # Three White Soldiers
    if all_bullish:
        # Each opens within previous body and closes higher
        valid = True
        for i in range(-2, 0):
            if not (opens[i] > opens[i-1] and opens[i] < closes[i-1] and
                    closes[i] > closes[i-1]):
                valid = False
                break
        
        if valid:
            return PatternResult(
                name="Three White Soldiers",
                type=PatternType.BULLISH,
                strength=PatternStrength.STRONG,
                confidence=85,
                description="Very strong bullish signal. Strong buying momentum.",
                action="Strong buy signal - trend likely to continue"
            )
    
    # Three Black Crows
    if all_bearish:
        valid = True
        for i in range(-2, 0):
            if not (opens[i] < opens[i-1] and opens[i] > closes[i-1] and
                    closes[i] < closes[i-1]):
                valid = False
                break
        
        if valid:
            return PatternResult(
                name="Three Black Crows",
                type=PatternType.BEARISH,
                strength=PatternStrength.STRONG,
                confidence=85,
                description="Very strong bearish signal. Strong selling momentum.",
                action="Strong sell signal - downtrend likely to continue"
            )
    
    return None


def detect_piercing_dark_cloud(
    curr_open: float, curr_close: float, curr_high: float, curr_low: float,
    prev_open: float, prev_close: float, prev_high: float, prev_low: float,
    prev_trend: str
) -> Optional[PatternResult]:
    """
    Detect Piercing Pattern (bullish) or Dark Cloud Cover (bearish)
    """
    prev_is_bullish = prev_close > prev_open
    curr_is_bullish = curr_close > curr_open
    prev_midpoint = (prev_open + prev_close) / 2
    
    # Piercing Pattern: After downtrend, bearish then bullish that closes above midpoint
    if (prev_trend == 'down' and
        not prev_is_bullish and curr_is_bullish and
        curr_open < prev_low and  # Gap down open
        curr_close > prev_midpoint and curr_close < prev_open):  # Closes above midpoint
        
        return PatternResult(
            name="Piercing Pattern",
            type=PatternType.BULLISH,
            strength=PatternStrength.MODERATE,
            confidence=70,
            description="Bullish reversal signal. Buyers recovering from gap down.",
            action="Consider buying with confirmation"
        )
    
    # Dark Cloud Cover: After uptrend, bullish then bearish that closes below midpoint
    if (prev_trend == 'up' and
        prev_is_bullish and not curr_is_bullish and
        curr_open > prev_high and  # Gap up open
        curr_close < prev_midpoint and curr_close > prev_close):  # Closes below midpoint
        
        return PatternResult(
            name="Dark Cloud Cover",
            type=PatternType.BEARISH,
            strength=PatternStrength.MODERATE,
            confidence=70,
            description="Bearish reversal signal. Sellers recovering from gap up.",
            action="Consider selling or tightening stops"
        )
    
    return None


def detect_tweezer(
    curr_high: float, curr_low: float,
    prev_high: float, prev_low: float,
    curr_is_bullish: bool, prev_is_bullish: bool,
    prev_trend: str,
    tolerance: float = 0.001
) -> Optional[PatternResult]:
    """
    Detect Tweezer Top (bearish) or Tweezer Bottom (bullish)
    Two candles with matching highs or lows
    """
    # Tweezer Top: Matching highs at resistance
    if (prev_trend == 'up' and
        abs(curr_high - prev_high) / prev_high <= tolerance and
        prev_is_bullish and not curr_is_bullish):
        
        return PatternResult(
            name="Tweezer Top",
            type=PatternType.BEARISH,
            strength=PatternStrength.MODERATE,
            confidence=70,
            description="Bearish reversal at resistance. Price rejected at same level twice.",
            action="Watch for selling opportunity"
        )
    
    # Tweezer Bottom: Matching lows at support
    if (prev_trend == 'down' and
        abs(curr_low - prev_low) / prev_low <= tolerance and
        not prev_is_bullish and curr_is_bullish):
        
        return PatternResult(
            name="Tweezer Bottom",
            type=PatternType.BULLISH,
            strength=PatternStrength.MODERATE,
            confidence=70,
            description="Bullish reversal at support. Price held at same level twice.",
            action="Watch for buying opportunity"
        )
    
    return None


# =============================================================================
# CHART PATTERN DETECTION
# =============================================================================

def detect_double_top_bottom(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    lookback: int = 50,
    tolerance: float = 0.02
) -> Optional[PatternResult]:
    """
    Detect Double Top (bearish) or Double Bottom (bullish)
    Two peaks/troughs at similar levels with a valley/peak between
    
    Industry-Standard Measured Move:
    - Double Bottom: Target = Neckline + (Neckline - Bottom)
    - Double Top: Target = Neckline - (Top - Neckline)
    - Invalidation: For Double Bottom, below the second trough; for Double Top, above the second peak
    """
    if len(highs) < lookback:
        return None
    
    window_highs = highs.tail(lookback)
    window_lows = lows.tail(lookback)
    window_closes = closes.tail(lookback)
    
    current_price = closes.iloc[-1]
    
    # Find peaks for double top
    high_max = window_highs.max()
    high_indices = window_highs[window_highs >= high_max * (1 - tolerance)].index
    
    if len(high_indices) >= 2:
        # Check if there's a valley between the two peaks
        first_peak_idx = high_indices[0]
        last_peak_idx = high_indices[-1]
        
        if first_peak_idx != last_peak_idx:
            between = window_lows.loc[first_peak_idx:last_peak_idx]
            if len(between) > 5:
                valley = between.min()
                neckline = valley
                
                # Price breaking below neckline confirms pattern
                if current_price < neckline:
                    # Calculate measured move (industry standard)
                    pattern_height = high_max - neckline
                    measured_target = neckline - pattern_height  # Target below neckline
                    invalidation_level = high_max * 1.01  # 1% above the top invalidates
                    
                    # Get horizon data
                    horizon_data = get_pattern_horizon("Double Top")
                    
                    target_pct = ((measured_target - current_price) / current_price) * 100
                    
                    return PatternResult(
                        name="Double Top",
                        type=PatternType.BEARISH,
                        strength=PatternStrength.STRONG,
                        confidence=80,
                        description=f"Bearish reversal confirmed. Neckline: Rs {neckline:.2f}",
                        action=f"Target: Rs {measured_target:.2f} ({target_pct:.1f}%). Stop above Rs {invalidation_level:.2f}",
                        neckline=neckline,
                        pattern_height=pattern_height,
                        measured_target=measured_target,
                        invalidation_level=invalidation_level,
                        breakout_level=neckline,
                        min_days=horizon_data['min_days'],
                        max_days=horizon_data['max_days'],
                        recommended_horizon=horizon_data['recommended_horizon'],
                        reliability=horizon_data['reliability']
                    )
    
    # Find troughs for double bottom
    low_min = window_lows.min()
    low_indices = window_lows[window_lows <= low_min * (1 + tolerance)].index
    
    if len(low_indices) >= 2:
        first_trough_idx = low_indices[0]
        last_trough_idx = low_indices[-1]
        
        if first_trough_idx != last_trough_idx:
            between = window_highs.loc[first_trough_idx:last_trough_idx]
            if len(between) > 5:
                peak = between.max()
                neckline = peak
                
                # Price breaking above neckline confirms pattern
                if current_price > neckline:
                    # Calculate measured move (industry standard)
                    pattern_height = neckline - low_min
                    measured_target = neckline + pattern_height  # Target above neckline
                    invalidation_level = low_min * 0.99  # 1% below the bottom invalidates
                    
                    # Get horizon data
                    horizon_data = get_pattern_horizon("Double Bottom")
                    
                    target_pct = ((measured_target - current_price) / current_price) * 100
                    
                    return PatternResult(
                        name="Double Bottom",
                        type=PatternType.BULLISH,
                        strength=PatternStrength.STRONG,
                        confidence=80,
                        description=f"Bullish reversal confirmed. Neckline: Rs {neckline:.2f}",
                        action=f"Target: Rs {measured_target:.2f} (+{target_pct:.1f}%). Stop below Rs {invalidation_level:.2f}",
                        neckline=neckline,
                        pattern_height=pattern_height,
                        measured_target=measured_target,
                        invalidation_level=invalidation_level,
                        breakout_level=neckline,
                        min_days=horizon_data['min_days'],
                        max_days=horizon_data['max_days'],
                        recommended_horizon=horizon_data['recommended_horizon'],
                        reliability=horizon_data['reliability']
                    )
    
    return None


def detect_head_shoulders(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    lookback: int = 60
) -> Optional[PatternResult]:
    """
    Detect Head and Shoulders (bearish) or Inverse Head and Shoulders (bullish)
    Three peaks with middle one highest, or three troughs with middle one lowest
    
    Industry-Standard Measured Move:
    - H&S: Target = Neckline - (Head - Neckline)
    - Inverse H&S: Target = Neckline + (Neckline - Head)
    - Most reliable reversal pattern (83% historical success rate)
    """
    if len(highs) < lookback:
        return None
    
    window = lookback
    window_highs = highs.tail(window)
    window_lows = lows.tail(window)
    current_price = closes.iloc[-1]
    
    # Divide into three sections
    section_len = window // 3
    
    left_highs = window_highs.iloc[:section_len]
    middle_highs = window_highs.iloc[section_len:2*section_len]
    right_highs = window_highs.iloc[2*section_len:]
    
    left_lows = window_lows.iloc[:section_len]
    middle_lows = window_lows.iloc[section_len:2*section_len]
    right_lows = window_lows.iloc[2*section_len:]
    
    # Head and Shoulders (bearish)
    left_shoulder = left_highs.max()
    head = middle_highs.max()
    right_shoulder = right_highs.max()
    
    # Neckline from the two troughs
    left_trough = left_lows.min()
    right_trough = right_lows.min()
    neckline = (left_trough + right_trough) / 2
    
    # Check pattern validity
    if (head > left_shoulder and head > right_shoulder and
        abs(left_shoulder - right_shoulder) / head < 0.05 and  # Shoulders similar height
        left_shoulder > neckline and right_shoulder > neckline):
        
        # Calculate measured move
        pattern_height = head - neckline
        measured_target = neckline - pattern_height
        invalidation_level = head * 1.01  # Above head invalidates
        
        if current_price < neckline:
            # Get horizon data
            horizon_data = get_pattern_horizon("Head and Shoulders")
            target_pct = ((measured_target - current_price) / current_price) * 100
            
            return PatternResult(
                name="Head and Shoulders",
                type=PatternType.BEARISH,
                strength=PatternStrength.STRONG,
                confidence=85,
                description=f"Classic bearish reversal. Neckline: Rs {neckline:.2f}, Head: Rs {head:.2f}",
                action=f"Target: Rs {measured_target:.2f} ({target_pct:.1f}%). Stop above Rs {invalidation_level:.2f}",
                neckline=neckline,
                pattern_height=pattern_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=neckline,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
        elif current_price < right_shoulder:
            # Pattern forming - use forming horizon
            horizon_data = get_pattern_horizon("Head and Shoulders (forming)")
            potential_target_pct = ((measured_target - neckline) / neckline) * 100
            
            return PatternResult(
                name="Head and Shoulders (forming)",
                type=PatternType.BEARISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description=f"Pattern forming. Neckline at Rs {neckline:.2f}. Watch for break.",
                action=f"If neckline breaks, target Rs {measured_target:.2f} ({potential_target_pct:.1f}%)",
                neckline=neckline,
                pattern_height=pattern_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=neckline,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
    
    # Inverse Head and Shoulders (bullish)
    left_shoulder_inv = left_lows.min()
    head_inv = middle_lows.min()
    right_shoulder_inv = right_lows.min()
    
    left_peak = left_highs.max()
    right_peak = right_highs.max()
    neckline_inv = (left_peak + right_peak) / 2
    
    if (head_inv < left_shoulder_inv and head_inv < right_shoulder_inv and
        abs(left_shoulder_inv - right_shoulder_inv) / abs(head_inv) < 0.05 and
        left_shoulder_inv < neckline_inv and right_shoulder_inv < neckline_inv):
        
        # Calculate measured move
        pattern_height = neckline_inv - head_inv
        measured_target = neckline_inv + pattern_height
        invalidation_level = head_inv * 0.99  # Below head invalidates
        
        if current_price > neckline_inv:
            # Get horizon data
            horizon_data = get_pattern_horizon("Inverse Head and Shoulders")
            target_pct = ((measured_target - current_price) / current_price) * 100
            
            return PatternResult(
                name="Inverse Head and Shoulders",
                type=PatternType.BULLISH,
                strength=PatternStrength.STRONG,
                confidence=85,
                description=f"Classic bullish reversal. Neckline: Rs {neckline_inv:.2f}, Head: Rs {head_inv:.2f}",
                action=f"Target: Rs {measured_target:.2f} (+{target_pct:.1f}%). Stop below Rs {invalidation_level:.2f}",
                neckline=neckline_inv,
                pattern_height=pattern_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=neckline_inv,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
        elif current_price > right_shoulder_inv:
            # Pattern forming
            horizon_data = get_pattern_horizon("Inverse Head and Shoulders (forming)")
            potential_target_pct = ((measured_target - neckline_inv) / neckline_inv) * 100
            
            return PatternResult(
                name="Inverse Head and Shoulders (forming)",
                type=PatternType.BULLISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description=f"Pattern forming. Neckline at Rs {neckline_inv:.2f}. Watch for break.",
                action=f"If neckline breaks, target Rs {measured_target:.2f} (+{potential_target_pct:.1f}%)",
                neckline=neckline_inv,
                pattern_height=pattern_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=neckline_inv,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
    
    return None


def detect_triangle(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    lookback: int = 30
) -> Optional[PatternResult]:
    """
    Detect Triangle patterns: Ascending, Descending, or Symmetrical
    
    Industry-Standard Measured Move:
    - Target = Breakout level +/- Triangle Height (widest part)
    - Triangle Height = High at start of pattern - Low at start of pattern
    """
    if len(highs) < lookback:
        return None
    
    window_highs = highs.tail(lookback)
    window_lows = lows.tail(lookback)
    current_price = closes.iloc[-1]
    
    # Calculate trendlines using linear regression
    x = np.arange(lookback)
    
    # Fit upper trendline (highs)
    try:
        high_slope, high_intercept = np.polyfit(x, window_highs.values, 1)
        low_slope, low_intercept = np.polyfit(x, window_lows.values, 1)
    except:
        return None
    
    # Determine triangle type
    high_flat = abs(high_slope) < 0.001 * window_highs.mean()
    low_flat = abs(low_slope) < 0.001 * window_lows.mean()
    converging = high_slope < 0 and low_slope > 0
    
    # Calculate triangle height (widest part - usually at the start)
    triangle_height = window_highs.iloc[0] - window_lows.iloc[0]
    
    # Ascending Triangle: Flat top, rising bottom
    if high_flat and low_slope > 0:
        resistance = window_highs.max()
        support = window_lows.iloc[-1]  # Current support level
        
        if current_price > resistance:
            # Breakout confirmed
            measured_target = resistance + triangle_height
            invalidation_level = support * 0.98  # Below support invalidates
            
            horizon_data = get_pattern_horizon("Ascending Triangle Breakout")
            target_pct = ((measured_target - current_price) / current_price) * 100
            
            return PatternResult(
                name="Ascending Triangle Breakout",
                type=PatternType.BULLISH,
                strength=PatternStrength.STRONG,
                confidence=80,
                description=f"Bullish breakout confirmed. Resistance broken at Rs {resistance:.2f}",
                action=f"Target: Rs {measured_target:.2f} (+{target_pct:.1f}%). Stop below Rs {invalidation_level:.2f}",
                neckline=resistance,
                pattern_height=triangle_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=resistance,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
        else:
            # Pattern forming
            potential_target = resistance + triangle_height
            horizon_data = get_pattern_horizon("Ascending Triangle")
            potential_target_pct = ((potential_target - resistance) / resistance) * 100
            
            return PatternResult(
                name="Ascending Triangle",
                type=PatternType.BULLISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description=f"Bullish pattern forming. Resistance at Rs {resistance:.2f}",
                action=f"On breakout, target Rs {potential_target:.2f} (+{potential_target_pct:.1f}%)",
                neckline=resistance,
                pattern_height=triangle_height,
                measured_target=potential_target,
                invalidation_level=window_lows.min() * 0.98,
                breakout_level=resistance,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
    
    # Descending Triangle: Flat bottom, falling top
    if low_flat and high_slope < 0:
        support = window_lows.min()
        resistance = window_highs.iloc[-1]  # Current resistance level
        
        if current_price < support:
            # Breakdown confirmed
            measured_target = support - triangle_height
            invalidation_level = resistance * 1.02  # Above resistance invalidates
            
            horizon_data = get_pattern_horizon("Descending Triangle Breakdown")
            target_pct = ((measured_target - current_price) / current_price) * 100
            
            return PatternResult(
                name="Descending Triangle Breakdown",
                type=PatternType.BEARISH,
                strength=PatternStrength.STRONG,
                confidence=80,
                description=f"Bearish breakdown confirmed. Support broken at Rs {support:.2f}",
                action=f"Target: Rs {measured_target:.2f} ({target_pct:.1f}%). Stop above Rs {invalidation_level:.2f}",
                neckline=support,
                pattern_height=triangle_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=support,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
        else:
            # Pattern forming
            potential_target = support - triangle_height
            horizon_data = get_pattern_horizon("Descending Triangle")
            potential_target_pct = ((potential_target - support) / support) * 100
            
            return PatternResult(
                name="Descending Triangle",
                type=PatternType.BEARISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description=f"Bearish pattern forming. Support at Rs {support:.2f}",
                action=f"On breakdown, target Rs {potential_target:.2f} ({potential_target_pct:.1f}%)",
                neckline=support,
                pattern_height=triangle_height,
                measured_target=potential_target,
                invalidation_level=window_highs.max() * 1.02,
                breakout_level=support,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
    
    # Symmetrical Triangle: Converging trendlines
    if converging:
        apex_price = (window_highs.iloc[-1] + window_lows.iloc[-1]) / 2
        recent_high = window_highs.iloc[-5:].max()
        recent_low = window_lows.iloc[-5:].min()
        
        if current_price > recent_high:
            # Bullish breakout
            measured_target = recent_high + triangle_height
            invalidation_level = recent_low * 0.98
            
            horizon_data = get_pattern_horizon("Symmetrical Triangle Bullish Breakout")
            target_pct = ((measured_target - current_price) / current_price) * 100
            
            return PatternResult(
                name="Symmetrical Triangle Bullish Breakout",
                type=PatternType.BULLISH,
                strength=PatternStrength.MODERATE,
                confidence=70,
                description=f"Bullish breakout from symmetrical triangle at Rs {recent_high:.2f}",
                action=f"Target: Rs {measured_target:.2f} (+{target_pct:.1f}%). Stop below Rs {invalidation_level:.2f}",
                neckline=recent_high,
                pattern_height=triangle_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=recent_high,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
        elif current_price < recent_low:
            # Bearish breakdown
            measured_target = recent_low - triangle_height
            invalidation_level = recent_high * 1.02
            
            horizon_data = get_pattern_horizon("Symmetrical Triangle Bearish Breakdown")
            target_pct = ((measured_target - current_price) / current_price) * 100
            
            return PatternResult(
                name="Symmetrical Triangle Bearish Breakdown",
                type=PatternType.BEARISH,
                strength=PatternStrength.MODERATE,
                confidence=70,
                description=f"Bearish breakdown from symmetrical triangle at Rs {recent_low:.2f}",
                action=f"Target: Rs {measured_target:.2f} ({target_pct:.1f}%). Stop above Rs {invalidation_level:.2f}",
                neckline=recent_low,
                pattern_height=triangle_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=recent_low,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
        else:
            # Pattern still forming
            horizon_data = get_pattern_horizon("Symmetrical Triangle")
            
            return PatternResult(
                name="Symmetrical Triangle",
                type=PatternType.NEUTRAL,
                strength=PatternStrength.WEAK,
                confidence=55,
                description=f"Symmetrical triangle forming. Range: Rs {recent_low:.2f} - Rs {recent_high:.2f}",
                action="Wait for breakout. Target = triangle height from breakout point.",
                neckline=apex_price,
                pattern_height=triangle_height,
                measured_target=None,  # Unknown until breakout direction
                invalidation_level=None,
                breakout_level=None,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
    
    return None


def detect_wedge(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    lookback: int = 30
) -> Optional[PatternResult]:
    """
    Detect Rising Wedge (bearish) or Falling Wedge (bullish)
    
    Industry-Standard Measured Move:
    - Target = Breakout point +/- Wedge Height (widest part)
    - Rising Wedge breaks down, Falling Wedge breaks up
    """
    if len(highs) < lookback:
        return None
    
    window_highs = highs.tail(lookback)
    window_lows = lows.tail(lookback)
    current_price = closes.iloc[-1]
    
    x = np.arange(lookback)
    
    try:
        high_slope, _ = np.polyfit(x, window_highs.values, 1)
        low_slope, _ = np.polyfit(x, window_lows.values, 1)
    except:
        return None
    
    # Wedge height (widest part - at the start)
    wedge_height = window_highs.iloc[0] - window_lows.iloc[0]
    
    # Rising Wedge: Both slopes positive, but converging (high slope < low slope)
    if high_slope > 0 and low_slope > 0 and high_slope < low_slope:
        breakdown_level = window_lows.iloc[-5:].min()
        
        if current_price < breakdown_level:
            # Breakdown confirmed
            measured_target = breakdown_level - wedge_height
            invalidation_level = window_highs.max() * 1.01
            
            horizon_data = get_pattern_horizon("Rising Wedge Breakdown")
            target_pct = ((measured_target - current_price) / current_price) * 100
            
            return PatternResult(
                name="Rising Wedge Breakdown",
                type=PatternType.BEARISH,
                strength=PatternStrength.STRONG,
                confidence=80,
                description=f"Bearish breakdown confirmed at Rs {breakdown_level:.2f}",
                action=f"Target: Rs {measured_target:.2f} ({target_pct:.1f}%). Stop above Rs {invalidation_level:.2f}",
                neckline=breakdown_level,
                pattern_height=wedge_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=breakdown_level,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
        else:
            # Pattern forming
            potential_target = breakdown_level - wedge_height
            horizon_data = get_pattern_horizon("Rising Wedge")
            potential_target_pct = ((potential_target - breakdown_level) / breakdown_level) * 100
            
            return PatternResult(
                name="Rising Wedge",
                type=PatternType.BEARISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description=f"Rising wedge forming. Watch support at Rs {breakdown_level:.2f}",
                action=f"On breakdown, target Rs {potential_target:.2f} ({potential_target_pct:.1f}%)",
                neckline=breakdown_level,
                pattern_height=wedge_height,
                measured_target=potential_target,
                invalidation_level=window_highs.max() * 1.01,
                breakout_level=breakdown_level,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
    
    # Falling Wedge: Both slopes negative, but converging (high slope > low slope)
    if high_slope < 0 and low_slope < 0 and high_slope > low_slope:
        breakout_level = window_highs.iloc[-5:].max()
        
        if current_price > breakout_level:
            # Breakout confirmed
            measured_target = breakout_level + wedge_height
            invalidation_level = window_lows.min() * 0.99
            
            horizon_data = get_pattern_horizon("Falling Wedge Breakout")
            target_pct = ((measured_target - current_price) / current_price) * 100
            
            return PatternResult(
                name="Falling Wedge Breakout",
                type=PatternType.BULLISH,
                strength=PatternStrength.STRONG,
                confidence=80,
                description=f"Bullish breakout confirmed at Rs {breakout_level:.2f}",
                action=f"Target: Rs {measured_target:.2f} (+{target_pct:.1f}%). Stop below Rs {invalidation_level:.2f}",
                neckline=breakout_level,
                pattern_height=wedge_height,
                measured_target=measured_target,
                invalidation_level=invalidation_level,
                breakout_level=breakout_level,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
        else:
            # Pattern forming
            potential_target = breakout_level + wedge_height
            horizon_data = get_pattern_horizon("Falling Wedge")
            potential_target_pct = ((potential_target - breakout_level) / breakout_level) * 100
            
            return PatternResult(
                name="Falling Wedge",
                type=PatternType.BULLISH,
                strength=PatternStrength.MODERATE,
                confidence=65,
                description=f"Falling wedge forming. Watch resistance at Rs {breakout_level:.2f}",
                action=f"On breakout, target Rs {potential_target:.2f} (+{potential_target_pct:.1f}%)",
                neckline=breakout_level,
                pattern_height=wedge_height,
                measured_target=potential_target,
                invalidation_level=window_lows.min() * 0.99,
                breakout_level=breakout_level,
                min_days=horizon_data['min_days'],
                max_days=horizon_data['max_days'],
                recommended_horizon=horizon_data['recommended_horizon'],
                reliability=horizon_data['reliability']
            )
    
    return None


def detect_flag_pennant(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    lookback: int = 20
) -> Optional[PatternResult]:
    """
    Detect Bull/Bear Flags and Pennants
    Short consolidation after strong move
    
    Industry-Standard Measured Move:
    - Target = Breakout point + Flagpole Height
    - Flagpole Height = Price move before the flag formed
    - Flags are short-term patterns (typically 1-3 weeks)
    """
    if len(closes) < lookback + 10:
        return None
    
    # Check for strong prior move (flagpole)
    prior_move = closes.tail(lookback + 10).head(10)
    prior_change = (prior_move.iloc[-1] - prior_move.iloc[0]) / prior_move.iloc[0] * 100
    
    # Need significant prior move (>5%)
    if abs(prior_change) < 5:
        return None
    
    # Calculate flagpole height (the strong move before consolidation)
    flagpole_height = abs(prior_move.iloc[-1] - prior_move.iloc[0])
    
    # Recent consolidation
    recent_highs = highs.tail(lookback)
    recent_lows = lows.tail(lookback)
    current_price = closes.iloc[-1]
    
    # Calculate consolidation range
    consolidation_range = (recent_highs.max() - recent_lows.min()) / recent_lows.min() * 100
    
    # Flag/Pennant should have tight consolidation (<50% of prior move)
    if consolidation_range > abs(prior_change) * 0.5:
        return None
    
    x = np.arange(lookback)
    try:
        high_slope, _ = np.polyfit(x, recent_highs.values, 1)
        low_slope, _ = np.polyfit(x, recent_lows.values, 1)
    except:
        return None
    
    is_bullish_prior = prior_change > 0
    
    if is_bullish_prior:
        # Bull Flag: Prior up move, slight downward consolidation
        if high_slope < 0 and low_slope < 0:
            breakout_level = recent_highs.max()
            
            if current_price > breakout_level:
                # Breakout confirmed
                measured_target = breakout_level + flagpole_height
                invalidation_level = recent_lows.min() * 0.98
                
                horizon_data = get_pattern_horizon("Bull Flag Breakout")
                target_pct = ((measured_target - current_price) / current_price) * 100
                
                return PatternResult(
                    name="Bull Flag Breakout",
                    type=PatternType.BULLISH,
                    strength=PatternStrength.STRONG,
                    confidence=80,
                    description=f"Bullish continuation. Breakout at Rs {breakout_level:.2f}. Flagpole: {prior_change:.1f}%",
                    action=f"Target: Rs {measured_target:.2f} (+{target_pct:.1f}%). Stop below Rs {invalidation_level:.2f}",
                    neckline=breakout_level,
                    pattern_height=flagpole_height,
                    measured_target=measured_target,
                    invalidation_level=invalidation_level,
                    breakout_level=breakout_level,
                    min_days=horizon_data['min_days'],
                    max_days=horizon_data['max_days'],
                    recommended_horizon=horizon_data['recommended_horizon'],
                    reliability=horizon_data['reliability']
                )
            else:
                # Pattern forming
                potential_target = breakout_level + flagpole_height
                horizon_data = get_pattern_horizon("Bull Flag")
                potential_target_pct = ((potential_target - breakout_level) / breakout_level) * 100
                
                return PatternResult(
                    name="Bull Flag",
                    type=PatternType.BULLISH,
                    strength=PatternStrength.MODERATE,
                    confidence=70,
                    description=f"Bull flag forming. Prior move: +{prior_change:.1f}%. Resistance: Rs {breakout_level:.2f}",
                    action=f"On breakout, target Rs {potential_target:.2f} (+{potential_target_pct:.1f}%)",
                    neckline=breakout_level,
                    pattern_height=flagpole_height,
                    measured_target=potential_target,
                    invalidation_level=recent_lows.min() * 0.98,
                    breakout_level=breakout_level,
                    min_days=horizon_data['min_days'],
                    max_days=horizon_data['max_days'],
                    recommended_horizon=horizon_data['recommended_horizon'],
                    reliability=horizon_data['reliability']
                )
    else:
        # Bear Flag: Prior down move, slight upward consolidation
        if high_slope > 0 and low_slope > 0:
            breakdown_level = recent_lows.min()
            
            if current_price < breakdown_level:
                # Breakdown confirmed
                measured_target = breakdown_level - flagpole_height
                invalidation_level = recent_highs.max() * 1.02
                
                horizon_data = get_pattern_horizon("Bear Flag Breakdown")
                target_pct = ((measured_target - current_price) / current_price) * 100
                
                return PatternResult(
                    name="Bear Flag Breakdown",
                    type=PatternType.BEARISH,
                    strength=PatternStrength.STRONG,
                    confidence=80,
                    description=f"Bearish continuation. Breakdown at Rs {breakdown_level:.2f}. Flagpole: {prior_change:.1f}%",
                    action=f"Target: Rs {measured_target:.2f} ({target_pct:.1f}%). Stop above Rs {invalidation_level:.2f}",
                    neckline=breakdown_level,
                    pattern_height=flagpole_height,
                    measured_target=measured_target,
                    invalidation_level=invalidation_level,
                    breakout_level=breakdown_level,
                    min_days=horizon_data['min_days'],
                    max_days=horizon_data['max_days'],
                    recommended_horizon=horizon_data['recommended_horizon'],
                    reliability=horizon_data['reliability']
                )
            else:
                # Pattern forming
                potential_target = breakdown_level - flagpole_height
                horizon_data = get_pattern_horizon("Bear Flag")
                potential_target_pct = ((potential_target - breakdown_level) / breakdown_level) * 100
                
                return PatternResult(
                    name="Bear Flag",
                    type=PatternType.BEARISH,
                    strength=PatternStrength.MODERATE,
                    confidence=70,
                    description=f"Bear flag forming. Prior move: {prior_change:.1f}%. Support: Rs {breakdown_level:.2f}",
                    action=f"On breakdown, target Rs {potential_target:.2f} ({potential_target_pct:.1f}%)",
                    neckline=breakdown_level,
                    pattern_height=flagpole_height,
                    measured_target=potential_target,
                    invalidation_level=recent_highs.max() * 1.02,
                    breakout_level=breakdown_level,
                    min_days=horizon_data['min_days'],
                    max_days=horizon_data['max_days'],
                    recommended_horizon=horizon_data['recommended_horizon'],
                    reliability=horizon_data['reliability']
                )
    
    return None


# =============================================================================
# MAIN PATTERN DETECTION FUNCTION
# =============================================================================

def detect_all_patterns(df: pd.DataFrame) -> Dict[str, any]:
    """
    Detect all candlestick and chart patterns
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        Dictionary containing all detected patterns and summary
    """
    if df is None or df.empty or len(df) < 20:
        return {
            'candlestick_patterns': [],
            'chart_patterns': [],
            'bullish_count': 0,
            'bearish_count': 0,
            'pattern_bias': 'neutral',
            'strongest_pattern': None,
            'pattern_summary': "Insufficient data for pattern detection"
        }
    
    opens = df['open'].values
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    
    # Calculate candle properties for recent candles
    candle_props = []
    for i in range(-5, 0):
        if len(opens) >= abs(i):
            props = calculate_candle_properties(opens[i], highs[i], lows[i], closes[i])
            candle_props.append(props)
    
    # Determine recent trend
    if len(closes) >= 10:
        recent_change = (closes[-1] - closes[-10]) / closes[-10] * 100
        if recent_change > 3:
            prev_trend = 'up'
        elif recent_change < -3:
            prev_trend = 'down'
        else:
            prev_trend = 'sideways'
    else:
        prev_trend = 'sideways'
    
    candlestick_patterns = []
    chart_patterns = []
    
    # Detect single candle patterns (most recent candle)
    if candle_props:
        current_candle = candle_props[-1]
        
        patterns = [
            detect_doji(current_candle),
            detect_hammer(current_candle, prev_trend),
            detect_shooting_star(current_candle, prev_trend),
            detect_marubozu(current_candle),
            detect_spinning_top(current_candle),
        ]
        
        for p in patterns:
            if p:
                candlestick_patterns.append(p)
    
    # Detect double candle patterns
    if len(candle_props) >= 2:
        patterns = [
            detect_engulfing(
                opens[-1], closes[-1], opens[-2], closes[-2], prev_trend
            ),
            detect_harami(
                opens[-1], closes[-1], opens[-2], closes[-2], prev_trend
            ),
            detect_piercing_dark_cloud(
                opens[-1], closes[-1], highs[-1], lows[-1],
                opens[-2], closes[-2], highs[-2], lows[-2], prev_trend
            ),
            detect_tweezer(
                highs[-1], lows[-1], highs[-2], lows[-2],
                closes[-1] > opens[-1], closes[-2] > opens[-2], prev_trend
            ),
        ]
        
        for p in patterns:
            if p:
                candlestick_patterns.append(p)
    
    # Detect triple candle patterns
    if len(candle_props) >= 3:
        patterns = [
            detect_morning_evening_star(
                candle_props[-3:],
                list(opens[-3:]), list(closes[-3:]), prev_trend
            ),
            detect_three_soldiers_crows(
                candle_props[-3:],
                list(opens[-3:]), list(closes[-3:]),
                list(highs[-3:]), list(lows[-3:])
            ),
        ]
        
        for p in patterns:
            if p:
                candlestick_patterns.append(p)
    
    # Detect chart patterns
    highs_series = df['high']
    lows_series = df['low']
    closes_series = df['close']
    
    chart_pattern_funcs = [
        lambda: detect_double_top_bottom(highs_series, lows_series, closes_series),
        lambda: detect_head_shoulders(highs_series, lows_series, closes_series),
        lambda: detect_triangle(highs_series, lows_series, closes_series),
        lambda: detect_wedge(highs_series, lows_series, closes_series),
        lambda: detect_flag_pennant(highs_series, lows_series, closes_series),
    ]
    
    for func in chart_pattern_funcs:
        try:
            p = func()
            if p:
                chart_patterns.append(p)
        except Exception:
            continue
    
    # Analyze patterns
    all_patterns = candlestick_patterns + chart_patterns
    bullish = [p for p in all_patterns if p.type == PatternType.BULLISH]
    bearish = [p for p in all_patterns if p.type == PatternType.BEARISH]
    
    # Determine overall bias
    bullish_score = sum(p.confidence for p in bullish)
    bearish_score = sum(p.confidence for p in bearish)
    
    if bullish_score > bearish_score + 20:
        pattern_bias = 'bullish'
    elif bearish_score > bullish_score + 20:
        pattern_bias = 'bearish'
    else:
        pattern_bias = 'neutral'
    
    # Find strongest pattern
    strongest = max(all_patterns, key=lambda p: p.confidence) if all_patterns else None
    
    # Generate summary
    if strongest:
        summary = f"{strongest.name} detected ({strongest.type.value}, {strongest.confidence}% confidence). {strongest.description}"
    elif all_patterns:
        summary = f"Found {len(all_patterns)} patterns. Overall bias: {pattern_bias}"
    else:
        summary = "No significant patterns detected"
    
    return {
        'candlestick_patterns': candlestick_patterns,
        'chart_patterns': chart_patterns,
        'all_patterns': all_patterns,
        'bullish_count': len(bullish),
        'bearish_count': len(bearish),
        'bullish_score': bullish_score,
        'bearish_score': bearish_score,
        'pattern_bias': pattern_bias,
        'strongest_pattern': strongest,
        'pattern_summary': summary,
    }

