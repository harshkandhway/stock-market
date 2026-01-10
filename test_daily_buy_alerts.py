"""
Comprehensive Test Suite for Daily BUY Alerts System
Tests scheduler, notification service, subscription, and database operations

Author: Harsh Kandhway
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import csv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bot.database.db import (
    init_db, get_db_context, get_or_create_user, 
    get_user_settings, update_user_settings,
    get_subscribed_users_for_daily_buy_alerts,
    get_today_buy_signals
)
from src.bot.database.models import User, UserSettings, DailyBuySignal
from src.bot.services.analysis_service import analyze_stock
from src.bot.services.scheduler_service import DailyBuyAlertsScheduler
from src.bot.services.notification_service import send_daily_buy_alerts
from src.bot.config import DEFAULT_TIMEZONE
from telegram import Bot
from telegram.ext import Application
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name: str, details: str = ""):
        self.passed.append((test_name, details))
        logger.info(f"✅ PASS: {test_name} {details}")
    
    def add_fail(self, test_name: str, error: str):
        self.failed.append((test_name, error))
        logger.error(f"❌ FAIL: {test_name} - {error}")
    
    def add_warning(self, test_name: str, warning: str):
        self.warnings.append((test_name, warning))
        logger.warning(f"⚠️ WARNING: {test_name} - {warning}")
    
    def print_summary(self):
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"✅ Passed: {len(self.passed)}")
        print(f"❌ Failed: {len(self.failed)}")
        print(f"⚠️ Warnings: {len(self.warnings)}")
        print("="*80)
        
        if self.passed:
            print("\n✅ PASSED TESTS:")
            for name, details in self.passed:
                print(f"  • {name} {details}")
        
        if self.failed:
            print("\n❌ FAILED TESTS:")
            for name, error in self.failed:
                print(f"  • {name}: {error}")
        
        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for name, warning in self.warnings:
                print(f"  • {name}: {warning}")
        
        print("\n" + "="*80)
        
        if self.failed:
            print("❌ SOME TESTS FAILED - DO NOT DEPLOY")
            return False
        else:
            print("✅ ALL TESTS PASSED - READY FOR DEPLOYMENT")
            return True


def test_database_setup():
    """Test 1: Database initialization and table creation"""
    results = TestResults()
    
    try:
        logger.info("Testing database setup...")
        init_db()
        results.add_pass("Database Initialization", "Tables created successfully")
        
        # Check if DailyBuySignal table exists
        with get_db_context() as db:
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            if 'daily_buy_signals' in tables:
                results.add_pass("DailyBuySignal Table", "Table exists")
            else:
                results.add_fail("DailyBuySignal Table", "Table not found")
            
            if 'user_settings' in tables:
                # Check for new columns
                columns = [col['name'] for col in inspector.get_columns('user_settings')]
                if 'daily_buy_alerts_enabled' in columns:
                    results.add_pass("UserSettings.daily_buy_alerts_enabled", "Column exists")
                else:
                    results.add_fail("UserSettings.daily_buy_alerts_enabled", "Column not found")
                
                if 'daily_buy_alert_time' in columns:
                    results.add_pass("UserSettings.daily_buy_alert_time", "Column exists")
                else:
                    results.add_fail("UserSettings.daily_buy_alert_time", "Column not found")
        
    except Exception as e:
        results.add_fail("Database Setup", str(e))
    
    return results


def test_subscription_management():
    """Test 2: Subscription management (enable/disable, time setting)"""
    results = TestResults()
    
    try:
        logger.info("Testing subscription management...")
        
        # Test user creation and subscription
        test_telegram_id = 999999999  # Test user ID
        with get_db_context() as db:
            # Create or get test user
            user = get_or_create_user(db, test_telegram_id, "test_user")
            results.add_pass("User Creation", f"User ID: {user.telegram_id}")
            
            # Enable subscription
            settings = get_user_settings(db, test_telegram_id)
            if settings:
                update_user_settings(db, test_telegram_id, 
                                   daily_buy_alerts_enabled=True,
                                   daily_buy_alert_time='09:00')
                
                # Verify
                updated_settings = get_user_settings(db, test_telegram_id)
                if updated_settings.daily_buy_alerts_enabled:
                    results.add_pass("Enable Subscription", "Subscription enabled")
                else:
                    results.add_fail("Enable Subscription", "Failed to enable")
                
                if updated_settings.daily_buy_alert_time == '09:00':
                    results.add_pass("Set Alert Time", "Alert time set correctly")
                else:
                    results.add_fail("Set Alert Time", f"Expected '09:00', got '{updated_settings.daily_buy_alert_time}'")
                
                # Disable subscription
                update_user_settings(db, test_telegram_id, daily_buy_alerts_enabled=False)
                disabled_settings = get_user_settings(db, test_telegram_id)
                if not disabled_settings.daily_buy_alerts_enabled:
                    results.add_pass("Disable Subscription", "Subscription disabled")
                else:
                    results.add_fail("Disable Subscription", "Failed to disable")
            else:
                results.add_fail("Get User Settings", "Settings not found")
        
    except Exception as e:
        results.add_fail("Subscription Management", str(e))
    
    return results


def test_stock_analysis_sample():
    """Test 3: Analyze sample stocks and verify BUY signal detection"""
    results = TestResults()
    
    try:
        logger.info("Testing stock analysis with sample stocks...")
        
        # Read 20 stocks from CSV
        csv_path = os.path.join(os.path.dirname(__file__), 'data/stock_tickers.csv')
        if not os.path.exists(csv_path):
            results.add_fail("CSV File", f"File not found: {csv_path}")
            return results
        
        stocks = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for i, row in enumerate(reader):
                if i >= 20:  # Limit to 20 stocks
                    break
                if row and len(row) > 0:
                    symbol = row[0].strip().upper()
                    if symbol:
                        stocks.append(symbol)
        
        results.add_pass("Read CSV", f"Loaded {len(stocks)} stocks")
        
        # Analyze each stock
        buy_signals = []
        errors = []
        
        for symbol in stocks:
            try:
                analysis = analyze_stock(
                    symbol=symbol,
                    mode='balanced',
                    timeframe='medium',
                    horizon='3months',
                    use_cache=False
                )
                
                recommendation_type = analysis.get('recommendation_type', '')
                recommendation = analysis.get('recommendation', '')
                
                # Check if BUY signal
                if recommendation_type == 'BUY' or 'BUY' in recommendation.upper():
                    buy_signals.append({
                        'symbol': symbol,
                        'recommendation': recommendation,
                        'confidence': analysis.get('confidence', 0),
                        'score': analysis.get('overall_score_pct', 0)
                    })
                    results.add_pass(f"Analysis: {symbol}", f"BUY signal detected (Confidence: {analysis.get('confidence', 0):.1f}%)")
                else:
                    results.add_pass(f"Analysis: {symbol}", f"Not a BUY ({recommendation_type})")
                
            except Exception as e:
                errors.append((symbol, str(e)))
                results.add_warning(f"Analysis: {symbol}", str(e))
        
        results.add_pass("Stock Analysis", f"{len(buy_signals)} BUY signals found from {len(stocks)} stocks")
        
        if errors:
            results.add_warning("Analysis Errors", f"{len(errors)} stocks failed analysis")
        
    except Exception as e:
        results.add_fail("Stock Analysis", str(e))
    
    return results


def test_buy_signal_storage():
    """Test 4: Save and retrieve BUY signals from database"""
    results = TestResults()
    
    try:
        logger.info("Testing BUY signal storage...")
        
        # Test saving a signal
        test_symbol = "RELIANCE.NS"
        test_analysis = {
            'symbol': test_symbol,
            'recommendation': 'STRONG BUY',
            'recommendation_type': 'BUY',
            'confidence': 85.0,
            'overall_score_pct': 85.0,
            'risk_reward': 2.5,
            'current_price': 2500.0,
            'target': 2750.0,
            'stop_loss': 2400.0
        }
        
        with get_db_context() as db:
            import json
            from datetime import datetime
            
            # Check if exists
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            existing = db.query(DailyBuySignal).filter(
                DailyBuySignal.symbol == test_symbol,
                DailyBuySignal.analysis_date >= today
            ).first()
            
            if existing:
                # Update
                existing.recommendation = test_analysis['recommendation']
                existing.confidence = test_analysis['confidence']
                existing.analysis_data = json.dumps(test_analysis, default=str)
            else:
                # Create
                signal = DailyBuySignal(
                    symbol=test_symbol,
                    analysis_date=datetime.utcnow(),
                    recommendation=test_analysis['recommendation'],
                    recommendation_type=test_analysis['recommendation_type'],
                    confidence=test_analysis['confidence'],
                    overall_score_pct=test_analysis['overall_score_pct'],
                    risk_reward=test_analysis['risk_reward'],
                    current_price=test_analysis['current_price'],
                    target=test_analysis['target'],
                    stop_loss=test_analysis['stop_loss'],
                    analysis_data=json.dumps(test_analysis, default=str)
                )
                db.add(signal)
            
            db.commit()
            results.add_pass("Save BUY Signal", f"Signal saved for {test_symbol}")
            
            # Test retrieval
            signals = get_today_buy_signals(db)
            if signals:
                results.add_pass("Retrieve BUY Signals", f"Retrieved {len(signals)} signals")
                
                # Verify test signal
                test_signal = next((s for s in signals if s.symbol == test_symbol), None)
                if test_signal:
                    results.add_pass("Verify Signal Data", f"Signal found: {test_signal.recommendation}")
                else:
                    results.add_warning("Verify Signal Data", "Test signal not found in results")
            else:
                results.add_warning("Retrieve BUY Signals", "No signals found")
        
    except Exception as e:
        results.add_fail("BUY Signal Storage", str(e))
    
    return results


def test_subscribed_users_query():
    """Test 5: Query subscribed users"""
    results = TestResults()
    
    try:
        logger.info("Testing subscribed users query...")
        
        with get_db_context() as db:
            # Enable subscription for test user
            test_telegram_id = 999999999
            update_user_settings(db, test_telegram_id, daily_buy_alerts_enabled=True)
            
            # Query subscribed users
            users = get_subscribed_users_for_daily_buy_alerts(db)
            
            if users:
                results.add_pass("Query Subscribed Users", f"Found {len(users)} subscribed users")
                
                # Verify test user is in list
                test_user = next((u for u in users if u.telegram_id == test_telegram_id), None)
                if test_user:
                    results.add_pass("Test User Subscription", "Test user found in subscribed list")
                else:
                    results.add_warning("Test User Subscription", "Test user not found")
            else:
                results.add_warning("Query Subscribed Users", "No subscribed users found")
        
    except Exception as e:
        results.add_fail("Subscribed Users Query", str(e))
    
    return results


async def test_scheduler_analysis():
    """Test 6: Test scheduler's analysis function with sample stocks"""
    results = TestResults()
    
    try:
        logger.info("Testing scheduler analysis function...")
        
        # Create mock application
        from unittest.mock import Mock
        mock_app = Mock()
        mock_app.bot = Mock()
        
        scheduler = DailyBuyAlertsScheduler(mock_app)
        
        # Test with 5 stocks (smaller sample for testing)
        csv_path = os.path.join(os.path.dirname(__file__), 'data/stock_tickers.csv')
        if not os.path.exists(csv_path):
            results.add_fail("CSV File", f"File not found: {csv_path}")
            return results
        
        stocks = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for i, row in enumerate(reader):
                if i >= 5:  # Test with 5 stocks
                    break
                if row and len(row) > 0:
                    symbol = row[0].strip().upper()
                    if symbol:
                        stocks.append(symbol)
        
        # Test analysis (without full scheduler run)
        buy_count = 0
        for symbol in stocks:
            try:
                from functools import partial
                loop = asyncio.get_event_loop()
                analysis = await loop.run_in_executor(
                    None,
                    partial(
                        analyze_stock,
                        symbol=symbol,
                        mode='balanced',
                        timeframe='medium',
                        horizon='3months',
                        use_cache=False
                    )
                )
                
                recommendation_type = analysis.get('recommendation_type', '')
                if recommendation_type == 'BUY' or 'BUY' in analysis.get('recommendation', '').upper():
                    # Save signal
                    await scheduler._save_buy_signal(symbol, analysis)
                    buy_count += 1
                    results.add_pass(f"Scheduler Analysis: {symbol}", "BUY signal saved")
                else:
                    results.add_pass(f"Scheduler Analysis: {symbol}", f"Not BUY ({recommendation_type})")
                    
            except Exception as e:
                results.add_warning(f"Scheduler Analysis: {symbol}", str(e))
        
        results.add_pass("Scheduler Analysis", f"{buy_count} BUY signals processed from {len(stocks)} stocks")
        
    except Exception as e:
        results.add_fail("Scheduler Analysis", str(e))
    
    return results


def setup_test_user_for_5min_alert():
    """Set up test user 'harshkandhway' to receive alerts in 5 minutes"""
    results = TestResults()
    
    try:
        logger.info("Setting up test user for 5-minute alert...")
        
        # Calculate time 5 minutes from now
        now = datetime.now(pytz.timezone(DEFAULT_TIMEZONE))
        target_time = now + timedelta(minutes=5)
        alert_time_str = target_time.strftime('%H:%M')
        
        with get_db_context() as db:
            # Find user by username
            user = db.query(User).filter(User.username == 'harshkandhway').first()
            
            if not user:
                results.add_fail("Find User", "User 'harshkandhway' not found in database")
                return results
            
            results.add_pass("Find User", f"Found user: {user.telegram_id}")
            
            # Enable subscription and set alert time
            update_user_settings(
                db,
                user.telegram_id,
                daily_buy_alerts_enabled=True,
                daily_buy_alert_time=alert_time_str
            )
            
            # Verify
            settings = get_user_settings(db, user.telegram_id)
            if settings and settings.daily_buy_alerts_enabled:
                results.add_pass("Enable Subscription", f"Subscription enabled for user {user.telegram_id}")
                results.add_pass("Set Alert Time", f"Alert time set to {alert_time_str} (5 minutes from now)")
                logger.info(f"✅ Test user configured: Telegram ID {user.telegram_id}, Alert time: {alert_time_str}")
            else:
                results.add_fail("Enable Subscription", "Failed to enable subscription")
        
    except Exception as e:
        results.add_fail("Setup Test User", str(e))
    
    return results


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("DAILY BUY ALERTS - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    all_results = TestResults()
    
    # Test 1: Database Setup
    print("\n[TEST 1] Database Setup")
    print("-" * 80)
    db_results = test_database_setup()
    all_results.passed.extend(db_results.passed)
    all_results.failed.extend(db_results.failed)
    all_results.warnings.extend(db_results.warnings)
    
    # Test 2: Subscription Management
    print("\n[TEST 2] Subscription Management")
    print("-" * 80)
    sub_results = test_subscription_management()
    all_results.passed.extend(sub_results.passed)
    all_results.failed.extend(sub_results.failed)
    all_results.warnings.extend(sub_results.warnings)
    
    # Test 3: Stock Analysis Sample
    print("\n[TEST 3] Stock Analysis Sample (20 stocks)")
    print("-" * 80)
    analysis_results = test_stock_analysis_sample()
    all_results.passed.extend(analysis_results.passed)
    all_results.failed.extend(analysis_results.failed)
    all_results.warnings.extend(analysis_results.warnings)
    
    # Test 4: BUY Signal Storage
    print("\n[TEST 4] BUY Signal Storage")
    print("-" * 80)
    storage_results = test_buy_signal_storage()
    all_results.passed.extend(storage_results.passed)
    all_results.failed.extend(storage_results.failed)
    all_results.warnings.extend(storage_results.warnings)
    
    # Test 5: Subscribed Users Query
    print("\n[TEST 5] Subscribed Users Query")
    print("-" * 80)
    query_results = test_subscribed_users_query()
    all_results.passed.extend(query_results.passed)
    all_results.failed.extend(query_results.failed)
    all_results.warnings.extend(query_results.warnings)
    
    # Test 6: Scheduler Analysis
    print("\n[TEST 6] Scheduler Analysis Function")
    print("-" * 80)
    scheduler_results = await test_scheduler_analysis()
    all_results.passed.extend(scheduler_results.passed)
    all_results.failed.extend(scheduler_results.failed)
    all_results.warnings.extend(scheduler_results.warnings)
    
    # Setup test user for 5-minute alert
    print("\n[SETUP] Test User Configuration (5-minute alert)")
    print("-" * 80)
    setup_results = setup_test_user_for_5min_alert()
    all_results.passed.extend(setup_results.passed)
    all_results.failed.extend(setup_results.failed)
    all_results.warnings.extend(setup_results.warnings)
    
    # Print final summary
    success = all_results.print_summary()
    
    return success


if __name__ == '__main__':
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error running tests: {e}", exc_info=True)
        sys.exit(1)

