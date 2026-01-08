"""
Output Module for Stock Analyzer Pro
Handles all report formatting and display
"""

from typing import Dict, List, Optional
from datetime import datetime
from config import CURRENCY_SYMBOL, REPORT_WIDTH, SIGNAL_WEIGHTS


def print_header(symbol: str, mode: str, timeframe: str):
    """Print report header"""
    print(f"\n{'='*REPORT_WIDTH}")
    print(f"  {symbol} - PROFESSIONAL TECHNICAL ANALYSIS")
    print(f"  Mode: {mode.upper()} | Timeframe: {timeframe.upper()} | Date: {datetime.now().strftime('%b %d, %Y')}")
    print(f"{'='*REPORT_WIDTH}")


def print_hard_filter_warning(is_blocked: bool, block_reasons: List[str], direction: str):
    """Print hard filter warnings"""
    if not is_blocked:
        return
    
    header = f"HARD FILTER TRIGGERED - {direction.upper()} BLOCKED"
    print(f"\n  {'⚠️  ' + header:^{REPORT_WIDTH-4}}")
    print(f"  {'─'*40}")
    for reason in block_reasons:
        print(f"  • {reason}")


def print_market_regime(indicators: Dict):
    """Print market regime section"""
    print(f"\n  MARKET REGIME")
    print(f"  {'─'*40}")
    
    # Primary trend
    price_vs_trend = indicators['price_vs_trend_ema']
    trend_ema_period = indicators['ema_trend_period']
    trend_status = "BULLISH" if price_vs_trend == 'above' else "BEARISH"
    print(f"  Primary Trend:       {trend_status} (Price {'>' if price_vs_trend == 'above' else '<'} {trend_ema_period} EMA)")
    
    # Trend strength
    adx = indicators['adx']
    strength = indicators['adx_strength'].replace('_', ' ').upper()
    print(f"  Trend Strength:      {strength} (ADX = {adx:.1f})")
    
    # Market phase
    phase = indicators['market_phase'].replace('_', ' ').upper()
    print(f"  Market Phase:        {phase}")
    
    # EMA alignment
    alignment = indicators['ema_alignment'].replace('_', ' ').upper()
    print(f"  EMA Alignment:       {alignment}")


def print_indicator_table(indicators: Dict, signal_data: Dict):
    """Print technical indicators table"""
    print(f"\n  TECHNICAL INDICATORS")
    print(f"  {'─'*70}")
    print(f"  {'Indicator':<22} {'Value':>12} {'Signal':>12} {'Weight':>8}")
    print(f"  {'─'*70}")
    
    # Get signals for display
    signals = signal_data['signals']
    
    # RSI
    rsi = indicators['rsi']
    rsi_signal = '▲ BUY' if signals['rsi_zone'][0] > 0 else '▼ SELL' if signals['rsi_zone'][0] < 0 else '○ NEUTRAL'
    print(f"  {'RSI (' + str(indicators['rsi_period']) + ')':<22} {rsi:>12.2f} {rsi_signal:>12} {SIGNAL_WEIGHTS['rsi_zone']:>7}%")
    
    # MACD
    macd_hist = indicators['macd_hist']
    macd_signal = '▲ BUY' if signals['macd_signal'][0] > 0 else '▼ SELL' if signals['macd_signal'][0] < 0 else '○ NEUTRAL'
    crossover = ' [CROSS]' if indicators['macd_crossover'] != 'none' else ''
    print(f"  {'MACD Histogram':<22} {macd_hist:>12.4f} {macd_signal:>12} {SIGNAL_WEIGHTS['macd_signal']:>7}%{crossover}")
    
    # Trend EMA
    trend_ema = indicators['ema_trend']
    trend_signal = '▲ BUY' if signals['price_vs_trend_ema'][0] > 0 else '▼ SELL'
    print(f"  {'Price vs ' + str(indicators['ema_trend_period']) + ' EMA':<22} {trend_ema:>12.2f} {trend_signal:>12} {SIGNAL_WEIGHTS['price_vs_trend_ema']:>7}%")
    
    # Medium EMA
    med_ema = indicators['ema_medium']
    med_signal = '▲ BUY' if signals['price_vs_medium_ema'][0] > 0 else '▼ SELL'
    print(f"  {'Price vs ' + str(indicators['ema_medium_period']) + ' EMA':<22} {med_ema:>12.2f} {med_signal:>12} {SIGNAL_WEIGHTS['price_vs_medium_ema']:>7}%")
    
    # ADX
    adx = indicators['adx']
    adx_signal = '▲ TREND' if indicators['trend_exists'] else '○ NO TREND'
    print(f"  {'ADX':<22} {adx:>12.2f} {adx_signal:>12} {SIGNAL_WEIGHTS['adx_strength']:>7}%")
    
    # Volume
    vol_ratio = indicators['volume_ratio']
    vol_signal = '▲ HIGH' if vol_ratio > 1.5 else '▼ LOW' if vol_ratio < 0.5 else '○ NORMAL'
    print(f"  {'Volume Ratio':<22} {vol_ratio:>11.2f}x {vol_signal:>12} {SIGNAL_WEIGHTS['volume_confirmation']:>7}%")
    
    # Bollinger %B
    bb_pct = indicators['bb_percent']
    bb_signal = '▼ SELL' if bb_pct > 0.8 else '▲ BUY' if bb_pct < 0.2 else '○ NEUTRAL'
    print(f"  {'Bollinger %B':<22} {bb_pct:>12.2f} {bb_signal:>12} {SIGNAL_WEIGHTS['bollinger_position']:>7}%")
    
    # Divergence
    div = indicators['divergence']
    div_signal = '▲ BULLISH' if div == 'bullish' else '▼ BEARISH' if div == 'bearish' else '○ NONE'
    print(f"  {'Divergence':<22} {div.upper():>12} {div_signal:>12} {SIGNAL_WEIGHTS['divergence']:>7}%")
    
    print(f"  {'─'*70}")


def print_signal_summary(signal_data: Dict):
    """Print signal summary"""
    print(f"\n  SIGNAL SUMMARY")
    print(f"  {'─'*40}")
    print(f"  Bullish Signals:     {signal_data['bullish_count']} ({signal_data['bullish_score']:.1f} points)")
    print(f"  Bearish Signals:     {signal_data['bearish_count']} ({signal_data['bearish_score']:.1f} points)")
    print(f"  Neutral Signals:     {signal_data['neutral_count']}")
    print(f"  Net Score:           {signal_data['net_score']:+.1f}")


def print_recommendation_box(
    recommendation: str,
    confidence: float,
    confidence_level: str,
    is_blocked: bool
):
    """Print the main recommendation box"""
    print(f"\n  {'═'*40}")
    
    if is_blocked:
        print(f"  {'RECOMMENDATION:':<20} ⛔ {recommendation}")
        print(f"  {'CONFIDENCE:':<20} N/A (Blocked)")
    else:
        # Color-code recommendation (using text symbols)
        if 'BUY' in recommendation:
            symbol = '🟢'
        elif 'SELL' in recommendation:
            symbol = '🔴'
        else:
            symbol = '🟡'
        
        print(f"  {'RECOMMENDATION:':<20} {symbol} {recommendation}")
        print(f"  {'CONFIDENCE:':<20} {confidence:.0f}% ({confidence_level})")
    
    print(f"  {'═'*40}")


def print_reasoning(reasoning: List[str]):
    """Print reasoning section"""
    print(f"\n  REASONING")
    print(f"  {'─'*40}")
    for reason in reasoning:
        if reason.startswith('WARNING'):
            print(f"  ⚠️  {reason}")
        else:
            print(f"  • {reason}")


def print_action_plan(actions: Dict[str, str]):
    """Print action plan for different investor types"""
    print(f"\n  ACTION PLAN")
    print(f"  {'─'*40}")
    print(f"  ├── NEW INVESTORS: {actions['new_investors']}")
    print(f"  ├── EXISTING HOLDERS: {actions['existing_holders']}")
    print(f"  └── TRADERS: {actions['traders']}")


def print_price_levels(
    indicators: Dict,
    target_data: Dict,
    stop_data: Dict
):
    """Print price levels section"""
    print(f"\n  LEVELS TO WATCH")
    print(f"  {'─'*40}")
    
    current = indicators['current_price']
    print(f"  Current Price:       {CURRENCY_SYMBOL}{current:.2f}")
    print()
    
    # Resistance levels
    print(f"  RESISTANCE:")
    print(f"    52-Week High:      {CURRENCY_SYMBOL}{indicators['high_52w']:.2f} ({((indicators['high_52w'] - current) / current * 100):+.1f}%)")
    print(f"    Recent High:       {CURRENCY_SYMBOL}{indicators['resistance']:.2f} ({((indicators['resistance'] - current) / current * 100):+.1f}%)")
    
    # Targets
    print(f"\n  TARGETS:")
    print(f"    Conservative:      {CURRENCY_SYMBOL}{target_data['conservative_target']:.2f} ({target_data['conservative_target_pct']:+.1f}%)")
    print(f"    ATR-Based:         {CURRENCY_SYMBOL}{target_data['atr_target']:.2f} ({target_data['atr_target_pct']:+.1f}%)")
    if 'aggressive_target' in target_data:
        print(f"    Aggressive:        {CURRENCY_SYMBOL}{target_data['aggressive_target']:.2f} ({target_data['aggressive_target_pct']:+.1f}%)")
    
    # Support levels
    print(f"\n  SUPPORT:")
    print(f"    Recent Low:        {CURRENCY_SYMBOL}{indicators['support']:.2f} ({((indicators['support'] - current) / current * 100):+.1f}%)")
    print(f"    52-Week Low:       {CURRENCY_SYMBOL}{indicators['low_52w']:.2f} ({((indicators['low_52w'] - current) / current * 100):+.1f}%)")
    
    # Stop loss
    print(f"\n  STOP LOSS:")
    print(f"    Recommended:       {CURRENCY_SYMBOL}{stop_data['recommended_stop']:.2f} ({-stop_data['recommended_stop_pct']:.1f}%)")


def print_risk_reward(
    risk_reward: float,
    is_valid: bool,
    explanation: str,
    mode: str
):
    """Print risk/reward section"""
    print(f"\n  RISK MANAGEMENT")
    print(f"  {'─'*40}")
    
    status = "✓ VALID" if is_valid else "✗ INVALID"
    print(f"  Risk/Reward Ratio:   {risk_reward:.2f}:1 [{status}]")
    print(f"  {explanation}")
    
    if not is_valid:
        print(f"\n  ⛔ TRADE NOT RECOMMENDED AT CURRENT LEVELS")
        print(f"  Reason: R:R below professional minimum")


def print_position_sizing(position_data: Dict):
    """Print position sizing section"""
    if position_data.get('error'):
        print(f"\n  POSITION SIZING")
        print(f"  {'─'*40}")
        print(f"  Error: {position_data['message']}")
        return
    
    print(position_data['explanation'])


def print_trailing_stop_strategy(trailing_data: Dict):
    """Print trailing stop strategy"""
    print(trailing_data['explanation'])


def print_full_report(analysis: Dict, position_data: Optional[Dict] = None):
    """Print the complete analysis report"""
    
    # Header
    print_header(
        analysis['symbol'],
        analysis['mode'],
        analysis['timeframe']
    )
    
    # Hard filter warnings
    print_hard_filter_warning(
        analysis['is_buy_blocked'],
        analysis.get('buy_block_reasons', []),
        'buy'
    )
    print_hard_filter_warning(
        analysis['is_sell_blocked'],
        analysis.get('sell_block_reasons', []),
        'sell'
    )
    
    # Market regime
    print_market_regime(analysis['indicators'])
    
    # Indicator table
    print_indicator_table(analysis['indicators'], analysis['signal_data'])
    
    # Signal summary
    print_signal_summary(analysis['signal_data'])
    
    # Recommendation
    print_recommendation_box(
        analysis['recommendation'],
        analysis['confidence'],
        analysis['confidence_level'],
        analysis['is_buy_blocked'] or analysis['is_sell_blocked']
    )
    
    # Reasoning
    print_reasoning(analysis['reasoning'])
    
    # Action plan
    print_action_plan(analysis['actions'])
    
    # Price levels
    print_price_levels(
        analysis['indicators'],
        analysis['target_data'],
        analysis['stop_data']
    )
    
    # Risk/Reward
    print_risk_reward(
        analysis['risk_reward'],
        analysis['rr_valid'],
        analysis['rr_explanation'],
        analysis['mode']
    )
    
    # Position sizing (if capital provided)
    if position_data:
        print_position_sizing(position_data)
    
    # Trailing stops
    if analysis.get('trailing_data'):
        print_trailing_stop_strategy(analysis['trailing_data'])
    
    print(f"\n{'='*REPORT_WIDTH}")


def print_summary_table(analyses: List[Dict]):
    """Print summary table for multiple stocks"""
    print(f"\n{'='*REPORT_WIDTH}")
    print(f"  SUMMARY")
    print(f"{'='*REPORT_WIDTH}")
    
    print(f"\n  {'Symbol':<20} {'Price':>10} {'Confidence':>12} {'Recommendation':<15} {'R:R':>8} {'Valid':>6}")
    print(f"  {'-'*75}")
    
    for a in analyses:
        rr_str = f"{a['risk_reward']:.2f}:1" if a['risk_reward'] > 0 else "N/A"
        valid_str = "✓" if a['rr_valid'] else "✗"
        conf_str = f"{a['confidence']:.0f}%" if not a['is_buy_blocked'] else "N/A"
        
        print(f"  {a['symbol']:<20} {CURRENCY_SYMBOL}{a['current_price']:>8.2f} {conf_str:>12} {a['recommendation']:<15} {rr_str:>8} {valid_str:>6}")
    
    print(f"\n{'='*REPORT_WIDTH}")


def print_portfolio_ranking(analyses: List[Dict]):
    """Print stocks ranked by confidence"""
    print(f"\n{'='*REPORT_WIDTH}")
    print(f"  PORTFOLIO RANKING BY CONFIDENCE")
    print(f"{'='*REPORT_WIDTH}")
    
    # Sort by confidence (handle blocked ones)
    sorted_analyses = sorted(
        analyses,
        key=lambda x: x['confidence'] if not x['is_buy_blocked'] else -1,
        reverse=True
    )
    
    print(f"\n  {'Rank':<6} {'Symbol':<20} {'Confidence':>12} {'Recommendation':<18} {'R:R':>8} {'Valid':>6}")
    print(f"  {'-'*75}")
    
    for i, a in enumerate(sorted_analyses, 1):
        rr_str = f"{a['risk_reward']:.2f}:1" if a['risk_reward'] > 0 else "-"
        valid_str = "✓" if a['rr_valid'] else "✗"
        
        if a['is_buy_blocked']:
            conf_str = "BLOCKED"
            rec_str = "⛔ " + a['recommendation']
        else:
            conf_str = f"{a['confidence']:.0f}%"
            if 'BUY' in a['recommendation']:
                rec_str = "🟢 " + a['recommendation']
            elif 'SELL' in a['recommendation']:
                rec_str = "🔴 " + a['recommendation']
            else:
                rec_str = "🟡 " + a['recommendation']
        
        print(f"  {i:<6} {a['symbol']:<20} {conf_str:>12} {rec_str:<18} {rr_str:>8} {valid_str:>6}")
    
    print(f"\n{'='*REPORT_WIDTH}")


def print_portfolio_allocation(allocation_data: Dict, capital: float):
    """Print portfolio allocation suggestions"""
    print(f"\n{'='*REPORT_WIDTH}")
    print(f"  SUGGESTED PORTFOLIO ALLOCATION (Capital: {CURRENCY_SYMBOL}{capital:,.2f})")
    print(f"{'='*REPORT_WIDTH}")
    
    if not allocation_data['investable']:
        print(f"\n  ⛔ NO STOCKS MEET INVESTMENT CRITERIA")
        print(f"\n  Hold cash and wait for better opportunities.")
    else:
        print(f"\n  INVESTABLE STOCKS (Meet all criteria):")
        print(f"  {'─'*65}")
        print(f"  {'Symbol':<20} {'Confidence':>12} {'Allocation':>12} {'Amount':>12} {'Shares':>8}")
        print(f"  {'─'*65}")
        
        for alloc in allocation_data['investable']:
            print(f"  {alloc['symbol']:<20} {alloc['confidence']:>11.0f}% {alloc['weight_pct']:>11.1f}% {CURRENCY_SYMBOL}{alloc['allocated_amount']:>10,.2f} {alloc['shares']:>8}")
        
        print(f"  {'─'*65}")
        print(f"  {'TOTAL INVESTED:':<20} {'':<12} {'':<12} {CURRENCY_SYMBOL}{allocation_data['total_allocated']:>10,.2f}")
        print(f"  {'CASH REMAINING:':<20} {'':<12} {'':<12} {CURRENCY_SYMBOL}{allocation_data['cash_remaining']:>10,.2f}")
    
    if allocation_data['not_recommended']:
        print(f"\n  NOT RECOMMENDED:")
        print(f"  {'─'*65}")
        for nr in allocation_data['not_recommended']:
            print(f"  • {nr['symbol']}: {nr['reason']}")
    
    print(f"\n{'='*REPORT_WIDTH}")


def print_disclaimer():
    """Print disclaimer"""
    print(f"\n{'='*REPORT_WIDTH}")
    print(f"  DISCLAIMER")
    print(f"{'='*REPORT_WIDTH}")
    print(f"  • This is technical analysis for educational purposes only.")
    print(f"  • Past performance is NOT indicative of future results.")
    print(f"  • Always consult a SEBI-registered financial advisor.")
    print(f"  • Never invest more than you can afford to lose.")
    print(f"  • Use proper position sizing and risk management.")
    print(f"{'='*REPORT_WIDTH}\n")
