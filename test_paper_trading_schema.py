"""
Test Script for Paper Trading Database Schema
Tests table creation, migrations, and sample data insertion

Run: python test_paper_trading_schema.py
"""

import sys
import os
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bot.database.db import init_db, get_db_context, get_or_create_user
from src.bot.database.models import (
    PaperTradingSession,
    PaperPosition,
    PaperTrade,
    PaperTradeAnalytics,
    PaperTradingLog,
    UserSettings,
    DailyBuySignal
)
from sqlalchemy import inspect, text


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_table_creation():
    """Test that all paper trading tables are created"""
    print_section("Testing Table Creation")
    
    from src.bot.database.db import engine
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = [
        'paper_trading_sessions',
        'paper_positions',
        'paper_trades',
        'paper_trade_analytics',
        'paper_trading_logs'
    ]
    
    print(f"\nFound {len(tables)} tables in database")
    print("\nChecking required paper trading tables:")
    
    all_present = True
    for table in required_tables:
        if table in tables:
            print(f"  ✅ {table}")
        else:
            print(f"  ❌ {table} - MISSING!")
            all_present = False
    
    if all_present:
        print("\n✅ All paper trading tables created successfully!")
    else:
        print("\n❌ Some tables are missing!")
    
    return all_present


def test_user_settings_columns():
    """Test that UserSettings has paper trading columns"""
    print_section("Testing UserSettings Columns")
    
    from src.bot.database.db import engine
    inspector = inspect(engine)
    
    if 'user_settings' not in inspector.get_table_names():
        print("❌ user_settings table not found!")
        return False
    
    columns = [col['name'] for col in inspector.get_columns('user_settings')]
    
    required_columns = [
        'paper_trading_enabled',
        'paper_trading_capital',
        'paper_trading_max_positions',
        'paper_trading_risk_per_trade_pct'
    ]
    
    print("\nChecking paper trading columns in user_settings:")
    
    all_present = True
    for col in required_columns:
        if col in columns:
            print(f"  ✅ {col}")
        else:
            print(f"  ❌ {col} - MISSING!")
            all_present = False
    
    if all_present:
        print("\n✅ All paper trading columns added to UserSettings!")
    else:
        print("\n❌ Some columns are missing!")
    
    return all_present


def create_sample_data():
    """Create sample data for testing"""
    print_section("Creating Sample Data")
    
    with get_db_context() as db:
        # Create a test user
        print("\n1. Creating test user...")
        user = get_or_create_user(
            db=db,
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        print(f"   ✅ User created: ID={user.id}, Telegram ID={user.telegram_id}")
        
        # Update user settings with paper trading defaults
        print("\n2. Updating user settings...")
        settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        if settings:
            settings.paper_trading_enabled = True
            settings.paper_trading_capital = 500000.0
            settings.paper_trading_max_positions = 15
            settings.paper_trading_risk_per_trade_pct = 1.0
            db.commit()
            print(f"   ✅ Settings updated: Capital=₹{settings.paper_trading_capital:,.0f}, Max Positions={settings.paper_trading_max_positions}")
        
        # Create a paper trading session
        print("\n3. Creating paper trading session...")
        session = PaperTradingSession(
            user_id=user.id,
            initial_capital=500000.0,
            current_capital=500000.0,
            peak_capital=500000.0,
            max_positions=15,
            current_positions=0,
            is_active=True
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        print(f"   ✅ Session created: ID={session.id}, Capital=₹{session.initial_capital:,.0f}")
        
        # Create a sample DailyBuySignal (if table exists)
        print("\n4. Creating sample BUY signal...")
        try:
            signal = DailyBuySignal(
                symbol="RELIANCE.NS",
                recommendation_type="STRONG BUY",
                confidence=78.5,
                overall_score_pct=82.0,
                current_price=2450.50,
                target_price=2680.00,
                stop_loss_price=2325.00,
                risk_reward_ratio=1.84,
                analysis_date=datetime.utcnow().date(),
                data=json.dumps({
                    "indicators": {"rsi": 65, "macd": "bullish", "atr": 50},
                    "summary": "Strong bullish momentum"
                })
            )
            db.add(signal)
            db.commit()
            db.refresh(signal)
            print(f"   ✅ Signal created: {signal.symbol} - {signal.recommendation_type} (Confidence: {signal.confidence}%)")
        except Exception as e:
            print(f"   ⚠️ Could not create signal (table may not exist): {e}")
            signal = None
        
        # Create a sample paper position
        print("\n5. Creating sample paper position...")
        position = PaperPosition(
            session_id=session.id,
            symbol="RELIANCE.NS",
            entry_date=datetime.utcnow(),
            entry_price=2450.50,
            shares=40,
            position_value=98020.0,
            target_price=2680.00,
            stop_loss_price=2325.00,
            initial_risk_reward=1.84,
            recommendation_type="STRONG BUY",
            entry_confidence=78.5,
            entry_score_pct=82.0,
            current_price=2500.00,
            unrealized_pnl=1980.0,
            unrealized_pnl_pct=2.02,
            highest_price=2500.00,
            is_open=True,
            days_held=0,
            entry_analysis=json.dumps({
                "indicators": {"rsi": 65, "macd": "bullish"},
                "summary": "Strong entry signal"
            })
        )
        if signal:
            position.signal_id = signal.id
        
        db.add(position)
        db.commit()
        db.refresh(position)
        print(f"   ✅ Position created: {position.symbol} - {position.shares} shares @ ₹{position.entry_price:.2f}")
        
        # Update session
        session.current_positions = 1
        session.current_capital = 500000.0 - position.position_value
        db.commit()
        
        # Create a sample completed trade
        print("\n6. Creating sample completed trade...")
        trade = PaperTrade(
            session_id=session.id,
            position_id=position.id,
            symbol="TCS.NS",
            entry_date=datetime.utcnow() - timedelta(days=7),
            entry_price=3890.00,
            shares=25,
            entry_value=97250.0,
            exit_date=datetime.utcnow(),
            exit_price=4150.00,
            exit_value=103750.0,
            exit_reason="TARGET_HIT",
            pnl=6500.0,
            pnl_pct=6.68,
            days_held=7,
            r_multiple=1.84,
            is_winner=True,
            met_target=True,
            hit_stop_loss=False,
            recommendation_type="BUY",
            entry_confidence=75.0,
            entry_score_pct=78.0,
            initial_risk_reward=1.84,
            target_price=4150.00,
            stop_loss_price=3700.00,
            highest_price=4150.00,
            max_unrealized_gain=6500.0,
            max_unrealized_loss=0.0,
            entry_analysis=json.dumps({"summary": "Good entry"}),
            exit_analysis=json.dumps({"summary": "Target achieved"})
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        print(f"   ✅ Trade created: {trade.symbol} - P&L: ₹{trade.pnl:,.0f} ({trade.pnl_pct:+.2f}%)")
        
        # Update session stats
        session.total_trades = 1
        session.winning_trades = 1
        session.total_profit = 6500.0
        session.current_capital = 500000.0 - position.position_value + trade.pnl
        db.commit()
        
        # Create sample analytics
        print("\n7. Creating sample analytics...")
        analytics = PaperTradeAnalytics(
            session_id=session.id,
            period_type="daily",
            period_start=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            period_end=datetime.utcnow().replace(hour=23, minute=59, second=59),
            trades_count=1,
            winning_trades=1,
            losing_trades=0,
            win_rate_pct=100.0,
            gross_profit=6500.0,
            gross_loss=0.0,
            net_pnl=6500.0,
            profit_factor=0.0,  # Will be calculated
            avg_win=6500.0,
            avg_loss=0.0,
            avg_r_multiple=1.84,
            best_trade_pnl=6500.0,
            worst_trade_pnl=0.0,
            avg_hold_time_days=7.0,
            max_concurrent_positions=1,
            starting_capital=500000.0,
            ending_capital=506500.0,
            period_return_pct=1.3,
            max_drawdown_pct=0.0,
            exit_reasons_breakdown=json.dumps({"TARGET_HIT": 1}),
            insights=json.dumps({"summary": "Good start"})
        )
        db.add(analytics)
        db.commit()
        db.refresh(analytics)
        print(f"   ✅ Analytics created: {analytics.period_type} - Win Rate: {analytics.win_rate_pct}%")
        
        # Create sample log entries
        print("\n8. Creating sample log entries...")
        log1 = PaperTradingLog(
            session_id=session.id,
            timestamp=datetime.utcnow(),
            log_level="INFO",
            category="ENTRY",
            symbol="RELIANCE.NS",
            message="Position opened",
            details=json.dumps({"entry_price": 2450.50, "shares": 40}),
            position_id=position.id
        )
        log2 = PaperTradingLog(
            session_id=session.id,
            timestamp=datetime.utcnow(),
            log_level="INFO",
            category="EXIT",
            symbol="TCS.NS",
            message="Position closed - TARGET HIT",
            details=json.dumps({"exit_price": 4150.00, "pnl": 6500.0}),
            trade_id=trade.id
        )
        db.add(log1)
        db.add(log2)
        db.commit()
        print(f"   ✅ Log entries created: {log1.category} and {log2.category}")
        
        print("\n✅ Sample data created successfully!")
        return session.id


def verify_data_integrity():
    """Verify relationships and data integrity"""
    print_section("Verifying Data Integrity")
    
    with get_db_context() as db:
        # Check session
        session = db.query(PaperTradingSession).first()
        if not session:
            print("❌ No session found!")
            return False
        
        print(f"\n✅ Session found: ID={session.id}, Capital=₹{session.current_capital:,.0f}")
        
        # Check positions
        positions = db.query(PaperPosition).filter(PaperPosition.session_id == session.id).all()
        print(f"✅ Found {len(positions)} position(s)")
        for pos in positions:
            print(f"   - {pos.symbol}: {pos.shares} shares @ ₹{pos.entry_price:.2f}")
        
        # Check trades
        trades = db.query(PaperTrade).filter(PaperTrade.session_id == session.id).all()
        print(f"✅ Found {len(trades)} trade(s)")
        for trade in trades:
            print(f"   - {trade.symbol}: P&L ₹{trade.pnl:,.0f} ({trade.pnl_pct:+.2f}%)")
        
        # Check analytics
        analytics = db.query(PaperTradeAnalytics).filter(PaperTradeAnalytics.session_id == session.id).all()
        print(f"✅ Found {len(analytics)} analytics record(s)")
        
        # Check logs
        logs = db.query(PaperTradingLog).filter(PaperTradingLog.session_id == session.id).all()
        print(f"✅ Found {len(logs)} log entry/entries")
        
        # Verify relationships
        print("\nVerifying relationships:")
        if positions and positions[0].session_id == session.id:
            print("  ✅ Position → Session relationship valid")
        if trades and trades[0].session_id == session.id:
            print("  ✅ Trade → Session relationship valid")
        if logs and logs[0].session_id == session.id:
            print("  ✅ Log → Session relationship valid")
        
        return True


def print_summary():
    """Print database summary"""
    print_section("Database Summary")
    
    from src.bot.database.db import engine
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    with get_db_context() as db:
        session_count = db.query(PaperTradingSession).count()
        position_count = db.query(PaperPosition).count()
        trade_count = db.query(PaperTrade).count()
        analytics_count = db.query(PaperTradeAnalytics).count()
        log_count = db.query(PaperTradingLog).count()
        
        print(f"\nTotal Tables: {len(tables)}")
        print(f"\nPaper Trading Data:")
        print(f"  Sessions: {session_count}")
        print(f"  Positions: {position_count}")
        print(f"  Trades: {trade_count}")
        print(f"  Analytics: {analytics_count}")
        print(f"  Logs: {log_count}")


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("  PAPER TRADING DATABASE SCHEMA TEST")
    print("="*70)
    
    try:
        # Initialize database
        print("\n📦 Initializing database...")
        init_db()
        
        # Test table creation
        if not test_table_creation():
            print("\n❌ Table creation test failed!")
            return
        
        # Test user settings columns
        if not test_user_settings_columns():
            print("\n❌ UserSettings columns test failed!")
            return
        
        # Create sample data
        session_id = create_sample_data()
        
        # Verify data integrity
        if not verify_data_integrity():
            print("\n❌ Data integrity test failed!")
            return
        
        # Print summary
        print_summary()
        
        print("\n" + "="*70)
        print("  ✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nDatabase schema is ready for paper trading system!")
        print(f"Test session ID: {session_id}")
        print("\nYou can now proceed with Phase 2 implementation.")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == '__main__':
    main()


