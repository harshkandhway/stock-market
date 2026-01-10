"""
Test 360ONE.NS to verify the divergence override fix
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.bot.services.analysis_service import analyze_stock

print("=" * 60)
print("Testing 360ONE.NS - Divergence Override Fix")
print("=" * 60)

result = analyze_stock('360ONE.NS', mode='balanced', horizon='1week', use_cache=False)

print(f"\nRecommendation: {result['recommendation']}")
print(f"Type: {result['recommendation_type']}")
print(f"Score: {result['overall_score_pct']:.1f}%")
print(f"R:R: {result['risk_reward']:.2f}:1")
print(f"Confidence: {result['confidence']:.1f}%")
print(f"Buy Blocked: {result['is_buy_blocked']}")
print(f"Divergence: {result['indicators'].get('divergence', 'none')}")

# Check pattern
strongest_pattern = result['indicators'].get('strongest_pattern')
if strongest_pattern:
    pattern_conf = getattr(strongest_pattern, 'confidence', 0)
    pattern_type = None
    if hasattr(strongest_pattern, 'type'):
        if hasattr(strongest_pattern.type, 'value'):
            pattern_type = strongest_pattern.type.value
        else:
            pattern_type = str(strongest_pattern.type)
    print(f"Pattern: {getattr(strongest_pattern, 'name', 'Unknown')} ({pattern_conf}%) - {pattern_type}")

adx = result['indicators'].get('adx', 0)
print(f"ADX: {adx:.1f}")

# Check if override conditions are met
score = result['overall_score_pct']
rr = result['risk_reward']
pattern_conf_val = getattr(strongest_pattern, 'confidence', 0) if strongest_pattern else 0
pattern_type_val = None
if strongest_pattern and hasattr(strongest_pattern, 'type'):
    if hasattr(strongest_pattern.type, 'value'):
        pattern_type_val = strongest_pattern.type.value

override_conditions = (
    score >= 80 and
    rr >= 3.0 and
    pattern_conf_val >= 75 and
    pattern_type_val and pattern_type_val.lower() == 'bullish' and
    adx >= 25
)

print(f"\nOverride Conditions Met: {override_conditions}")
print(f"  - Score >= 80%: {score >= 80} ({score:.1f}%)")
print(f"  - R:R >= 3.0:1: {rr >= 3.0} ({rr:.2f}:1)")
print(f"  - Pattern >= 75% bullish: {pattern_conf_val >= 75 and pattern_type_val and pattern_type_val.lower() == 'bullish'} ({pattern_conf_val}%)")
print(f"  - ADX >= 25: {adx >= 25} ({adx:.1f})")

if result['recommendation_type'] == 'BLOCKED' and override_conditions:
    print("\n❌ ERROR: Override conditions met but still BLOCKED!")
elif 'DIVERGENCE WARNING' in result['recommendation'] or 'STRONG SIGNALS OVERRIDE' in result['recommendation']:
    print("\n✅ SUCCESS: Divergence override working - recommendation includes warning")
elif result['recommendation_type'] == 'BUY':
    print("\n✅ SUCCESS: Recommendation is BUY (not blocked)")
else:
    print(f"\n⚠️  WARNING: Recommendation is {result['recommendation_type']}")

