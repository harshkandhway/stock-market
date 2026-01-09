"""
Output Module for Stock Analyzer Pro
Beginner-Friendly Report Formatting

Author: Harsh Kandhway
"""

import sys
import io
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .config import (
    CURRENCY_SYMBOL, REPORT_WIDTH, SIGNAL_WEIGHTS,
    INVESTMENT_HORIZONS, ACTION_RECOMMENDATIONS, SIMPLE_EXPLANATIONS,
    MARKET_HEALTH_SCORES, get_expected_dates
)

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# ASCII-safe alternatives for special characters
BOX_DOUBLE = "="
BOX_SINGLE = "-"
BULLET = "*"
ARROW = "->"
CHECK = "[Y]"
CROSS = "[X]"
WARNING = "[!]"


def get_market_health_indicator(confidence: float) -> dict:
    """Get market health indicator based on confidence"""
    for rating, config in MARKET_HEALTH_SCORES.items():
        if config['min'] <= confidence <= config['max']:
            return {
                'rating': rating,
                'emoji': config['emoji'],
                'advice': config['advice'],
            }
    return {'rating': 'UNKNOWN', 'emoji': '⚪', 'advice': 'Unable to determine'}


def format_price(price: float) -> str:
    """Format price with currency symbol"""
    return f"{CURRENCY_SYMBOL}{price:,.2f}"


def format_percentage(pct: float, include_sign: bool = True) -> str:
    """Format percentage"""
    if include_sign:
        return f"{pct:+.1f}%"
    return f"{pct:.1f}%"


def print_beginner_header(symbol: str, horizon: str, analysis_date: datetime = None):
    """Print a clean, beginner-friendly header"""
    if analysis_date is None:
        analysis_date = datetime.now()
    
    horizon_config = INVESTMENT_HORIZONS.get(horizon, INVESTMENT_HORIZONS['3months'])
    
    print(f"\n{BOX_DOUBLE * REPORT_WIDTH}")
    print(f"  {horizon_config['emoji']} INVESTMENT ANALYSIS REPORT")
    print(f"  Stock: {symbol}")
    print(f"  Date: {analysis_date.strftime('%A, %d %B %Y')}")
    print(f"  Investment Period: {horizon_config['display_name']} ({horizon_config['name']})")
    print(f"{BOX_DOUBLE * REPORT_WIDTH}")


def print_quick_summary(analysis: Dict, horizon: str = '3months'):
    """Print the most important information first - for quick decision making"""
    horizon_config = INVESTMENT_HORIZONS.get(horizon, INVESTMENT_HORIZONS['3months'])
    rec_type = analysis['recommendation_type']
    rec_config = ACTION_RECOMMENDATIONS.get(analysis['recommendation'], ACTION_RECOMMENDATIONS.get('HOLD'))
    
    health = get_market_health_indicator(analysis['confidence'])
    safety = analysis.get('safety_score', {})
    
    print(f"\n  {BOX_SINGLE * 40}")
    print(f"  QUICK SUMMARY - What Should You Do?")
    print(f"  {BOX_SINGLE * 40}")
    
    # Main recommendation with emoji
    if rec_config:
        print(f"\n  {rec_config['emoji']} {rec_config['title']}")
        print(f"  {rec_config['simple']}")
        print(f"\n  {ARROW} Action: {rec_config['action']}")
        print(f"  {ARROW} Timing: {rec_config['timing']}")
    
    # Safety rating
    if safety:
        print(f"\n  Safety Rating: {safety.get('emoji', '')} ({safety.get('rating', 'N/A')})")
        print(f"  {safety.get('advice', '')}")
    
    # Current price
    print(f"\n  Current Price: {format_price(analysis['current_price'])}")


def print_investment_plan(analysis: Dict, horizon: str = '3months'):
    """Print the investment plan with clear buy/sell guidance"""
    horizon_config = INVESTMENT_HORIZONS.get(horizon, INVESTMENT_HORIZONS['3months'])
    dates = get_expected_dates(horizon)
    
    target = analysis.get('target', 0)
    stop_loss = analysis.get('stop_loss', 0)
    current = analysis['current_price']
    
    target_pct = ((target - current) / current * 100) if target > current else 0
    stop_pct = ((current - stop_loss) / current * 100) if stop_loss < current else 0
    
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  YOUR INVESTMENT PLAN")
    print(f"  {BOX_DOUBLE * 40}")
    
    # When to Buy
    print(f"\n  WHEN TO BUY:")
    if analysis['recommendation_type'] == 'BUY':
        print(f"     {CHECK} Now is a good time to buy")
        print(f"     Buy between: {dates['buy_date'].strftime('%d %b')} - {(dates['buy_date'] + timedelta(days=7)).strftime('%d %b %Y')}")
    elif analysis['recommendation_type'] == 'HOLD':
        print(f"     [WAIT] Wait for a better entry point")
        print(f"     Look for price to drop to {format_price(analysis['indicators'].get('support', current * 0.95))}")
    else:
        print(f"     {CROSS} Not recommended to buy now")
        print(f"     Wait until the trend improves")
    
    # Target Price
    print(f"\n  TARGET PRICE (When to Sell for Profit):")
    print(f"     Target: {format_price(target)} ({format_percentage(target_pct)})")
    if analysis.get('target_data', {}).get('conservative_target'):
        conservative = analysis['target_data']['conservative_target']
        cons_pct = ((conservative - current) / current * 100)
        print(f"     Safe Target: {format_price(conservative)} ({format_percentage(cons_pct)})")
    
    # Expected Timeline
    time_estimate = analysis.get('time_estimate', {})
    if time_estimate:
        print(f"\n  EXPECTED TIMELINE:")
        print(f"     Earliest: {time_estimate.get('earliest_date', dates['min_sell_date']).strftime('%d %b %Y')}")
        print(f"     Expected: {time_estimate.get('estimated_date', dates['expected_sell_date']).strftime('%d %b %Y')}")
        print(f"     Latest:   {time_estimate.get('latest_date', dates['max_sell_date']).strftime('%d %b %Y')}")
    else:
        print(f"\n  EXPECTED TIMELINE:")
        print(f"     Hold for approximately {horizon_config['avg_days']} trading days")
        print(f"     Expected sell date: Around {dates['expected_sell_date'].strftime('%d %b %Y')}")
    
    # Stop Loss
    print(f"\n  STOP LOSS (Exit to Limit Loss):")
    print(f"     If price falls to {format_price(stop_loss)}, SELL immediately")
    print(f"     Maximum loss: -{stop_pct:.1f}% of your investment")
    print(f"     This protects you from larger losses")
    
    # Holding Period
    print(f"\n  RECOMMENDED HOLDING PERIOD:")
    print(f"     {horizon_config['display_name']} ({horizon_config['min_days']}-{horizon_config['max_days']} trading days)")
    print(f"     Risk Level: {horizon_config['risk_level']}")
    print(f"     {horizon_config['suitable_for']}")


def print_profit_loss_calculator(analysis: Dict, capital: Optional[float] = None):
    """Print potential profit/loss in simple terms"""
    if capital is None:
        capital = 10000  # Default example capital
    
    current = analysis['current_price']
    target = analysis.get('target', current * 1.05)
    stop_loss = analysis.get('stop_loss', current * 0.95)
    
    shares = int(capital / current)
    investment = shares * current
    
    # Profit scenario
    profit = shares * (target - current)
    profit_pct = ((target - current) / current) * 100
    
    # Loss scenario
    loss = shares * (current - stop_loss)
    loss_pct = ((current - stop_loss) / current) * 100
    
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  PROFIT/LOSS CALCULATOR")
    print(f"  {BOX_DOUBLE * 40}")
    print(f"  (Example with {format_price(capital)} investment)")
    
    print(f"\n  Investment Details:")
    print(f"     Amount: {format_price(investment)}")
    print(f"     Shares: {shares} units @ {format_price(current)}")
    
    print(f"\n  {CHECK} If Stock Reaches Target ({format_price(target)}):")
    print(f"     Your Profit: {format_price(profit)}")
    print(f"     Return: +{profit_pct:.1f}%")
    print(f"     Total Value: {format_price(investment + profit)}")
    
    print(f"\n  {CROSS} If Stock Hits Stop Loss ({format_price(stop_loss)}):")
    print(f"     Your Loss: {format_price(loss)}")
    print(f"     Loss: -{loss_pct:.1f}%")
    print(f"     Remaining Value: {format_price(investment - loss)}")
    
    # Risk/Reward
    rr = analysis.get('risk_reward', 0)
    print(f"\n  Risk vs Reward:")
    print(f"     For every Rs.1 you risk, you could gain Rs.{rr:.2f}")
    if rr >= 2:
        print(f"     {CHECK} Good risk/reward ratio!")
    elif rr >= 1.5:
        print(f"     {WARNING} Acceptable, but not ideal")
    else:
        print(f"     {CROSS} Poor risk/reward - consider waiting")


def print_market_conditions(analysis: Dict):
    """Print current market conditions in simple terms"""
    indicators = analysis['indicators']
    
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  CURRENT MARKET CONDITIONS")
    print(f"  {BOX_DOUBLE * 40}")
    
    # Market Trend
    phase = indicators['market_phase'].replace('_', ' ').title()
    if 'uptrend' in indicators['market_phase']:
        trend_emoji = '[UP]'
    elif 'downtrend' in indicators['market_phase']:
        trend_emoji = '[DOWN]'
    else:
        trend_emoji = '[SIDEWAYS]'
    print(f"\n  {trend_emoji} Market Trend: {phase}")
    
    if 'strong_uptrend' in indicators['market_phase']:
        print(f"     Stock is moving UP strongly - Good for buying!")
    elif 'uptrend' in indicators['market_phase']:
        print(f"     Stock is moving UP - Favorable for buying")
    elif 'weak_uptrend' in indicators['market_phase']:
        print(f"     Stock is slightly UP - Okay to buy with caution")
    elif 'consolidation' in indicators['market_phase']:
        print(f"     Stock is moving SIDEWAYS - Wait for clear direction")
    elif 'weak_downtrend' in indicators['market_phase']:
        print(f"     Stock is slightly DOWN - Not ideal for buying")
    elif 'downtrend' in indicators['market_phase']:
        print(f"     Stock is moving DOWN - Avoid buying now")
    else:
        print(f"     Stock is moving DOWN strongly - Do not buy!")
    
    # Trend Strength
    adx = indicators['adx']
    strength = indicators['adx_strength'].replace('_', ' ').title()
    if adx >= 30:
        strength_desc = "Strong and reliable trend"
        strength_emoji = '[STRONG]'
    elif adx >= 25:
        strength_desc = "Moderate trend, reasonably reliable"
        strength_emoji = '[MODERATE]'
    elif adx >= 20:
        strength_desc = "Weak trend, less reliable"
        strength_emoji = '[WEAK]'
    else:
        strength_desc = "No clear trend, unpredictable"
        strength_emoji = '[UNCLEAR]'
    
    print(f"\n  {strength_emoji} Trend Strength: {strength}")
    print(f"     {strength_desc}")
    
    # Momentum
    rsi = indicators['rsi']
    rsi_zone = indicators['rsi_zone']
    
    if rsi >= 70:
        momentum_desc = "Stock is OVERBOUGHT - might fall soon"
        momentum_emoji = '[HIGH]'
    elif rsi <= 30:
        momentum_desc = "Stock is OVERSOLD - might rise soon"
        momentum_emoji = '[LOW]'
    else:
        momentum_desc = "Stock momentum is NORMAL"
        momentum_emoji = '[NORMAL]'
    
    print(f"\n  {momentum_emoji} Buying/Selling Pressure:")
    print(f"     {momentum_desc}")
    
    # Volume
    vol_ratio = indicators['volume_ratio']
    if vol_ratio >= 1.5:
        vol_desc = "HIGH trading activity - many traders interested"
        vol_emoji = '[HIGH]'
    elif vol_ratio >= 0.7:
        vol_desc = "NORMAL trading activity"
        vol_emoji = '[NORMAL]'
    else:
        vol_desc = "LOW trading activity - fewer traders interested"
        vol_emoji = '[LOW]'
    
    print(f"\n  {vol_emoji} Trading Activity: {vol_ratio:.1f}x average")
    print(f"     {vol_desc}")


def print_chart_patterns(analysis: Dict):
    """Print detected chart patterns in beginner-friendly format"""
    indicators = analysis.get('indicators', {})
    
    candlestick_patterns = indicators.get('candlestick_patterns', [])
    chart_patterns = indicators.get('chart_patterns', [])
    strongest = indicators.get('strongest_pattern')
    pattern_bias = indicators.get('pattern_bias', 'neutral')
    
    # Skip if no patterns detected
    if not candlestick_patterns and not chart_patterns:
        return
    
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  CHART PATTERN ANALYSIS")
    print(f"  {BOX_DOUBLE * 40}")
    
    # Overall pattern bias
    if pattern_bias == 'bullish':
        bias_emoji = '[BULLISH]'
        bias_desc = "Patterns suggest UPWARD movement"
    elif pattern_bias == 'bearish':
        bias_emoji = '[BEARISH]'
        bias_desc = "Patterns suggest DOWNWARD movement"
    else:
        bias_emoji = '[NEUTRAL]'
        bias_desc = "No clear pattern direction"
    
    print(f"\n  {bias_emoji} Overall: {bias_desc}")
    
    # Strongest pattern highlight
    if strongest:
        print(f"\n  [KEY SIGNAL] {strongest.name}")
        print(f"     Confidence: {strongest.confidence}%")
        print(f"     {strongest.description}")
        print(f"     Action: {strongest.action}")
    
    # Candlestick patterns
    if candlestick_patterns:
        print(f"\n  Recent Candlestick Patterns:")
        for p in candlestick_patterns[:3]:  # Show top 3
            if p.type.value == 'bullish':
                emoji = '[+]'
            elif p.type.value == 'bearish':
                emoji = '[-]'
            else:
                emoji = '[?]'
            
            print(f"   {emoji} {p.name} ({p.confidence}% confidence)")
            print(f"      {p.description}")
    
    # Chart patterns
    if chart_patterns:
        print(f"\n  Chart Formation Patterns:")
        for p in chart_patterns[:2]:  # Show top 2
            if p.type.value == 'bullish':
                emoji = '[+]'
            elif p.type.value == 'bearish':
                emoji = '[-]'
            else:
                emoji = '[?]'
            
            print(f"   {emoji} {p.name} ({p.confidence}% confidence)")
            print(f"      {p.description}")
            print(f"      Suggested Action: {p.action}")
    
    # Pattern explanation for beginners
    print(f"\n  {BOX_SINGLE * 40}")
    print(f"  [INFO] What are these patterns?")
    print(f"  Patterns are shapes formed by price movements")
    print(f"  that help predict future price direction.")
    print(f"  Higher confidence = more reliable signal.")


def print_important_price_levels(analysis: Dict):
    """Print key price levels in simple terms"""
    indicators = analysis['indicators']
    current = analysis['current_price']
    
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  IMPORTANT PRICE LEVELS")
    print(f"  {BOX_DOUBLE * 40}")
    
    # Current Price
    print(f"\n  Current Price: {format_price(current)}")
    
    # Resistance (Ceiling)
    resistance = indicators['resistance']
    res_pct = ((resistance - current) / current) * 100
    print(f"\n  [UP] Resistance (Price Ceiling): {format_price(resistance)} ({format_percentage(res_pct)})")
    print(f"     Stock may struggle to go above this level")
    
    # Support (Floor)
    support = indicators['support']
    sup_pct = ((support - current) / current) * 100
    print(f"\n  [DOWN] Support (Price Floor): {format_price(support)} ({format_percentage(sup_pct)})")
    print(f"     Stock usually bounces back from this level")
    
    # 52-week range
    high_52 = indicators['high_52w']
    low_52 = indicators['low_52w']
    print(f"\n  52-Week Range:")
    print(f"     Highest: {format_price(high_52)}")
    print(f"     Lowest:  {format_price(low_52)}")
    
    # Where is current price in the range
    range_pct = ((current - low_52) / (high_52 - low_52)) * 100 if high_52 != low_52 else 50
    print(f"     Current position: {range_pct:.0f}% of range")
    
    if range_pct >= 80:
        print(f"     {WARNING} Near yearly high - expensive, limited upside")
    elif range_pct <= 20:
        print(f"     {CHECK} Near yearly low - potentially good value")
    else:
        print(f"     {BULLET} In middle range - fair price")


def print_simple_checklist(analysis: Dict):
    """Print a simple checklist for beginners"""
    indicators = analysis['indicators']
    
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  INVESTMENT CHECKLIST")
    print(f"  {BOX_DOUBLE * 40}")
    
    checks = []
    
    # Trend check
    if indicators['price_vs_trend_ema'] == 'above':
        checks.append(("Price above long-term average", True, "Stock is in uptrend"))
    else:
        checks.append(("Price above long-term average", False, "Stock is in downtrend"))
    
    # RSI check
    if 30 <= indicators['rsi'] <= 70:
        checks.append(("Not overbought or oversold", True, "Healthy momentum"))
    elif indicators['rsi'] > 70:
        checks.append(("Not overbought or oversold", False, "Stock may be too expensive"))
    else:
        checks.append(("Not overbought or oversold", False, "Stock may be too cheap (risky)"))
    
    # Trend strength check
    if indicators['adx'] >= 25:
        checks.append(("Clear trend direction", True, "Reliable movement"))
    else:
        checks.append(("Clear trend direction", False, "Unclear direction"))
    
    # Volume check
    if indicators['volume_ratio'] >= 0.7:
        checks.append(("Adequate trading volume", True, "Enough market interest"))
    else:
        checks.append(("Adequate trading volume", False, "Low interest, harder to sell"))
    
    # Risk/Reward check
    rr = analysis.get('risk_reward', 0)
    if rr >= 2:
        checks.append(("Good risk/reward ratio", True, "Potential gain > potential loss"))
    else:
        checks.append(("Good risk/reward ratio", False, "Risk may exceed reward"))
    
    # Print checklist
    passed = 0
    for check_name, passed_check, explanation in checks:
        emoji = CHECK if passed_check else CROSS
        print(f"\n  {emoji} {check_name}")
        print(f"     {explanation}")
        if passed_check:
            passed += 1
    
    # Summary
    print(f"\n  {BOX_SINGLE * 40}")
    print(f"  Passed {passed}/{len(checks)} checks")
    
    if passed >= 4:
        print(f"  {CHECK} Good investment opportunity!")
    elif passed >= 3:
        print(f"  {BULLET} Moderate opportunity - proceed with caution")
    else:
        print(f"  {CROSS} Not recommended at this time")


def print_when_to_sell(analysis: Dict, horizon: str = '3months'):
    """Print clear guidance on when to sell"""
    target = analysis.get('target', 0)
    stop_loss = analysis.get('stop_loss', 0)
    current = analysis['current_price']
    
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  WHEN TO SELL - SET THESE ALERTS!")
    print(f"  {BOX_DOUBLE * 40}")
    
    print(f"\n  Set Price Alerts for These Levels:")
    
    # Take Profit
    print(f"\n  1. TAKE PROFIT ALERT: {format_price(target)}")
    print(f"      When price reaches this {ARROW} SELL for profit")
    print(f"      Expected profit: {format_percentage(((target - current) / current) * 100)}")
    
    # Partial Profit
    partial_target = current + (target - current) * 0.5
    print(f"\n  2. PARTIAL PROFIT ALERT: {format_price(partial_target)}")
    print(f"      Consider selling half your shares here")
    print(f"      This locks in some profit safely")
    
    # Stop Loss
    loss_pct = ((current - stop_loss) / current) * 100
    print(f"\n  3. STOP LOSS ALERT: {format_price(stop_loss)}")
    print(f"      When price falls to this {ARROW} SELL to limit loss")
    print(f"      Maximum loss: -{loss_pct:.1f}%")
    print(f"      {WARNING} DO NOT IGNORE THIS - protects your capital!")
    
    print(f"\n  IMPORTANT:")
    print(f"     {BULLET} Set these alerts in your trading app")
    print(f"     {BULLET} Don't change stop loss to avoid loss - discipline is key!")
    print(f"     {BULLET} Review your position every week")


def print_beginner_tips(analysis: Dict):
    """Print helpful tips for beginners"""
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  TIPS FOR BEGINNERS")
    print(f"  {BOX_DOUBLE * 40}")
    
    tips = [
        "Never invest money you can't afford to lose",
        "Start with small amounts to learn the market",
        "Always set a stop loss to protect your capital",
        "Don't check prices every hour - it causes stress",
        "Diversify - don't put all money in one stock",
        "Patience is key - don't panic sell on small dips",
        "Markets go up and down - temporary drops are normal",
    ]
    
    for i, tip in enumerate(tips, 1):
        print(f"\n  {i}. {tip}")


def print_decision_breakdown(analysis: Dict):
    """Print comprehensive decision breakdown showing WHY the recommendation was made"""
    indicators = analysis['indicators']
    rec_type = analysis['recommendation_type']
    confidence = analysis['confidence']
    risk_reward = analysis['risk_reward']
    rr_valid = analysis['rr_valid']
    
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  WHY THIS RECOMMENDATION?")
    print(f"  {BOX_DOUBLE * 40}")
    
    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================
    trend_score = 0
    print(f"\n  [TREND ANALYSIS]")
    print(f"  {BOX_SINGLE * 40}")
    
    # Price vs EMA
    if indicators['price_vs_trend_ema'] == 'above':
        trend_score += 1
        print(f"  {CHECK} Price ABOVE long-term average")
        print(f"       -> Bullish signal")
    else:
        print(f"  {CROSS} Price BELOW long-term average")
        print(f"       -> Bearish signal")
    
    # Market Phase
    phase = indicators['market_phase']
    if 'uptrend' in phase:
        trend_score += 1
        print(f"  {CHECK} Market Phase: {phase.replace('_', ' ').title()}")
        print(f"       -> Stock is moving UP")
    elif 'downtrend' in phase:
        print(f"  {CROSS} Market Phase: {phase.replace('_', ' ').title()}")
        print(f"       -> Stock is moving DOWN")
    else:
        print(f"  [?] Market Phase: {phase.replace('_', ' ').title()}")
        print(f"       -> No clear direction")
    
    # EMA Alignment
    ema_alignment = indicators.get('ema_alignment', 'mixed')
    if ema_alignment in ['strong_bullish', 'bullish']:
        trend_score += 1
        print(f"  {CHECK} Moving Averages: All aligned UP")
        print(f"       -> Strong bullish structure")
    elif ema_alignment in ['strong_bearish', 'bearish']:
        print(f"  {CROSS} Moving Averages: All aligned DOWN")
        print(f"       -> Bearish structure")
    else:
        print(f"  [?] Moving Averages: Mixed/Unclear")
        print(f"       -> No clear trend")
    
    print(f"\n  Trend Score: {trend_score}/3 bullish")
    
    # =========================================================================
    # MOMENTUM ANALYSIS
    # =========================================================================
    momentum_score = 0
    print(f"\n  [MOMENTUM ANALYSIS]")
    print(f"  {BOX_SINGLE * 40}")
    
    # RSI
    rsi = indicators['rsi']
    rsi_zone = indicators['rsi_zone']
    if rsi_zone in ['oversold', 'extremely_oversold']:
        momentum_score += 1
        print(f"  {CHECK} RSI: {rsi:.1f} (Oversold)")
        print(f"       -> Price may bounce UP soon")
    elif rsi_zone in ['overbought', 'extremely_overbought']:
        print(f"  {CROSS} RSI: {rsi:.1f} (Overbought)")
        print(f"       -> Price may fall soon")
    else:
        print(f"  [?] RSI: {rsi:.1f} (Neutral)")
        print(f"       -> No extreme condition")
    
    # MACD
    macd_hist = indicators.get('macd_hist', 0)
    if macd_hist > 0:
        momentum_score += 1
        print(f"  {CHECK} MACD: Positive ({macd_hist:.4f})")
        print(f"       -> Upward momentum")
    else:
        print(f"  {CROSS} MACD: Negative ({macd_hist:.4f})")
        print(f"       -> Downward momentum")
    
    # ADX
    adx = indicators['adx']
    if adx >= 25:
        momentum_score += 1
        print(f"  {CHECK} ADX: {adx:.1f} (Strong Trend)")
        print(f"       -> Trend is reliable")
    else:
        print(f"  {WARNING} ADX: {adx:.1f} (Weak Trend)")
        print(f"       -> Trend may reverse easily")
    
    print(f"\n  Momentum Score: {momentum_score}/3 bullish")
    
    # =========================================================================
    # CHART PATTERN ANALYSIS
    # =========================================================================
    pattern_score = 0
    strongest_pattern = indicators.get('strongest_pattern')
    pattern_bias = indicators.get('pattern_bias', 'neutral')
    
    print(f"\n  [CHART PATTERN ANALYSIS]")
    print(f"  {BOX_SINGLE * 40}")
    
    if strongest_pattern:
        pattern_type = strongest_pattern.type.value
        if pattern_type == 'bullish':
            pattern_score += 2
            print(f"  {CHECK} Key Pattern: {strongest_pattern.name}")
            print(f"       Confidence: {strongest_pattern.confidence}%")
            print(f"       -> {strongest_pattern.action}")
        elif pattern_type == 'bearish':
            print(f"  {CROSS} Key Pattern: {strongest_pattern.name}")
            print(f"       Confidence: {strongest_pattern.confidence}%")
            print(f"       -> {strongest_pattern.action}")
        else:
            print(f"  [?] Key Pattern: {strongest_pattern.name}")
            print(f"       -> Neutral, wait for confirmation")
        
        # Check for conflict
        if pattern_type == 'bullish' and rec_type in ['SELL', 'BLOCKED']:
            print(f"\n  {WARNING} CONFLICT DETECTED:")
            print(f"       Pattern says BUY but other factors say AVOID")
            print(f"       -> Wait for trend to confirm the pattern")
    else:
        print(f"  [?] No significant patterns detected")
    
    if pattern_bias == 'bullish':
        pattern_score += 1
        print(f"\n  Overall Pattern Bias: BULLISH")
    elif pattern_bias == 'bearish':
        print(f"\n  Overall Pattern Bias: BEARISH")
    else:
        print(f"\n  Overall Pattern Bias: NEUTRAL")
    
    print(f"\n  Pattern Score: {pattern_score}/3 bullish")
    
    # =========================================================================
    # RISK ANALYSIS
    # =========================================================================
    risk_score = 0
    print(f"\n  [RISK ANALYSIS]")
    print(f"  {BOX_SINGLE * 40}")
    
    if rr_valid:
        risk_score += 1
        print(f"  {CHECK} Risk/Reward: {risk_reward:.2f}:1")
        print(f"       -> Good ratio (minimum is 2:1)")
    else:
        print(f"  {CROSS} Risk/Reward: {risk_reward:.2f}:1")
        print(f"       -> Below minimum 2:1 ratio")
    
    # Volume
    vol_ratio = indicators.get('volume_ratio', 1.0)
    if vol_ratio >= 1.0:
        risk_score += 1
        print(f"  {CHECK} Volume: {vol_ratio:.1f}x average")
        print(f"       -> Good trading activity")
    else:
        print(f"  {WARNING} Volume: {vol_ratio:.1f}x average")
        print(f"       -> Low trading activity")
    
    # Check for blocks
    if analysis.get('is_buy_blocked'):
        print(f"\n  {WARNING} HARD FILTER TRIGGERED:")
        for reason in analysis.get('buy_block_reasons', [])[:2]:
            print(f"       - {reason}")
    
    print(f"\n  Risk Score: {risk_score}/2 favorable")
    
    # =========================================================================
    # OVERALL SCORE
    # =========================================================================
    total_score = trend_score + momentum_score + pattern_score + risk_score
    max_score = 11
    score_pct = (total_score / max_score) * 100
    
    print(f"\n  {BOX_DOUBLE * 40}")
    print(f"  OVERALL SCORE: {total_score}/{max_score} ({score_pct:.0f}%)")
    print(f"  {BOX_DOUBLE * 40}")
    
    # Visual bar
    filled = int(score_pct / 10)
    empty = 10 - filled
    bar = "[" + "#" * filled + "." * empty + "]"
    print(f"\n  {bar}")
    
    if score_pct >= 70:
        print(f"\n  {CHECK} STRONG BUY CONDITIONS")
        print(f"       Most factors are bullish")
    elif score_pct >= 50:
        print(f"\n  [?] MODERATE CONDITIONS")
        print(f"       Mixed signals - proceed with caution")
    elif score_pct >= 30:
        print(f"\n  {WARNING} WEAK CONDITIONS")
        print(f"       Most factors are against buying")
    else:
        print(f"\n  {CROSS} POOR CONDITIONS")
        print(f"       Strongly recommend avoiding")


def print_full_report(analysis: Dict, position_data: Optional[Dict] = None, horizon: str = '3months'):
    """Print the complete beginner-friendly analysis report"""
    
    # Header
    print_beginner_header(analysis['symbol'], horizon)
    
    # Quick Summary (most important info first)
    print_quick_summary(analysis, horizon)
    
    # === NEW: Decision Breakdown - WHY this recommendation ===
    print_decision_breakdown(analysis)
    
    # Investment Plan
    print_investment_plan(analysis, horizon)
    
    # Profit/Loss Calculator
    if position_data and 'capital' in position_data:
        print_profit_loss_calculator(analysis, position_data['capital'])
    else:
        print_profit_loss_calculator(analysis)
    
    # When to Sell
    print_when_to_sell(analysis, horizon)
    
    # Market Conditions
    print_market_conditions(analysis)
    
    # Chart Patterns
    print_chart_patterns(analysis)
    
    # Important Price Levels
    print_important_price_levels(analysis)
    
    # Checklist
    print_simple_checklist(analysis)
    
    # Tips
    print_beginner_tips(analysis)
    
    # Footer
    print_disclaimer()


def print_summary_table(analyses: List[Dict]):
    """Print summary table for multiple stocks"""
    print(f"\n{BOX_DOUBLE * REPORT_WIDTH}")
    print(f"  COMPARISON SUMMARY")
    print(f"{BOX_DOUBLE * REPORT_WIDTH}")
    
    print(f"\n  {'Stock':<15} {'Price':>10} {'Action':>12} {'Safety':>10} {'Target':>10} {'Timeline':>12}")
    print(f"  {BOX_SINGLE * 70}")
    
    for a in analyses:
        safety = a.get('safety_score', {})
        rec = a['recommendation'].replace('STRONG ', '').replace('WEAK ', '')[:10]
        target_pct = ((a.get('target', 0) - a['current_price']) / a['current_price'] * 100) if a.get('target') else 0
        
        time_est = a.get('time_estimate', {})
        timeline = f"{time_est.get('trading_days', '?')} days" if time_est else "N/A"
        
        safety_str = f"{safety.get('stars', 0)}/5" if safety else "N/A"
        print(f"  {a['symbol']:<15} {format_price(a['current_price']):>10} {rec:>12} {safety_str:>10} {format_percentage(target_pct):>10} {timeline:>12}")
    
    print(f"\n{BOX_DOUBLE * REPORT_WIDTH}")


def print_portfolio_ranking(analyses: List[Dict]):
    """Print stocks ranked by investment quality"""
    print(f"\n{BOX_DOUBLE * REPORT_WIDTH}")
    print(f"  RANKED BY INVESTMENT QUALITY")
    print(f"{BOX_DOUBLE * REPORT_WIDTH}")
    
    # Sort by safety score
    sorted_analyses = sorted(
        analyses,
        key=lambda x: x.get('safety_score', {}).get('score', 0),
        reverse=True
    )
    
    for i, a in enumerate(sorted_analyses, 1):
        safety = a.get('safety_score', {})
        rank_label = f"#{i}"
        
        print(f"\n  {rank_label} {a['symbol']}")
        print(f"     Safety: {safety.get('stars', 0)}/5 stars - {safety.get('rating', 'N/A')}")
        print(f"     {safety.get('advice', '')}")


def print_portfolio_allocation(allocation_data: Dict, capital: float):
    """Print portfolio allocation suggestions"""
    print(f"\n{BOX_DOUBLE * REPORT_WIDTH}")
    print(f"  SUGGESTED PORTFOLIO ALLOCATION")
    print(f"  (Total Capital: {format_price(capital)})")
    print(f"{BOX_DOUBLE * REPORT_WIDTH}")
    
    if not allocation_data['investable']:
        print(f"\n  {WARNING} No stocks recommended for investment right now.")
        print(f"  Suggestion: Keep your money in savings and wait for better opportunities.")
    else:
        print(f"\n  RECOMMENDED INVESTMENTS:")
        for alloc in allocation_data['investable']:
            print(f"\n  {BULLET} {alloc['symbol']}")
            print(f"     Invest: {format_price(alloc['allocated_amount'])} ({alloc['weight_pct']:.0f}%)")
            print(f"     Buy: {alloc['shares']} shares @ {format_price(alloc['entry_price'])}")
        
        print(f"\n  {BOX_SINGLE * 40}")
        print(f"  Total to Invest: {format_price(allocation_data['total_allocated'])}")
        print(f"  Keep as Cash: {format_price(allocation_data['cash_remaining'])}")
    
    if allocation_data['not_recommended']:
        print(f"\n  {CROSS} NOT RECOMMENDED:")
        for nr in allocation_data['not_recommended']:
            print(f"     {nr['symbol']}: {nr['reason']}")


def print_disclaimer():
    """Print disclaimer"""
    print(f"\n{BOX_DOUBLE * REPORT_WIDTH}")
    print(f"  {WARNING} IMPORTANT DISCLAIMER")
    print(f"{BOX_DOUBLE * REPORT_WIDTH}")
    print(f"  {BULLET} This is for educational purposes only - NOT financial advice")
    print(f"  {BULLET} Past performance does not guarantee future results")
    print(f"  {BULLET} Always consult a SEBI-registered financial advisor")
    print(f"  {BULLET} Never invest more than you can afford to lose")
    print(f"  {BULLET} The author is not responsible for any investment losses")
    print(f"{BOX_DOUBLE * REPORT_WIDTH}")
    print(f"  Developed by Harsh Kandhway | v3.0 (Beginner-Friendly Edition)")
    print(f"{BOX_DOUBLE * REPORT_WIDTH}\n")


# Legacy functions for backward compatibility
def print_header(symbol: str, mode: str, timeframe: str):
    """Legacy header function"""
    print_beginner_header(symbol, '3months')


def print_hard_filter_warning(is_blocked: bool, block_reasons: List[str], direction: str):
    """Print hard filter warnings"""
    if not is_blocked:
        return
    
    print(f"\n  {'!' * 40}")
    print(f"  {WARNING} WARNING: {direction.upper()} NOT RECOMMENDED")
    for reason in block_reasons:
        print(f"     {BULLET} {reason}")
    print(f"  {'!' * 40}")


def print_market_regime(indicators: Dict):
    """Legacy - now handled by print_market_conditions"""
    pass


def print_indicator_table(indicators: Dict, signal_data: Dict):
    """Legacy - now hidden from beginners"""
    pass


def print_signal_summary(signal_data: Dict):
    """Legacy - now hidden from beginners"""
    pass


def print_recommendation_box(recommendation: str, confidence: float, confidence_level: str, is_blocked: bool):
    """Legacy - now handled by print_quick_summary"""
    pass


def print_reasoning(reasoning: List[str]):
    """Legacy - now simplified"""
    pass


def print_action_plan(actions: Dict[str, str]):
    """Legacy - now handled by print_investment_plan"""
    pass


def print_price_levels(indicators: Dict, target_data: Dict, stop_data: Dict):
    """Legacy - now handled by print_important_price_levels"""
    pass


def print_risk_reward(risk_reward: float, is_valid: bool, explanation: str, mode: str):
    """Legacy - now simplified in profit/loss calculator"""
    pass


def print_position_sizing(position_data: Dict):
    """Legacy - now handled by print_profit_loss_calculator"""
    pass


def print_trailing_stop_strategy(trailing_data: Dict):
    """Legacy - simplified for beginners"""
    pass
