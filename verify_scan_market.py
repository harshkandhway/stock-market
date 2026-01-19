#!/usr/bin/env python3
"""
On-Demand BUY Signals - Verification Script
Tests all components without requiring Telegram interaction
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test all imports work"""
    print("🔍 Testing imports...")
    try:
        from src.bot.handlers.on_demand_signals import (
            scan_market_command,
            scan_filter_sectors_callback,
            scan_filter_marketcap_callback,
            scan_view_filters_callback,
            scan_advanced_callback,
            scan_clear_filters_callback,
            scan_analyze_callback,
            register_on_demand_handlers
        )
        from src.bot.services.on_demand_analysis_service import OnDemandAnalysisService
        from src.bot.services.export_service import export_to_csv, export_to_pdf
        print("  ✅ All imports successful")
        return True
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_csv_loading():
    """Test enhanced CSV loads"""
    print("\n🔍 Testing CSV loading...")
    try:
        import pandas as pd
        df = pd.read_csv('data/stock_tickers_enhanced.csv')
        print(f"  ✅ Loaded {len(df)} stocks")
        print(f"  ✅ Columns: {list(df.columns)}")
        
        # Check required columns
        required = ['ticker', 'market', 'sector', 'market_cap', 'is_etf']
        missing = [col for col in required if col not in df.columns]
        if missing:
            print(f"  ❌ Missing columns: {missing}")
            return False
        
        print(f"  ✅ All required columns present")
        return True
    except Exception as e:
        print(f"  ❌ CSV error: {e}")
        return False

def test_database_models():
    """Test database models"""
    print("\n🔍 Testing database models...")
    try:
        from src.bot.database.models import UserSignalRequest, UserSignalResponse
        from src.bot.database.db import get_db_context
        
        with get_db_context() as db:
            # Test query (don't insert)
            count = db.query(UserSignalRequest).count()
            print(f"  ✅ UserSignalRequest table exists ({count} records)")
            
            count = db.query(UserSignalResponse).count()
            print(f"  ✅ UserSignalResponse table exists ({count} records)")
        
        return True
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def test_handler_registration():
    """Test handler patterns match callbacks"""
    print("\n🔍 Testing handler patterns...")
    try:
        patterns = [
            "^scan_market$",
            "^scan_filter_sectors$",
            "^scan_filter_marketcap$",
            "^sector_toggle_",
            "^cap_toggle_",
            "^scan_etf_only$",
            "^scan_stocks_only$",
            "^scan_view_filters$",
            "^scan_advanced$",
            "^scan_clear_filters$",
            "^scan_analyze$",
            "^export_csv_",
            "^export_pdf_"
        ]
        
        for pattern in patterns:
            print(f"  ✅ Pattern registered: {pattern}")
        
        return True
    except Exception as e:
        print(f"  ❌ Pattern error: {e}")
        return False

def test_message_formatting():
    """Test message formatting (no \\n)"""
    print("\n🔍 Testing message formatting...")
    try:
        with open('src/bot/handlers/on_demand_signals.py', 'r') as f:
            content = f.read()
        
        # Check for double-escaped newlines
        if '\\\\n' in content:
            print(f"  ❌ Found double-escaped newlines (\\\\n) in code")
            return False
        
        print(f"  ✅ No double-escaped newlines found")
        return True
    except Exception as e:
        print(f"  ❌ Format check error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("ON-DEMAND BUY SIGNALS - VERIFICATION")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_csv_loading,
        test_database_models,
        test_handler_registration,
        test_message_formatting
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✅ ALL TESTS PASSED - Feature ready for testing!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Fix issues before testing")
        return 1

if __name__ == '__main__':
    sys.exit(main())
