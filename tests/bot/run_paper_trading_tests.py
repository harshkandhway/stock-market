#!/usr/bin/env python3
"""
Test Runner for Paper Trading System
Runs all paper trading tests and generates report

Author: Harsh Kandhway
"""

import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def run_tests():
    """Run all paper trading tests"""
    print("=" * 70)
    print("PAPER TRADING SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Test files to run
    test_files = [
        "tests/bot/test_paper_trading_market_hours.py",
        "tests/bot/test_paper_trading_services.py",
        "tests/bot/test_paper_trading_pending_trades.py",
        "tests/bot/test_paper_trading_handlers.py",
        "tests/bot/test_paper_trading_scheduler.py",
        "tests/bot/test_paper_trading_integration.py",
        "tests/bot/test_paper_trading_comprehensive.py",
    ]
    
    # Check which files exist
    existing_tests = []
    for test_file in test_files:
        test_path = project_root / test_file
        if test_path.exists():
            existing_tests.append(test_file)
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    if not existing_tests:
        print("❌ No test files found!")
        return False
    
    print(f"Found {len(existing_tests)} test files\n")
    print("Running tests...\n")
    
    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        "--color=yes",  # Colored output
        "-x",  # Stop on first failure (remove for full run)
    ] + existing_tests
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        success = result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return success


def run_with_coverage():
    """Run tests with coverage report"""
    print("=" * 70)
    print("PAPER TRADING SYSTEM - TEST COVERAGE REPORT")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    test_files = [
        "tests/bot/test_paper_trading_*.py",
    ]
    
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "--cov=src.bot.services.paper_trading",
        "--cov=src.bot.services.market_hours_service",
        "--cov=src.bot.services.paper_portfolio_service",
        "--cov=src.bot.services.paper_trade_execution_service",
        "--cov=src.bot.services.paper_trade_analysis_service",
        "--cov=src.bot.services.paper_trading_scheduler",
        "--cov=src.bot.handlers.paper_trading",
        "--cov=src.bot.handlers.callbacks",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/paper_trading",
    ] + test_files
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running coverage: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--coverage":
        success = run_with_coverage()
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1)


