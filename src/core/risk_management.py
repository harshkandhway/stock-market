"""
Risk Management Module for Stock Analyzer Pro
Handles position sizing, stop losses, targets, and trailing stops

Author: Harsh Kandhway
"""

from typing import Dict, Tuple, Optional
from .config import RISK_MODES, FIBONACCI_EXTENSION, CURRENCY_SYMBOL


def calculate_targets(
    current_price: float,
    atr: float,
    resistance: float,
    support: float,
    fib_extensions: Dict[str, float],
    mode: str = 'balanced',
    direction: str = 'long'
) -> Dict[str, any]:
    """
    Calculate price targets using multiple professional methods
    
    Methods:
    1. ATR-based (volatility)
    2. Support/Resistance based
    3. Fibonacci extension based
    
    Returns the most conservative target for safety
    """
    mode_config = RISK_MODES[mode]
    atr_multiplier = mode_config['atr_target_multiplier']
    
    targets = {}
    
    if direction == 'long':
        # ATR-based target
        targets['atr_target'] = current_price + (atr_multiplier * atr)
        targets['atr_target_pct'] = ((targets['atr_target'] - current_price) / current_price) * 100
        
        # Resistance-based target
        targets['resistance_target'] = resistance
        targets['resistance_target_pct'] = ((resistance - current_price) / current_price) * 100
        
        # Fibonacci extension targets
        fib_127 = fib_extensions.get('fib_ext_127', current_price * 1.05)
        fib_161 = fib_extensions.get('fib_ext_161', current_price * 1.08)
        targets['fib_target_1'] = fib_127
        targets['fib_target_1_pct'] = ((fib_127 - current_price) / current_price) * 100
        targets['fib_target_2'] = fib_161
        targets['fib_target_2_pct'] = ((fib_161 - current_price) / current_price) * 100
        
        # Conservative target (lowest of reasonable targets)
        reasonable_targets = [
            targets['atr_target'],
            targets['resistance_target'],
            targets['fib_target_1']
        ]
        targets['conservative_target'] = min(t for t in reasonable_targets if t > current_price)
        targets['conservative_target_pct'] = ((targets['conservative_target'] - current_price) / current_price) * 100
        
        # Aggressive target
        targets['aggressive_target'] = targets['fib_target_2']
        targets['aggressive_target_pct'] = targets['fib_target_2_pct']
        
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
    
    # Recommended target based on mode
    if mode == 'conservative':
        targets['recommended_target'] = targets['conservative_target']
        targets['recommended_target_pct'] = targets['conservative_target_pct']
    elif mode == 'aggressive':
        targets['recommended_target'] = targets.get('aggressive_target', targets['atr_target'])
        targets['recommended_target_pct'] = targets.get('aggressive_target_pct', targets['atr_target_pct'])
    else:  # balanced
        targets['recommended_target'] = targets['atr_target']
        targets['recommended_target_pct'] = targets['atr_target_pct']
    
    targets['direction'] = direction
    
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
    
    Allocation is weighted by:
    1. Confidence score
    2. Risk/Reward validity
    3. Recommendation type (only BUY recommendations get allocated)
    """
    # Filter for investable stocks (BUY recommendations with valid R:R)
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
    
    # Calculate weights based on confidence
    total_confidence = sum(a['confidence'] for a in investable)
    
    allocations = []
    total_allocated = 0
    
    for analysis in investable:
        weight = analysis['confidence'] / total_confidence
        allocation_amount = capital * weight
        
        # Calculate shares
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
