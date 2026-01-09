"""
Unit Test Script for Recommendation Logic
Tests the fixed recommendation system with multiple stocks
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.bot.services.analysis_service import analyze_stock
from src.core.formatters import format_analysis_comprehensive

# Test stocks - mix of different market conditions
TEST_STOCKS = [
    'TCS.NS',      # The problematic case from user
    'RELIANCE.NS', # Large cap
    'INFY.NS',     # IT sector
    'HDFCBANK.NS', # Banking
    'ICICIBANK.NS', # Banking
]

def test_stock_analysis(symbol: str, mode: str = 'balanced', horizon: str = '1week'):
    """Test analysis for a single stock"""
    print(f"\n{'='*80}")
    print(f"TESTING: {symbol}")
    print(f"{'='*80}")
    
    try:
        # Perform analysis
        analysis = analyze_stock(
            symbol=symbol,
            mode=mode,
            timeframe='medium',
            horizon=horizon,
            use_cache=False
        )
        
        # Extract key metrics
        confidence = analysis['confidence']
        recommendation = analysis['recommendation']
        rec_type = analysis['recommendation_type']
        risk_reward = analysis['risk_reward']
        rr_valid = analysis['rr_valid']
        
        # Calculate overall score (matching formatter logic)
        indicators = analysis['indicators']
        
        # Trend score (max 3)
        trend_score = 0
        price_vs_trend = indicators.get('price_vs_trend_ema', 'below')
        price_vs_medium = indicators.get('price_vs_medium_ema', 'below')
        ema_alignment = indicators.get('ema_alignment', 'mixed')
        
        if price_vs_trend == 'above':
            trend_score += 1
        if price_vs_medium == 'above':
            trend_score += 1
        if ema_alignment in ['strong_bullish', 'bullish']:
            trend_score += 1
        
        # Momentum score (max 3)
        momentum_score = 0
        rsi_zone = indicators.get('rsi_zone', 'neutral')
        macd_hist = indicators.get('macd_hist', 0)
        adx = indicators.get('adx', 0)
        
        if rsi_zone in ['oversold', 'extremely_oversold']:
            momentum_score += 1
        if macd_hist > 0:
            momentum_score += 1
        if adx >= 25:
            momentum_score += 1
        
        # Volume score (max 1)
        vol_ratio = indicators.get('volume_ratio', 1.0)
        volume_score = 1 if vol_ratio >= 1.5 else 0
        
        # Pattern score (max 3)
        pattern_score = 0
        strongest_pattern = indicators.get('strongest_pattern')
        pattern_bias = indicators.get('pattern_bias', 'neutral')
        
        if strongest_pattern and hasattr(strongest_pattern, 'type'):
            try:
                pattern_type = strongest_pattern.type.value if hasattr(strongest_pattern.type, 'value') else str(strongest_pattern.type)
                if pattern_type == 'bullish':
                    pattern_score += 2
            except:
                pass
        
        if pattern_bias == 'bullish':
            pattern_score += 1
        
        # Risk score (max 1)
        risk_score = 1 if rr_valid else 0
        
        total_score = trend_score + momentum_score + volume_score + pattern_score + risk_score
        score_pct = (total_score / 10) * 100
        
        # Display results
        print(f"\n📊 ANALYSIS RESULTS:")
        print(f"   Confidence: {confidence:.1f}%")
        print(f"   Recommendation: {recommendation}")
        print(f"   Type: {rec_type}")
        print(f"   Risk/Reward: {risk_reward:.2f}:1")
        print(f"   R:R Valid: {rr_valid}")
        print(f"\n📈 SCORE BREAKDOWN:")
        print(f"   Trend: {trend_score}/3")
        print(f"   Momentum: {momentum_score}/3")
        print(f"   Volume: {volume_score}/1")
        print(f"   Patterns: {pattern_score}/3")
        print(f"   Risk: {risk_score}/1")
        print(f"   TOTAL: {total_score}/10 ({score_pct:.1f}%)")
        
        # Validation checks
        print(f"\n✅ VALIDATION CHECKS:")
        issues = []
        
        # Check 1: Low score should not be BUY
        if total_score < 4 and rec_type == 'BUY':
            issues.append(f"❌ FAIL: Score {total_score}/10 ({score_pct:.1f}%) but recommendation is BUY")
        else:
            print(f"   ✓ Score validation: OK")
        
        # Check 2: Invalid R:R should not be BUY
        if not rr_valid and rec_type == 'BUY':
            issues.append(f"❌ FAIL: R:R {risk_reward:.2f}:1 is invalid but recommendation is BUY")
        else:
            print(f"   ✓ R:R validation: OK")
        
        # Check 3: Confidence thresholds
        if rec_type == 'BUY':
            if confidence < 60:
                issues.append(f"❌ FAIL: BUY recommendation with confidence {confidence:.1f}% < 60%")
            else:
                print(f"   ✓ Confidence threshold: OK (≥60%)")
        
        # Check 4: Score < 40% should downgrade BUY
        if score_pct < 40 and rec_type == 'BUY':
            issues.append(f"❌ FAIL: Score {score_pct:.1f}% < 40% but recommendation is BUY")
        else:
            print(f"   ✓ Score threshold: OK")
        
        # Display issues
        if issues:
            print(f"\n⚠️  ISSUES FOUND:")
            for issue in issues:
                print(f"   {issue}")
            return False
        else:
            print(f"\n✅ ALL CHECKS PASSED")
            return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests on all stocks"""
    print("="*80)
    print("RECOMMENDATION LOGIC TEST SUITE")
    print("="*80)
    print("\nTesting fixes:")
    print("  1. Low scores (<40%) should not result in BUY")
    print("  2. Invalid R:R should downgrade BUY to HOLD")
    print("  3. Confidence thresholds (WEAK_BUY ≥60%, BUY ≥70%)")
    print("  4. Overall score validation")
    
    results = {}
    
    for symbol in TEST_STOCKS:
        try:
            result = test_stock_analysis(symbol, mode='balanced', horizon='1week')
            results[symbol] = result
        except Exception as e:
            print(f"\n❌ FAILED to test {symbol}: {str(e)}")
            results[symbol] = False
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    print(f"\nDetailed Results:")
    for symbol, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {symbol}: {status}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  SOME TESTS FAILED - Review the issues above")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

