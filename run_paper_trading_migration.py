"""
Run Paper Trading Database Migration
Creates all tables and adds columns to existing tables

Run: python3 run_paper_trading_migration.py
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bot.database.db import init_db, get_db_context, test_connection
from src.bot.database.models import (
    PaperTradingSession, PaperPosition, PaperTrade,
    PaperTradeAnalytics, PaperTradingLog, UserSettings
)
from sqlalchemy import inspect


def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def verify_migration():
    """Verify that all tables and columns exist"""
    print_section("Verifying Migration")

    from src.bot.database.db import engine
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Check tables
    required_tables = [
        'paper_trading_sessions',
        'paper_positions',
        'paper_trades',
        'paper_trade_analytics',
        'paper_trading_logs'
    ]

    print("\nChecking paper trading tables:")
    all_tables_present = True
    for table in required_tables:
        if table in tables:
            print(f"  ✅ {table}")
        else:
            print(f"  ❌ {table} - MISSING!")
            all_tables_present = False

    # Check UserSettings columns
    if 'user_settings' in tables:
        columns = [col['name'] for col in inspector.get_columns('user_settings')]
        required_columns = [
            'paper_trading_enabled',
            'paper_trading_capital',
            'paper_trading_max_positions',
            'paper_trading_risk_per_trade_pct'
        ]

        print("\nChecking UserSettings columns:")
        all_columns_present = True
        for col in required_columns:
            if col in columns:
                print(f"  ✅ {col}")
            else:
                print(f"  ❌ {col} - MISSING!")
                all_columns_present = False

        if all_tables_present and all_columns_present:
            print("\n✅ Migration verification PASSED!")
            return True
        else:
            print("\n❌ Migration verification FAILED!")
            return False
    else:
        print("\n⚠️ user_settings table not found")
        return False


def test_basic_operations():
    """Test basic database operations"""
    print_section("Testing Basic Operations")

    try:
        with get_db_context() as db:
            # Test creating a session
            from src.bot.database.models import User
            from src.bot.database.db import get_or_create_user

            # Create test user
            user = get_or_create_user(db, 999999999, username="test_paper_trading")
            print(f"✅ Created test user: ID={user.id}")

            # Test session creation
            session = PaperTradingSession(
                user_id=user.id,
                initial_capital=500000.0,
                current_capital=500000.0,
                peak_capital=500000.0,
                max_positions=15
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            print(f"✅ Created test session: ID={session.id}")

            # Test position creation
            position = PaperPosition(
                session_id=session.id,
                symbol="TEST.NS",
                entry_date=datetime.utcnow(),
                entry_price=100.0,
                shares=10,
                position_value=1000.0,
                target_price=110.0,
                stop_loss_price=95.0,
                initial_risk_reward=2.0,
                recommendation_type="STRONG BUY",
                entry_confidence=80.0,
                entry_score_pct=85.0,
                current_price=105.0,
                is_open=True
            )
            db.add(position)
            db.commit()
            db.refresh(position)
            print(f"✅ Created test position: ID={position.id}")

            # Test trade creation
            trade = PaperTrade(
                session_id=session.id,
                position_id=position.id,
                symbol="TEST.NS",
                entry_date=datetime.utcnow() - timedelta(days=5),
                entry_price=100.0,
                shares=10,
                entry_value=1000.0,
                exit_date=datetime.utcnow(),
                exit_price=110.0,
                exit_value=1100.0,
                exit_reason="TARGET_HIT",
                pnl=100.0,
                pnl_pct=10.0,
                days_held=5,
                r_multiple=2.0,
                is_winner=True,
                met_target=True,
                recommendation_type="STRONG BUY",
                entry_confidence=80.0,
                entry_score_pct=85.0,
                initial_risk_reward=2.0,
                target_price=110.0,
                stop_loss_price=95.0
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)
            print(f"✅ Created test trade: ID={trade.id}")

            # Test analytics creation
            analytics = PaperTradeAnalytics(
                session_id=session.id,
                period_type='daily',
                period_start=datetime.utcnow().replace(hour=0, minute=0, second=0),
                period_end=datetime.utcnow().replace(hour=23, minute=59, second=59),
                trades_count=1,
                winning_trades=1,
                losing_trades=0,
                win_rate_pct=100.0,
                gross_profit=100.0,
                gross_loss=0.0,
                net_pnl=100.0,
                profit_factor=0.0,
                starting_capital=500000.0,
                ending_capital=500100.0,
                period_return_pct=0.02
            )
            db.add(analytics)
            db.commit()
            db.refresh(analytics)
            print(f"✅ Created test analytics: ID={analytics.id}")

            # Test log creation
            log = PaperTradingLog(
                session_id=session.id,
                log_level='INFO',
                category='ENTRY',
                symbol='TEST.NS',
                message='Test log entry',
                position_id=position.id
            )
            db.add(log)
            db.commit()
            print(f"✅ Created test log entry: ID={log.id}")

            # Cleanup test data
            db.delete(log)
            db.delete(analytics)
            db.delete(trade)
            db.delete(position)
            db.delete(session)
            db.commit()
            print("\n✅ Cleaned up test data")

            print("\n✅ All basic operations test PASSED!")
            return True

    except Exception as e:
        print(f"\n❌ Basic operations test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main migration and test function"""
    print("\n" + "="*70)
    print("  PAPER TRADING DATABASE MIGRATION & TEST")
    print("="*70)

    # Test connection
    print("\n📦 Testing database connection...")
    if not test_connection():
        print("❌ Database connection failed!")
        return

    # Initialize database
    print("\n📦 Initializing database...")
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Verify migration
    if not verify_migration():
        print("\n❌ Migration verification failed!")
        return

    # Test basic operations
    if not test_basic_operations():
        print("\n❌ Basic operations test failed!")
        return

    print("\n" + "="*70)
    print("  ✅ ALL TESTS PASSED!")
    print("="*70)
    print("\nPaper trading database is ready!")
    print("\nNext steps:")
    print("1. Start the bot: python3 -m src.bot.bot")
    print("2. Use /papertrade start to begin paper trading")
    print("3. Monitor logs in logs/paper_trading/ directory")


if __name__ == '__main__':
    main()

