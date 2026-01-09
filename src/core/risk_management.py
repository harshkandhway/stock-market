"""
Risk Management Module for Stock Analyzer Pro
Handles position sizing, stop losses, targets, trailing stops, and time estimation

Author: Harsh Kandhway
"""

from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import math
from .config import (
    RISK_MODES, FIBONACCI_EXTENSION, CURRENCY_SYMBOL,
    INVESTMENT_HORIZONS, TRADING_DAYS_PER_YEAR, TRADING_DAYS_PER_MONTH
)


def calculate_targets(
    current_price: float,
    atr: float,
    resistance: float,
    support: float,
    fib_extensions: Dict[str, float],
    mode: str = 'balanced',
    direction: str = 'long',
    horizon: str = '3months',
    strongest_pattern: Optional[any] = None
) -> Dict[str, any]:
    """
    Calculate price targets using multiple professional methods AND investment horizons
    
    Methods:
    1. ATR-based (volatility)
    2. Support/Resistance based
    3. Fibonacci extension based
    4. Horizon-based (expected returns for different time periods)
    5. Pattern-based (industry-standard measured moves) - NEW
    
    Pattern Integration:
    - If pattern has measured_target, use 40% pattern + 30% horizon + 30% technical
    - If pattern reliability > 0.7, increase pattern weight to 50%
    - Pattern invalidation_level used for tighter stop loss
    
    Returns targets for ALL horizons, marking the selected one as recommended
    """
    mode_config = RISK_MODES[mode]
    atr_multiplier = mode_config['atr_target_multiplier']
    
    targets = {}
    
    # Initialize pattern target info
    targets['has_pattern_target'] = False
    targets['pattern_target'] = None
    targets['pattern_target_pct'] = None
    targets['pattern_name'] = None
    targets['pattern_reliability'] = None
    targets['pattern_horizon'] = None
    targets['pattern_invalidation'] = None
    
    if direction == 'long':
        # ATR-based target (short-term technical)
        targets['atr_target'] = current_price + (atr_multiplier * atr)
        targets['atr_target_pct'] = ((targets['atr_target'] - current_price) / current_price) * 100
        
        # Resistance-based target
        targets['resistance_target'] = resistance
        targets['resistance_target_pct'] = ((resistance - current_price) / current_price) * 100
        
        # Fibonacci extension targets
        fib_127 = fib_extensions.get('fib_ext_127', current_price * 1.05)
        fib_161 = fib_extensions.get('fib_ext_161', current_price * 1.08)
        fib_200 = fib_extensions.get('fib_ext_200', current_price * 1.12)
        targets['fib_target_1'] = fib_127
        targets['fib_target_1_pct'] = ((fib_127 - current_price) / current_price) * 100
        targets['fib_target_2'] = fib_161
        targets['fib_target_2_pct'] = ((fib_161 - current_price) / current_price) * 100
        targets['fib_target_3'] = fib_200
        targets['fib_target_3_pct'] = ((fib_200 - current_price) / current_price) * 100
        
        # =====================================================================
        # HORIZON-BASED TARGETS - Calculate for ALL investment horizons
        # =====================================================================
        targets['horizon_targets'] = {}
        
        for horizon_key, horizon_config in INVESTMENT_HORIZONS.items():
            # Get expected return range for this horizon
            min_return = horizon_config['expected_return_min']
            max_return = horizon_config['expected_return_max']
            
            # Calculate target based on mode
            if mode == 'conservative':
                # Use minimum expected return
                target_pct = min_return
            elif mode == 'aggressive':
                # Use maximum expected return
                target_pct = max_return
            else:  # balanced/moderate
                # Use average of min and max
                target_pct = (min_return + max_return) / 2
            
            # Calculate price target
            horizon_target = current_price * (1 + target_pct / 100)
            
            # Combine with technical targets for better accuracy
            # Give 70% weight to horizon expectation, 30% to technical
            technical_target = targets['atr_target']
            if horizon_key in ['1week', '2weeks']:
                technical_target = targets['atr_target']
            elif horizon_key in ['1month', '3months']:
                technical_target = targets['fib_target_1']
            else:  # 6months, 1year
                technical_target = targets['fib_target_2']
            
            combined_target = (horizon_target * 0.7) + (technical_target * 0.3)
            
            targets['horizon_targets'][horizon_key] = {
                'target': combined_target,
                'target_pct': ((combined_target - current_price) / current_price) * 100,
                'horizon_name': horizon_config['display_name'],
                'timeframe': horizon_config['avg_days'],
                'min_days': horizon_config['min_days'],
                'max_days': horizon_config['max_days'],
                'emoji': horizon_config['emoji'],
                'is_recommended': horizon_key == horizon
            }
        
        # Conservative target (lowest of reasonable targets)
        reasonable_targets = [
            targets['atr_target'],
            targets['resistance_target'],
            targets['fib_target_1']
        ]
        # Filter targets that are above current price
        valid_targets = [t for t in reasonable_targets if t > current_price]
        if valid_targets:
            targets['conservative_target'] = min(valid_targets)
        else:
            # Fallback: use ATR target if no valid targets (add small buffer)
            targets['conservative_target'] = current_price * 1.02  # 2% default
        targets['conservative_target_pct'] = ((targets['conservative_target'] - current_price) / current_price) * 100
        
        # Aggressive target
        targets['aggressive_target'] = targets['fib_target_2']
        targets['aggressive_target_pct'] = targets['fib_target_2_pct']
        
        # =====================================================================
        # PATTERN-BASED TARGETS - Industry-standard measured moves
        # =====================================================================
        if strongest_pattern is not None and hasattr(strongest_pattern, 'measured_target'):
            pattern_target = strongest_pattern.measured_target
            
            if pattern_target is not None and pattern_target > current_price:
                targets['has_pattern_target'] = True
                targets['pattern_target'] = pattern_target
                targets['pattern_target_pct'] = ((pattern_target - current_price) / current_price) * 100
                targets['pattern_name'] = strongest_pattern.name
                targets['pattern_reliability'] = strongest_pattern.reliability
                targets['pattern_horizon'] = strongest_pattern.recommended_horizon
                targets['pattern_invalidation'] = strongest_pattern.invalidation_level
                targets['pattern_height'] = strongest_pattern.pattern_height
                targets['pattern_neckline'] = strongest_pattern.neckline
                targets['pattern_min_days'] = strongest_pattern.min_days
                targets['pattern_max_days'] = strongest_pattern.max_days
                
                # Recalculate horizon targets with pattern integration
                # When pattern is present with high confidence, give more weight to pattern
                pattern_reliability = strongest_pattern.reliability or 0.5
                
                for horizon_key in targets['horizon_targets'].keys():
                    horizon_data = targets['horizon_targets'][horizon_key]
                    old_target = horizon_data['target']
                    
                    # Determine weight based on pattern reliability
                    if pattern_reliability >= 0.75:
                        # High reliability: 50% pattern, 25% horizon, 25% technical
                        pattern_weight = 0.50
                        horizon_weight = 0.25
                        technical_weight = 0.25
                    elif pattern_reliability >= 0.65:
                        # Medium reliability: 40% pattern, 30% horizon, 30% technical
                        pattern_weight = 0.40
                        horizon_weight = 0.30
                        technical_weight = 0.30
                    else:
                        # Low reliability: 30% pattern, 40% horizon, 30% technical
                        pattern_weight = 0.30
                        horizon_weight = 0.40
                        technical_weight = 0.30
                    
                    # Get technical target for this horizon
                    if horizon_key in ['1week', '2weeks']:
                        tech_target = targets['atr_target']
                    elif horizon_key in ['1month', '3months']:
                        tech_target = targets['fib_target_1']
                    else:
                        tech_target = targets['fib_target_2']
                    
                    # Calculate original horizon-only target (before pattern)
                    horizon_config = INVESTMENT_HORIZONS[horizon_key]
                    if mode == 'conservative':
                        exp_return = horizon_config['expected_return_min']
                    elif mode == 'aggressive':
                        exp_return = horizon_config['expected_return_max']
                    else:
                        exp_return = (horizon_config['expected_return_min'] + horizon_config['expected_return_max']) / 2
                    horizon_only_target = current_price * (1 + exp_return / 100)
                    
                    # Combined target with pattern
                    combined_target = (
                        pattern_target * pattern_weight +
                        horizon_only_target * horizon_weight +
                        tech_target * technical_weight
                    )
                    
                    targets['horizon_targets'][horizon_key]['target'] = combined_target
                    targets['horizon_targets'][horizon_key]['target_pct'] = ((combined_target - current_price) / current_price) * 100
                    targets['horizon_targets'][horizon_key]['pattern_integrated'] = True
                    targets['horizon_targets'][horizon_key]['pattern_weight'] = pattern_weight
        
    else:  # short
        # ATR-based target
        targets['atr_target'] = current_price - (atr_multiplier * atr)
        targets['atr_target_pct'] = ((current_price - targets['atr_target']) / current_price) * 100
        
        # Support-based target
        targets['support_target'] = support
        targets['support_target_pct'] = ((current_price - support) / current_price) * 100
        
        # Conservative target (highest of targets, meaning smallest move)
        targets['conservative_target'] = max(targets['atr_target'], targets['support_target'])
        targets['conservative_target_pct'] = ((current_price - targets['conservative_target']) / current_price) * 100
    
    # Recommended target based on SELECTED HORIZON
    if horizon in targets.get('horizon_targets', {}):
        horizon_data = targets['horizon_targets'][horizon]
        targets['recommended_target'] = horizon_data['target']
        targets['recommended_target_pct'] = horizon_data['target_pct']
        targets['recommended_timeframe'] = horizon_data['timeframe']
    else:
        # Fallback to mode-based (old logic)
        if mode == 'conservative':
            targets['recommended_target'] = targets['conservative_target']
            targets['recommended_target_pct'] = targets['conservative_target_pct']
        elif mode == 'aggressive':
            targets['recommended_target'] = targets.get('aggressive_target', targets['atr_target'])
            targets['recommended_target_pct'] = targets.get('aggressive_target_pct', targets['atr_target_pct'])
        else:  # balanced
            targets['recommended_target'] = targets['atr_target']
            targets['recommended_target_pct'] = targets['atr_target_pct']
        targets['recommended_timeframe'] = 90  # default 3 months
    
    # Check for pattern-horizon mismatch warning
    targets['pattern_horizon_warning'] = None
    if targets.get('has_pattern_target') and targets.get('pattern_horizon'):
        pattern_horizon = targets['pattern_horizon']
        if pattern_horizon != horizon:
            # Map horizons to approximate days for comparison
            horizon_days = INVESTMENT_HORIZONS.get(horizon, {}).get('avg_days', 90)
            pattern_days = INVESTMENT_HORIZONS.get(pattern_horizon, {}).get('avg_days', 30)
            
            if abs(horizon_days - pattern_days) > 30:  # Significant mismatch
                targets['pattern_horizon_warning'] = (
                    f"Pattern '{targets['pattern_name']}' typically plays out in {pattern_horizon} "
                    f"({pattern_days} days), but you selected {horizon} ({horizon_days} days). "
                    f"Consider adjusting your timeframe for optimal results."
                )
    
    targets['direction'] = direction
    targets['selected_horizon'] = horizon
    
    return targets


def calculate_stoploss(
    current_price: float,
    atr: float,
    support: float,
    resistance: float,
    mode: str = 'balanced',
    direction: str = 'long'
) -> Dict[str, any]:
    """
    Calculate stop loss using ATR + Support/Resistance levels
    
    Conservative: 2.5 × ATR
    Balanced: 2.0 × ATR
    Aggressive: 1.5 × ATR
    
    Also considers support/resistance with buffer
    """
    mode_config = RISK_MODES[mode]
    atr_multiplier = mode_config['atr_stop_multiplier']
    
    stops = {}
    
    if direction == 'long':
        # ATR-based stop
        stops['atr_stop'] = current_price - (atr_multiplier * atr)
        stops['atr_stop_pct'] = ((current_price - stops['atr_stop']) / current_price) * 100
        
        # Support-based stop (with buffer)
        buffer = 0.5 * atr
        stops['support_stop'] = support - buffer
        stops['support_stop_pct'] = ((current_price - stops['support_stop']) / current_price) * 100
        
        # Use the higher (closer) stop for safety
        stops['recommended_stop'] = max(stops['atr_stop'], stops['support_stop'])
        stops['recommended_stop_pct'] = ((current_price - stops['recommended_stop']) / current_price) * 100
        
    else:  # short
        # ATR-based stop
        stops['atr_stop'] = current_price + (atr_multiplier * atr)
        stops['atr_stop_pct'] = ((stops['atr_stop'] - current_price) / current_price) * 100
        
        # Resistance-based stop (with buffer)
        buffer = 0.5 * atr
        stops['resistance_stop'] = resistance + buffer
        stops['resistance_stop_pct'] = ((stops['resistance_stop'] - current_price) / current_price) * 100
        
        # Use the lower (closer) stop for safety
        stops['recommended_stop'] = min(stops['atr_stop'], stops['resistance_stop'])
        stops['recommended_stop_pct'] = ((stops['recommended_stop'] - current_price) / current_price) * 100
    
    stops['direction'] = direction
    stops['atr_multiplier'] = atr_multiplier
    
    return stops


def validate_risk_reward(
    entry_price: float,
    target_price: float,
    stop_loss: float,
    mode: str = 'balanced'
) -> Tuple[float, bool, str]:
    """
    Validate that the risk-reward ratio meets minimum requirements
    
    Returns:
        Tuple of (ratio, is_valid, explanation)
    """
    mode_config = RISK_MODES[mode]
    min_rr = mode_config['min_risk_reward']
    
    reward = abs(target_price - entry_price)
    risk = abs(entry_price - stop_loss)
    
    if risk == 0:
        return 0, False, "Invalid stop loss (same as entry price)"
    
    ratio = reward / risk
    is_valid = ratio >= min_rr
    
    if is_valid:
        explanation = f"Risk/Reward {ratio:.2f}:1 meets minimum requirement of {min_rr}:1"
    else:
        explanation = f"Risk/Reward {ratio:.2f}:1 is BELOW minimum requirement of {min_rr}:1"
    
    return ratio, is_valid, explanation


def calculate_trailing_stops(
    entry_price: float,
    atr: float,
    mode: str = 'balanced'
) -> Dict[str, any]:
    """
    Calculate trailing stop strategy levels
    
    Returns levels and triggers for managing the trade
    """
    mode_config = RISK_MODES[mode]
    atr_multiplier = mode_config['atr_stop_multiplier']
    
    trailing = {
        'entry_price': entry_price,
        
        # Initial stop
        'initial_stop': entry_price - (atr_multiplier * atr),
        'initial_stop_pct': atr_multiplier * (atr / entry_price) * 100,
        
        # Breakeven trigger (move stop to entry when profit reaches 1R)
        'breakeven_trigger': entry_price + (1.0 * atr_multiplier * atr),
        'breakeven_trigger_pct': 1.0 * atr_multiplier * (atr / entry_price) * 100,
        
        # Trail start trigger (start trailing when profit reaches 2R)
        'trail_start_trigger': entry_price + (2.0 * atr_multiplier * atr),
        'trail_start_trigger_pct': 2.0 * atr_multiplier * (atr / entry_price) * 100,
        
        # Trail distance (how far to trail behind price)
        'trail_distance': 1.5 * atr,
        'trail_distance_pct': 1.5 * (atr / entry_price) * 100,
        
        'explanation': f"""
TRAILING STOP STRATEGY ({mode.upper()} MODE)
{'='*50}

1. INITIAL PHASE (Entry to 1R profit)
   Stop Loss: {CURRENCY_SYMBOL}{entry_price - (atr_multiplier * atr):.2f}
   Action: Hold stop at initial level

2. BREAKEVEN PHASE (At 1R profit: {CURRENCY_SYMBOL}{entry_price + (atr_multiplier * atr):.2f})
   Action: Move stop to breakeven ({CURRENCY_SYMBOL}{entry_price:.2f})
   Why: Eliminates risk on the trade

3. TRAILING PHASE (At 2R profit: {CURRENCY_SYMBOL}{entry_price + (2 * atr_multiplier * atr):.2f})
   Action: Start trailing stop {1.5 * atr:.2f} below price
   Why: Lock in profits while letting winner run

4. EXIT
   Exit when price hits trailing stop
   Or when target is reached

BENEFITS:
- Limits losses to initial risk amount
- Protects profits as trade moves in your favor
- Allows winning trades to run
- Removes emotion from exit decisions
"""
    }
    
    return trailing


def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_loss: float,
    mode: str = 'balanced'
) -> Dict[str, any]:
    """
    Professional position sizing based on risk management
    
    The 1% Rule: Never risk more than 1-2% of capital per trade
    
    Formula: Position Size = (Capital × Risk%) / (Entry - Stop)
    
    Args:
        capital: Total capital available
        entry_price: Entry price for the trade
        stop_loss: Stop loss price
        mode: Risk mode ('conservative', 'balanced', 'aggressive')
    
    Returns:
        Dictionary with position sizing details or error information
    """
    # Validate inputs
    if capital is None or not isinstance(capital, (int, float)):
        return {
            'error': True,
            'message': 'Invalid capital: must be a number',
        }
    
    if capital <= 0:
        return {
            'error': True,
            'message': f'Invalid capital: {capital} must be greater than 0',
        }
    
    if entry_price is None or not isinstance(entry_price, (int, float)):
        return {
            'error': True,
            'message': 'Invalid entry price: must be a number',
        }
    
    if entry_price <= 0:
        return {
            'error': True,
            'message': f'Invalid entry price: {entry_price} must be greater than 0',
        }
    
    if stop_loss is None or not isinstance(stop_loss, (int, float)):
        return {
            'error': True,
            'message': 'Invalid stop loss: must be a number',
        }
    
    if stop_loss <= 0:
        return {
            'error': True,
            'message': f'Invalid stop loss: {stop_loss} must be greater than 0',
        }
    
    # Validate mode
    if mode not in RISK_MODES:
        return {
            'error': True,
            'message': f'Invalid mode: {mode}. Must be one of {list(RISK_MODES.keys())}',
        }
    
    mode_config = RISK_MODES[mode]
    risk_pct = mode_config['risk_per_trade']
    
    risk_amount = capital * risk_pct
    stop_distance = abs(entry_price - stop_loss)
    
    # Check for zero stop distance
    if stop_distance == 0:
        return {
            'error': True,
            'message': 'Invalid stop loss: same as entry price (no risk)',
        }
    
    # Check for unreasonably large stop distance (more than 50% of entry)
    stop_distance_pct = (stop_distance / entry_price) * 100
    if stop_distance_pct > 50:
        return {
            'error': True,
            'message': f'Stop distance too large: {stop_distance_pct:.1f}% of entry price',
        }
    
    # Calculate position size
    shares = int(risk_amount / stop_distance)
    position_value = shares * entry_price
    actual_risk = shares * stop_distance
    position_pct = (position_value / capital) * 100
    
    # Ensure we don't exceed capital
    if position_value > capital:
        shares = int(capital / entry_price)
        position_value = shares * entry_price
        actual_risk = shares * stop_distance
        position_pct = (position_value / capital) * 100
    
    result = {
        'error': False,
        'capital': capital,
        'mode': mode,
        'risk_per_trade_pct': risk_pct * 100,
        'risk_amount': risk_amount,
        'entry_price': entry_price,
        'stop_loss': stop_loss,
        'stop_distance': stop_distance,
        'stop_distance_pct': stop_distance_pct,
        'shares_to_buy': shares,
        'position_value': position_value,
        'position_pct': position_pct,
        'actual_risk': actual_risk,
        'actual_risk_pct': (actual_risk / capital) * 100,
        'max_loss_consecutive': int(1 / risk_pct),  # How many consecutive losses before significant damage
    }
    
    result['explanation'] = generate_position_size_explanation(result)
    
    return result


def generate_position_size_explanation(data: Dict) -> str:
    """Generate detailed explanation for position sizing"""
    
    explanation = f"""
POSITION SIZING CALCULATOR
{'='*60}

YOUR CAPITAL:           {CURRENCY_SYMBOL}{data['capital']:,.2f}
RISK MODE:              {data['mode'].upper()}
RISK PER TRADE:         {data['risk_per_trade_pct']:.1f}% = {CURRENCY_SYMBOL}{data['risk_amount']:,.2f}

TRADE PARAMETERS:
  Entry Price:          {CURRENCY_SYMBOL}{data['entry_price']:.2f}
  Stop Loss:            {CURRENCY_SYMBOL}{data['stop_loss']:.2f}
  Stop Distance:        {CURRENCY_SYMBOL}{data['stop_distance']:.2f} ({data['stop_distance_pct']:.2f}%)

CALCULATION:
  Position Size = Risk Amount ÷ Stop Distance
  Position Size = {CURRENCY_SYMBOL}{data['risk_amount']:,.2f} ÷ {CURRENCY_SYMBOL}{data['stop_distance']:.2f}
  Position Size = {data['shares_to_buy']} shares

RECOMMENDATION:
{'─'*60}
  BUY:                  {data['shares_to_buy']} shares
  TOTAL INVESTMENT:     {CURRENCY_SYMBOL}{data['position_value']:,.2f} ({data['position_pct']:.1f}% of capital)
  MAXIMUM LOSS:         {CURRENCY_SYMBOL}{data['actual_risk']:,.2f} ({data['actual_risk_pct']:.2f}% of capital)

WHY THIS MATTERS:
{'─'*60}
  • If this trade hits stop loss, you lose only {data['actual_risk_pct']:.2f}% of capital
  • You can survive {data['max_loss_consecutive']} consecutive losing trades
  • This protects your capital for future opportunities
  • Professional traders NEVER risk more than 1-2% per trade

WARNINGS:
{'─'*60}
  • NEVER increase position size to "make back" losses
  • NEVER move stop loss further away to avoid loss
  • NEVER risk more than the calculated amount
  • ALWAYS use the recommended position size
"""
    
    return explanation


def generate_no_trade_explanation(
    reason: str,
    wait_conditions: list
) -> str:
    """Generate explanation when no trade is recommended"""
    
    conditions_text = '\n'.join([f"  • {cond}" for cond in wait_conditions])
    
    explanation = f"""
POSITION SIZING CALCULATOR
{'='*60}

⛔ NO POSITION RECOMMENDED

REASON:
{'─'*60}
  {reason}

WAIT FOR:
{'─'*60}
{conditions_text}

PATIENCE IS KEY:
{'─'*60}
  • Not every setup deserves your capital
  • Protecting capital is more important than being in a trade
  • Wait for high-probability setups with favorable risk/reward
  • The best traders often sit on their hands waiting
"""
    
    return explanation


def calculate_portfolio_allocation(
    analyses: list,
    capital: float,
    mode: str = 'balanced'
) -> Dict[str, any]:
    """
    Calculate suggested portfolio allocation across multiple stocks
    """
    investable = []
    not_recommended = []
    
    for analysis in analyses:
        if analysis['recommendation_type'] == 'BUY' and analysis['rr_valid']:
            investable.append(analysis)
        else:
            not_recommended.append({
                'symbol': analysis['symbol'],
                'recommendation': analysis['recommendation'],
                'reason': analysis.get('block_reasons', ['Does not meet criteria'])[0] if analysis.get('is_buy_blocked') else 
                          f"R:R {analysis['risk_reward']:.2f}:1 below minimum" if not analysis['rr_valid'] else
                          analysis['recommendation']
            })
    
    if not investable:
        return {
            'investable': [],
            'not_recommended': not_recommended,
            'total_allocated': 0,
            'cash_remaining': capital,
            'explanation': "No stocks meet investment criteria. Hold cash.",
        }
    
    total_confidence = sum(a['confidence'] for a in investable)
    
    allocations = []
    total_allocated = 0
    
    for analysis in investable:
        weight = analysis['confidence'] / total_confidence
        allocation_amount = capital * weight
        
        entry = analysis['current_price']
        shares = int(allocation_amount / entry)
        actual_amount = shares * entry
        
        allocations.append({
            'symbol': analysis['symbol'],
            'confidence': analysis['confidence'],
            'weight_pct': weight * 100,
            'allocated_amount': actual_amount,
            'shares': shares,
            'entry_price': entry,
            'stop_loss': analysis['stop_loss'],
            'target': analysis['target'],
        })
        
        total_allocated += actual_amount
    
    return {
        'investable': allocations,
        'not_recommended': not_recommended,
        'total_allocated': total_allocated,
        'cash_remaining': capital - total_allocated,
        'num_positions': len(allocations),
    }


def estimate_time_to_target(
    current_price: float,
    target_price: float,
    atr: float,
    atr_percent: float,
    momentum: float,
    adx: float,
    horizon: str = '3months'
) -> Dict[str, any]:
    """
    Estimate the time required to reach the target price.
    
    Uses:
    - Historical volatility (ATR)
    - Current momentum
    - Trend strength (ADX)
    - Selected investment horizon
    
    Returns estimated days and dates for target achievement.
    """
    horizon_config = INVESTMENT_HORIZONS.get(horizon, INVESTMENT_HORIZONS['3months'])
    
    # Calculate required move percentage
    required_move = ((target_price - current_price) / current_price) * 100
    
    if required_move <= 0:
        return {
            'days_to_target': 0,
            'estimated_date': datetime.now(),
            'confidence': 0,
            'explanation': 'Target is at or below current price',
        }
    
    # Daily expected move based on ATR
    daily_move_pct = atr_percent  # ATR as % of price
    
    # Adjust for momentum
    momentum_factor = 1.0
    if momentum > 5:
        momentum_factor = 1.5  # Strong upward momentum, faster target
    elif momentum > 2:
        momentum_factor = 1.2
    elif momentum < -2:
        momentum_factor = 0.7  # Against momentum, slower
    elif momentum < -5:
        momentum_factor = 0.5
    
    # Adjust for trend strength
    trend_factor = 1.0
    if adx >= 40:
        trend_factor = 1.4  # Strong trend, more reliable
    elif adx >= 25:
        trend_factor = 1.2
    elif adx < 20:
        trend_factor = 0.8  # Weak trend, less reliable
    
    # Effective daily progress (conservative estimate: stocks don't go straight up)
    # Using 30-40% of ATR as expected daily progress in trending direction
    effective_daily_move = daily_move_pct * 0.35 * momentum_factor * trend_factor
    
    if effective_daily_move <= 0:
        effective_daily_move = daily_move_pct * 0.2  # Minimum progress
    
    # Calculate trading days to target
    trading_days = required_move / effective_daily_move
    trading_days = max(1, int(trading_days))  # At least 1 day
    
    # Cap at horizon maximum
    trading_days = min(trading_days, horizon_config['max_days'])
    
    # Convert to calendar days (5 trading days = 7 calendar days)
    calendar_days = int(trading_days * 7 / 5)
    
    # Calculate confidence in estimate
    estimate_confidence = 50  # Base confidence
    
    if adx >= 30:
        estimate_confidence += 15
    elif adx >= 25:
        estimate_confidence += 10
    
    if momentum > 2:
        estimate_confidence += 10
    elif momentum > 0:
        estimate_confidence += 5
    
    if trading_days <= horizon_config['avg_days']:
        estimate_confidence += 10
    
    estimate_confidence = min(85, estimate_confidence)  # Cap at 85%
    
    # Calculate dates
    today = datetime.now()
    target_date = today + timedelta(days=calendar_days)
    
    # Provide date ranges
    early_date = today + timedelta(days=int(calendar_days * 0.7))
    late_date = today + timedelta(days=int(calendar_days * 1.4))
    
    return {
        'trading_days': trading_days,
        'calendar_days': calendar_days,
        'estimated_date': target_date,
        'earliest_date': early_date,
        'latest_date': late_date,
        'confidence': estimate_confidence,
        'required_move_pct': required_move,
        'daily_move_pct': effective_daily_move,
        'within_horizon': trading_days <= horizon_config['max_days'],
        'explanation': generate_time_estimate_explanation(
            trading_days, target_date, early_date, late_date,
            estimate_confidence, required_move, horizon_config
        ),
    }


def generate_time_estimate_explanation(
    trading_days: int,
    target_date: datetime,
    early_date: datetime,
    late_date: datetime,
    confidence: int,
    required_move: float,
    horizon_config: dict
) -> str:
    """Generate beginner-friendly explanation of time estimate"""
    
    if trading_days <= 7:
        time_desc = "within 1-2 weeks"
    elif trading_days <= 14:
        time_desc = "within 2-3 weeks"
    elif trading_days <= 30:
        time_desc = "within 1-1.5 months"
    elif trading_days <= 60:
        time_desc = "within 2-3 months"
    elif trading_days <= 120:
        time_desc = "within 4-6 months"
    else:
        time_desc = "within 6-12 months"
    
    return f"""
Expected to reach target {time_desc}

📅 WHEN TO EXPECT RESULTS:
   Best Case:    {early_date.strftime('%d %b %Y')} (if market is favorable)
   Expected:     {target_date.strftime('%d %b %Y')} (most likely)
   Worst Case:   {late_date.strftime('%d %b %Y')} (if market is slow)

📊 WHAT THIS MEANS:
   • Stock needs to move +{required_move:.1f}% to hit target
   • Based on current trend and momentum
   • Estimate confidence: {confidence}%
   
💡 TIP: Set a calendar reminder for {target_date.strftime('%d %b %Y')} to review your investment.
"""


def calculate_investment_summary(
    current_price: float,
    target_price: float,
    stop_loss: float,
    investment_amount: float,
    horizon: str = '3months'
) -> Dict[str, any]:
    """
    Calculate a complete beginner-friendly investment summary.
    
    Shows potential profit, potential loss, and ROI in simple terms.
    """
    horizon_config = INVESTMENT_HORIZONS.get(horizon, INVESTMENT_HORIZONS['3months'])
    
    # Calculate shares
    shares = int(investment_amount / current_price)
    actual_investment = shares * current_price
    
    # Potential profit
    if target_price > current_price:
        profit_per_share = target_price - current_price
        total_profit = shares * profit_per_share
        profit_pct = ((target_price - current_price) / current_price) * 100
    else:
        total_profit = 0
        profit_pct = 0
    
    # Potential loss
    if stop_loss < current_price:
        loss_per_share = current_price - stop_loss
        total_loss = shares * loss_per_share
        loss_pct = ((current_price - stop_loss) / current_price) * 100
    else:
        total_loss = 0
        loss_pct = 0
    
    # ROI calculation (annualized)
    holding_days = horizon_config['avg_days']
    if holding_days > 0 and profit_pct > 0:
        annualized_roi = (profit_pct / holding_days) * TRADING_DAYS_PER_YEAR
    else:
        annualized_roi = 0
    
    return {
        'investment_amount': actual_investment,
        'shares': shares,
        'current_price': current_price,
        'target_price': target_price,
        'stop_loss': stop_loss,
        'potential_profit': total_profit,
        'potential_profit_pct': profit_pct,
        'potential_loss': total_loss,
        'potential_loss_pct': loss_pct,
        'roi_expected': profit_pct,
        'roi_annualized': annualized_roi,
        'holding_period': horizon_config['display_name'],
        'risk_level': horizon_config['risk_level'],
    }


def calculate_safety_score(
    confidence: float,
    risk_reward: float,
    adx: float,
    rsi: float,
    is_blocked: bool,
    horizon: str = '3months'
) -> Dict[str, any]:
    """
    Calculate an overall safety score for beginners.
    
    Returns a 1-5 star rating with explanation.
    """
    horizon_config = INVESTMENT_HORIZONS.get(horizon, INVESTMENT_HORIZONS['3months'])
    
    # Start with base score
    score = 50
    
    # Confidence contribution (0-25 points)
    if confidence >= 80:
        score += 25
    elif confidence >= 70:
        score += 20
    elif confidence >= 60:
        score += 15
    elif confidence >= 50:
        score += 10
    else:
        score += 0
    
    # Risk/Reward contribution (0-20 points)
    if risk_reward >= 3:
        score += 20
    elif risk_reward >= 2.5:
        score += 15
    elif risk_reward >= 2:
        score += 10
    elif risk_reward >= 1.5:
        score += 5
    else:
        score += 0
    
    # Trend strength contribution (0-15 points)
    if adx >= 30:
        score += 15
    elif adx >= 25:
        score += 10
    elif adx >= 20:
        score += 5
    
    # RSI contribution (penalty for extremes)
    if 40 <= rsi <= 60:
        score += 10  # Neutral is good
    elif 30 <= rsi <= 70:
        score += 5
    else:
        score -= 10  # Extreme RSI is risky
    
    # Blocked trade penalty
    if is_blocked:
        score -= 30
    
    # Horizon contribution
    if horizon_config['risk_level'] in ['LOW', 'VERY LOW']:
        score += 10
    elif horizon_config['risk_level'] == 'MEDIUM':
        score += 5
    elif horizon_config['risk_level'] in ['HIGH', 'MEDIUM-HIGH']:
        score -= 5
    
    # Clamp score
    score = max(0, min(100, score))
    
    # Convert to stars
    if score >= 80:
        stars = 5
        rating = 'VERY SAFE'
        emoji = '⭐⭐⭐⭐⭐'
        advice = 'This looks like a safe investment opportunity.'
    elif score >= 65:
        stars = 4
        rating = 'SAFE'
        emoji = '⭐⭐⭐⭐'
        advice = 'Good investment opportunity with manageable risk.'
    elif score >= 50:
        stars = 3
        rating = 'MODERATE'
        emoji = '⭐⭐⭐'
        advice = 'Average risk. Invest only what you can afford to lose.'
    elif score >= 35:
        stars = 2
        rating = 'RISKY'
        emoji = '⭐⭐'
        advice = 'High risk. Consider waiting for a better opportunity.'
    else:
        stars = 1
        rating = 'VERY RISKY'
        emoji = '⭐'
        advice = 'Very high risk. Not recommended for beginners.'
    
    return {
        'score': score,
        'stars': stars,
        'rating': rating,
        'emoji': emoji,
        'advice': advice,
    }
