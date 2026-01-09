"""
Final Comprehensive Verification Test
Tests all critical scenarios to ensure recommendation logic is working correctly
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.bot.services.analysis_service import analyze_stock

def verify_recommendation(symbol, description):
    """Verify recommendation logic for a stock"""
    print(f"\n{'='*80}")
    print(f"VERIFYING: {symbol}")
    print(f"Description: {description}")
    print(f"{'='*80}")
    
    try:
        analysis = analyze_stock(symbol, mode='balanced', horizon='1week', use_cache=False)
        
        confidence = analysis['confidence']
        recommendation = analysis['recommendation']
        rec_type = analysis['recommendation_type']
        risk_reward = analysis['risk_reward']
        rr_valid = analysis['rr_valid']
        is_buy_blocked = analysis.get('is_buy_blocked', False)
        
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
        
        print(f"\n📊 Metrics:")
        print(f"   Confidence: {confidence:.1f}%")
        print(f"   Recommendation: {recommendation}")
        print(f"   Type: {rec_type}")
        print(f"   Score: {total_score}/10 ({score_pct:.1f}%)")
        print(f"   R:R: {risk_reward:.2f}:1 (Valid: {rr_valid}, Min Required: 2.0:1)")
        print(f"   Buy Blocked: {is_buy_blocked}")
        
        # Validation rules
        print(f"\n✅ Validation Rules Applied:")
        rules_passed = []
        rules_failed = []
        
        # Rule 1: Invalid R:R should downgrade BUY
        if not rr_valid:
            if rec_type == 'BUY':
                rules_failed.append("❌ Invalid R:R but still BUY")
            else:
                rules_passed.append("✓ Invalid R:R correctly downgraded to HOLD")
        else:
            rules_passed.append("✓ R:R is valid")
        
        # Rule 2: Low score (<40%) should not be BUY
        if score_pct < 40:
            if rec_type == 'BUY':
                rules_failed.append(f"❌ Score {score_pct:.1f}% < 40% but still BUY")
            else:
                rules_passed.append(f"✓ Low score {score_pct:.1f}% correctly not BUY")
        else:
            rules_passed.append(f"✓ Score {score_pct:.1f}% is acceptable")
        
        # Rule 3: Confidence thresholds
        if rec_type == 'BUY':
            if confidence < 60:
                rules_failed.append(f"❌ BUY with confidence {confidence:.1f}% < 60%")
            elif confidence < 70 and 'STRONG' not in recommendation:
                rules_passed.append(f"✓ WEAK BUY with confidence {confidence:.1f}% (≥60%)")
            else:
                rules_passed.append(f"✓ BUY with confidence {confidence:.1f}% (≥70%)")
        
        # Rule 4: Blocked trades should not be BUY
        if is_buy_blocked:
            if rec_type == 'BUY':
                rules_failed.append("❌ Buy blocked but still showing BUY")
            else:
                rules_passed.append("✓ Buy blocked correctly prevents BUY")
        
        # Display results
        for rule in rules_passed:
            print(f"   {rule}")
        
        if rules_failed:
            print(f"\n⚠️  Issues Found:")
            for rule in rules_failed:
                print(f"   {rule}")
            return False
        else:
            print(f"\n✅ All validation rules passed!")
            return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run final verification"""
    print("="*80)
    print("FINAL COMPREHENSIVE VERIFICATION")
    print("="*80)
    print("\nTesting 5 stocks to verify:")
    print("  1. Invalid R:R downgrades BUY to HOLD")
    print("  2. Low scores (<40%) prevent BUY")
    print("  3. Confidence thresholds enforced (WEAK_BUY ≥60%, BUY ≥70%)")
    print("  4. Blocked trades don't show BUY")
    
    test_cases = [
        ("TCS.NS", "Original problematic case - should be HOLD"),
        ("RELIANCE.NS", "Low score case - should be HOLD"),
        ("INFY.NS", "Low score with patterns - should be HOLD"),
        ("HDFCBANK.NS", "Blocked case - should not be BUY"),
        ("ICICIBANK.NS", "High confidence but invalid R:R - should be HOLD"),
    ]
    
    results = {}
    for symbol, description in test_cases:
        result = verify_recommendation(symbol, description)
        results[symbol] = result
    
    # Summary
    print(f"\n{'='*80}")
    print("FINAL VERIFICATION SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nTotal Stocks Tested: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    
    print(f"\nDetailed Results:")
    for symbol, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {symbol}: {status}")
    
    if passed == total:
        print(f"\n🎉 ALL VERIFICATIONS PASSED!")
        print(f"\n✅ Recommendation logic is working correctly:")
        print(f"   • Invalid R:R correctly downgrades BUY")
        print(f"   • Low scores correctly prevent BUY")
        print(f"   • Confidence thresholds are enforced")
        print(f"   • Blocked trades are handled correctly")
        return 0
    else:
        print(f"\n⚠️  SOME VERIFICATIONS FAILED")
        print(f"   Review the issues above")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

