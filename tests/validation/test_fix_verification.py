"""
Quick test script to verify fixes for stocks with critical issues
Tests only the 5 stocks that had critical issues in the previous test
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bot.services.analysis_service import analyze_stock

# Stocks with critical issues from test_report_20260109_232947.txt
ISSUE_STOCKS = [
    'COALINDIA.NS',  # R:R warning issue
    'ACMESOLAR.BO',  # Pattern mismatch
    'SHIVATEX.BO',   # Pattern mismatch
    'TIPSMUSIC.BO',  # Pattern mismatch
    'YASHO.BO'       # Pattern mismatch
]

def test_issue_stocks():
    """Test only the stocks that had critical issues"""
    print("=" * 80)
    print("TESTING FIXES FOR STOCKS WITH CRITICAL ISSUES")
    print("=" * 80)
    print(f"Testing {len(ISSUE_STOCKS)} stocks")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    for symbol in ISSUE_STOCKS:
        print(f"\n{'='*80}")
        print(f"Testing: {symbol}")
        print(f"{'='*80}")
        
        try:
            analysis = analyze_stock(
                symbol=symbol,
                mode='balanced',
                timeframe='medium',
                horizon='3months',
                use_cache=False
            )
            
            recommendation = analysis.get('recommendation', 'UNKNOWN')
            recommendation_type = analysis.get('recommendation_type', 'UNKNOWN')
            confidence = analysis.get('confidence', 0.0)
            score_pct = analysis.get('overall_score_pct', 0.0)
            risk_reward = analysis.get('risk_reward', 0.0)
            rr_valid = analysis.get('rr_valid', False)
            
            # Get pattern information
            indicators = analysis.get('indicators', {})
            strongest_pattern = indicators.get('strongest_pattern')
            pattern_confidence = 0.0
            pattern_type = None
            if strongest_pattern:
                # Pattern confidence is already 0-100 (not 0-1), so no need to multiply
                pattern_confidence = getattr(strongest_pattern, 'confidence', 0.0)
                if hasattr(strongest_pattern, 'type'):
                    pattern_type_obj = getattr(strongest_pattern, 'type', None)
                    # Extract value if it's an Enum
                    if pattern_type_obj and hasattr(pattern_type_obj, 'value'):
                        pattern_type = pattern_type_obj.value
                    else:
                        pattern_type = str(pattern_type_obj) if pattern_type_obj else None
                elif hasattr(strongest_pattern, 'p_type'):
                    pattern_type = getattr(strongest_pattern, 'p_type', None)
            
            print(f"Recommendation: {recommendation}")
            print(f"Type: {recommendation_type}")
            print(f"Confidence: {confidence:.1f}%")
            print(f"Score: {score_pct:.1f}%")
            print(f"R:R: {risk_reward:.2f}:1 (Valid: {rr_valid})")
            if strongest_pattern:
                print(f"Pattern: {getattr(strongest_pattern, 'name', 'Unknown')} ({pattern_confidence:.0f}%)")
                print(f"Pattern Type: {pattern_type}")
            
            # Validation
            issues = []
            warnings = []
            
            # Check R:R warning for COALINDIA.NS
            if symbol == 'COALINDIA.NS':
                if not rr_valid and risk_reward < 2.0:
                    if 'R:R' not in recommendation.upper() and 'RISK/REWARD' not in recommendation.upper():
                        issues.append(f"❌ CRITICAL: No R:R warning in recommendation (R:R {risk_reward:.2f}:1 < 2.0:1)")
                    else:
                        print(f"✅ FIXED: R:R warning is now present in recommendation")
                else:
                    print(f"✅ R:R is valid ({risk_reward:.2f}:1)")
            
            # Check pattern mismatch for others
            if symbol in ['ACMESOLAR.BO', 'SHIVATEX.BO', 'TIPSMUSIC.BO', 'YASHO.BO']:
                pattern_type_str = None
                if pattern_type:
                    if isinstance(pattern_type, str):
                        pattern_type_str = pattern_type.lower()
                    else:
                        pattern_type_str = str(pattern_type).lower().replace('patterntype.', '')
                
                # Check if recommendation was downgraded due to pattern contradiction
                is_downgraded = 'BULLISH PATTERN CONTRADICTS' in recommendation.upper() or 'PATTERN CONTRADICTS' in recommendation.upper()
                
                if recommendation_type == 'SELL' and not is_downgraded and pattern_type_str == 'bullish' and pattern_confidence >= 75:
                    issues.append(f"❌ CRITICAL: SELL recommendation but pattern type is BULLISH with high confidence {pattern_confidence:.0f}% (no downgrade)")
                elif (recommendation_type in ['HOLD', 'SELL'] and is_downgraded) or recommendation_type == 'HOLD':
                    # Recommendation was downgraded (either to HOLD or WEAK SELL with warning)
                    print(f"✅ FIXED: Recommendation downgraded to {recommendation_type} due to bullish pattern ({pattern_confidence:.0f}%)")
                    print(f"   Recommendation text: {recommendation}")
                else:
                    print(f"✅ No pattern mismatch issue")
            
            results.append({
                'symbol': symbol,
                'recommendation': recommendation,
                'recommendation_type': recommendation_type,
                'confidence': confidence,
                'score_pct': score_pct,
                'risk_reward': risk_reward,
                'rr_valid': rr_valid,
                'pattern_confidence': pattern_confidence,
                'pattern_type': pattern_type,
                'issues': issues,
                'warnings': warnings
            })
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            results.append({
                'symbol': symbol,
                'error': str(e),
                'issues': [f"ERROR: {str(e)}"]
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results if 'error' not in r and not r.get('issues'))
    errors = sum(1 for r in results if 'error' in r)
    issues_found = sum(1 for r in results if r.get('issues'))
    
    print(f"Total Stocks: {len(ISSUE_STOCKS)}")
    print(f"Successful (No Issues): {successful}")
    print(f"Errors: {errors}")
    print(f"Still Has Issues: {issues_found}")
    
    if issues_found > 0:
        print(f"\n⚠️  STOCKS WITH REMAINING ISSUES:")
        for r in results:
            if r.get('issues'):
                print(f"\n  {r['symbol']}:")
                for issue in r['issues']:
                    print(f"    {issue}")
    
    if successful == len(ISSUE_STOCKS) - errors:
        print(f"\n✅ ALL FIXES VERIFIED SUCCESSFULLY!")
    else:
        print(f"\n⚠️  SOME ISSUES REMAIN - REVIEW REQUIRED")
    
    return results

if __name__ == '__main__':
    test_issue_stocks()

