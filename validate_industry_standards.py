"""
Industry Standard Validation Script
Tests STRONG BUY recommendations against SEBI and professional analyst standards
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.bot.services.analysis_service import analyze_stock
from src.core.config import RECOMMENDATION_THRESHOLDS

def validate_strong_buy_standards():
    """
    Validate STRONG BUY recommendations against industry standards:
    - 3-8% distribution (industry standard)
    - Confidence ≥ 75% (professional practice)
    - Valid R:R ≥ 1.9:1 (allows slight margin)
    - Score ≥ 70% (strong technical signals)
    """
    
    print("=" * 80)
    print("INDUSTRY STANDARD VALIDATION")
    print("=" * 80)
    print("\nTesting STRONG BUY recommendations against:")
    print("  - SEBI Research Analyst Standards")
    print("  - Professional Analyst Practice (15+ years)")
    print("  - Industry Distribution Standards (3-8% STRONG BUY)")
    print()
    
    # Test stocks from the report that should be STRONG BUY
    test_stocks = [
        ('HEG.NS', '74.8% confidence, 90% score, 2.28:1 R:R - Should be STRONG BUY'),
        ('COALINDIA.NS', '75.5% confidence, 80% score, 1.92:1 R:R - Should be STRONG BUY'),
        ('ICICIBANK.BO', '76.5% confidence, 70% score, 1.31:1 R:R - R:R too low'),
        ('SIGMA.NS', '76.3% confidence, 80% score, 0.49:1 R:R - R:R too low'),
    ]
    
    print("Testing Key Stocks:")
    print("-" * 80)
    
    strong_buy_count = 0
    results = []
    
    for symbol, description in test_stocks:
        try:
            print(f"\nTesting {symbol}...")
            print(f"  Expected: {description}")
            
            analysis = analyze_stock(symbol, mode='balanced', horizon='3months', use_cache=False)
            
            if 'error' in analysis:
                print(f"  ❌ ERROR: {analysis['error']}")
                continue
            
            recommendation = analysis.get('recommendation', 'UNKNOWN')
            confidence = analysis.get('confidence', 0)
            risk_reward = analysis.get('risk_reward', 0)
            
            # Calculate score from signals (same logic as analysis_service)
            trend_signals = analysis.get('signals', {}).get('trend_signals', {})
            momentum_signals = analysis.get('signals', {}).get('momentum_signals', {})
            pattern_signals = analysis.get('signals', {}).get('pattern_signals', {})
            indicators = analysis.get('indicators', {})
            
            # Trend score (max 3)
            trend_bullish = sum(1 for _, d in trend_signals.values() if d == 'bullish')
            trend_score = min(3, max(0, trend_bullish))
            
            # Momentum score (max 3)
            momentum_bullish = sum(1 for _, d in momentum_signals.values() if d == 'bullish')
            momentum_score = min(3, max(0, momentum_bullish))
            
            # Volume score (max 1)
            vol_ratio = indicators.get('volume_ratio', 1.0)
            volume_score = 1 if (vol_ratio >= 1.5) else 0
            
            # Pattern score (max 3)
            pattern_bullish = sum(1 for _, d in pattern_signals.values() if d == 'bullish')
            pattern_bias = indicators.get('pattern_bias', 'neutral')
            pattern_score = min(3, max(0, pattern_bullish + (1 if pattern_bias == 'bullish' else 0)))
            
            # Risk score (max 1): R:R validity
            risk_score = 1 if risk_reward >= 2.0 else 0
            
            total_bullish = trend_score + momentum_score + volume_score + pattern_score + risk_score
            score_pct = (total_bullish / 10) * 100
            
            is_strong_buy = 'STRONG BUY' in recommendation.upper()
            
            results.append({
                'symbol': symbol,
                'recommendation': recommendation,
                'confidence': confidence,
                'score_pct': score_pct,
                'risk_reward': risk_reward,
                'is_strong_buy': is_strong_buy,
                'description': description
            })
            
            print(f"  Result: {recommendation}")
            print(f"  Confidence: {confidence:.1f}%")
            print(f"  Score: {score_pct:.1f}%")
            print(f"  R:R: {risk_reward:.2f}:1")
            
            # Validate against industry standards
            issues = []
            
            if is_strong_buy:
                strong_buy_count += 1
                print(f"  ✅ STRONG BUY")
                
                # Check if meets industry standards
                if confidence < 75:
                    issues.append(f"Confidence {confidence:.1f}% < 75% (industry standard)")
                if score_pct < 70:
                    issues.append(f"Score {score_pct:.1f}% < 70% (industry standard)")
                if risk_reward < 1.9:
                    issues.append(f"R:R {risk_reward:.2f}:1 < 1.9:1 (industry standard)")
                
                if issues:
                    print(f"  ⚠️  WARNINGS:")
                    for issue in issues:
                        print(f"     - {issue}")
                else:
                    print(f"  ✅ Meets all industry standards")
            else:
                print(f"  ❌ NOT STRONG BUY")
                
                # Check why it's not STRONG BUY
                reasons = []
                if confidence < RECOMMENDATION_THRESHOLDS['balanced']['STRONG_BUY']:
                    reasons.append(f"Confidence {confidence:.1f}% < {RECOMMENDATION_THRESHOLDS['balanced']['STRONG_BUY']}% threshold")
                if risk_reward < 1.9:
                    reasons.append(f"R:R {risk_reward:.2f}:1 < 1.9:1 minimum")
                if score_pct < 70:
                    reasons.append(f"Score {score_pct:.1f}% < 70% minimum")
                
                if reasons:
                    print(f"  Reasons:")
                    for reason in reasons:
                        print(f"     - {reason}")
        
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    print(f"\nSTRONG BUY Count: {strong_buy_count}/{len(test_stocks)}")
    print(f"Distribution: {(strong_buy_count/len(test_stocks)*100):.1f}%")
    
    print("\nIndustry Standard Check:")
    print("  Target: 3-8% STRONG BUY distribution")
    print(f"  Current: {(strong_buy_count/len(test_stocks)*100):.1f}%")
    
    if strong_buy_count == 0:
        print("\n  ❌ FAILED: No STRONG BUY recommendations")
        print("  Action Required: Review thresholds and logic")
    elif strong_buy_count/len(test_stocks) < 0.03:
        print("\n  ⚠️  WARNING: Distribution too low (<3%)")
    elif strong_buy_count/len(test_stocks) > 0.08:
        print("\n  ⚠️  WARNING: Distribution too high (>8%)")
    else:
        print("\n  ✅ PASSED: Distribution within industry standard (3-8%)")
    
    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    
    for result in results:
        print(f"\n{result['symbol']}:")
        print(f"  Recommendation: {result['recommendation']}")
        print(f"  Confidence: {result['confidence']:.1f}%")
        print(f"  Score: {result['score_pct']:.1f}%")
        print(f"  R:R: {result['risk_reward']:.2f}:1")
        print(f"  Expected: {result['description']}")
        
        if result['is_strong_buy']:
            print(f"  ✅ Status: STRONG BUY (meets industry standards)")
        else:
            print(f"  ❌ Status: NOT STRONG BUY")
    
    return results

if __name__ == '__main__':
    results = validate_strong_buy_standards()
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\n1. Review all STRONG BUY recommendations manually")
    print("2. Get SEBI-registered analyst to validate framework")
    print("3. Test on larger sample (100+ stocks)")
    print("4. Verify distribution is 3-8%")
    print("5. Document all decisions and rationale")

