"""
Comprehensive Stock Testing Framework
Tests all stocks from stock_tickers.csv with expert-level validation

Author: Harsh Kandhway
Purpose: Validate recommendation logic before public rollout
"""

import sys
import os
import csv
import time
from datetime import datetime
from typing import Dict, List, Tuple, Any
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.bot.services.analysis_service import analyze_stock
from src.core.formatters import format_analysis_comprehensive

# Expert-level validation rules (20+ years trading experience + Professional Standards)
# Aligned with Bloomberg, Zacks, TipRanks, TradingView, MetaTrader
EXPERT_VALIDATION_RULES = {
    'min_confidence_for_strong_buy': 75,  # Professional standard (Bloomberg, Zacks, TipRanks)
    'min_score_for_strong_buy': 70,  # Professional standard
    'min_rr_for_strong_buy': 1.8,  # Professional exception minimum (1.8:1)
    'min_confidence_for_buy': 70,  # Increased from 60% (professional standard)
    'min_score_for_buy': 40,  # Minimum score % for BUY
    'min_rr_for_buy': 2.0,  # Minimum R:R for BUY (balanced mode)
    'max_rr_warning': 1.95,  # R:R below this needs warning even with high score
    'min_confidence_for_weak_buy': 60,  # Increased from 55% (professional standard)
    'pattern_confidence_min': 50,  # Minimum pattern confidence to trust
    'adx_min_for_trend': 20,  # Minimum ADX for reliable trend
    'adx_preferred_for_strong_buy': 25,  # Preferred ADX for STRONG BUY (MetaTrader/TradingView)
    'min_confirmations_for_strong_buy': 3,  # Preferred bullish indicators for STRONG BUY
    'rsi_extreme_threshold': 30,  # RSI < 30 or > 70 needs caution
    'volume_min_for_confirmation': 1.2,  # Volume should be at least 1.2x for confirmation
    'strong_buy_distribution_min': 3.0,  # Industry standard minimum %
    'strong_buy_distribution_max': 8.0,  # Industry standard maximum %
}

# Critical issues that must be fixed
CRITICAL_ISSUES = {
    'invalid_buy_low_score': [],  # BUY with score < 40%
    'invalid_buy_low_rr': [],  # BUY with R:R < 2.0:1 (no warning)
    'invalid_buy_low_confidence': [],  # BUY with confidence < 60%
    'pattern_mismatch': [],  # Pattern type doesn't match recommendation
    'contradictory_signals': [],  # All indicators bearish but BUY
    'missing_pattern_validation': [],  # Pattern detected but confidence/type invalid
    'rr_calculation_error': [],  # R:R calculation seems wrong
    'target_stop_error': [],  # Target/Stop calculation seems wrong
}

# Warnings (should review but not critical)
WARNINGS = {
    'weak_buy_high_risk': [],  # WEAK BUY with high risk factors
    'pattern_low_confidence': [],  # Pattern detected but low confidence
    'trend_weak_adx': [],  # Trend signal but ADX too low
    'volume_low_confirmation': [],  # Buy signal but volume doesn't confirm
    'rsi_extreme': [],  # RSI in extreme zone but still BUY
}

def load_stock_list(csv_path: str) -> List[str]:
    """Load all stock tickers from CSV"""
    stocks = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get('ticker', '').strip()
                if ticker:
                    stocks.append(ticker)
        print(f"✅ Loaded {len(stocks)} stocks from {csv_path}")
        return stocks
    except Exception as e:
        print(f"❌ Error loading stocks: {e}")
        return []

def calculate_score(analysis: Dict[str, Any]) -> Tuple[int, float]:
    """Calculate overall score matching formatter logic"""
    indicators = analysis['indicators']
    
    # Trend score (max 3)
    trend_score = 0
    if indicators.get('price_vs_trend_ema') == 'above':
        trend_score += 1
    if indicators.get('price_vs_medium_ema') == 'above':
        trend_score += 1
    if indicators.get('ema_alignment') in ['strong_bullish', 'bullish']:
        trend_score += 1
    
    # Momentum score (max 3)
    momentum_score = 0
    if indicators.get('rsi_zone') in ['oversold', 'extremely_oversold']:
        momentum_score += 1
    if indicators.get('macd_hist', 0) > 0:
        momentum_score += 1
    if indicators.get('adx', 0) >= 25:
        momentum_score += 1
    
    # Volume score (max 1)
    volume_score = 1 if indicators.get('volume_ratio', 1.0) >= 1.5 else 0
    
    # Pattern score (max 3)
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
    
    # Risk score (max 1)
    risk_score = 1 if analysis['rr_valid'] else 0
    
    total_score = trend_score + momentum_score + volume_score + pattern_score + risk_score
    score_pct = (total_score / 10) * 100
    
    return total_score, score_pct

def validate_expert_rules(symbol: str, analysis: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Validate analysis against expert trading rules
    Returns: (critical_issues, warnings)
    """
    critical_issues = []
    warnings = []
    
    confidence = analysis['confidence']
    recommendation = analysis['recommendation']
    rec_type = analysis['recommendation_type']
    risk_reward = analysis['risk_reward']
    rr_valid = analysis['rr_valid']
    indicators = analysis['indicators']
    
    total_score, score_pct = calculate_score(analysis)
    
    # CRITICAL: STRONG BUY validation (Professional Standard)
    is_strong_buy = 'STRONG BUY' in recommendation.upper()
    if is_strong_buy:
        # STRONG BUY must have confidence ≥75% (professional standard)
        if confidence < EXPERT_VALIDATION_RULES['min_confidence_for_strong_buy']:
            critical_issues.append(
                f"STRONG BUY with confidence {confidence:.1f}% < {EXPERT_VALIDATION_RULES['min_confidence_for_strong_buy']}% (professional standard)"
            )
        
        # STRONG BUY must have score ≥70% (professional standard)
        if score_pct < EXPERT_VALIDATION_RULES['min_score_for_strong_buy']:
            critical_issues.append(
                f"STRONG BUY with score {total_score}/10 ({score_pct:.1f}%) < {EXPERT_VALIDATION_RULES['min_score_for_strong_buy']}% (professional standard)"
            )
        
        # STRONG BUY must have R:R ≥1.8:1 (professional exception minimum)
        if risk_reward < EXPERT_VALIDATION_RULES['min_rr_for_strong_buy']:
            critical_issues.append(
                f"STRONG BUY with R:R {risk_reward:.2f}:1 < {EXPERT_VALIDATION_RULES['min_rr_for_strong_buy']}:1 (professional minimum)"
            )
    
    # CRITICAL: BUY with low score
    if rec_type == 'BUY' and not is_strong_buy and score_pct < EXPERT_VALIDATION_RULES['min_score_for_buy']:
        critical_issues.append(
            f"BUY recommendation with score {total_score}/10 ({score_pct:.1f}%) < {EXPERT_VALIDATION_RULES['min_score_for_buy']}%"
        )
    
    # CRITICAL: BUY with low confidence (70% for BUY, 60% for WEAK BUY)
    if rec_type == 'BUY' and not is_strong_buy:
        if 'WEAK BUY' in recommendation.upper():
            min_conf = EXPERT_VALIDATION_RULES.get('min_confidence_for_weak_buy', 60)
        else:
            min_conf = EXPERT_VALIDATION_RULES['min_confidence_for_buy']
        
        if confidence < min_conf:
            critical_issues.append(
                f"{recommendation} with confidence {confidence:.1f}% < {min_conf}% (professional standard)"
            )
    
    # CRITICAL: BUY with invalid R:R (unless it's the special warning case)
    if rec_type == 'BUY' and not rr_valid:
        if 'R:R' not in recommendation.upper() and 'RISK/REWARD' not in recommendation.upper():
            critical_issues.append(
                f"BUY recommendation with invalid R:R {risk_reward:.2f}:1 < {EXPERT_VALIDATION_RULES['min_rr_for_buy']}:1 (no warning in recommendation)"
            )
        elif risk_reward < EXPERT_VALIDATION_RULES['max_rr_warning']:
            # Even with warning, if R:R is too low, it's critical
            if score_pct < 70 or confidence < 70:
                critical_issues.append(
                    f"BUY with R:R warning but R:R {risk_reward:.2f}:1 too low and score/confidence not high enough"
                )
    
    # CRITICAL: Contradictory signals (all bearish but BUY)
    trend_bullish = sum(1 for k, v in [
        ('price_vs_trend_ema', 'above'),
        ('price_vs_medium_ema', 'above'),
        ('ema_alignment', ['strong_bullish', 'bullish'])
    ] if indicators.get(k) == v or (isinstance(v, list) and indicators.get(k) in v))
    
    momentum_bullish = sum(1 for k, v in [
        ('rsi_zone', ['oversold', 'extremely_oversold']),
        ('macd_hist', lambda x: x > 0),
        ('adx', lambda x: x >= 25)
    ] if (isinstance(v, list) and indicators.get(k) in v) or (callable(v) and v(indicators.get(k, 0))))
    
    if rec_type == 'BUY' and trend_bullish == 0 and momentum_bullish == 0:
        critical_issues.append(
            f"BUY recommendation but all trend and momentum indicators are bearish (0/6 bullish)"
        )
    
    # CRITICAL: AVOID/BLOCKED with extremely strong signals (contradiction)
    # This catches cases like: 9/10 score, 3.6:1 R:R, strong bullish pattern, but showing AVOID
    # Professional standard: Only flag if signals meet override criteria but still blocked
    if rec_type == 'BLOCKED' or 'AVOID' in recommendation.upper():
        # Check if signals meet the STRICT override criteria (professional standard)
        # Override should happen if:
        # - Score >= 90% AND R:R >= 3.0:1 AND confidence >= 65%, OR
        # - Score >= 85% AND R:R >= 4.0:1 AND confidence >= 65%, OR
        # - ALL: Score >= 85%, R:R >= 3.5:1, Pattern >= 80%, ADX >= 30
        
        meets_override_criteria = False
        
        # Check for exceptional score + R:R combinations
        exceptional_combo_1 = (score_pct >= 90 and risk_reward >= 3.0 and confidence >= 65)
        exceptional_combo_2 = (score_pct >= 85 and risk_reward >= 4.0 and confidence >= 65)
        
        # Check for all 4 conditions
        has_exceptional_score = score_pct >= 85
        has_exceptional_rr = risk_reward >= 3.5
        has_very_strong_pattern = False
        has_very_strong_trend = False
        
        if strongest_pattern:
            try:
                pattern_conf = getattr(strongest_pattern, 'confidence', 0)
                pattern_type_val = None
                if hasattr(strongest_pattern, 'type'):
                    if hasattr(strongest_pattern.type, 'value'):
                        pattern_type_val = strongest_pattern.type.value
                    else:
                        pattern_type_val = str(strongest_pattern.type)
                
                if pattern_type_val and pattern_type_val.lower() == 'bullish' and pattern_conf >= 80:
                    has_very_strong_pattern = True
            except:
                pass
        
        adx = indicators.get('adx', 0)
        if adx >= 30:
            has_very_strong_trend = True
        
        all_conditions_met = (has_exceptional_score and has_exceptional_rr and 
                             has_very_strong_pattern and has_very_strong_trend)
        
        meets_override_criteria = exceptional_combo_1 or exceptional_combo_2 or all_conditions_met
        
        if meets_override_criteria:
            # This is a contradiction - signals meet override criteria but still blocked
            # Only flag if it's NOT already handled with a warning override
            if 'DIVERGENCE WARNING' not in recommendation.upper() and 'EXCEPTIONAL SIGNALS' not in recommendation.upper():
                critical_issues.append(
                    f"AVOID/BLOCKED recommendation but signals meet override criteria: "
                    f"score {score_pct:.1f}%, R:R {risk_reward:.2f}:1, confidence {confidence:.1f}% - "
                    f"should be overridden per professional standards"
                )
    
    # CRITICAL: Pattern validation
    strongest_pattern = indicators.get('strongest_pattern')
    if strongest_pattern:
        try:
            pattern_conf = getattr(strongest_pattern, 'confidence', 0)
            pattern_type = None
            if hasattr(strongest_pattern, 'type'):
                if hasattr(strongest_pattern.type, 'value'):
                    pattern_type = strongest_pattern.type.value
                else:
                    pattern_type = str(strongest_pattern.type)
            
            if pattern_conf < EXPERT_VALIDATION_RULES['pattern_confidence_min']:
                critical_issues.append(
                    f"Pattern detected with low confidence {pattern_conf}% < {EXPERT_VALIDATION_RULES['pattern_confidence_min']}%"
                )
            
            # Pattern type should match recommendation
            # BUT: Only flag as critical if pattern confidence is high (>70%) AND contradicts recommendation
            # Low confidence patterns can be overridden by other strong signals (professional practice)
            if rec_type == 'BUY' and pattern_type and pattern_type.lower() == 'bearish':
                if pattern_conf > 70:
                    # High confidence bearish pattern but BUY - check if contradiction is already handled
                    # If recommendation contains "BEARISH PATTERN CONTRADICTS", it's already being handled
                    if 'BEARISH PATTERN CONTRADICTS' in recommendation.upper() or 'STRONG BEARISH PATTERN CONTRADICTS' in recommendation.upper():
                        # Contradiction is already handled in the recommendation - not a critical issue
                        pass
                    else:
                        # High confidence bearish pattern but BUY - this is a real contradiction
                        critical_issues.append(
                            f"BUY recommendation but pattern type is BEARISH with high confidence {pattern_conf}% - contradiction"
                        )
                else:
                    # Low confidence pattern - acceptable to override with other signals
                    warnings.append(
                        f"BUY recommendation but pattern type is BEARISH (confidence {pattern_conf}%) - verify manually"
                    )
            elif rec_type == 'SELL' and pattern_type and pattern_type.lower() == 'bullish':
                if pattern_conf > 70:
                    # High confidence bullish pattern but SELL - check if contradiction is already handled
                    # If recommendation contains "BULLISH PATTERN CONTRADICTS", it's already being handled
                    if 'BULLISH PATTERN CONTRADICTS' in recommendation.upper() or 'STRONG BULLISH PATTERN CONTRADICTS' in recommendation.upper():
                        # Contradiction is already handled in the recommendation - not a critical issue
                        pass
                    else:
                        # High confidence bullish pattern but SELL - this is a real contradiction
                        critical_issues.append(
                            f"SELL recommendation but pattern type is BULLISH with high confidence {pattern_conf}% - contradiction"
                        )
                else:
                    # Low confidence pattern - acceptable to override with other signals
                    warnings.append(
                        f"SELL recommendation but pattern type is BULLISH (confidence {pattern_conf}%) - verify manually"
                    )
        except Exception as e:
            critical_issues.append(f"Error validating pattern: {str(e)}")
    
    # CRITICAL: R:R calculation validation
    current_price = analysis['current_price']
    target = analysis['target']
    stop_loss = analysis['stop_loss']
    
    calculated_reward = abs(target - current_price)
    calculated_risk = abs(current_price - stop_loss)
    calculated_rr = calculated_reward / calculated_risk if calculated_risk > 0 else 0
    
    if abs(calculated_rr - risk_reward) > 0.1:  # Allow small rounding differences
        critical_issues.append(
            f"R:R calculation mismatch: reported {risk_reward:.2f}:1 vs calculated {calculated_rr:.2f}:1"
        )
    
    # WARNINGS: Weak buy with high risk
    if 'WEAK BUY' in recommendation.upper() and score_pct < 50:
        warnings.append(
            f"WEAK BUY with score {score_pct:.1f}% - high risk"
        )
    
    # WARNINGS: Pattern low confidence
    if strongest_pattern:
        pattern_conf = getattr(strongest_pattern, 'confidence', 0)
        if pattern_conf < 60:
            warnings.append(
                f"Pattern confidence {pattern_conf}% is moderate - verify manually"
            )
    
    # WARNINGS: Trend signal but ADX too low
    adx = indicators.get('adx', 0)
    if rec_type == 'BUY' and adx < EXPERT_VALIDATION_RULES['adx_min_for_trend']:
        warnings.append(
            f"BUY recommendation but ADX {adx:.1f} < {EXPERT_VALIDATION_RULES['adx_min_for_trend']} - weak trend"
        )
    
    # WARNINGS: Volume doesn't confirm
    volume_ratio = indicators.get('volume_ratio', 1.0)
    if rec_type == 'BUY' and volume_ratio < EXPERT_VALIDATION_RULES['volume_min_for_confirmation']:
        warnings.append(
            f"BUY recommendation but volume {volume_ratio:.2f}x < {EXPERT_VALIDATION_RULES['volume_min_for_confirmation']}x - weak confirmation"
        )
    
    # WARNINGS: RSI extreme
    rsi = indicators.get('rsi', 50)
    if rec_type == 'BUY' and (rsi > 70 or rsi < 30):
        warnings.append(
            f"BUY recommendation but RSI {rsi:.1f} is in extreme zone ({'overbought' if rsi > 70 else 'oversold'})"
        )
    
    return critical_issues, warnings

def test_single_stock(symbol: str, mode: str = 'balanced', horizon: str = '1week') -> Dict[str, Any]:
    """Test a single stock and return results"""
    result = {
        'symbol': symbol,
        'status': 'success',
        'error': None,
        'analysis': None,
        'critical_issues': [],
        'warnings': [],
        'metrics': {}
    }
    
    try:
        # Perform analysis
        analysis = analyze_stock(
            symbol=symbol,
            mode=mode,
            timeframe='medium',
            horizon=horizon,
            use_cache=False
        )
        
        result['analysis'] = analysis
        
        # Extract metrics
        result['metrics'] = {
            'confidence': analysis['confidence'],
            'recommendation': analysis['recommendation'],
            'rec_type': analysis['recommendation_type'],
            'risk_reward': analysis['risk_reward'],
            'rr_valid': analysis['rr_valid'],
            'score': calculate_score(analysis)[0],
            'score_pct': calculate_score(analysis)[1],
        }
        
        # Validate with expert rules
        critical_issues, warnings = validate_expert_rules(symbol, analysis)
        result['critical_issues'] = critical_issues
        result['warnings'] = warnings
        
    except ValueError as e:
        result['status'] = 'error'
        result['error'] = f"Data/Validation Error: {str(e)}"
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f"Unexpected Error: {str(e)}"
    
    return result

def run_comprehensive_test(csv_path: str, max_stocks: int = None, sample_size: int = None, offset: int = 0):
    """
    Run comprehensive test on all stocks
    
    Args:
        csv_path: Path to stock_tickers.csv
        max_stocks: Maximum number of stocks to test (None = all)
        sample_size: If provided, test random sample of this size
    """
    print("="*80)
    print("COMPREHENSIVE STOCK TESTING FRAMEWORK")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load stocks
    all_stocks = load_stock_list(csv_path)
    if not all_stocks:
        print("❌ No stocks loaded. Exiting.")
        return
    
    # Apply limits
    if sample_size and sample_size < len(all_stocks):
        if offset > 0:
            # Test specific range: offset to offset+sample_size
            end_idx = min(offset + sample_size, len(all_stocks))
            test_stocks = all_stocks[offset:end_idx]
            print(f"📊 Testing stocks {offset+1} to {end_idx} ({len(test_stocks)} stocks)")
        else:
            # Random sample
            import random
            random.seed(42)  # Reproducible
            test_stocks = random.sample(all_stocks, sample_size)
            print(f"📊 Testing random sample of {sample_size} stocks")
    elif max_stocks:
        test_stocks = all_stocks[:max_stocks]
        print(f"📊 Testing first {max_stocks} stocks")
    else:
        test_stocks = all_stocks
        print(f"📊 Testing ALL {len(test_stocks)} stocks")
    
    print()
    
    # Test results
    results = []
    stats = {
        'total': 0,
        'success': 0,
        'errors': 0,
        'critical_issues': 0,
        'warnings': 0,
        'buy_recommendations': 0,
        'hold_recommendations': 0,
        'sell_recommendations': 0,
        'blocked_recommendations': 0,
    }
    
    # Categorize issues
    issue_categories = defaultdict(list)
    warning_categories = defaultdict(list)
    
    # Test each stock
    start_time = time.time()
    for i, symbol in enumerate(test_stocks, 1):
        print(f"[{i}/{len(test_stocks)}] Testing {symbol}...", end=' ', flush=True)
        
        result = test_single_stock(symbol, mode='balanced', horizon='1week')
        results.append(result)
        
        stats['total'] += 1
        
        if result['status'] == 'success':
            stats['success'] += 1
            
            # Count recommendations
            rec_type = result['metrics'].get('rec_type', 'UNKNOWN')
            recommendation = result['metrics'].get('recommendation', '')
            is_strong_buy = 'STRONG BUY' in recommendation.upper()
            
            if rec_type == 'BUY':
                if is_strong_buy:
                    stats['strong_buy_recommendations'] = stats.get('strong_buy_recommendations', 0) + 1
                else:
                    stats['buy_recommendations'] += 1
            elif rec_type == 'HOLD':
                stats['hold_recommendations'] += 1
            elif rec_type == 'SELL':
                stats['sell_recommendations'] += 1
            elif rec_type == 'BLOCKED':
                stats['blocked_recommendations'] = stats.get('blocked_recommendations', 0) + 1
            
            # Count issues
            if result['critical_issues']:
                stats['critical_issues'] += len(result['critical_issues'])
                for issue in result['critical_issues']:
                    issue_type = issue.split(':')[0] if ':' in issue else 'general'
                    issue_categories[issue_type].append((symbol, issue))
            
            if result['warnings']:
                stats['warnings'] += len(result['warnings'])
                for warning in result['warnings']:
                    warning_type = warning.split(':')[0] if ':' in warning else 'general'
                    warning_categories[warning_type].append((symbol, warning))
            
            # Status indicator
            if result['critical_issues']:
                print("❌ CRITICAL ISSUES")
            elif result['warnings']:
                print("⚠️  WARNINGS")
            else:
                print("✅ OK")
        else:
            stats['errors'] += 1
            print(f"❌ ERROR: {result['error']}")
        
        # Progress update every 50 stocks
        if i % 50 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed
            remaining = (len(test_stocks) - i) / rate if rate > 0 else 0
            print(f"\n   Progress: {i}/{len(test_stocks)} ({i/len(test_stocks)*100:.1f}%)")
            print(f"   Elapsed: {elapsed/60:.1f} min | Estimated remaining: {remaining/60:.1f} min")
            print()
    
    elapsed_time = time.time() - start_time
    
    # Generate comprehensive report
    print("\n" + "="*80)
    print("TEST SUMMARY REPORT")
    print("="*80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Time: {elapsed_time/60:.1f} minutes")
    print()
    
    print(f"📊 STATISTICS:")
    print(f"   Total Stocks Tested: {stats['total']}")
    print(f"   ✅ Successful: {stats['success']}")
    print(f"   ❌ Errors: {stats['errors']}")
    print(f"   🔴 Critical Issues: {stats['critical_issues']}")
    print(f"   ⚠️  Warnings: {stats['warnings']}")
    print()
    
    print(f"📈 RECOMMENDATION DISTRIBUTION:")
    if stats['success'] > 0:
        strong_buy_count = stats.get('strong_buy_recommendations', 0)
        strong_buy_pct = (strong_buy_count / stats['success'] * 100) if stats['success'] > 0 else 0
        
        print(f"   🟢 STRONG BUY: {strong_buy_count} ({strong_buy_pct:.1f}%)")
        
        # Validate STRONG BUY distribution (industry standard: 3-8%)
        if strong_buy_pct < EXPERT_VALIDATION_RULES['strong_buy_distribution_min']:
            print(f"      ⚠️  WARNING: Distribution {strong_buy_pct:.1f}% < {EXPERT_VALIDATION_RULES['strong_buy_distribution_min']}% (industry minimum)")
        elif strong_buy_pct > EXPERT_VALIDATION_RULES['strong_buy_distribution_max']:
            print(f"      ⚠️  WARNING: Distribution {strong_buy_pct:.1f}% > {EXPERT_VALIDATION_RULES['strong_buy_distribution_max']}% (industry maximum)")
        else:
            print(f"      ✅ Distribution within industry standard (3-8%)")
        
        print(f"   BUY: {stats['buy_recommendations']} ({stats['buy_recommendations']/stats['success']*100:.1f}%)")
        print(f"   HOLD: {stats['hold_recommendations']} ({stats['hold_recommendations']/stats['success']*100:.1f}%)")
        print(f"   SELL: {stats['sell_recommendations']} ({stats['sell_recommendations']/stats['success']*100:.1f}%)")
        if stats.get('blocked_recommendations', 0) > 0:
            print(f"   BLOCKED: {stats['blocked_recommendations']} ({stats['blocked_recommendations']/stats['success']*100:.1f}%)")
    print()
    
    # Critical Issues Report
    if issue_categories:
        print("="*80)
        print("🔴 CRITICAL ISSUES (MUST FIX BEFORE ROLLOUT)")
        print("="*80)
        
        for issue_type, issues in sorted(issue_categories.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n{issue_type.upper()} ({len(issues)} occurrences):")
            for symbol, issue in issues[:10]:  # Show first 10
                print(f"   {symbol}: {issue}")
            if len(issues) > 10:
                print(f"   ... and {len(issues) - 10} more")
        print()
    else:
        print("✅ NO CRITICAL ISSUES FOUND!")
        print()
    
    # Warnings Report
    if warning_categories:
        print("="*80)
        print("⚠️  WARNINGS (REVIEW RECOMMENDED)")
        print("="*80)
        
        for warning_type, warnings in sorted(warning_categories.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n{warning_type.upper()} ({len(warnings)} occurrences):")
            for symbol, warning in warnings[:5]:  # Show first 5
                print(f"   {symbol}: {warning}")
            if len(warnings) > 5:
                print(f"   ... and {len(warnings) - 5} more")
        print()
    
    # Error Report
    error_stocks = [r for r in results if r['status'] == 'error']
    if error_stocks:
        print("="*80)
        print("❌ ERRORS (Data/API Issues)")
        print("="*80)
        error_types = defaultdict(list)
        for r in error_stocks:
            error_types[r['error']].append(r['symbol'])
        
        for error, symbols in error_types.items():
            print(f"\n{error}:")
            print(f"   Affected stocks: {len(symbols)}")
            if len(symbols) <= 10:
                print(f"   {', '.join(symbols)}")
            else:
                print(f"   {', '.join(symbols[:10])} ... and {len(symbols) - 10} more")
        print()
    
    # Detailed issue breakdown
    print("="*80)
    print("DETAILED ISSUE BREAKDOWN")
    print("="*80)
    
    # Stocks with critical issues
    critical_stocks = [r for r in results if r['critical_issues']]
    if critical_stocks:
        print(f"\n🔴 Stocks with Critical Issues: {len(critical_stocks)}")
        print("   These MUST be fixed before rollout:")
        for r in critical_stocks[:20]:  # Show first 20
            print(f"\n   {r['symbol']}:")
            print(f"      Recommendation: {r['metrics'].get('recommendation', 'N/A')}")
            print(f"      Confidence: {r['metrics'].get('confidence', 0):.1f}%")
            print(f"      Score: {r['metrics'].get('score', 0)}/10 ({r['metrics'].get('score_pct', 0):.1f}%)")
            print(f"      R:R: {r['metrics'].get('risk_reward', 0):.2f}:1")
            for issue in r['critical_issues']:
                print(f"      ❌ {issue}")
        if len(critical_stocks) > 20:
            print(f"\n   ... and {len(critical_stocks) - 20} more stocks with critical issues")
    
    # Final verdict
    print("\n" + "="*80)
    print("FINAL VERDICT")
    print("="*80)
    
    if stats['critical_issues'] == 0:
        print("✅ ALL TESTS PASSED - READY FOR ROLLOUT")
        print("\n   No critical issues found. The system is safe to deploy.")
    else:
        print("❌ NOT READY FOR ROLLOUT")
        print(f"\n   Found {stats['critical_issues']} critical issues across {len(critical_stocks)} stocks.")
        print("   These must be fixed before public release.")
        print("\n   Recommended actions:")
        print("   1. Review all critical issues above")
        print("   2. Fix recommendation logic for edge cases")
        print("   3. Validate pattern detection accuracy")
        print("   4. Re-run tests after fixes")
        print("   5. Get expert review of fixes")
    
    # Save detailed report
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    save_detailed_report(results, stats, issue_categories, warning_categories, report_file)
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    return stats['critical_issues'] == 0

def save_detailed_report(results, stats, issue_categories, warning_categories, filename):
    """Save detailed test report to file"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("COMPREHENSIVE STOCK TESTING REPORT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("SUMMARY\n")
        f.write("-"*80 + "\n")
        f.write(f"Total Stocks: {stats['total']}\n")
        f.write(f"Successful: {stats['success']}\n")
        f.write(f"Errors: {stats['errors']}\n")
        f.write(f"Critical Issues: {stats['critical_issues']}\n")
        f.write(f"Warnings: {stats['warnings']}\n\n")
        
        # Critical issues
        if issue_categories:
            f.write("CRITICAL ISSUES\n")
            f.write("-"*80 + "\n")
            for issue_type, issues in sorted(issue_categories.items(), key=lambda x: len(x[1]), reverse=True):
                f.write(f"\n{issue_type.upper()} ({len(issues)} occurrences):\n")
                for symbol, issue in issues:
                    f.write(f"  {symbol}: {issue}\n")
            f.write("\n")
        
        # All results
        f.write("DETAILED RESULTS\n")
        f.write("-"*80 + "\n")
        for r in results:
            f.write(f"\n{r['symbol']}:\n")
            if r['status'] == 'success':
                f.write(f"  Recommendation: {r['metrics'].get('recommendation', 'N/A')}\n")
                f.write(f"  Confidence: {r['metrics'].get('confidence', 0):.1f}%\n")
                f.write(f"  Score: {r['metrics'].get('score', 0)}/10 ({r['metrics'].get('score_pct', 0):.1f}%)\n")
                f.write(f"  R:R: {r['metrics'].get('risk_reward', 0):.2f}:1\n")
                if r['critical_issues']:
                    f.write("  Critical Issues:\n")
                    for issue in r['critical_issues']:
                        f.write(f"    - {issue}\n")
                if r['warnings']:
                    f.write("  Warnings:\n")
                    for warning in r['warnings']:
                        f.write(f"    - {warning}\n")
            else:
                f.write(f"  ERROR: {r['error']}\n")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive Stock Testing Framework')
    parser.add_argument('--csv', default='data/stock_tickers.csv', help='Path to stock_tickers.csv')
    parser.add_argument('--max', type=int, help='Maximum number of stocks to test')
    parser.add_argument('--sample', type=int, help='Test random sample of N stocks')
    parser.add_argument('--offset', type=int, default=0, help='Start from this index (for testing next batch)')
    parser.add_argument('--quick', action='store_true', help='Quick test with 10 stocks')
    
    args = parser.parse_args()
    
    if args.quick:
        max_stocks = 10
        sample_size = None
    else:
        max_stocks = args.max
        sample_size = args.sample
    
    success = run_comprehensive_test(
        csv_path=args.csv,
        max_stocks=max_stocks,
        sample_size=sample_size
    )
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

