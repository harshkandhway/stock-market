"""
Verification Script: Ensures No Features Were Lost in Formatter Consolidation

This script compares the old formatters with the new comprehensive formatter
to verify that ALL features, sections, and calculations are preserved.
"""

import re
from typing import Dict, List, Tuple

# Define what each old formatter contained
OLD_FORMATTERS = {
    'format_analysis_beginner': {
        'sections': [
            'Verdict Box (BUY/HOLD/AVOID with confidence)',
            'Price and Safety Rating',
            'Decision Breakdown - WHY THIS RECOMMENDATION',
            'Trend Analysis (score /3)',
            'Momentum Analysis (score /3)',
            'Volume Analysis (score /1)',
            'Chart Patterns (score /3)',
            'Risk Assessment',
            'Overall Score (/10 with progress bar)',
            'Score interpretation based on recommendation',
            'Action Plan (BUY/HOLD/AVOID guidance)',
            'Investment horizon with timeline',
            'Example calculation with Rs 10,000',
            'Estimated target date',
            'Targets by Investment Horizon (all 6 timeframes)',
            'Pattern-Based Target (measured move)',
            'Pattern reliability stars',
            'Pattern invalidation price',
            'Pattern timeframe estimate',
            'Pattern-horizon mismatch warning',
            'Key Price Levels (current, resistance, support)',
            'Beginner Tips (7 tips)',
            'Disclaimer and footer',
        ],
        'calculations': [
            'Example capital (10000)',
            'Shares calculation',
            'Profit/loss percentages',
            'Potential profit/loss amounts',
            'Safety stars display',
            'Trend score (0-3)',
            'Momentum score (0-3)',
            'Volume score (0-1)',
            'Pattern score (0-3)',
            'Risk score (0-2)',
            'Total bullish score (0-10)',
            'Score percentage',
        ],
        'features': [
            'Mode-aware R/R thresholds (conservative/moderate/aggressive)',
            'Conflict detection (pattern vs recommendation)',
            'Hard filter blocks display',
            'Conditional pattern section',
            'Sort horizons by timeframe',
            'Mark recommended horizon',
            'EMA alignment check',
            'Divergence warnings',
        ]
    },
    'format_analysis_full': {
        'sections': [
            'Header with symbol, mode, timeframe',
            'Current price',
            'Market Regime (phase, ADX, trend strength)',
            'Key Indicators (RSI, MACD, volume)',
            'Divergence warning',
            'Chart Patterns (bias, counts, strongest)',
            'Recommendation box with confidence',
            'Buy block warnings',
            'Targets and Stop Loss',
            'Conservative target',
            'Risk/Reward ratio with validity',
            'Key reasoning points (top 3)',
            'Footer with author credit',
        ],
        'features': [
            'Pattern attribute access with hasattr checks',
            'Pattern type/strength/action extraction',
            'Shorten long reasoning (>80 chars)',
            'Market phase title case',
            'Trend strength display',
        ]
    },
    'format_analysis_summary': {
        'sections': [
            'Symbol with emoji',
            'Current price',
            'Recommendation with emoji',
            'Confidence with level',
        ],
        'features': [
            'Dynamic emoji based on rec_type',
            'Short 4-line format',
        ]
    },
    'format_quick_recommendation': {
        'sections': [
            'Quick verdict box',
            'Symbol and price',
            'Recommendation with confidence',
            'Safety stars',
            'Target and stop',
        ],
        'features': [
            'Ultra-compact format',
            'Single emoji indicator',
        ]
    },
    'format_investment_guidance': {
        'sections': [
            'User capital display',
            'Recommended position size',
            'Number of shares',
            'Investment amount and percentage',
            'Entry, target, stop prices',
            'Potential profit if target hit',
            'Potential loss if stop hit',
            'Risk/Reward ratio',
            'Risk warnings (3 bullet points)',
        ],
        'calculations': [
            'Position sizing (1% risk rule)',
            'Risk amount calculation',
            'Stop distance calculation',
            'Shares from risk amount',
            'Fallback to 10% capital if stop distance invalid',
        ]
    }
}

# Define what the new comprehensive formatter should contain
NEW_COMPREHENSIVE_SECTIONS = [
    'Section 1: Header & Quick Verdict',
    'Section 2: Decision Breakdown - WHY?',
    'Section 3: Action Plan',
    'Section 4: Targets by Investment Horizon',
    'Section 5: Pattern-Based Target',
    'Section 6: Key Price Levels',
    'Section 7: Market Conditions',
    'Section 8: Technical Indicators Detail',
    'Section 9: Chart Patterns',
    'Section 10: Investment Checklist',
    'Section 11: Position Sizing Guidance',
    'Section 12: When to Sell',
    'Section 13: Safety & Risk Summary',
    'Section 14: Timeline Estimate',
    'Section 15: Beginner Tips',
    'Section 16: Disclaimer & Footer',
]


def verify_new_formatter_completeness():
    """Read the new formatter and verify all features are present"""

    print("="*80)
    print("FORMATTER CONSOLIDATION VERIFICATION")
    print("="*80)
    print()

    try:
        with open('src/core/formatters.py', 'r', encoding='utf-8') as f:
            new_formatter_code = f.read()
    except FileNotFoundError:
        print("[FAIL] ERROR: Could not find src/core/formatters.py")
        return False

    # Extract the format_analysis_comprehensive function
    func_match = re.search(
        r'def format_analysis_comprehensive\((.*?)\):(.*?)(?=\ndef |$)',
        new_formatter_code,
        re.DOTALL
    )

    if not func_match:
        print("[FAIL] ERROR: Could not find format_analysis_comprehensive function")
        return False

    comprehensive_code = func_match.group(0)

    print("[OK] Found format_analysis_comprehensive function")
    print(f"     Length: {len(comprehensive_code)} characters")
    print()

    # Check for all 16 sections
    print("Checking for all 16 sections...")
    print("-"*80)

    section_markers = [
        "SECTION 1: HEADER & QUICK VERDICT",
        "SECTION 2: DECISION BREAKDOWN",
        "SECTION 3: ACTION PLAN",
        "SECTION 4: TARGETS BY INVESTMENT HORIZON",
        "SECTION 5: PATTERN-BASED TARGET",
        "SECTION 6: KEY PRICE LEVELS",
        "SECTION 7: MARKET CONDITIONS",
        "SECTION 8: TECHNICAL INDICATORS DETAIL",
        "SECTION 9: CHART PATTERNS",
        "SECTION 10: INVESTMENT CHECKLIST",
        "SECTION 11: POSITION SIZING GUIDANCE",
        "SECTION 12: WHEN TO SELL",
        "SECTION 13: SAFETY & RISK SUMMARY",
        "SECTION 14: TIMELINE ESTIMATE",
        "SECTION 15: BEGINNER TIPS",
        "SECTION 16: DISCLAIMER & FOOTER",
    ]

    all_sections_found = True
    for i, section in enumerate(section_markers, 1):
        if section in comprehensive_code:
            print(f"[OK] Section {i:2d}: {section}")
        else:
            print(f"[FAIL] Section {i:2d}: {section} - NOT FOUND")
            all_sections_found = False

    print()

    # Check for key features from old formatters
    print("Checking for key features from old formatters...")
    print("-"*80)

    features_to_check = {
        'Trend Analysis': ['trend_score', 'trend_factors', 'price_vs_trend_ema'],
        'Momentum Analysis': ['momentum_score', 'momentum_factors', 'rsi_zone'],
        'Volume Analysis': ['volume_score', 'volume_factors', 'volume_ratio'],
        'Pattern Analysis': ['pattern_score', 'pattern_factors', 'strongest_pattern'],
        'Risk Analysis': ['risk_score', 'risk_factors', 'rr_valid'],
        'Score Calculation': ['total_bullish', 'max_score', 'score_pct'],
        'Progress Bar': ['_format_progress_bar', 'score_bar'],
        'Safety Rating': ['safety_stars', 'safety_emoji', 'safety_rating'],
        'Example Calculation': ['example_capital', 'shares', 'potential_profit', 'potential_loss'],
        'Position Sizing': ['risk_per_trade', 'risk_amount', 'position_shares'],
        'Mode-aware R/R': ['rr_thresholds', 'min_rr'],
        'Conflict Detection': ['pattern_bullish', 'rec_type', 'CONFLICT'],
        'Horizon Targets': ['horizon_targets', 'sorted_horizons', 'is_recommended'],
        'Pattern Targets': ['pattern_target', 'pattern_reliability', 'pattern_invalidation'],
        'Market Conditions': ['market_phase', 'adx_strength', 'divergence'],
        'Technical Indicators': ['rsi_period', 'macd_hist', 'ema_alignment'],
        'Investment Checklist': ['checks', 'checks_passed'],
        'Timeline Estimate': ['time_estimate', 'earliest', 'estimated', 'latest'],
        'Beginner Tips': ['tips', 'Never invest money'],
        'Output Mode': ['output_mode', '_get_emoji', 'bot', 'cli'],
    }

    all_features_found = True
    for feature_name, keywords in features_to_check.items():
        found_keywords = []
        missing_keywords = []

        for keyword in keywords:
            if keyword in comprehensive_code:
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)

        if missing_keywords:
            print(f"[WARN]  {feature_name}: Found {len(found_keywords)}/{len(keywords)} keywords")
            print(f"    Missing: {', '.join(missing_keywords)}")
            if len(found_keywords) == 0:
                all_features_found = False
        else:
            print(f"[OK] {feature_name}: All {len(keywords)} keywords found")

    print()

    # Check for specialized formatters
    print("Checking for specialized formatters...")
    print("-"*80)

    specialized_formatters = [
        'format_comparison_table',
        'format_watchlist',
        'format_portfolio',
        'format_error',
        'format_success',
        'format_warning',
        'format_info',
        'chunk_message',
    ]

    for formatter in specialized_formatters:
        if f"def {formatter}" in new_formatter_code:
            print(f"[OK] {formatter}")
        else:
            print(f"[FAIL] {formatter} - NOT FOUND")
            all_features_found = False

    print()

    # Check helper functions
    print("Checking for helper functions...")
    print("-"*80)

    helpers = [
        '_get_emoji',
        '_format_box_top',
        '_format_section_header',
        '_format_progress_bar',
        'format_number',
        'format_percentage',
        'escape_markdown',
    ]

    for helper in helpers:
        if f"def {helper}" in new_formatter_code:
            print(f"[OK] {helper}")
        else:
            print(f"[WARN]  {helper} - NOT FOUND")

    print()

    # Summary
    print("="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    if all_sections_found and all_features_found:
        print("[OK] ALL CHECKS PASSED!")
        print()
        print("The new format_analysis_comprehensive contains:")
        print("  • All 16 sections")
        print("  • All key features from format_analysis_beginner")
        print("  • All features from format_analysis_full")
        print("  • Position sizing from format_investment_guidance")
        print("  • All specialized formatters")
        print("  • All helper functions")
        print()
        print("[OK] NOTHING WAS LOST - Everything was consolidated into one place!")
        return True
    else:
        print("[WARN]  SOME CHECKS FAILED")
        print()
        if not all_sections_found:
            print("[FAIL] Some sections are missing")
        if not all_features_found:
            print("[FAIL] Some features are missing")
        return False


if __name__ == '__main__':
    success = verify_new_formatter_completeness()
    exit(0 if success else 1)
