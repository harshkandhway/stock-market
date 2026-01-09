"""
Message Formatters for Telegram Bot
Formats analysis results and other data for Telegram display

Author: Harsh Kandhway
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from src.bot.config import EMOJI, MAX_MESSAGE_LENGTH, CURRENCY_SYMBOL


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped text safe for MarkdownV2
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_number(value: float, decimals: int = 2) -> str:
    """
    Format number with proper decimals and thousand separators
    
    Args:
        value: Number to format
        decimals: Number of decimal places
    
    Returns:
        Formatted number string
    """
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2, show_sign: bool = True) -> str:
    """
    Format percentage value
    
    Args:
        value: Percentage value
        decimals: Number of decimal places
        show_sign: Whether to show + sign for positive values
    
    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"
    
    sign = '+' if value > 0 and show_sign else ''
    return f"{sign}{value:.{decimals}f}%"


def chunk_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Split long message into chunks that fit Telegram's limit
    
    Args:
        text: Message text
        max_length: Maximum length per chunk
    
    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 <= max_length:
            current_chunk += line + '\n'
        else:
            if current_chunk:
                chunks.append(current_chunk.rstrip())
            current_chunk = line + '\n'
    
    if current_chunk:
        chunks.append(current_chunk.rstrip())
    
    return chunks


def format_analysis_summary(analysis: Dict[str, Any]) -> str:
    """
    Format analysis result as a short summary
    
    Args:
        analysis: Analysis dictionary from analysis_service
    
    Returns:
        Formatted summary string
    """
    symbol = analysis['symbol']
    price = analysis['current_price']
    recommendation = analysis['recommendation']
    confidence = analysis['confidence']
    confidence_level = analysis['confidence_level']
    rec_type = analysis['recommendation_type']
    
    # Emoji based on recommendation
    if rec_type == 'BUY':
        emoji = EMOJI['buy']
    elif rec_type == 'SELL':
        emoji = EMOJI['sell']
    elif rec_type == 'BLOCKED':
        emoji = EMOJI['blocked']
    else:
        emoji = EMOJI['hold']
    
    summary = f"""
{EMOJI['analyze']} **{symbol} Analysis**

{EMOJI['money']} **Price:** {CURRENCY_SYMBOL}{format_number(price)}

{EMOJI['target']} **Recommendation:** {emoji} {recommendation}
{EMOJI['chart']} **Confidence:** {format_number(confidence, 0)}% ({confidence_level})
"""
    
    return summary.strip()


def format_analysis_full(analysis: Dict[str, Any]) -> str:
    """
    Format complete analysis result with all details
    
    Args:
        analysis: Analysis dictionary from analysis_service
    
    Returns:
        Formatted full analysis string
    """
    symbol = analysis['symbol']
    mode = analysis['mode'].upper()
    timeframe = analysis['timeframe']
    price = analysis['current_price']
    recommendation = analysis['recommendation']
    confidence = analysis['confidence']
    confidence_level = analysis['confidence_level']
    rec_type = analysis['recommendation_type']
    
    indicators = analysis['indicators']
    target_data = analysis['target_data']
    stop_data = analysis['stop_data']
    risk_reward = analysis['risk_reward']
    rr_valid = analysis['rr_valid']
    
    # Emoji based on recommendation
    if rec_type == 'BUY':
        emoji = EMOJI['buy']
    elif rec_type == 'SELL':
        emoji = EMOJI['sell']
    elif rec_type == 'BLOCKED':
        emoji = EMOJI['blocked']
    else:
        emoji = EMOJI['hold']
    
    # Header
    message = f"""
{'='*40}
{EMOJI['chart']} **{symbol} - ANALYSIS**
Mode: {mode} | Timeframe: {timeframe}
{'='*40}

{EMOJI['money']} **Current Price:** {CURRENCY_SYMBOL}{format_number(price)}

"""
    
    # Market Regime
    phase = indicators['market_phase'].replace('_', ' ').title()
    adx = indicators['adx']
    trend_strength = indicators['adx_strength'].replace('_', ' ').title()
    
    message += f"""
{EMOJI['info']} **Market Regime**
{'-'*40}
Phase: {phase}
Trend Strength: {trend_strength} (ADX: {format_number(adx, 1)})

"""
    
    # Key Indicators
    rsi = indicators['rsi']
    macd_hist = indicators['macd_hist']
    volume_ratio = indicators['volume_ratio']
    
    message += f"""
{EMOJI['chart']} **Key Indicators**
{'-'*40}
RSI ({indicators['rsi_period']}): {format_number(rsi, 1)} - {indicators['rsi_zone'].replace('_', ' ').title()}
MACD Histogram: {format_number(macd_hist, 4)}
Volume Ratio: {format_number(volume_ratio, 2)}x average
"""
    
    # Divergence warning if present
    if indicators['divergence'] != 'none':
        div_emoji = EMOJI['warning']
        div_text = indicators['divergence'].upper()
        message += f"\n{div_emoji} **{div_text} DIVERGENCE DETECTED**"
    
    # Chart Pattern Analysis
    strongest_pattern = indicators.get('strongest_pattern')
    pattern_bias = indicators.get('pattern_bias', 'neutral')
    bullish_count = indicators.get('pattern_bullish_count', 0)
    bearish_count = indicators.get('pattern_bearish_count', 0)
    
    if strongest_pattern or bullish_count > 0 or bearish_count > 0:
        message += f"""

📊 **Chart Patterns**
{'-'*40}
Pattern Bias: {pattern_bias.upper()}
Bullish Patterns: {bullish_count} | Bearish Patterns: {bearish_count}
"""
        if strongest_pattern and hasattr(strongest_pattern, 'name'):
            try:
                p_name = getattr(strongest_pattern, 'name', 'Unknown')
                p_conf = getattr(strongest_pattern, 'confidence', 0)
                p_type = strongest_pattern.type.value.upper() if hasattr(strongest_pattern, 'type') and hasattr(strongest_pattern.type, 'value') else 'UNKNOWN'
                p_strength = strongest_pattern.strength.value.upper() if hasattr(strongest_pattern, 'strength') and hasattr(strongest_pattern.strength, 'value') else 'UNKNOWN'
                p_action = getattr(strongest_pattern, 'action', 'Check chart')
                
                message += f"""
Key Pattern: **{p_name}** ({p_conf}%)
Type: {p_type} | Strength: {p_strength}
Action: {p_action}
"""
            except Exception:
                message += "\nKey Pattern: Pattern detected (check chart)\n"
    
    message += "\n"
    
    # Recommendation Box
    message += f"""
{'='*40}
{EMOJI['target']} **RECOMMENDATION**
{'='*40}
{emoji} **{recommendation}**
Confidence: {format_number(confidence, 0)}% ({confidence_level})

"""
    
    # Hard filter warnings
    if analysis['is_buy_blocked']:
        message += f"{EMOJI['warning']} **BUY BLOCKED:**\n"
        for reason in analysis['buy_block_reasons'][:2]:  # Limit to 2 reasons
            message += f"• {reason}\n"
        message += "\n"
    
    # Targets and Stop Loss
    target = target_data['recommended_target']
    target_pct = target_data['recommended_target_pct']
    stop = stop_data['recommended_stop']
    stop_pct = stop_data['recommended_stop_pct']
    
    message += f"""
{EMOJI['target']} **TARGETS**
{'-'*40}
Target: {CURRENCY_SYMBOL}{format_number(target)} ({format_percentage(target_pct)})
Conservative: {CURRENCY_SYMBOL}{format_number(target_data.get('conservative_target', target))}

{EMOJI['stop']} **STOP LOSS**
{'-'*40}
Stop: {CURRENCY_SYMBOL}{format_number(stop)} ({format_percentage(-stop_pct)})

{EMOJI['info']} **RISK/REWARD**
{'-'*40}
Ratio: {format_number(risk_reward, 2)}:1
"""
    
    if rr_valid:
        message += f"{EMOJI['success']} Meets minimum requirements\n"
    else:
        message += f"{EMOJI['warning']} Below minimum threshold\n"
    
    message += "\n"
    
    # Key Reasoning (top 3)
    message += f"""
{EMOJI['info']} **KEY POINTS**
{'-'*40}
"""
    for i, reason in enumerate(analysis['reasoning'][:3], 1):
        # Shorten reason if too long
        if len(reason) > 80:
            reason = reason[:77] + "..."
        message += f"{i}. {reason}\n"
    
    message += f"\n{'='*40}\n"
    message += f"\n*Developed by Harsh Kandhway*\n"
    
    return message.strip()


def format_comparison_table(analyses: List[Dict[str, Any]]) -> str:
    """
    Format multiple analyses as a comparison table
    
    Args:
        analyses: List of analysis dictionaries
    
    Returns:
        Formatted comparison table
    """
    message = f"""
{EMOJI['compare']} **STOCK COMPARISON**
{'='*40}

"""
    
    for analysis in analyses:
        symbol = analysis['symbol']
        price = analysis['current_price']
        rec = analysis['recommendation']
        conf = analysis['confidence']
        rr = analysis['risk_reward']
        
        # Emoji
        if analysis['recommendation_type'] == 'BUY':
            emoji = EMOJI['buy']
        elif analysis['recommendation_type'] == 'SELL':
            emoji = EMOJI['sell']
        else:
            emoji = EMOJI['hold']
        
        message += f"""
**{symbol}**
Price: {CURRENCY_SYMBOL}{format_number(price)} | {emoji} {rec}
Confidence: {format_number(conf, 0)}% | R:R: {format_number(rr, 2)}:1
{'-'*40}

"""
    
    message += f"\n*Developed by Harsh Kandhway*\n"
    
    return message.strip()


def format_watchlist(watchlist: List, show_details: bool = False) -> str:
    """
    Format watchlist for display
    
    Args:
        watchlist: List of watchlist items (Watchlist objects or dicts with symbol, added_at, etc.)
        show_details: Whether to show additional details
    
    Returns:
        Formatted watchlist string
    """
    if not watchlist:
        return f"{EMOJI['info']} Your watchlist is empty.\n\nUse /watchlist add [SYMBOL] to add stocks."
    
    message = f"""
{EMOJI['watchlist']} **YOUR WATCHLIST** ({len(watchlist)} stocks)
{'='*40}

"""
    
    for item in watchlist:
        # Handle both Watchlist objects and dictionaries
        # Check if it's a dictionary by trying to access it as a dict
        if isinstance(item, dict):
            # Dictionary access
            symbol = item['symbol']
            added_at = item.get('added_at')
            notes = item.get('notes')
        else:
            # Watchlist object (SQLAlchemy model) - use attribute access
            symbol = item.symbol
            added_at = getattr(item, 'added_at', None)
            notes = getattr(item, 'notes', None)
        
        message += f"{EMOJI['chart']} **{symbol}**\n"
        
        if show_details and added_at:
            added_date = added_at.strftime('%b %d, %Y') if isinstance(added_at, datetime) else added_at
            message += f"   Added: {added_date}\n"
        
        if show_details and notes:
            message += f"   Notes: {notes}\n"
        
        message += "\n"
    
    return message.strip()


def format_alert(alert: Dict) -> str:
    """
    Format single alert for display
    
    Args:
        alert: Alert dictionary
    
    Returns:
        Formatted alert string
    """
    alert_id = alert['id']
    symbol = alert['symbol']
    alert_type = alert['alert_type']
    condition_type = alert['condition_type']
    threshold = alert.get('threshold_value')
    is_active = alert['is_active']
    
    status_emoji = EMOJI['success'] if is_active else EMOJI['error']
    status = "Active" if is_active else "Inactive"
    
    message = f"{EMOJI['alert']} **Alert #{alert_id}** {status_emoji} {status}\n"
    message += f"Symbol: {symbol}\n"
    message += f"Type: {alert_type.replace('_', ' ').title()}\n"
    
    if alert_type == 'price' and threshold:
        message += f"Condition: Price {condition_type} {CURRENCY_SYMBOL}{format_number(threshold)}\n"
    elif alert_type == 'technical' and threshold:
        message += f"Condition: {condition_type.upper()} {condition_type} {format_number(threshold)}\n"
    else:
        message += f"Condition: {condition_type.replace('_', ' ').title()}\n"
    
    return message


def format_alert_list(alerts: List[Dict]) -> str:
    """
    Format list of alerts for display
    
    Args:
        alerts: List of alert dictionaries
    
    Returns:
        Formatted alerts list string
    """
    if not alerts:
        return f"{EMOJI['info']} You have no active alerts.\n\nUse /alert to set up alerts."
    
    message = f"""
{EMOJI['alert']} **YOUR ALERTS** ({len(alerts)} active)
{'='*40}

"""
    
    for alert in alerts:
        message += format_alert(alert) + "\n"
        message += f"{'-'*40}\n\n"
    
    return message.strip()


def format_portfolio(portfolio: List[Dict], current_prices: Optional[Dict[str, float]] = None) -> str:
    """
    Format portfolio for display with P&L calculation
    
    Args:
        portfolio: List of portfolio positions
        current_prices: Dict of symbol -> current price (optional)
    
    Returns:
        Formatted portfolio string
    """
    if not portfolio:
        return f"{EMOJI['info']} Your portfolio is empty.\n\nUse /portfolio add [SYMBOL] [SHARES] [PRICE] to add positions."
    
    message = f"""
{EMOJI['portfolio']} **YOUR PORTFOLIO** ({len(portfolio)} positions)
{'='*40}

"""
    
    total_investment = 0
    total_current_value = 0
    
    for position in portfolio:
        symbol = position['symbol']
        shares = position['shares']
        avg_price = position['avg_buy_price']
        investment = shares * avg_price
        
        total_investment += investment
        
        message += f"{EMOJI['chart']} **{symbol}**\n"
        message += f"   Shares: {format_number(shares, 2)}\n"
        message += f"   Avg Price: {CURRENCY_SYMBOL}{format_number(avg_price)}\n"
        message += f"   Investment: {CURRENCY_SYMBOL}{format_number(investment)}\n"
        
        # If current prices provided, calculate P&L
        if current_prices and symbol in current_prices:
            current_price = current_prices[symbol]
            current_value = shares * current_price
            pnl = current_value - investment
            pnl_pct = (pnl / investment) * 100
            
            total_current_value += current_value
            
            pnl_emoji = EMOJI['profit'] if pnl >= 0 else EMOJI['loss']
            message += f"   Current: {CURRENCY_SYMBOL}{format_number(current_price)}\n"
            message += f"   Value: {CURRENCY_SYMBOL}{format_number(current_value)}\n"
            message += f"   P&L: {pnl_emoji} {CURRENCY_SYMBOL}{format_number(pnl)} ({format_percentage(pnl_pct)})\n"
        
        message += "\n"
    
    # Portfolio Summary
    if current_prices and total_current_value > 0:
        total_pnl = total_current_value - total_investment
        total_pnl_pct = (total_pnl / total_investment) * 100
        pnl_emoji = EMOJI['profit'] if total_pnl >= 0 else EMOJI['loss']
        
        message += f"""
{'='*40}
{EMOJI['info']} **PORTFOLIO SUMMARY**
{'='*40}
Total Investment: {CURRENCY_SYMBOL}{format_number(total_investment)}
Current Value: {CURRENCY_SYMBOL}{format_number(total_current_value)}
Total P&L: {pnl_emoji} {CURRENCY_SYMBOL}{format_number(total_pnl)} ({format_percentage(total_pnl_pct)})
"""
    
    return message.strip()


def format_error(error_message: str, command: Optional[str] = None) -> str:
    """
    Format error message
    
    Args:
        error_message: Error message text
        command: Command that caused the error (optional)
    
    Returns:
        Formatted error message
    """
    message = f"{EMOJI['error']} **Error**\n\n{error_message}\n"
    
    if command:
        message += f"\nCommand: `{command}`"
    
    message += f"\n\nUse /help for usage instructions."
    
    return message


def format_success(success_message: str) -> str:
    """
    Format success message
    
    Args:
        success_message: Success message text
    
    Returns:
        Formatted success message
    """
    return f"{EMOJI['success']} {success_message}"


def format_info(info_message: str) -> str:
    """
    Format info message
    
    Args:
        info_message: Info message text
    
    Returns:
        Formatted info message
    """
    return f"{EMOJI['info']} {info_message}"


def format_warning(warning_message: str) -> str:
    """
    Format warning message
    
    Args:
        warning_message: Warning message text
    
    Returns:
        Formatted warning message
    """
    return f"{EMOJI['warning']} {warning_message}"


# =============================================================================
# BEGINNER-FRIENDLY FORMATTERS
# =============================================================================

def format_analysis_beginner(analysis: Dict[str, Any], horizon: str = '3months') -> str:
    """
    Format analysis result in beginner-friendly format with complete decision breakdown.
    Shows exactly WHY the recommendation was made.
    """
    symbol = analysis['symbol']
    price = analysis['current_price']
    recommendation = analysis['recommendation']
    confidence = analysis['confidence']
    rec_type = analysis['recommendation_type']
    
    indicators = analysis['indicators']
    target_data = analysis['target_data']
    stop_data = analysis['stop_data']
    risk_reward = analysis['risk_reward']
    rr_valid = analysis['rr_valid']
    reasoning = analysis.get('reasoning', [])
    
    # Safety score
    safety = analysis.get('safety_score', {})
    time_estimate = analysis.get('time_estimate', {})
    
    # Calculate values
    example_capital = 10000
    shares = max(1, int(example_capital / price))
    target = target_data['recommended_target']
    stop = stop_data['recommended_stop']
    
    profit_pct = ((target - price) / price) * 100
    loss_pct = ((price - stop) / price) * 100
    potential_profit = shares * (target - price)
    potential_loss = shares * (price - stop)
    
    # Safety rating
    safety_stars = safety.get('stars', 3)
    safety_emoji = '⭐' * safety_stars + '☆' * (5 - safety_stars)
    safety_rating = safety.get('rating', 'MODERATE')
    
    # =========================================================================
    # BUILD THE DECISION SCORECARD
    # =========================================================================
    
    # Trend Analysis
    trend_score = 0
    trend_factors = []
    
    if indicators['price_vs_trend_ema'] == 'above':
        trend_score += 1
        trend_factors.append(("✅", "Price above long-term average", "Bullish"))
    else:
        trend_factors.append(("❌", "Price below long-term average", "Bearish"))
    
    if 'uptrend' in indicators['market_phase']:
        trend_score += 1
        trend_factors.append(("✅", f"Market in {indicators['market_phase'].replace('_', ' ')}", "Bullish"))
    elif 'downtrend' in indicators['market_phase']:
        trend_factors.append(("❌", f"Market in {indicators['market_phase'].replace('_', ' ')}", "Bearish"))
    else:
        trend_factors.append(("⚪", "Market moving sideways", "Neutral"))
    
    ema_alignment = indicators.get('ema_alignment', 'mixed')
    if ema_alignment in ['strong_bullish', 'bullish']:
        trend_score += 1
        trend_factors.append(("✅", "All moving averages aligned UP", "Strong signal"))
    elif ema_alignment in ['strong_bearish', 'bearish']:
        trend_factors.append(("❌", "All moving averages aligned DOWN", "Weak signal"))
    else:
        trend_factors.append(("⚪", "Moving averages mixed", "No clear signal"))
    
    # Momentum Analysis
    momentum_score = 0
    momentum_factors = []
    
    rsi = indicators['rsi']
    rsi_zone = indicators['rsi_zone']
    if rsi_zone in ['oversold', 'extremely_oversold']:
        momentum_score += 1
        momentum_factors.append(("✅", f"RSI at {rsi:.0f} (Oversold)", "May bounce up soon"))
    elif rsi_zone in ['overbought', 'extremely_overbought']:
        momentum_factors.append(("❌", f"RSI at {rsi:.0f} (Overbought)", "May fall soon"))
    else:
        momentum_factors.append(("⚪", f"RSI at {rsi:.0f} (Neutral)", "No extreme"))
    
    macd_hist = indicators.get('macd_hist', 0)
    if macd_hist > 0:
        momentum_score += 1
        momentum_factors.append(("✅", "MACD positive", "Upward momentum"))
    else:
        momentum_factors.append(("❌", "MACD negative", "Downward momentum"))
    
    adx = indicators['adx']
    if adx >= 25:
        momentum_score += 1
        momentum_factors.append(("✅", f"ADX at {adx:.0f} (Strong trend)", "Trend is reliable"))
    else:
        momentum_factors.append(("⚠️", f"ADX at {adx:.0f} (Weak trend)", "Trend may reverse"))
    
    # Volume Analysis
    volume_score = 0
    volume_factors = []
    
    vol_ratio = indicators.get('volume_ratio', 1.0)
    if vol_ratio >= 1.5:
        volume_score += 1
        volume_factors.append(("✅", f"Volume {vol_ratio:.1f}x average", "High interest"))
    elif vol_ratio >= 0.8:
        volume_factors.append(("⚪", f"Volume {vol_ratio:.1f}x average", "Normal activity"))
    else:
        volume_factors.append(("❌", f"Volume {vol_ratio:.1f}x average", "Low interest"))
    
    # Chart Pattern Analysis
    pattern_score = 0
    pattern_factors = []
    
    strongest_pattern = indicators.get('strongest_pattern')
    pattern_bias = indicators.get('pattern_bias', 'neutral')
    candlestick_patterns = indicators.get('candlestick_patterns', [])
    chart_patterns = indicators.get('chart_patterns', [])
    
    if strongest_pattern and hasattr(strongest_pattern, 'type'):
        try:
            pattern_type = strongest_pattern.type.value if hasattr(strongest_pattern.type, 'value') else str(strongest_pattern.type)
            pattern_name = getattr(strongest_pattern, 'name', 'Unknown Pattern')
            pattern_conf = getattr(strongest_pattern, 'confidence', 0)
            pattern_action = getattr(strongest_pattern, 'action', 'No action')
            
            if pattern_type == 'bullish':
                pattern_score += 2
                pattern_factors.append(("✅", f"{pattern_name} ({pattern_conf}%)", pattern_action))
            elif pattern_type == 'bearish':
                pattern_factors.append(("❌", f"{pattern_name} ({pattern_conf}%)", pattern_action))
            else:
                pattern_factors.append(("⚪", f"{pattern_name} ({pattern_conf}%)", "Neutral pattern"))
        except Exception:
            pattern_factors.append(("⚪", "Pattern detected", "Check chart"))
    
    if pattern_bias == 'bullish':
        pattern_score += 1
    
    # Risk Analysis
    risk_score = 0
    risk_factors = []
    
    # Get mode-specific R/R threshold
    mode = analysis.get('mode', 'moderate')
    rr_thresholds = {
        'conservative': 3.0,
        'moderate': 2.0,
        'balanced': 2.0,
        'aggressive': 1.5
    }
    min_rr = rr_thresholds.get(mode, 2.0)
    
    if rr_valid:
        risk_score += 1
        risk_factors.append(("✅", f"Risk/Reward {risk_reward:.1f}:1", f"Meets minimum {min_rr:.1f}:1 for {mode} mode"))
    else:
        risk_factors.append(("❌", f"Risk/Reward {risk_reward:.1f}:1", f"Below minimum {min_rr:.1f}:1 for {mode} mode"))
    
    # Check for blocks
    if analysis.get('is_buy_blocked'):
        risk_factors.append(("🚫", "Hard filter triggered", analysis.get('buy_block_reasons', ['Risk too high'])[0] if analysis.get('buy_block_reasons') else 'Risk too high'))
    
    # =========================================================================
    # CALCULATE FINAL SCORES
    # =========================================================================
    
    total_bullish = trend_score + momentum_score + volume_score + pattern_score + risk_score
    max_score = 10
    score_pct = (total_bullish / max_score) * 100
    
    # =========================================================================
    # BUILD THE MESSAGE
    # =========================================================================
    
    # Header with clear verdict
    if rec_type == 'BUY':
        verdict_box = f"""
╔══════════════════════════════════╗
║  🟢 *{symbol}* - *BUY*  
║  
║  ✅ Good opportunity to invest
║  💪 Confidence: {confidence:.0f}%
╚══════════════════════════════════╝"""
    elif rec_type == 'HOLD':
        verdict_box = f"""
╔══════════════════════════════════╗
║  🟡 *{symbol}* - *WAIT*  
║  
║  ⏳ Not the right time yet
║  🔍 Confidence: {confidence:.0f}%
╚══════════════════════════════════╝"""
    else:
        verdict_box = f"""
╔══════════════════════════════════╗
║  🔴 *{symbol}* - *AVOID*  
║  
║  ❌ Conditions are unfavorable
║  ⚠️ Confidence: {confidence:.0f}%
╚══════════════════════════════════╝"""
    
    message = verdict_box + f"""

💰 *Price:* Rs {format_number(price)}
🛡️ *Safety:* {safety_emoji} ({safety_rating})

"""
    
    # =========================================================================
    # DECISION BREAKDOWN - WHY THIS RECOMMENDATION?
    # =========================================================================
    
    message += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 *WHY THIS RECOMMENDATION?*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    # Trend Section
    message += f"*📈 TREND ANALYSIS* ({trend_score}/3 bullish)\n"
    for emoji, factor, meaning in trend_factors:
        message += f"   {emoji} {factor}\n      ↳ _{meaning}_\n"
    message += "\n"
    
    # Momentum Section
    message += f"*⚡ MOMENTUM* ({momentum_score}/3 bullish)\n"
    for emoji, factor, meaning in momentum_factors:
        message += f"   {emoji} {factor}\n      ↳ _{meaning}_\n"
    message += "\n"
    
    # Volume Section
    message += f"*📊 VOLUME* ({volume_score}/1 bullish)\n"
    for emoji, factor, meaning in volume_factors:
        message += f"   {emoji} {factor}\n      ↳ _{meaning}_\n"
    message += "\n"
    
    # Pattern Section
    if pattern_factors:
        message += f"*🔮 CHART PATTERNS* ({pattern_score}/3 bullish)\n"
        for emoji, factor, meaning in pattern_factors:
            message += f"   {emoji} {factor}\n      ↳ _{meaning}_\n"
        
        # Add conflict warning if needed
        if strongest_pattern and hasattr(strongest_pattern, 'type'):
            try:
                pattern_type = strongest_pattern.type.value if hasattr(strongest_pattern.type, 'value') else str(strongest_pattern.type)
                pattern_bullish = pattern_type == 'bullish'
            except Exception:
                pattern_bullish = False
            if pattern_bullish and rec_type in ['SELL', 'BLOCKED']:
                message += "\n   ⚠️ *CONFLICT:* Pattern says BUY but other factors say AVOID\n"
                message += "   _Wait for trend to confirm the pattern_\n"
            elif not pattern_bullish and rec_type == 'BUY':
                message += "\n   ⚠️ *CAUTION:* Pattern is bearish - use tight stop loss\n"
        message += "\n"
    
    # Risk Section
    message += f"*⚖️ RISK ASSESSMENT*\n"
    for emoji, factor, meaning in risk_factors:
        message += f"   {emoji} {factor}\n      ↳ _{meaning}_\n"
    message += "\n"
    
    # =========================================================================
    # OVERALL SCORE
    # =========================================================================
    
    # Visual score bar
    filled = int(score_pct / 10)
    empty = 10 - filled
    score_bar = "🟢" * filled + "⚫" * empty
    
    message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 *OVERALL SCORE*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{score_bar} {total_bullish}/{max_score}
_Individual factors score (trend, momentum, volume, patterns, risk)_

"""
    
    # Score label should respect the actual recommendation
    # If blocked or AVOID recommendation, don't show "STRONG BUY CONDITIONS"
    is_blocked = analysis.get('is_buy_blocked', False) or analysis.get('is_sell_blocked', False)
    
    if is_blocked:
        # Hard filter blocked this trade
        message += "🚫 *BLOCKED BY SAFETY FILTERS*\n"
        message += "_Despite good scores, risk factors prevent entry_\n"
    elif rec_type == 'BLOCKED':
        message += "🚫 *BLOCKED BY SAFETY FILTERS*\n"
        message += "_High-risk conditions detected_\n"
    elif rec_type == 'BUY':
        # For BUY recommendations, show confidence-based label
        if score_pct >= 70:
            message += "✅ *STRONG BUY CONDITIONS*\n"
            message += "_Most indicators are bullish_\n"
        elif score_pct >= 50:
            message += "🟡 *MODERATE BUY CONDITIONS*\n"
            message += "_Mixed signals, proceed with caution_\n"
        else:
            message += "⚠️ *WEAK BUY CONDITIONS*\n"
            message += "_Few bullish signals, higher risk_\n"
    elif rec_type == 'HOLD':
        message += "⏸️ *NEUTRAL CONDITIONS*\n"
        message += "_Not enough conviction to buy or sell_\n"
    elif rec_type == 'SELL':
        if score_pct <= 30:
            message += "❌ *STRONG SELL CONDITIONS*\n"
            message += "_Most indicators are bearish_\n"
        else:
            message += "⚠️ *SELL CONDITIONS*\n"
            message += "_Bearish signals detected_\n"
    else:
        # Default AVOID case
        if score_pct >= 70:
            message += "⚠️ *CONFLICTING SIGNALS*\n"
            message += "_Good scores but blocked by risk filters_\n"
        elif score_pct >= 50:
            message += "🟡 *MODERATE - Proceed with caution*\n"
            message += "_Mixed conditions, wait for clarity_\n"
        elif score_pct >= 30:
            message += "⚠️ *WEAK - High risk*\n"
            message += "_Mostly bearish signals_\n"
        else:
            message += "❌ *AVOID - Unfavorable conditions*\n"
            message += "_Strong bearish indicators_\n"
    
    # =========================================================================
    # ACTION PLAN
    # =========================================================================
    
    message += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 *YOUR ACTION PLAN*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    if rec_type == 'BUY':
        message += f"""✅ *RECOMMENDED: BUY*

*Entry:* Rs {format_number(price)} (current price)
*Target:* Rs {format_number(target)} (+{profit_pct:.1f}%)
*Stop Loss:* Rs {format_number(stop)} (-{loss_pct:.1f}%)

"""
        # Show timeline based on selected horizon
        selected_horizon = analysis.get('horizon', '3months')
        horizon_name = target_data.get('horizon_targets', {}).get(selected_horizon, {}).get('horizon_name', '3 Months')
        recommended_timeframe = target_data.get('recommended_timeframe', 90)
        
        message += f"*Investment Horizon:* {horizon_name} (~{recommended_timeframe} days)\n"
        message += f"_Target based on your selected timeframe_\n\n"
        
        if time_estimate and time_estimate.get('estimated_date'):
            from datetime import datetime
            est_date = time_estimate.get('estimated_date')
            if isinstance(est_date, datetime):
                message += f"*Estimated Target Date:* {est_date.strftime('%d %b %Y')}\n\n"
        
        message += f"""*Example with Rs 10,000:*
   Buy {shares} shares @ Rs {format_number(price)}
   ✅ Profit if target hit: Rs {format_number(potential_profit)} (+{profit_pct:.1f}%)
   ❌ Loss if stop hit: Rs {format_number(potential_loss)} (-{loss_pct:.1f}%)
"""
    elif rec_type == 'HOLD':
        support = indicators.get('support', price * 0.95)
        message += f"""⏳ *RECOMMENDED: WAIT*

*Do not buy now.* Wait for:
   • Price to drop to Rs {format_number(support)} (better entry)
   • OR trend to strengthen

*Check again in:* 1-2 weeks
"""
    else:
        message += f"""❌ *RECOMMENDED: AVOID*

*Do not buy this stock now.*

*Why to avoid:*
"""
        # Show key reasons
        if analysis.get('buy_block_reasons'):
            for reason in analysis['buy_block_reasons'][:3]:
                message += f"   • {reason}\n"
        else:
            if 'downtrend' in indicators['market_phase']:
                message += "   • Stock is in a downtrend\n"
            if trend_score == 0:
                message += "   • All trend indicators are bearish\n"
            if not rr_valid:
                message += "   • Risk/reward ratio is unfavorable\n"
        
        message += f"""
*When conditions might improve:*
   • When trend turns upward
   • When RSI shows oversold (below 30)
   • When a bullish pattern confirms

*Check again in:* 2-3 weeks
"""
    
    # =========================================================================
    # INVESTMENT HORIZONS - Show ALL opportunities
    # =========================================================================
    
    horizon_targets = target_data.get('horizon_targets', {})
    if horizon_targets and rec_type == 'BUY':
        message += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 *TARGETS BY INVESTMENT HORIZON*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_Opportunities across different timeframes_

"""
        # Sort horizons by timeframe (shortest to longest)
        sorted_horizons = sorted(
            horizon_targets.items(),
            key=lambda x: x[1]['timeframe']
        )
        
        for horizon_key, horizon_data in sorted_horizons:
            emoji = horizon_data['emoji']
            name = horizon_data['horizon_name']
            target_price = horizon_data['target']
            target_pct = horizon_data['target_pct']
            days = horizon_data['timeframe']
            is_recommended = horizon_data['is_recommended']
            
            recommended_tag = " ⭐ *RECOMMENDED*" if is_recommended else ""
            
            message += f"{emoji} *{name}* (~{days} days){recommended_tag}\n"
            message += f"   Target: Rs {format_number(target_price)} (+{target_pct:.1f}%)\n"
            
            if is_recommended:
                message += f"   _Your selected investment period_\n"
            
            message += "\n"
        
        message += "_All targets shown - pick your preferred timeline_\n\n"
    
    # =========================================================================
    # PATTERN-BASED TARGET (Industry Standard Measured Move)
    # =========================================================================
    
    if target_data.get('has_pattern_target') and rec_type == 'BUY':
        pattern_name = target_data.get('pattern_name', 'Unknown')
        pattern_target = target_data.get('pattern_target')
        pattern_target_pct = target_data.get('pattern_target_pct', 0)
        pattern_reliability = target_data.get('pattern_reliability', 0)
        pattern_horizon = target_data.get('pattern_horizon')
        pattern_invalidation = target_data.get('pattern_invalidation')
        pattern_min_days = target_data.get('pattern_min_days', 0)
        pattern_max_days = target_data.get('pattern_max_days', 0)
        
        reliability_pct = int((pattern_reliability or 0) * 100)
        reliability_stars = '⭐' * min(5, max(1, reliability_pct // 20))
        
        message += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 *PATTERN-BASED TARGET*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_Industry-standard measured move calculation_

"""
        message += f"*Pattern:* {pattern_name}\n"
        message += f"*Reliability:* {reliability_pct}% {reliability_stars}\n\n"
        
        if pattern_target:
            message += f"📎 *Measured Move Target:* Rs {format_number(pattern_target)} (+{pattern_target_pct:.1f}%)\n"
        
        if pattern_invalidation:
            message += f"🚫 *Pattern Invalid If:* Price drops below Rs {format_number(pattern_invalidation)}\n"
        
        if pattern_horizon:
            from src.core.config import INVESTMENT_HORIZONS
            horizon_info = INVESTMENT_HORIZONS.get(pattern_horizon, {})
            display_name = horizon_info.get('display_name', pattern_horizon)
            message += f"⏱️ *Expected Timeframe:* {display_name} ({pattern_min_days}-{pattern_max_days} days)\n"
        
        # Add pattern-horizon mismatch warning if exists
        if target_data.get('pattern_horizon_warning'):
            message += f"\n⚠️ *Notice:* {target_data['pattern_horizon_warning']}\n"
        
        message += "\n"
        message += "_Pattern targets are based on classical technical analysis_\n"
        message += "_Measured move = pattern height projected from breakout_\n\n"
    
    # =========================================================================
    # KEY PRICE LEVELS
    # =========================================================================
    
    support = indicators.get('support', price * 0.95)
    resistance = indicators.get('resistance', price * 1.05)
    
    message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 *KEY PRICE LEVELS*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current: Rs {format_number(price)}
         │
🔺 Resistance: Rs {format_number(resistance)} (+{((resistance-price)/price)*100:.1f}%)
         │  ↑ Price may struggle here
         │
🔻 Support: Rs {format_number(support)} ({((support-price)/price)*100:.1f}%)
            ↓ Price may bounce here

"""
    
    # =========================================================================
    # FOOTER
    # =========================================================================
    
    message += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *DISCLAIMER*
This is educational analysis, not financial advice.
Always do your own research. Past performance
doesn't guarantee future results.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_Stock Analyzer Pro by Harsh Kandhway_
"""
    
    return message.strip()


def format_quick_recommendation(analysis: Dict[str, Any]) -> str:
    """
    Format a quick recommendation message (very short).
    
    Args:
        analysis: Analysis dictionary
    
    Returns:
        Short recommendation message
    """
    symbol = analysis['symbol']
    price = analysis['current_price']
    recommendation = analysis['recommendation']
    rec_type = analysis['recommendation_type']
    confidence = analysis['confidence']
    
    safety = analysis.get('safety_score', {})
    target = analysis.get('target', price * 1.05)
    stop = analysis.get('stop_loss', price * 0.95)
    
    target_pct = ((target - price) / price) * 100
    stop_pct = ((price - stop) / price) * 100
    
    # Emoji
    if rec_type == 'BUY':
        emoji = "🟢"
    elif rec_type == 'SELL':
        emoji = "🔴"
    elif rec_type == 'BLOCKED':
        emoji = "⛔"
    else:
        emoji = "🟡"
    
    safety_stars = '⭐' * safety.get('stars', 3)
    
    message = f"""
{emoji} *{symbol}* @ Rs {format_number(price)}

*{recommendation}* ({confidence:.0f}%)
Safety: {safety_stars}

🎯 Target: Rs {format_number(target)} (+{target_pct:.1f}%)
🛡️ Stop: Rs {format_number(stop)} (-{stop_pct:.1f}%)
"""
    
    return message.strip()


def format_investment_guidance(analysis: Dict[str, Any], capital: float = 100000) -> str:
    """
    Format detailed investment guidance with position sizing.
    
    Args:
        analysis: Analysis dictionary
        capital: User's capital
    
    Returns:
        Formatted guidance message
    """
    symbol = analysis['symbol']
    price = analysis['current_price']
    target = analysis.get('target', price * 1.05)
    stop = analysis.get('stop_loss', price * 0.95)
    risk_reward = analysis.get('risk_reward', 1.0)
    rec_type = analysis['recommendation_type']
    
    # Position sizing
    risk_per_trade = 0.01  # 1% risk
    risk_amount = capital * risk_per_trade
    stop_distance = price - stop
    
    if stop_distance > 0:
        shares = int(risk_amount / stop_distance)
    else:
        shares = int(capital * 0.1 / price)  # 10% of capital
    
    investment = shares * price
    potential_profit = shares * (target - price)
    potential_loss = shares * stop_distance if stop_distance > 0 else shares * price * 0.05
    
    message = f"""
💼 *INVESTMENT GUIDANCE FOR {symbol}*
━━━━━━━━━━━━━━━━━━━━

💰 *Your Capital:* Rs {capital:,.0f}

📊 *Recommended Position:*
   Buy: {shares} shares
   Investment: Rs {investment:,.0f} ({investment/capital*100:.1f}% of capital)
   
   Entry: Rs {format_number(price)}
   Target: Rs {format_number(target)}
   Stop Loss: Rs {format_number(stop)}

💵 *Potential Outcomes:*
   ✅ Profit if target hit: Rs {potential_profit:,.0f}
   ❌ Loss if stop hit: Rs {potential_loss:,.0f}
   
   Risk/Reward: {format_number(risk_reward, 2)}:1

⚠️ *IMPORTANT:*
   • Never invest more than you can afford to lose
   • Always set a stop loss
   • Don't put all money in one stock
━━━━━━━━━━━━━━━━━━━━
"""
    
    return message.strip()
