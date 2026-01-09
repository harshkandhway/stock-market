"""Test COALINDIA.NS recommendation"""
from src.bot.services.analysis_service import analyze_stock

analysis = analyze_stock('COALINDIA.NS', mode='balanced', horizon='1week', use_cache=False)

print(f"Recommendation: {analysis['recommendation']}")
print(f"Type: {analysis['recommendation_type']}")
print(f"Confidence: {analysis['confidence']:.1f}%")
print(f"R:R: {analysis['risk_reward']:.2f}:1")
print(f"R:R Valid: {analysis['rr_valid']}")

# Calculate score
indicators = analysis['indicators']
trend_score = 0
if indicators.get('price_vs_trend_ema') == 'above':
    trend_score += 1
if indicators.get('price_vs_medium_ema') == 'above':
    trend_score += 1
if indicators.get('ema_alignment') in ['strong_bullish', 'bullish']:
    trend_score += 1

momentum_score = 0
if indicators.get('rsi_zone') in ['oversold', 'extremely_oversold']:
    momentum_score += 1
if indicators.get('macd_hist', 0) > 0:
    momentum_score += 1
if indicators.get('adx', 0) >= 25:
    momentum_score += 1

volume_score = 1 if indicators.get('volume_ratio', 1.0) >= 1.5 else 0

pattern_score = 0
strongest_pattern = indicators.get('strongest_pattern')
if strongest_pattern and hasattr(strongest_pattern, 'type'):
    try:
        pattern_type = strongest_pattern.type.value if hasattr(strongest_pattern.type, 'value') else str(strongest_pattern.type)
        if pattern_type == 'bullish':
            pattern_score += 2
    except:
        pass
if indicators.get('pattern_bias') == 'bullish':
    pattern_score += 1

risk_score = 1 if analysis['rr_valid'] else 0
total_score = trend_score + momentum_score + volume_score + pattern_score + risk_score
score_pct = (total_score / 10) * 100

print(f"Score: {total_score}/10 ({score_pct:.1f}%)")

