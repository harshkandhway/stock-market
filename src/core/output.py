"""
CLI Output Module for Stock Analyzer Pro
Thin wrapper around core formatters with ASCII-safe output

This module has been refactored to use the unified formatter system.
All formatting logic is now in src/core/formatters.py

Author: Harsh Kandhway
"""

import sys
import io
from typing import Dict, List, Optional
from datetime import datetime

from .formatters import (
    format_analysis_comprehensive,
    format_comparison_table,
    format_portfolio
)
from .config import CURRENCY_SYMBOL

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass


# ============================================================================
# MAIN CLI OUTPUT FUNCTIONS
# ============================================================================

def print_full_report(
    analysis: Dict,
    position_data: Optional[Dict] = None,
    horizon: str = '3months'
):
    """
    Print complete analysis report to console using comprehensive formatter.

    This is the main output function for CLI analysis.
    All 16 sections are included automatically.

    Args:
        analysis: Analysis dictionary from analysis_service
        position_data: Optional position data with 'capital' key
        horizon: Investment horizon
    """
    capital = position_data.get('capital') if position_data else None

    output = format_analysis_comprehensive(
        analysis,
        output_mode='cli',
        capital=capital,
        horizon=horizon
    )

    print(output)


def print_summary_table(analyses: List[Dict]):
    """
    Print comparison table for multiple stocks.

    Args:
        analyses: List of analysis dictionaries
    """
    output = format_comparison_table(analyses, output_mode='cli')
    print(output)


def print_portfolio_ranking(analyses: List[Dict]):
    """
    Print stocks ranked by safety score.

    Args:
        analyses: List of analysis dictionaries
    """
    # Sort by safety score
    sorted_analyses = sorted(
        analyses,
        key=lambda x: x.get('safety_score', {}).get('stars', 0),
        reverse=True
    )

    output = format_comparison_table(sorted_analyses, output_mode='cli')
    print(output)


def print_portfolio_allocation(allocation_data: Dict, capital: float):
    """
    Print portfolio allocation suggestions.

    Args:
        allocation_data: Allocation dictionary with 'investable' and 'not_recommended' lists
        capital: Total capital
    """
    output = format_portfolio(allocation_data, output_mode='cli')
    print(output)


def print_disclaimer():
    """Print standard disclaimer."""
    print(f"\n{'='*80}")
    print(f"  [!] IMPORTANT DISCLAIMER")
    print(f"{'='*80}")
    print(f"  * This is for educational purposes only - NOT financial advice")
    print(f"  * Past performance does not guarantee future results")
    print(f"  * Always consult a SEBI-registered financial advisor")
    print(f"  * Never invest more than you can afford to lose")
    print(f"  * The author is not responsible for any investment losses")
    print(f"{'='*80}")
    print(f"  Developed by Harsh Kandhway | Stock Analyzer Pro v3.0")
    print(f"{'='*80}\n")


# ============================================================================
# HELPER FUNCTIONS (Kept for backwards compatibility)
# ============================================================================

def format_price(price: float) -> str:
    """Format price with currency symbol"""
    return f"{CURRENCY_SYMBOL}{price:,.2f}"


def format_percentage(pct: float, include_sign: bool = True) -> str:
    """Format percentage"""
    if include_sign:
        return f"{pct:+.1f}%"
    return f"{pct:.1f}%"


# ============================================================================
# LEGACY FUNCTIONS (Deprecated - redirect to new functions)
# ============================================================================

def print_header(symbol: str, mode: str, timeframe: str):
    """
    Legacy header function - redirects to print_full_report.

    DEPRECATED: Use print_full_report() instead.
    """
    pass  # Header is now part of comprehensive formatter


def print_beginner_header(symbol: str, horizon: str, analysis_date: datetime = None):
    """
    Legacy beginner header function.

    DEPRECATED: Header is now part of format_analysis_comprehensive.
    """
    pass


def print_quick_summary(analysis: Dict, horizon: str = '3months'):
    """
    DEPRECATED: Quick summary is now part of format_analysis_comprehensive.
    """
    pass


def print_investment_plan(analysis: Dict, horizon: str = '3months'):
    """
    DEPRECATED: Investment plan is now part of format_analysis_comprehensive.
    """
    pass


def print_profit_loss_calculator(analysis: Dict, capital: Optional[float] = None):
    """
    DEPRECATED: P&L calculator is now part of format_analysis_comprehensive.
    """
    pass


def print_market_conditions(analysis: Dict):
    """
    DEPRECATED: Market conditions are now part of format_analysis_comprehensive.
    """
    pass


def print_chart_patterns(analysis: Dict):
    """
    DEPRECATED: Chart patterns are now part of format_analysis_comprehensive.
    """
    pass


def print_important_price_levels(analysis: Dict):
    """
    DEPRECATED: Price levels are now part of format_analysis_comprehensive.
    """
    pass


def print_simple_checklist(analysis: Dict):
    """
    DEPRECATED: Checklist is now part of format_analysis_comprehensive.
    """
    pass


def print_when_to_sell(analysis: Dict, horizon: str = '3months'):
    """
    DEPRECATED: Sell guidance is now part of format_analysis_comprehensive.
    """
    pass


def print_beginner_tips(analysis: Dict):
    """
    DEPRECATED: Tips are now part of format_analysis_comprehensive.
    """
    pass


def print_decision_breakdown(analysis: Dict):
    """
    DEPRECATED: Decision breakdown is now part of format_analysis_comprehensive.
    """
    pass


def print_hard_filter_warning(is_blocked: bool, block_reasons: List[str], direction: str):
    """
    DEPRECATED: Warnings are now part of format_analysis_comprehensive.
    """
    pass


def print_market_regime(indicators: Dict):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass


def print_indicator_table(indicators: Dict, signal_data: Dict):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass


def print_signal_summary(signal_data: Dict):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass


def print_recommendation_box(recommendation: str, confidence: float, confidence_level: str, is_blocked: bool):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass


def print_reasoning(reasoning: List[str]):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass


def print_action_plan(actions: Dict[str, str]):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass


def print_price_levels(indicators: Dict, target_data: Dict, stop_data: Dict):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass


def print_risk_reward(risk_reward: float, is_valid: bool, explanation: str, mode: str):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass


def print_position_sizing(position_data: Dict):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass


def print_trailing_stop_strategy(trailing_data: Dict):
    """DEPRECATED: Now handled by format_analysis_comprehensive"""
    pass
