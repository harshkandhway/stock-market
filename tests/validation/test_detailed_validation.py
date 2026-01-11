"""
Detailed Validation Test
Tests edge cases and specific scenarios
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.bot.services.analysis_service import analyze_stock

def test_scenario(name, symbol, expected_behavior):
    """Test a specific scenario"""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {name}")
    print(f"Stock: {symbol}")
    print(f"{'='*80}")
    
    try:
        analysis = analyze_stock(symbol, mode='balanced', horizon='1week', use_cache=False)
        
        confidence = analysis['confidence']
        recommendation = analysis['recommendation']
        rec_type = analysis['recommendation_type']
        risk_reward = analysis['risk_reward']
        rr_valid = analysis['rr_valid']
        
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
        
        risk_score = 1 if rr_valid else 0
        total_score = trend_score + momentum_score + volume_score + pattern_score + risk_score
        score_pct = (total_score / 10) * 100
        
        print(f"\nResults:")
        print(f"   Confidence: {confidence:.1f}%")
        print(f"   Recommendation: {recommendation}")
        print(f"   Type: {rec_type}")
        print(f"   Score: {total_score}/10 ({score_pct:.1f}%)")
        print(f"   R:R: {risk_reward:.2f}:1 (Valid: {rr_valid})")
        
        # Check expected behavior
        print(f"\nExpected: {expected_behavior}")
        
        passed = True
        if "should be HOLD" in expected_behavior.lower():
            if rec_type != 'HOLD':
                print(f"   ❌ FAIL: Expected HOLD, got {rec_type}")
                passed = False
            else:
                print(f"   ✅ PASS: Correctly shows HOLD")
        
        if "should not be BUY" in expected_behavior.lower():
            if rec_type == 'BUY':
                print(f"   ❌ FAIL: Should not be BUY, but got BUY")
                passed = False
            else:
                print(f"   ✅ PASS: Correctly not BUY")
        
        if "invalid R:R" in expected_behavior.lower():
            if rr_valid:
                print(f"   ❌ FAIL: R:R should be invalid")
                passed = False
            else:
                print(f"   ✅ PASS: R:R correctly invalid")
        
        if "low score" in expected_behavior.lower():
            if score_pct >= 40:
                print(f"   ❌ FAIL: Score should be <40%, got {score_pct:.1f}%")
                passed = False
            else:
                print(f"   ✅ PASS: Score correctly low ({score_pct:.1f}%)")
        
        return passed
        
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run detailed validation tests"""
    print("="*80)
    print("DETAILED VALIDATION TEST SUITE")
    print("="*80)
    
    scenarios = [
        ("Low Score + Invalid R:R", "TCS.NS", "Should be HOLD (not BUY) - low score and invalid R:R"),
        ("Very Low Score", "RELIANCE.NS", "Should be HOLD (not BUY) - very low score"),
        ("High Confidence but Invalid R:R", "ICICIBANK.NS", "Should be HOLD - invalid R:R should downgrade even with high confidence"),
        ("Low Score with Patterns", "INFY.NS", "Should be HOLD - patterns alone shouldn't drive BUY with low score"),
    ]
    
    results = {}
    for name, symbol, expected in scenarios:
        result = test_scenario(name, symbol, expected)
        results[name] = result
    
    # Summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nTotal Scenarios: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {name}: {status}")
    
    if passed == total:
        print(f"\n🎉 ALL VALIDATION TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  SOME VALIDATION TESTS FAILED")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

