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
    
    message += "\n\n"
    
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


def format_watchlist(watchlist: List[Dict], show_details: bool = False) -> str:
    """
    Format watchlist for display
    
    Args:
        watchlist: List of watchlist items (dict with symbol, added_at, etc.)
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
        symbol = item['symbol']
        added_at = item.get('added_at')
        notes = item.get('notes')
        
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
    Format analysis result in beginner-friendly format with clear guidance.
    
    Args:
        analysis: Analysis dictionary from analysis_service
        horizon: Investment horizon
    
    Returns:
        Formatted beginner-friendly analysis string
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
    
    # Safety score
    safety = analysis.get('safety_score', {})
    time_estimate = analysis.get('time_estimate', {})
    
    # Recommendation emoji and text
    if rec_type == 'BUY':
        rec_emoji = "🟢"
        action_text = "Good opportunity to invest"
        timing_text = "Buy within this week"
    elif rec_type == 'SELL':
        rec_emoji = "🔴"
        action_text = "Not recommended to buy"
        timing_text = "Wait for better conditions"
    elif rec_type == 'BLOCKED':
        rec_emoji = "⛔"
        action_text = "Avoid this stock for now"
        timing_text = "Wait until conditions improve"
    else:
        rec_emoji = "🟡"
        action_text = "Wait for clearer signals"
        timing_text = "Check again in 1-2 weeks"
    
    # Calculate profit/loss (example with Rs 10,000)
    example_capital = 10000
    shares = int(example_capital / price)
    target = target_data['recommended_target']
    stop = stop_data['recommended_stop']
    
    potential_profit = shares * (target - price)
    potential_loss = shares * (price - stop)
    profit_pct = ((target - price) / price) * 100
    loss_pct = ((price - stop) / price) * 100
    
    # Safety rating
    safety_stars = safety.get('stars', 3)
    safety_emoji = '⭐' * safety_stars
    safety_rating = safety.get('rating', 'MODERATE')
    
    message = f"""
{'='*35}
{EMOJI['chart']} *{symbol}*
{'='*35}

{rec_emoji} *{recommendation}*
_{action_text}_

━━━━━━━━━━━━━━━━━━━━

💰 *Current Price:* {CURRENCY_SYMBOL}{format_number(price)}

🛡️ *Safety Rating:* {safety_emoji}
   {safety_rating}

━━━━━━━━━━━━━━━━━━━━

📋 *WHAT TO DO*
━━━━━━━━━━━━━━━━━━━━
"""
    
    if rec_type == 'BUY':
        message += f"""
✅ *BUY NOW* at Rs {format_number(price)}
   Set these price alerts:

🎯 *Sell for Profit:* Rs {format_number(target)} (+{profit_pct:.1f}%)
🛡️ *Stop Loss:* Rs {format_number(stop)} (-{loss_pct:.1f}%)
"""
    elif rec_type == 'HOLD':
        message += f"""
⏳ *WAIT* - Don't buy yet
   Look for price to drop to Rs {format_number(indicators.get('support', price * 0.95))}
"""
    else:
        message += f"""
❌ *AVOID* - Not a good time
   Wait until trend improves
"""
    
    # Time estimate
    if time_estimate:
        est_date = time_estimate.get('estimated_date')
        if est_date:
            from datetime import datetime
            if isinstance(est_date, datetime):
                message += f"""
📅 *Expected Timeline:* ~{time_estimate.get('trading_days', '?')} trading days
   Target by: {est_date.strftime('%d %b %Y')}
"""
    
    # Profit/Loss example
    message += f"""
━━━━━━━━━━━━━━━━━━━━

💵 *Example: Rs 10,000 Investment*
━━━━━━━━━━━━━━━━━━━━
   Buy: {shares} shares @ Rs {format_number(price)}
   
   ✅ If target reached:
      Profit: Rs {format_number(potential_profit)} (+{profit_pct:.1f}%)
   
   ❌ If stop loss hits:
      Loss: Rs {format_number(potential_loss)} (-{loss_pct:.1f}%)
   
   ⚖️ Risk/Reward: {format_number(risk_reward, 2)}:1
"""
    
    if rr_valid:
        message += "   ✅ Good ratio\n"
    else:
        message += "   ⚠️ Below minimum\n"
    
    # Market conditions summary
    phase = indicators['market_phase'].replace('_', ' ').title()
    
    if 'uptrend' in indicators['market_phase']:
        trend_emoji = "📈"
        trend_text = "Moving UP"
    elif 'downtrend' in indicators['market_phase']:
        trend_emoji = "📉"
        trend_text = "Moving DOWN"
    else:
        trend_emoji = "↔️"
        trend_text = "Moving SIDEWAYS"
    
    message += f"""
━━━━━━━━━━━━━━━━━━━━

{EMOJI['info']} *MARKET CONDITIONS*
━━━━━━━━━━━━━━━━━━━━
{trend_emoji} Trend: {trend_text}
📊 Strength: {indicators['adx_strength'].replace('_', ' ').title()}
📈 Momentum: {indicators['rsi_zone'].replace('_', ' ').title()}

━━━━━━━━━━━━━━━━━━━━
"""
    
    # Checklist
    checks_passed = 0
    total_checks = 5
    
    if indicators['price_vs_trend_ema'] == 'above':
        checks_passed += 1
    if 30 <= indicators['rsi'] <= 70:
        checks_passed += 1
    if indicators['adx'] >= 25:
        checks_passed += 1
    if indicators['volume_ratio'] >= 0.7:
        checks_passed += 1
    if risk_reward >= 2:
        checks_passed += 1
    
    message += f"""
✅ *CHECKLIST:* {checks_passed}/{total_checks} passed
"""
    
    if checks_passed >= 4:
        message += "   Good investment opportunity!\n"
    elif checks_passed >= 3:
        message += "   Moderate - proceed with caution\n"
    else:
        message += "   Not recommended at this time\n"
    
    message += f"""
{'='*35}
_Developed by Harsh Kandhway_
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
