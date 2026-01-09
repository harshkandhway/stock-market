"""
Core Formatters Module for Stock Analyzer Pro
Single comprehensive formatter for all analysis output (CLI and Bot)

Consolidates all formatting logic into one place with:
- All 16 sections always included
- No conditional logic based on user preferences
- Output mode parameter for bot vs CLI formatting
- Zero information loss from previous formatters

Author: Harsh Kandhway
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Import config from both bot and core
try:
    from src.bot.config import EMOJI, MAX_MESSAGE_LENGTH, CURRENCY_SYMBOL as BOT_CURRENCY
    from src.core.config import (
        CURRENCY_SYMBOL, REPORT_WIDTH, INVESTMENT_HORIZONS,
        ACTION_RECOMMENDATIONS, get_expected_dates
    )
except ImportError:
    # Fallback if imports fail
    EMOJI = {}
    MAX_MESSAGE_LENGTH = 4096
    CURRENCY_SYMBOL = '₹'
    BOT_CURRENCY = '₹'
    REPORT_WIDTH = 80
    INVESTMENT_HORIZONS = {}
    ACTION_RECOMMENDATIONS = {}

    def get_expected_dates(horizon):
        from datetime import datetime, timedelta
        today = datetime.now()
        return {
            'buy_date': today,
            'expected_sell_date': today + timedelta(days=90),
            'min_sell_date': today + timedelta(days=30),
            'max_sell_date': today + timedelta(days=180)
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_emoji(name: str, output_mode: str) -> str:
    """
    Get emoji for bot mode or ASCII equivalent for CLI mode

    Args:
        name: Emoji name (check, cross, warning, etc.)
        output_mode: 'bot' or 'cli'

    Returns:
        Emoji for bot, ASCII for CLI
    """
    # Emoji mappings
    emoji_map = {
        # Basic indicators
        'check': ('✅', '[Y]'),
        'cross': ('❌', '[X]'),
        'warning': ('⚠️', '[!]'),
        'neutral': ('⚪', '[?]'),

        # Arrows and indicators
        'up': ('📈', '[UP]'),
        'down': ('📉', '[DOWN]'),
        'arrow': ('→', '->'),
        'bullet': ('•', '*'),

        # Financial
        'money': ('💰', '$'),
        'profit': ('💰', '[+]'),
        'loss': ('📉', '[-]'),
        'target': ('🎯', '[TARGET]'),
        'stop': ('🛡️', '[STOP]'),

        # Symbols
        'star': ('⭐', '*'),
        'star_empty': ('☆', 'o'),
        'blocked': ('🚫', '[BLOCKED]'),
        'success': ('✅', '[OK]'),
        'error': ('❌', '[ERR]'),

        # Chart/Analysis
        'chart': ('📊', '[CHART]'),
        'analyze': ('🔍', '[ANALYZE]'),
        'info': ('ℹ️', '[INFO]'),
        'compare': ('⚖️', '[COMPARE]'),

        # Actions
        'buy': ('🟢', '[BUY]'),
        'sell': ('🔴', '[SELL]'),
        'hold': ('🟡', '[HOLD]'),

        # Other
        'loading': ('⏳', '[...]'),
        'watchlist': ('👁️', '[WATCH]'),
        'portfolio': ('💼', '[PORTFOLIO]'),
        'alert': ('🔔', '[ALERT]'),
    }

    emoji, ascii_equiv = emoji_map.get(name, ('', ''))
    return emoji if output_mode == 'bot' else ascii_equiv


def _format_box_top(width: int, output_mode: str, style: str = 'double') -> str:
    """
    Format box top/bottom line

    Args:
        width: Width of the box
        output_mode: 'bot' or 'cli'
        style: 'double' or 'single'

    Returns:
        Box line string
    """
    if output_mode == 'bot':
        char = '━' if style == 'double' else '─'
        return char * width
    else:
        char = '=' if style == 'double' else '-'
        return char * width


def _format_section_header(title: str, output_mode: str) -> str:
    """
    Format section header

    Args:
        title: Section title
        output_mode: 'bot' or 'cli'

    Returns:
        Formatted header string
    """
    if output_mode == 'bot':
        return f"\n*{title}*\n"
    else:
        width = 60
        return f"\n{'='*width}\n  {title}\n{'='*width}\n"


def _format_progress_bar(score: int, max_score: int, output_mode: str) -> str:
    """
    Format visual progress bar

    Args:
        score: Current score
        max_score: Maximum possible score
        output_mode: 'bot' or 'cli'

    Returns:
        Progress bar string
    """
    percentage = (score / max_score * 100) if max_score > 0 else 0
    filled = int(percentage / 10)
    empty = 10 - filled

    if output_mode == 'bot':
        return "🟢" * filled + "⚫" * empty
    else:
        return "[" + "#" * filled + "." * empty + "]"


def format_number(value: float, decimals: int = 2) -> str:
    """Format number with proper decimals and thousand separators"""
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2, show_sign: bool = True) -> str:
    """Format percentage value"""
    if value is None:
        return "N/A"

    sign = '+' if value > 0 and show_sign else ''
    return f"{sign}{value:.{decimals}f}%"


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2
    Only used in bot mode
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def chunk_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Split long message into chunks for Telegram's 4096 byte limit
    Used only in bot mode

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


# ============================================================================
# MAIN COMPREHENSIVE FORMATTER
# ============================================================================

def format_analysis_comprehensive(
    analysis: Dict[str, Any],
    output_mode: str = 'bot',
    capital: Optional[float] = None,
    horizon: str = '3months'
) -> str:
    """
    Single comprehensive formatter for all analysis output.
    Includes ALL 16 sections from all previous formatters.
    No conditional logic - always shows complete analysis.

    Sections:
    1. Header & Quick Verdict
    2. Decision Breakdown - WHY?
    3. Action Plan
    4. Targets by Investment Horizon
    5. Pattern-Based Target (if pattern exists)
    6. Key Price Levels
    7. Market Conditions
    8. Technical Indicators Detail
    9. Chart Patterns
    10. Investment Checklist
    11. Position Sizing Guidance
    12. When to Sell
    13. Safety & Risk Summary
    14. Timeline Estimate
    15. Footer

    Args:
        analysis: Analysis dictionary from analysis_service
        output_mode: 'bot' (emojis, MarkdownV2) or 'cli' (ASCII, plain text)
        capital: User's capital for position sizing (optional, defaults to 10000 example)
        horizon: Investment horizon ('1week', '3months', etc.)

    Returns:
        Formatted analysis string ready for display
    """
    # Extract data from analysis
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

    # Safety score and time estimate
    safety = analysis.get('safety_score', {})
    time_estimate = analysis.get('time_estimate', {})

    # Calculate values for examples
    if capital is None:
        capital = 10000  # Default example capital

    shares = max(1, int(capital / price))
    target = target_data['recommended_target']
    stop = stop_data['recommended_stop']

    profit_pct = ((target - price) / price) * 100
    loss_pct = ((price - stop) / price) * 100
    potential_profit = shares * (target - price)
    potential_loss = shares * (price - stop)

    # Safety rating
    safety_stars = safety.get('stars', 3)
    if output_mode == 'bot':
        safety_emoji = '⭐' * safety_stars + '☆' * (5 - safety_stars)
    else:
        safety_emoji = '*' * safety_stars + 'o' * (5 - safety_stars)
    safety_rating = safety.get('rating', 'MODERATE')

    # Mode for R/R thresholds
    mode = analysis.get('mode', 'moderate')
    rr_thresholds = {
        'conservative': 3.0,
        'moderate': 2.0,
        'balanced': 2.0,
        'aggressive': 1.5
    }
    min_rr = rr_thresholds.get(mode, 2.0)

    # =========================================================================
    # BUILD THE DECISION SCORECARD
    # =========================================================================

    # Trend Analysis (score out of 3)
    trend_score = 0
    trend_factors = []

    if indicators['price_vs_trend_ema'] == 'above':
        trend_score += 1
        trend_factors.append((
            _get_emoji('check', output_mode),
            "Price above long-term average",
            "Bullish"
        ))
    else:
        trend_factors.append((
            _get_emoji('cross', output_mode),
            "Price below long-term average",
            "Bearish"
        ))

    if 'uptrend' in indicators['market_phase']:
        trend_score += 1
        trend_factors.append((
            _get_emoji('check', output_mode),
            f"Market in {indicators['market_phase'].replace('_', ' ')}",
            "Bullish"
        ))
    elif 'downtrend' in indicators['market_phase']:
        trend_factors.append((
            _get_emoji('cross', output_mode),
            f"Market in {indicators['market_phase'].replace('_', ' ')}",
            "Bearish"
        ))
    else:
        trend_factors.append((
            _get_emoji('neutral', output_mode),
            "Market moving sideways",
            "Neutral"
        ))

    ema_alignment = indicators.get('ema_alignment', 'mixed')
    if ema_alignment in ['strong_bullish', 'bullish']:
        trend_score += 1
        trend_factors.append((
            _get_emoji('check', output_mode),
            "All moving averages aligned UP",
            "Strong signal"
        ))
    elif ema_alignment in ['strong_bearish', 'bearish']:
        trend_factors.append((
            _get_emoji('cross', output_mode),
            "All moving averages aligned DOWN",
            "Weak signal"
        ))
    else:
        trend_factors.append((
            _get_emoji('neutral', output_mode),
            "Moving averages mixed",
            "No clear signal"
        ))

    # Momentum Analysis (score out of 3)
    momentum_score = 0
    momentum_factors = []

    rsi = indicators['rsi']
    rsi_zone = indicators['rsi_zone']
    if rsi_zone in ['oversold', 'extremely_oversold']:
        momentum_score += 1
        momentum_factors.append((
            _get_emoji('check', output_mode),
            f"RSI at {rsi:.0f} (Oversold)",
            "May bounce up soon"
        ))
    elif rsi_zone in ['overbought', 'extremely_overbought']:
        momentum_factors.append((
            _get_emoji('cross', output_mode),
            f"RSI at {rsi:.0f} (Overbought)",
            "May fall soon"
        ))
    else:
        momentum_factors.append((
            _get_emoji('neutral', output_mode),
            f"RSI at {rsi:.0f} (Neutral)",
            "No extreme"
        ))

    macd_hist = indicators.get('macd_hist', 0)
    if macd_hist > 0:
        momentum_score += 1
        momentum_factors.append((
            _get_emoji('check', output_mode),
            "MACD positive",
            "Upward momentum"
        ))
    else:
        momentum_factors.append((
            _get_emoji('cross', output_mode),
            "MACD negative",
            "Downward momentum"
        ))

    adx = indicators['adx']
    if adx >= 25:
        momentum_score += 1
        momentum_factors.append((
            _get_emoji('check', output_mode),
            f"ADX at {adx:.0f} (Strong trend)",
            "Trend is reliable"
        ))
    else:
        momentum_factors.append((
            _get_emoji('warning', output_mode),
            f"ADX at {adx:.0f} (Weak trend)",
            "Trend may reverse"
        ))

    # Volume Analysis (score out of 1)
    volume_score = 0
    volume_factors = []

    vol_ratio = indicators.get('volume_ratio', 1.0)
    if vol_ratio >= 1.5:
        volume_score += 1
        volume_factors.append((
            _get_emoji('check', output_mode),
            f"Volume {vol_ratio:.1f}x average",
            "High interest"
        ))
    elif vol_ratio >= 0.8:
        volume_factors.append((
            _get_emoji('neutral', output_mode),
            f"Volume {vol_ratio:.1f}x average",
            "Normal activity"
        ))
    else:
        volume_factors.append((
            _get_emoji('cross', output_mode),
            f"Volume {vol_ratio:.1f}x average",
            "Low interest"
        ))

    # Chart Pattern Analysis (score out of 3)
    pattern_score = 0
    pattern_factors = []

    strongest_pattern = indicators.get('strongest_pattern')
    pattern_bias = indicators.get('pattern_bias', 'neutral')

    if strongest_pattern and hasattr(strongest_pattern, 'type'):
        try:
            pattern_type = strongest_pattern.type.value if hasattr(strongest_pattern.type, 'value') else str(strongest_pattern.type)
            pattern_name = getattr(strongest_pattern, 'name', 'Unknown Pattern')
            pattern_conf = getattr(strongest_pattern, 'confidence', 0)
            pattern_action = getattr(strongest_pattern, 'action', 'No action')

            if pattern_type == 'bullish':
                pattern_score += 2
                pattern_factors.append((
                    _get_emoji('check', output_mode),
                    f"{pattern_name} ({pattern_conf}%)",
                    pattern_action
                ))
            elif pattern_type == 'bearish':
                pattern_factors.append((
                    _get_emoji('cross', output_mode),
                    f"{pattern_name} ({pattern_conf}%)",
                    pattern_action
                ))
            else:
                pattern_factors.append((
                    _get_emoji('neutral', output_mode),
                    f"{pattern_name} ({pattern_conf}%)",
                    "Neutral pattern"
                ))
        except Exception:
            pattern_factors.append((
                _get_emoji('neutral', output_mode),
                "Pattern detected",
                "Check chart"
            ))

    if pattern_bias == 'bullish':
        pattern_score += 1

    # Risk Analysis (score out of 2)
    risk_score = 0
    risk_factors = []

    if rr_valid:
        risk_score += 1
        risk_factors.append((
            _get_emoji('check', output_mode),
            f"Risk/Reward {risk_reward:.1f}:1",
            f"Meets minimum {min_rr:.1f}:1 for {mode} mode"
        ))
    else:
        risk_factors.append((
            _get_emoji('cross', output_mode),
            f"Risk/Reward {risk_reward:.1f}:1",
            f"Below minimum {min_rr:.1f}:1 for {mode} mode"
        ))

    # Volume for risk
    if vol_ratio >= 1.0:
        risk_score += 1

    # Check for blocks
    is_blocked = analysis.get('is_buy_blocked', False)
    if is_blocked:
        block_reason = analysis.get('buy_block_reasons', ['Risk too high'])[0] if analysis.get('buy_block_reasons') else 'Risk too high'
        risk_factors.append((
            _get_emoji('blocked', output_mode),
            "Hard filter triggered",
            block_reason
        ))

    # Calculate total score
    total_bullish = trend_score + momentum_score + volume_score + pattern_score + risk_score
    max_score = 10
    score_pct = (total_bullish / max_score) * 100

    # =========================================================================
    # START BUILDING THE MESSAGE
    # =========================================================================

    message = ""

    # =========================================================================
    # SECTION 1: HEADER & QUICK VERDICT
    # =========================================================================

    if output_mode == 'bot':
        # Bot-style header with box drawing
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

        message += verdict_box + f"""

💰 *Price:* Rs {format_number(price)}
🛡️ *Safety:* {safety_emoji} ({safety_rating})

"""
    else:
        # CLI-style header with ASCII
        box_width = 60
        if rec_type == 'BUY':
            message += f"\n{'='*box_width}\n"
            message += f"  [BUY] {symbol} - GOOD OPPORTUNITY\n"
            message += f"  Confidence: {confidence:.0f}%\n"
            message += f"{'='*box_width}\n"
        elif rec_type == 'HOLD':
            message += f"\n{'='*box_width}\n"
            message += f"  [WAIT] {symbol} - NOT THE RIGHT TIME\n"
            message += f"  Confidence: {confidence:.0f}%\n"
            message += f"{'='*box_width}\n"
        else:
            message += f"\n{'='*box_width}\n"
            message += f"  [AVOID] {symbol} - UNFAVORABLE CONDITIONS\n"
            message += f"  Confidence: {confidence:.0f}%\n"
            message += f"{'='*box_width}\n"

        message += f"\nPrice: Rs {format_number(price)}\n"
        message += f"Safety: {safety_emoji} ({safety_rating})\n"

    # =========================================================================
    # SECTION 2: DECISION BREAKDOWN - WHY THIS RECOMMENDATION?
    # =========================================================================

    message += _format_section_header("WHY THIS RECOMMENDATION?", output_mode)

    # Trend Section
    if output_mode == 'bot':
        message += f"*📈 TREND ANALYSIS* ({trend_score}/3 bullish)\n"
        for emoji, factor, meaning in trend_factors:
            message += f"\n   {emoji} {factor}\n      ↳ _{meaning}_"
        message += "\n\n"
    else:
        message += f"\n[TREND ANALYSIS] ({trend_score}/3 bullish)\n"
        message += f"{'-'*50}\n"
        for emoji, factor, meaning in trend_factors:
            message += f"\n  {emoji} {factor}\n       -> {meaning}"
        message += "\n\n"

    # Momentum Section
    if output_mode == 'bot':
        message += f"*⚡ MOMENTUM* ({momentum_score}/3 bullish)\n"
        for emoji, factor, meaning in momentum_factors:
            message += f"\n   {emoji} {factor}\n      ↳ _{meaning}_"
        message += "\n\n"
    else:
        message += f"[MOMENTUM] ({momentum_score}/3 bullish)\n"
        message += f"{'-'*50}\n"
        for emoji, factor, meaning in momentum_factors:
            message += f"\n  {emoji} {factor}\n       -> {meaning}"
        message += "\n\n"

    # Volume Section
    if output_mode == 'bot':
        message += f"*📊 VOLUME* ({volume_score}/1 bullish)\n"
        for emoji, factor, meaning in volume_factors:
            message += f"\n   {emoji} {factor}\n      ↳ _{meaning}_"
        message += "\n\n"
    else:
        message += f"[VOLUME] ({volume_score}/1 bullish)\n"
        message += f"{'-'*50}\n"
        for emoji, factor, meaning in volume_factors:
            message += f"\n  {emoji} {factor}\n       -> {meaning}"
        message += "\n\n"

    # Pattern Section (if patterns exist)
    if pattern_factors:
        if output_mode == 'bot':
            message += f"*🔮 CHART PATTERNS* ({pattern_score}/3 bullish)\n"
            for emoji, factor, meaning in pattern_factors:
                message += f"\n   {emoji} {factor}\n      ↳ _{meaning}_"

            # Add conflict warning if needed
            if strongest_pattern and hasattr(strongest_pattern, 'type'):
                try:
                    pattern_type = strongest_pattern.type.value if hasattr(strongest_pattern.type, 'value') else str(strongest_pattern.type)
                    pattern_bullish = pattern_type == 'bullish'
                except Exception:
                    pattern_bullish = False

                if pattern_bullish and rec_type in ['SELL', 'BLOCKED']:
                    message += "\n\n   ⚠️ *CONFLICT:* Pattern says BUY but other factors say AVOID\n"
                    message += "   _Wait for trend to confirm the pattern_"
                elif not pattern_bullish and rec_type == 'BUY':
                    message += "\n\n   ⚠️ *CAUTION:* Pattern is bearish - use tight stop loss"
            message += "\n\n"
        else:
            message += f"[CHART PATTERNS] ({pattern_score}/3 bullish)\n"
            message += f"{'-'*50}\n"
            for emoji, factor, meaning in pattern_factors:
                message += f"\n  {emoji} {factor}\n       -> {meaning}"

            # Conflict warning for CLI
            if strongest_pattern and hasattr(strongest_pattern, 'type'):
                try:
                    pattern_type = strongest_pattern.type.value if hasattr(strongest_pattern.type, 'value') else str(strongest_pattern.type)
                    pattern_bullish = pattern_type == 'bullish'
                except Exception:
                    pattern_bullish = False

                if pattern_bullish and rec_type in ['SELL', 'BLOCKED']:
                    message += "\n\n  [!] CONFLICT: Pattern says BUY but other factors say AVOID\n"
                    message += "      Wait for trend to confirm the pattern"
                elif not pattern_bullish and rec_type == 'BUY':
                    message += "\n\n  [!] CAUTION: Pattern is bearish - use tight stop loss"
            message += "\n\n"

    # Risk Section
    if output_mode == 'bot':
        message += f"*⚖️ RISK ASSESSMENT*\n"
        for emoji, factor, meaning in risk_factors:
            message += f"\n   {emoji} {factor}\n      ↳ _{meaning}_"
        message += "\n\n"
    else:
        message += f"[RISK ASSESSMENT]\n"
        message += f"{'-'*50}\n"
        for emoji, factor, meaning in risk_factors:
            message += f"\n  {emoji} {factor}\n       -> {meaning}"
        message += "\n\n"

    # =========================================================================
    # OVERALL SCORE
    # =========================================================================

    score_bar = _format_progress_bar(total_bullish, max_score, output_mode)

    if output_mode == 'bot':
        message += f"""
📊 *OVERALL SCORE*

{score_bar} {total_bullish}/{max_score}
_Individual factors score (trend, momentum, volume, patterns, risk)_

"""
    else:
        message += f"""{'='*60}
  OVERALL SCORE
{'='*60}
{score_bar} {total_bullish}/{max_score}
(Individual factors: trend, momentum, volume, patterns, risk)

"""

    # Score interpretation
    if is_blocked:
        if output_mode == 'bot':
            message += "🚫 *BLOCKED BY SAFETY FILTERS*\n"
            message += "_Despite good scores, risk factors prevent entry_\n\n"
        else:
            message += "[BLOCKED] BLOCKED BY SAFETY FILTERS\n"
            message += "Despite good scores, risk factors prevent entry\n\n"
    elif rec_type == 'BUY':
        if score_pct >= 70:
            msg_text = "STRONG BUY CONDITIONS" if output_mode == 'cli' else "*STRONG BUY CONDITIONS*"
            detail = "Most indicators are bullish" if output_mode == 'cli' else "_Most indicators are bullish_"
            check_emoji = _get_emoji('check', output_mode)
            message += f"{check_emoji} {msg_text}\n" if output_mode == 'bot' else f"{check_emoji} {msg_text}\n"
            message += f"{detail}\n\n" if output_mode == 'bot' else f"{detail}\n\n"
        elif score_pct >= 50:
            msg_text = "MODERATE BUY CONDITIONS"
            detail = "Mixed signals, proceed with caution"
            if output_mode == 'bot':
                message += f"🟡 *{msg_text}*\n_{detail}_\n\n"
            else:
                message += f"[?] {msg_text}\n{detail}\n\n"
        else:
            msg_text = "WEAK BUY CONDITIONS"
            detail = "Few bullish signals, higher risk"
            warn_emoji = _get_emoji('warning', output_mode)
            message += f"{warn_emoji} {msg_text}\n" if output_mode == 'bot' else f"{warn_emoji} {msg_text}\n"
            message += f"_{detail}_\n\n" if output_mode == 'bot' else f"{detail}\n\n"
            
            # Add strong warning if score is very low
            if score_pct < 30:
                if output_mode == 'bot':
                    message += f"⚠️ *CRITICAL WARNING:* Score is only {total_bullish}/10 ({score_pct:.0f}%).\n"
                    message += f"_This BUY recommendation is based on risk/reward ratio only._\n"
                    message += f"_All technical indicators are bearish. Proceed with extreme caution or wait for better entry._\n\n"
                else:
                    message += f"[!] CRITICAL WARNING: Score is only {total_bullish}/10 ({score_pct:.0f}%).\n"
                    message += f"This BUY recommendation is based on risk/reward ratio only.\n"
                    message += f"All technical indicators are bearish. Proceed with extreme caution or wait for better entry.\n\n"
    elif rec_type == 'HOLD':
        if output_mode == 'bot':
            message += "⏸️ *NEUTRAL CONDITIONS*\n_Not enough conviction to buy or sell_\n\n"
        else:
            message += "[HOLD] NEUTRAL CONDITIONS\nNot enough conviction to buy or sell\n\n"
    else:
        if score_pct <= 30:
            cross_emoji = _get_emoji('cross', output_mode)
            message += f"{cross_emoji} STRONG SELL CONDITIONS\n" if output_mode == 'bot' else f"{cross_emoji} STRONG SELL CONDITIONS\n"
            message += "_Most indicators are bearish_\n\n" if output_mode == 'bot' else "Most indicators are bearish\n\n"
        else:
            warn_emoji = _get_emoji('warning', output_mode)
            message += f"{warn_emoji} AVOID - Unfavorable conditions\n\n" if output_mode == 'bot' else f"{warn_emoji} AVOID - Unfavorable conditions\n\n"

    # Continue with remaining sections in next part...
    # (This is getting long, I'll continue in the actual implementation)

    message += "\n"

    # =========================================================================
    # SECTION 3: ACTION PLAN
    # =========================================================================

    message += _format_section_header("YOUR ACTION PLAN", output_mode)

    if rec_type == 'BUY':
        # Check if this is a WEAK BUY with R:R warning
        is_rr_warning = 'R:R' in recommendation.upper() or 'RISK/REWARD' in recommendation.upper()
        
        if output_mode == 'bot':
            if is_rr_warning:
                message += f"""🟡 *RECOMMENDED: {recommendation}*

⚠️ *Warning:* Risk/Reward is slightly below minimum ({risk_reward:.2f}:1 vs {min_rr:.1f}:1 required)
However, technical indicators are strong ({score_pct:.0f}% score, {confidence:.0f}% confidence)

💡 *Note:* Consider waiting for a better entry or using a tighter stop loss to improve R:R ratio

*Entry:* Rs {format_number(price)} (current price)
*Target:* Rs {format_number(target)} (+{profit_pct:.1f}%)
*Stop Loss:* Rs {format_number(stop)} (-{loss_pct:.1f}%)

"""
            else:
                message += f"""✅ *RECOMMENDED: {recommendation}*

*Entry:* Rs {format_number(price)} (current price)
*Target:* Rs {format_number(target)} (+{profit_pct:.1f}%)
*Stop Loss:* Rs {format_number(stop)} (-{loss_pct:.1f}%)

"""
        else:
            message += f"""[BUY] RECOMMENDED: BUY

Entry: Rs {format_number(price)} (current price)
Target: Rs {format_number(target)} (+{profit_pct:.1f}%)
Stop Loss: Rs {format_number(stop)} (-{loss_pct:.1f}%)

"""

        # Show timeline
        selected_horizon = analysis.get('horizon', '3months')
        horizon_name = target_data.get('horizon_targets', {}).get(selected_horizon, {}).get('horizon_name', '3 Months')
        recommended_timeframe = target_data.get('recommended_timeframe', 90)

        if output_mode == 'bot':
            message += f"*Investment Horizon:* {horizon_name} (~{recommended_timeframe} days)\n"
            message += f"_Target based on your selected timeframe_\n\n"
        else:
            message += f"Investment Horizon: {horizon_name} (~{recommended_timeframe} days)\n"
            message += f"Target based on your selected timeframe\n\n"

        # Estimated date
        if time_estimate and time_estimate.get('estimated_date'):
            est_date = time_estimate.get('estimated_date')
            if isinstance(est_date, datetime):
                date_str = est_date.strftime('%d %b %Y')
                if output_mode == 'bot':
                    message += f"*Estimated Target Date:* {date_str}\n\n"
                else:
                    message += f"Estimated Target Date: {date_str}\n\n"

        # Example calculation
        if output_mode == 'bot':
            message += f"""*Example with Rs 10,000:*
   Buy {shares} shares @ Rs {format_number(price)}
   ✅ Profit if target hit: Rs {format_number(potential_profit)} (+{profit_pct:.1f}%)
   ❌ Loss if stop hit: Rs {format_number(potential_loss)} (-{loss_pct:.1f}%)
"""
        else:
            message += f"""Example with Rs 10,000:
   Buy {shares} shares @ Rs {format_number(price)}
   [+] Profit if target hit: Rs {format_number(potential_profit)} (+{profit_pct:.1f}%)
   [-] Loss if stop hit: Rs {format_number(potential_loss)} (-{loss_pct:.1f}%)
"""

    elif rec_type == 'HOLD':
        support = indicators.get('support', price * 0.95)
        if output_mode == 'bot':
            message += f"""⏳ *RECOMMENDED: WAIT*

Do not buy now. Wait for:
   • Price to drop to Rs {format_number(support)} (better entry)
   • OR trend to strengthen

Check again in: 1-2 weeks
"""
        else:
            message += f"""[WAIT] RECOMMENDED: WAIT

Do not buy now. Wait for:
   * Price to drop to Rs {format_number(support)} (better entry)
   * OR trend to strengthen

Check again in: 1-2 weeks
"""

    else:  # AVOID
        if output_mode == 'bot':
            message += f"""❌ *RECOMMENDED: AVOID*

Do not buy this stock now.

*Why to avoid:*
"""
        else:
            message += f"""[AVOID] RECOMMENDED: AVOID

Do not buy this stock now.

Why to avoid:
"""

        # Show key reasons
        if analysis.get('buy_block_reasons'):
            for reason in analysis['buy_block_reasons'][:3]:
                if output_mode == 'bot':
                    message += f"   • {reason}\n"
                else:
                    message += f"   * {reason}\n"
        else:
            reasons = []
            if 'downtrend' in indicators['market_phase']:
                reasons.append("Stock is in a downtrend")
            if trend_score == 0:
                reasons.append("All trend indicators are bearish")
            if not rr_valid:
                reasons.append("Risk/reward ratio is unfavorable")

            for reason in reasons:
                if output_mode == 'bot':
                    message += f"   • {reason}\n"
                else:
                    message += f"   * {reason}\n"

        if output_mode == 'bot':
            message += f"""
*When conditions might improve:*
   • When trend turns upward
   • When RSI shows oversold (below 30)
   • When a bullish pattern confirms

Check again in: 2-3 weeks
"""
        else:
            message += f"""
When conditions might improve:
   * When trend turns upward
   * When RSI shows oversold (below 30)
   * When a bullish pattern confirms

Check again in: 2-3 weeks
"""

    # =========================================================================
    # SECTION 4: TARGETS BY INVESTMENT HORIZON
    # =========================================================================

    horizon_targets = target_data.get('horizon_targets', {})
    if horizon_targets and rec_type == 'BUY':
        message += _format_section_header("TARGETS BY INVESTMENT HORIZON", output_mode)

        if output_mode == 'bot':
            message += "_Opportunities across different timeframes_\n\n"
        else:
            message += "Opportunities across different timeframes\n\n"

        # Sort horizons by timeframe
        sorted_horizons = sorted(
            horizon_targets.items(),
            key=lambda x: x[1]['timeframe']
        )

        for horizon_key, horizon_data in sorted_horizons:
            emoji = horizon_data.get('emoji', '')
            name = horizon_data['horizon_name']
            target_price = horizon_data['target']
            target_pct = horizon_data['target_pct']
            days = horizon_data['timeframe']
            is_recommended = horizon_data.get('is_recommended', False)

            if output_mode == 'bot':
                recommended_tag = " ⭐ *RECOMMENDED*" if is_recommended else ""
                message += f"{emoji} *{name}* (~{days} days){recommended_tag}\n"
                message += f"   Target: Rs {format_number(target_price)} (+{target_pct:.1f}%)\n"
                if is_recommended:
                    message += f"   _Your selected investment period_\n"
                message += "\n"
            else:
                recommended_tag = " * RECOMMENDED" if is_recommended else ""
                message += f"{name} (~{days} days){recommended_tag}\n"
                message += f"   Target: Rs {format_number(target_price)} (+{target_pct:.1f}%)\n"
                if is_recommended:
                    message += f"   (Your selected investment period)\n"
                message += "\n"

        if output_mode == 'bot':
            message += "_All targets shown - pick your preferred timeline_\n\n"
        else:
            message += "All targets shown - pick your preferred timeline\n\n"

    # =========================================================================
    # SECTION 5: PATTERN-BASED TARGET (if exists)
    # =========================================================================

    if target_data.get('has_pattern_target') and rec_type == 'BUY':
        message += _format_section_header("PATTERN-BASED TARGET", output_mode)

        if output_mode == 'bot':
            message += "_Industry-standard measured move calculation_\n\n"
        else:
            message += "Industry-standard measured move calculation\n\n"

        pattern_name = target_data.get('pattern_name', 'Unknown')
        pattern_target = target_data.get('pattern_target')
        pattern_target_pct = target_data.get('pattern_target_pct', 0)
        pattern_reliability = target_data.get('pattern_reliability', 0)
        pattern_invalidation = target_data.get('pattern_invalidation')
        pattern_min_days = target_data.get('pattern_min_days', 0)
        pattern_max_days = target_data.get('pattern_max_days', 0)

        reliability_pct = int((pattern_reliability or 0) * 100)
        reliability_stars = min(5, max(1, reliability_pct // 20))
        star_emoji = _get_emoji('star', output_mode)
        stars_display = star_emoji * reliability_stars

        if output_mode == 'bot':
            message += f"*Pattern:* {pattern_name}\n"
            message += f"*Reliability:* {reliability_pct}% {stars_display}\n\n"

            if pattern_target:
                message += f"📎 *Measured Move Target:* Rs {format_number(pattern_target)} (+{pattern_target_pct:.1f}%)\n"

            if pattern_invalidation:
                message += f"🚫 *Pattern Invalid If:* Price drops below Rs {format_number(pattern_invalidation)}\n"

            if pattern_min_days and pattern_max_days:
                message += f"⏱️ *Expected Timeframe:* {pattern_min_days}-{pattern_max_days} days\n"

            if target_data.get('pattern_horizon_warning'):
                message += f"\n⚠️ *Notice:* {target_data['pattern_horizon_warning']}\n"

            message += "\n_Pattern targets are based on classical technical analysis_\n"
            message += "_Measured move = pattern height projected from breakout_\n\n"
        else:
            message += f"Pattern: {pattern_name}\n"
            message += f"Reliability: {reliability_pct}% {stars_display}\n\n"

            if pattern_target:
                message += f"Measured Move Target: Rs {format_number(pattern_target)} (+{pattern_target_pct:.1f}%)\n"

            if pattern_invalidation:
                message += f"Pattern Invalid If: Price drops below Rs {format_number(pattern_invalidation)}\n"

            if pattern_min_days and pattern_max_days:
                message += f"Expected Timeframe: {pattern_min_days}-{pattern_max_days} days\n"

            if target_data.get('pattern_horizon_warning'):
                message += f"\n[!] Notice: {target_data['pattern_horizon_warning']}\n"

            message += "\nPattern targets are based on classical technical analysis\n"
            message += "Measured move = pattern height projected from breakout\n\n"

    # =========================================================================
    # SECTION 6: KEY PRICE LEVELS
    # =========================================================================

    support = indicators.get('support', price * 0.95)
    resistance = indicators.get('resistance', price * 1.05)

    message += _format_section_header("KEY PRICE LEVELS", output_mode)

    if output_mode == 'bot':
        message += f"""
Current: Rs {format_number(price)}

🔺 Resistance: Rs {format_number(resistance)} (+{((resistance-price)/price)*100:.1f}%)
   ↑ Price may struggle here

🔻 Support: Rs {format_number(support)} ({((support-price)/price)*100:.1f}%)
   ↓ Price may bounce here

"""
    else:
        message += f"""
Current: Rs {format_number(price)}
         |
[UP] Resistance: Rs {format_number(resistance)} (+{((resistance-price)/price)*100:.1f}%)
         |  Price may struggle here
         |
[DOWN] Support: Rs {format_number(support)} ({((support-price)/price)*100:.1f}%)
              Price may bounce here

"""

    # =========================================================================
    # SECTION 7: MARKET CONDITIONS
    # =========================================================================

    message += _format_section_header("MARKET CONDITIONS", output_mode)

    phase = indicators['market_phase'].replace('_', ' ').title()
    adx_strength = indicators['adx_strength'].replace('_', ' ').title()

    if output_mode == 'bot':
        message += f"""Market Phase: {phase}
Trend Strength: {adx_strength} (ADX: {format_number(adx, 1)})
Momentum: RSI {format_number(rsi, 1)} - {rsi_zone.replace('_', ' ').title()}
Volume: {format_number(vol_ratio, 2)}x average

"""
    else:
        message += f"""Market Phase: {phase}
Trend Strength: {adx_strength} (ADX: {format_number(adx, 1)})
Momentum: RSI {format_number(rsi, 1)} - {rsi_zone.replace('_', ' ').title()}
Volume: {format_number(vol_ratio, 2)}x average

"""

    # Divergence warning
    if indicators.get('divergence', 'none') != 'none':
        div_text = indicators['divergence'].upper()
        warn_emoji = _get_emoji('warning', output_mode)
        if output_mode == 'bot':
            message += f"{warn_emoji} *{div_text} DIVERGENCE DETECTED*\n\n"
        else:
            message += f"{warn_emoji} {div_text} DIVERGENCE DETECTED\n\n"

    # =========================================================================
    # SECTION 8: TECHNICAL INDICATORS DETAIL
    # =========================================================================

    message += _format_section_header("TECHNICAL INDICATORS DETAIL", output_mode)

    rsi_period = indicators.get('rsi_period', 14)

    if output_mode == 'bot':
        message += f"""RSI ({rsi_period}): {format_number(rsi, 1)} - {rsi_zone.replace('_', ' ').title()}
MACD Histogram: {format_number(macd_hist, 4)}
ADX: {format_number(adx, 1)} - Trend is {adx_strength}
Volume Ratio: {format_number(vol_ratio, 2)}x average
EMA Alignment: {ema_alignment.replace('_', ' ').title()}

"""
    else:
        message += f"""RSI ({rsi_period}): {format_number(rsi, 1)} - {rsi_zone.replace('_', ' ').title()}
MACD Histogram: {format_number(macd_hist, 4)}
ADX: {format_number(adx, 1)} - Trend is {adx_strength}
Volume Ratio: {format_number(vol_ratio, 2)}x average
EMA Alignment: {ema_alignment.replace('_', ' ').title()}

"""

    # =========================================================================
    # SECTION 9: CHART PATTERNS
    # =========================================================================

    candlestick_patterns = indicators.get('candlestick_patterns', [])
    chart_patterns = indicators.get('chart_patterns', [])
    bullish_count = indicators.get('pattern_bullish_count', 0)
    bearish_count = indicators.get('pattern_bearish_count', 0)

    if strongest_pattern or candlestick_patterns or chart_patterns:
        message += _format_section_header("CHART PATTERNS", output_mode)

        if output_mode == 'bot':
            message += f"""Pattern Bias: {pattern_bias.upper()}
Bullish Patterns: {bullish_count} | Bearish Patterns: {bearish_count}

"""
        else:
            message += f"""Pattern Bias: {pattern_bias.upper()}
Bullish Patterns: {bullish_count} | Bearish Patterns: {bearish_count}

"""

        # Strongest pattern
        if strongest_pattern and strongest_pattern is not None:
            try:
                p_name = getattr(strongest_pattern, 'name', None)
                p_conf = getattr(strongest_pattern, 'confidence', 0)
                
                # Skip if pattern name is invalid or empty
                if not p_name or p_name == 'Unknown Pattern' or p_name == '' or p_conf == 0:
                    if output_mode == 'bot':
                        message += "Key Pattern: No significant pattern detected\n\n"
                    else:
                        message += "Key Pattern: No significant pattern detected\n\n"
                else:
                    # Get pattern type
                    if hasattr(strongest_pattern, 'type'):
                        if hasattr(strongest_pattern.type, 'value'):
                            p_type = strongest_pattern.type.value.upper()
                        else:
                            p_type = str(strongest_pattern.type).upper().replace('PATTERNTYPE.', '')
                    else:
                        p_type = 'UNKNOWN'
                    
                    # Get pattern strength
                    if hasattr(strongest_pattern, 'strength'):
                        if hasattr(strongest_pattern.strength, 'value'):
                            p_strength = strongest_pattern.strength.value.upper()
                        else:
                            p_strength = str(strongest_pattern.strength).upper().replace('PATTERNSTRENGTH.', '')
                    else:
                        p_strength = 'UNKNOWN'
                    
                    p_action = getattr(strongest_pattern, 'action', 'Check chart')

                    if output_mode == 'bot':
                        message += f"""Key Pattern: *{p_name}* ({p_conf}%)
Type: {p_type} | Strength: {p_strength}
Action: {p_action}

"""
                    else:
                        message += f"""Key Pattern: {p_name} ({p_conf}%)
Type: {p_type} | Strength: {p_strength}
Action: {p_action}

"""
            except Exception as e:
                # Fallback if pattern object structure is different
                try:
                    p_name = str(getattr(strongest_pattern, 'name', 'Pattern'))
                    p_conf = getattr(strongest_pattern, 'confidence', 0)
                    if p_name and p_name != 'Unknown Pattern' and p_conf > 0:
                        if output_mode == 'bot':
                            message += f"Key Pattern: *{p_name}* ({p_conf}%)\n\n"
                        else:
                            message += f"Key Pattern: {p_name} ({p_conf}%)\n\n"
                    else:
                        if output_mode == 'bot':
                            message += "Key Pattern: No significant pattern detected\n\n"
                        else:
                            message += "Key Pattern: No significant pattern detected\n\n"
                except Exception:
                    if output_mode == 'bot':
                        message += "Key Pattern: No significant pattern detected\n\n"
                    else:
                        message += "Key Pattern: No significant pattern detected\n\n"

    # =========================================================================
    # SECTION 10: INVESTMENT CHECKLIST - REMOVED FROM MAIN OUTPUT
    # (Now available via Position Sizing button)
    # =========================================================================

    # =========================================================================
    # SECTION 11: POSITION SIZING GUIDANCE - REMOVED FROM MAIN OUTPUT
    # (Now available via Position Sizing button)
    # =========================================================================

    # =========================================================================
    # SECTION 12: WHEN TO SELL - REMOVED FROM MAIN OUTPUT
    # (Now available via Position Sizing button)
    # =========================================================================

    # =========================================================================
    # SECTION 13: SAFETY & RISK SUMMARY
    # =========================================================================

    message += _format_section_header("SAFETY & RISK SUMMARY", output_mode)

    safety_advice = safety.get('advice', 'Moderate risk investment')
    risk_factors = safety.get('risk_factors', [])
    investor_profile = safety.get('suitable_for', 'Investors with moderate risk tolerance')

    if output_mode == 'bot':
        message += f"""Safety Score: {safety_emoji} {safety_stars}/5 stars
Rating: {safety_rating}

{safety_advice}

Suitable For: {investor_profile}

"""
        if risk_factors:
            message += "*Risk Factors:*\\n"
            for rf in risk_factors[:3]:
                message += f"   • {rf}\\n"
            message += "\\n"
    else:
        message += f"""Safety Score: {safety_emoji} {safety_stars}/5 stars
Rating: {safety_rating}

{safety_advice}

Suitable For: {investor_profile}

"""
        if risk_factors:
            message += "Risk Factors:\n"
            for rf in risk_factors[:3]:
                message += f"   * {rf}\n"
            message += "\n"

    # =========================================================================
    # SECTION 14: TIMELINE ESTIMATE
    # =========================================================================

    if time_estimate:
        message += _format_section_header("TIMELINE ESTIMATE", output_mode)

        earliest = time_estimate.get('earliest_date')
        estimated = time_estimate.get('estimated_date')
        latest = time_estimate.get('latest_date')
        trading_days = time_estimate.get('trading_days', 0)

        if output_mode == 'bot':
            message += f"""Hold Duration: Approximately {trading_days} trading days

"""
            if isinstance(earliest, datetime):
                message += f"Earliest Sell: {earliest.strftime('%d %b %Y')}\n"
            if isinstance(estimated, datetime):
                message += f"Expected Sell: {estimated.strftime('%d %b %Y')}\n"
            if isinstance(latest, datetime):
                message += f"Latest Sell: {latest.strftime('%d %b %Y')}\n"
            message += "\n"
        else:
            message += f"""Hold Duration: Approximately {trading_days} trading days

"""
            if isinstance(earliest, datetime):
                message += f"Earliest Sell: {earliest.strftime('%d %b %Y')}\n"
            if isinstance(estimated, datetime):
                message += f"Expected Sell: {estimated.strftime('%d %b %Y')}\n"
            if isinstance(latest, datetime):
                message += f"Latest Sell: {latest.strftime('%d %b %Y')}\n"
            message += "\n"

    # =========================================================================
    # SECTION 15: FOOTER (TIPS FOR BEGINNERS and DISCLAIMER removed per user request)
    # =========================================================================

    if output_mode == 'bot':
        message += f"\n_Stock Analyzer Pro by Harsh Kandhway_\n"
    else:
        message += f"\n{'='*60}\n"
        message += f"  Developed by Harsh Kandhway | Stock Analyzer Pro v3.0\n"
        message += f"{'='*60}\n"

    return message.strip()


def format_position_sizing(
    analysis: Dict[str, Any],
    capital: float,
    output_mode: str = 'bot'
) -> str:
    """
    Format position sizing details for a stock analysis.
    Includes Investment Checklist.
    
    Args:
        analysis: Analysis dictionary from analysis_service
        capital: User's capital amount
        output_mode: 'bot' or 'cli'
    
    Returns:
        Formatted position sizing string with investment checklist
    """
    symbol = analysis['symbol']
    price = analysis['current_price']
    rec_type = analysis['recommendation_type']
    stop_data = analysis['stop_data']
    target_data = analysis['target_data']
    indicators = analysis['indicators']
    risk_reward = analysis.get('risk_reward', 0)
    
    stop = stop_data['recommended_stop']
    target = target_data['recommended_target']
    
    # Calculate position sizing
    risk_per_trade = 0.01  # 1% risk
    risk_amount = capital * risk_per_trade
    stop_distance = price - stop
    
    if stop_distance > 0:
        position_shares = int(risk_amount / stop_distance)
    else:
        position_shares = int(capital * 0.1 / price)  # 10% of capital fallback
    
    investment_amount = position_shares * price
    position_pct = (investment_amount / capital) * 100
    max_loss = position_shares * stop_distance if stop_distance > 0 else position_shares * price * 0.05
    max_loss_pct = (max_loss / capital) * 100
    
    # Calculate potential profit
    profit_pct = ((target - price) / price) * 100 if target > price else 0
    potential_profit = position_shares * (target - price) if target > price else 0
    loss_pct = ((price - stop) / price) * 100 if stop < price else 0
    
    # Get indicators for checklist
    rsi = indicators.get('rsi', 50)
    adx = indicators.get('adx', 0)
    vol_ratio = indicators.get('volume_ratio', 1.0)
    
    # Build Investment Checklist
    checks = []
    checks_passed = 0
    
    # Check 1: Trend
    if indicators.get('price_vs_trend_ema') == 'above':
        checks.append(("Price above long-term average", True, "Stock is in uptrend"))
        checks_passed += 1
    else:
        checks.append(("Price above long-term average", False, "Stock is in downtrend"))
    
    # Check 2: RSI
    if 30 <= rsi <= 70:
        checks.append(("Not overbought or oversold", True, "Healthy momentum"))
        checks_passed += 1
    elif rsi > 70:
        checks.append(("Not overbought or oversold", False, "Stock may be too expensive"))
    else:
        checks.append(("Not overbought or oversold", False, "Stock may be too cheap (risky)"))
    
    # Check 3: Trend strength
    if adx >= 25:
        checks.append(("Clear trend direction", True, "Reliable movement"))
        checks_passed += 1
    else:
        checks.append(("Clear trend direction", False, "Unclear direction"))
    
    # Check 4: Volume
    if vol_ratio >= 0.7:
        checks.append(("Adequate trading volume", True, "Enough market interest"))
        checks_passed += 1
    else:
        checks.append(("Adequate trading volume", False, "Low interest, harder to sell"))
    
    # Check 5: Risk/Reward
    if risk_reward >= 2:
        checks.append(("Good risk/reward ratio", True, "Potential gain > potential loss"))
        checks_passed += 1
    else:
        checks.append(("Good risk/reward ratio", False, "Risk may exceed reward"))
    
    if output_mode == 'bot':
        message = f"""💰 *POSITION SIZING FOR {symbol}*

*Your Capital:* Rs {capital:,.0f}

*Recommended Position:*
   • Buy: *{position_shares} shares*
   • Investment: Rs {investment_amount:,.0f} ({position_pct:.1f}% of capital)
   • Entry Price: Rs {format_number(price)}
   • Stop Loss: Rs {format_number(stop)} (-{loss_pct:.1f}%)
   • Target Price: Rs {format_number(target)} (+{profit_pct:.1f}%)

*Risk Analysis:*
   • Max Loss: Rs {max_loss:,.0f} ({max_loss_pct:.2f}% of capital)
   • Potential Profit: Rs {potential_profit:,.0f} (+{profit_pct:.1f}%)
   • Risk/Reward: {risk_reward:.1f}:1
   • Based on 1% risk rule

*Recommendation:* {analysis['recommendation']}
*Confidence:* {analysis['confidence']:.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*INVESTMENT CHECKLIST*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        # Add checklist items
        for check_name, passed_check, explanation in checks:
            emoji = '✅' if passed_check else '❌'
            message += f"{emoji} *{check_name}*\n   _{explanation}_\n\n"
        
        # Summary
        message += f"*Passed {checks_passed}/{len(checks)} checks*\n"
        if checks_passed >= 4:
            message += f"✅ *Good investment opportunity!*\n\n"
        elif checks_passed >= 3:
            message += f"🟡 *Moderate opportunity* - proceed with caution\n\n"
        else:
            message += f"❌ *Not recommended at this time*\n\n"
        
        message += "💡 *Tip:* This calculation assumes you're willing to risk 1% of your capital on this trade. Adjust your position size based on your risk tolerance.\n\n"
        
        # Add "When to Sell" section
        partial_target = price + (target - price) * 0.5
        message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*WHEN TO SELL - SET ALERTS*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Set Price Alerts for These Levels:

1. *TAKE PROFIT ALERT:* Rs {format_number(target)}
   When price reaches → SELL for profit
   Expected profit: {format_percentage(profit_pct)}

2. *PARTIAL PROFIT ALERT:* Rs {format_number(partial_target)}
   Consider selling half your shares here
   This locks in some profit safely

3. *STOP LOSS ALERT:* Rs {format_number(stop)}
   When price falls to this → SELL to limit loss
   Maximum loss: -{loss_pct:.1f}%
   ⚠️ DO NOT IGNORE THIS - protects your capital!

*IMPORTANT:*
   • Set these alerts in your trading app
   • Don't change stop loss to avoid loss - discipline is key!
   • Review your position every week
"""
    else:
        message = f"""POSITION SIZING FOR {symbol}

Your Capital: Rs {capital:,.0f}

Recommended Position:
   * Buy: {position_shares} shares
   * Investment: Rs {investment_amount:,.0f} ({position_pct:.1f}% of capital)
   * Entry Price: Rs {format_number(price)}
   * Stop Loss: Rs {format_number(stop)} (-{loss_pct:.1f}%)
   * Target Price: Rs {format_number(target)} (+{profit_pct:.1f}%)

Risk Analysis:
   * Max Loss: Rs {max_loss:,.0f} ({max_loss_pct:.2f}% of capital)
   * Potential Profit: Rs {potential_profit:,.0f} (+{profit_pct:.1f}%)
   * Risk/Reward: {risk_reward:.1f}:1
   * Based on 1% risk rule

Recommendation: {analysis['recommendation']}
Confidence: {analysis['confidence']:.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVESTMENT CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        # Add checklist items
        for check_name, passed_check, explanation in checks:
            emoji = '[Y]' if passed_check else '[X]'
            message += f"{emoji} {check_name}\n     {explanation}\n\n"
        
        # Summary
        message += f"Passed {checks_passed}/{len(checks)} checks\n"
        if checks_passed >= 4:
            message += f"[Y] Good investment opportunity!\n\n"
        elif checks_passed >= 3:
            message += f"[?] Moderate opportunity - proceed with caution\n\n"
        else:
            message += f"[X] Not recommended at this time\n\n"
        
        message += "Tip: This calculation assumes you're willing to risk 1% of your capital on this trade.\n\n"
        
        # Add "When to Sell" section
        partial_target = price + (target - price) * 0.5
        message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHEN TO SELL - SET ALERTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Set Price Alerts for These Levels:

1. TAKE PROFIT ALERT: Rs {format_number(target)}
      When price reaches -> SELL for profit
      Expected profit: {format_percentage(profit_pct)}

2. PARTIAL PROFIT ALERT: Rs {format_number(partial_target)}
      Consider selling half your shares here
      This locks in some profit safely

3. STOP LOSS ALERT: Rs {format_number(stop)}
      When price falls to this -> SELL to limit loss
      Maximum loss: -{loss_pct:.1f}%
      [!] DO NOT IGNORE THIS - protects your capital!

IMPORTANT:
   * Set these alerts in your trading app
   * Don't change stop loss to avoid loss - discipline is key!
   * Review your position every week
"""
    
    return message.strip()


# ============================================================================
# SPECIALIZED FORMATTERS
# ============================================================================

def format_comparison_table(
    analyses: List[Dict[str, Any]],
    output_mode: str = 'bot'
) -> str:
    """
    Format multiple analyses as a comparison table

    Args:
        analyses: List of analysis dictionaries
        output_mode: 'bot' or 'cli'

    Returns:
        Formatted comparison table
    """
    if output_mode == 'bot':
        message = f"""
{_get_emoji('compare', 'bot')} *STOCK COMPARISON*
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
                emoji = _get_emoji('buy', 'bot')
            elif analysis['recommendation_type'] == 'SELL':
                emoji = _get_emoji('sell', 'bot')
            else:
                emoji = _get_emoji('hold', 'bot')

            message += f"""
*{symbol}*
Price: Rs {format_number(price)} | {emoji} {rec}
Confidence: {format_number(conf, 0)}% | R:R: {format_number(rr, 2)}:1
{'-'*40}

"""

        message += f"\\n_Developed by Harsh Kandhway_\\n"

    else:
        message = f"\n{'='*80}\n  STOCK COMPARISON\n{'='*80}\n\n"
        message += f"  {'Stock':<15} {'Price':>10} {'Action':>12} {'Confidence':>10} {'R:R':>10}\n"
        message += f"  {'-'*70}\n"

        for a in analyses:
            rec = a['recommendation'].replace('STRONG ', '').replace('WEAK ', '')[:10]
            message += f"  {a['symbol']:<15} Rs {a['current_price']:>8,.2f} {rec:>12} {a['confidence']:>9.0f}% {a['risk_reward']:>9.2f}:1\n"

        message += f"\n{'='*80}\n"

    return message.strip()


def format_watchlist(
    watchlist: List,
    output_mode: str = 'bot',
    show_details: bool = False
) -> str:
    """
    Format watchlist for display

    Args:
        watchlist: List of watchlist items
        output_mode: 'bot' or 'cli'
        show_details: Whether to show additional details

    Returns:
        Formatted watchlist string
    """
    if not watchlist:
        if output_mode == 'bot':
            return f"{_get_emoji('info', 'bot')} Your watchlist is empty.\\n\\nUse /watchlist add \\[SYMBOL\\] to add stocks\\."
        else:
            return "[INFO] Your watchlist is empty.\n\nUse the watchlist command to add stocks."

    if output_mode == 'bot':
        message = f"""
{_get_emoji('watchlist', 'bot')} *YOUR WATCHLIST* \\({len(watchlist)} stocks\\)
{'='*40}

"""
    else:
        message = f"\n{'='*60}\n  YOUR WATCHLIST ({len(watchlist)} stocks)\n{'='*60}\n\n"

    for item in watchlist:
        # Handle both dict and object
        if isinstance(item, dict):
            symbol = item['symbol']
            added_at = item.get('added_at')
            notes = item.get('notes')
        else:
            symbol = item.symbol
            added_at = getattr(item, 'added_at', None)
            notes = getattr(item, 'notes', None)

        if output_mode == 'bot':
            message += f"{_get_emoji('chart', 'bot')} *{symbol}*\\n"

            if show_details and added_at:
                added_date = added_at.strftime('%b %d, %Y') if isinstance(added_at, datetime) else added_at
                message += f"   Added: {added_date}\\n"

            if show_details and notes:
                message += f"   Notes: {notes}\\n"

            message += "\\n"
        else:
            message += f"  * {symbol}\n"

            if show_details and added_at:
                added_date = added_at.strftime('%b %d, %Y') if isinstance(added_at, datetime) else added_at
                message += f"     Added: {added_date}\n"

            if show_details and notes:
                message += f"     Notes: {notes}\n"

            message += "\n"

    return message.strip()


def format_portfolio(
    portfolio: List[Dict],
    output_mode: str = 'bot',
    current_prices: Optional[Dict[str, float]] = None
) -> str:
    """
    Format portfolio for display with P&L calculation

    Args:
        portfolio: List of portfolio positions
        output_mode: 'bot' or 'cli'
        current_prices: Dict of symbol -> current price (optional)

    Returns:
        Formatted portfolio string
    """
    if not portfolio:
        if output_mode == 'bot':
            return f"{_get_emoji('info', 'bot')} Your portfolio is empty.\\n\\nUse /portfolio add \\[SYMBOL\\] \\[SHARES\\] \\[PRICE\\] to add positions\\."
        else:
            return "[INFO] Your portfolio is empty.\n\nUse the portfolio command to add positions."

    if output_mode == 'bot':
        message = f"""
{_get_emoji('portfolio', 'bot')} *YOUR PORTFOLIO* \\({len(portfolio)} positions\\)
{'='*40}

"""
    else:
        message = f"\n{'='*60}\n  YOUR PORTFOLIO ({len(portfolio)} positions)\n{'='*60}\n\n"

    total_investment = 0
    total_current_value = 0

    for position in portfolio:
        symbol = position['symbol']
        shares = position['shares']
        avg_price = position['avg_buy_price']
        investment = shares * avg_price

        total_investment += investment

        if output_mode == 'bot':
            message += f"{_get_emoji('chart', 'bot')} *{symbol}*\\n"
            message += f"   Shares: {format_number(shares, 2)}\\n"
            message += f"   Avg Price: Rs {format_number(avg_price)}\\n"
            message += f"   Investment: Rs {format_number(investment)}\\n"
        else:
            message += f"  * {symbol}\n"
            message += f"     Shares: {format_number(shares, 2)}\n"
            message += f"     Avg Price: Rs {format_number(avg_price)}\n"
            message += f"     Investment: Rs {format_number(investment)}\n"

        # If current prices provided, calculate P&L
        if current_prices and symbol in current_prices:
            current_price = current_prices[symbol]
            current_value = shares * current_price
            pnl = current_value - investment
            pnl_pct = (pnl / investment) * 100

            total_current_value += current_value

            pnl_emoji = _get_emoji('profit' if pnl >= 0 else 'loss', output_mode)

            if output_mode == 'bot':
                message += f"   Current: Rs {format_number(current_price)}\\n"
                message += f"   Value: Rs {format_number(current_value)}\\n"
                message += f"   P&L: {pnl_emoji} Rs {format_number(pnl)} \\({format_percentage(pnl_pct)}\\)\\n"
            else:
                message += f"     Current: Rs {format_number(current_price)}\n"
                message += f"     Value: Rs {format_number(current_value)}\n"
                message += f"     P&L: {pnl_emoji} Rs {format_number(pnl)} ({format_percentage(pnl_pct)})\n"

        message += "\\n" if output_mode == 'bot' else "\n"

    # Portfolio Summary
    if current_prices and total_current_value > 0:
        total_pnl = total_current_value - total_investment
        total_pnl_pct = (total_pnl / total_investment) * 100
        pnl_emoji = _get_emoji('profit' if total_pnl >= 0 else 'loss', output_mode)

        if output_mode == 'bot':
            message += f"""
{'='*40}
{_get_emoji('info', 'bot')} *PORTFOLIO SUMMARY*
{'='*40}
Total Investment: Rs {format_number(total_investment)}
Current Value: Rs {format_number(total_current_value)}
Total P&L: {pnl_emoji} Rs {format_number(total_pnl)} \\({format_percentage(total_pnl_pct)}\\)
"""
        else:
            message += f"""
{'='*60}
  PORTFOLIO SUMMARY
{'='*60}
Total Investment: Rs {format_number(total_investment)}
Current Value: Rs {format_number(total_current_value)}
Total P&L: {pnl_emoji} Rs {format_number(total_pnl)} ({format_percentage(total_pnl_pct)})
"""

    return message.strip()


# ============================================================================
# UTILITY FORMATTERS
# ============================================================================

def format_error(error_message: str, output_mode: str = 'bot', command: Optional[str] = None) -> str:
    """Format error message"""
    error_emoji = _get_emoji('error', output_mode)

    if output_mode == 'bot':
        message = f"{error_emoji} *Error*\\n\\n{error_message}\\n"
        if command:
            message += f"\\nCommand: `{command}`"
        message += f"\\n\\nUse /help for usage instructions\\."
    else:
        message = f"{error_emoji} Error\n\n{error_message}\n"
        if command:
            message += f"\nCommand: {command}"
        message += f"\n\nUse help command for usage instructions."

    return message


def format_success(success_message: str, output_mode: str = 'bot') -> str:
    """Format success message"""
    success_emoji = _get_emoji('success', output_mode)
    return f"{success_emoji} {success_message}"


def format_warning(warning_message: str, output_mode: str = 'bot') -> str:
    """Format warning message"""
    warning_emoji = _get_emoji('warning', output_mode)
    return f"{warning_emoji} {warning_message}"


def format_info(info_message: str, output_mode: str = 'bot') -> str:
    """Format info message"""
    info_emoji = _get_emoji('info', output_mode)
    return f"{info_emoji} {info_message}"


def format_alert(alert: Dict, output_mode: str = 'bot') -> str:
    """
    Format single alert for display

    Args:
        alert: Alert dictionary
        output_mode: 'bot' or 'cli'

    Returns:
        Formatted alert string
    """
    alert_id = alert['id']
    symbol = alert['symbol']
    alert_type = alert['alert_type']
    condition_type = alert['condition_type']
    threshold = alert.get('threshold_value')
    is_active = alert['is_active']

    status_emoji = _get_emoji('success' if is_active else 'error', output_mode)
    status = "Active" if is_active else "Inactive"

    alert_emoji = _get_emoji('alert', output_mode)

    if output_mode == 'bot':
        message = f"{alert_emoji} *Alert \\#{alert_id}* {status_emoji} {status}\\n"
        message += f"Symbol: {symbol}\\n"
        message += f"Type: {alert_type.replace('_', ' ').title()}\\n"

        if alert_type == 'price' and threshold:
            message += f"Condition: Price {condition_type} Rs {format_number(threshold)}\\n"
        elif alert_type == 'technical' and threshold:
            message += f"Condition: {condition_type.upper()} {condition_type} {format_number(threshold)}\\n"
        else:
            message += f"Condition: {condition_type.replace('_', ' ').title()}\\n"
    else:
        message = f"{alert_emoji} Alert #{alert_id} {status_emoji} {status}\n"
        message += f"Symbol: {symbol}\n"
        message += f"Type: {alert_type.replace('_', ' ').title()}\n"

        if alert_type == 'price' and threshold:
            message += f"Condition: Price {condition_type} Rs {format_number(threshold)}\n"
        elif alert_type == 'technical' and threshold:
            message += f"Condition: {condition_type.upper()} {condition_type} {format_number(threshold)}\n"
        else:
            message += f"Condition: {condition_type.replace('_', ' ').title()}\n"

    return message


def format_alert_list(alerts: List[Dict], output_mode: str = 'bot') -> str:
    """
    Format list of alerts for display

    Args:
        alerts: List of alert dictionaries
        output_mode: 'bot' or 'cli'

    Returns:
        Formatted alerts list string
    """
    if not alerts:
        info_emoji = _get_emoji('info', output_mode)
        if output_mode == 'bot':
            return f"{info_emoji} You have no active alerts.\\n\\nUse /alert to set up alerts\\."
        else:
            return f"{info_emoji} You have no active alerts.\n\nUse the alert command to set up alerts."

    alert_emoji = _get_emoji('alert', output_mode)

    if output_mode == 'bot':
        message = f"""
{alert_emoji} *YOUR ALERTS* \\({len(alerts)} active\\)
{'='*40}

"""
        for alert in alerts:
            message += format_alert(alert, output_mode) + "\\n"
            message += f"{'-'*40}\\n\\n"
    else:
        message = f"\n{'='*60}\n  YOUR ALERTS ({len(alerts)} active)\n{'='*60}\n\n"
        for alert in alerts:
            message += format_alert(alert, output_mode) + "\n"
            message += f"{'-'*60}\n\n"

    return message.strip()
