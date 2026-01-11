"""
Schema Validation Script
Validates paper trading models are correctly defined without requiring database connection
"""

import sys
import os
import inspect
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_model_structure():
    """Validate that all paper trading models are correctly defined"""
    
    print("="*70)
    print("  PAPER TRADING SCHEMA VALIDATION")
    print("="*70)
    
    try:
        # Import models
        from src.bot.database.models import (
            PaperTradingSession,
            PaperPosition,
            PaperTrade,
            PaperTradeAnalytics,
            PaperTradingLog,
            UserSettings,
            Base
        )
        
        print("\n✅ Successfully imported all paper trading models")
        
        # Validate PaperTradingSession
        print("\n" + "-"*70)
        print("Validating PaperTradingSession...")
        print("-"*70)
        
        required_columns = [
            'id', 'user_id', 'is_active', 'session_start', 'session_end',
            'initial_capital', 'current_capital', 'peak_capital',
            'max_positions', 'current_positions',
            'total_trades', 'winning_trades', 'losing_trades',
            'total_profit', 'total_loss', 'max_drawdown_pct'
        ]
        
        session_columns = [col.name for col in PaperTradingSession.__table__.columns]
        missing = [col for col in required_columns if col not in session_columns]
        
        if missing:
            print(f"❌ Missing columns: {missing}")
            return False
        else:
            print(f"✅ All {len(required_columns)} required columns present")
            print(f"   Total columns: {len(session_columns)}")
        
        # Check relationships
        relationships = [rel.key for rel in PaperTradingSession.__mapper__.relationships]
        required_rels = ['positions', 'trades', 'analytics', 'logs']
        missing_rels = [rel for rel in required_rels if rel not in relationships]
        
        if missing_rels:
            print(f"❌ Missing relationships: {missing_rels}")
            return False
        else:
            print(f"✅ All {len(required_rels)} required relationships present")
        
        # Validate PaperPosition
        print("\n" + "-"*70)
        print("Validating PaperPosition...")
        print("-"*70)
        
        required_columns = [
            'id', 'session_id', 'symbol', 'entry_date', 'entry_price',
            'shares', 'position_value', 'target_price', 'stop_loss_price',
            'trailing_stop', 'initial_risk_reward', 'recommendation_type',
            'entry_confidence', 'entry_score_pct', 'current_price',
            'unrealized_pnl', 'unrealized_pnl_pct', 'highest_price',
            'is_open', 'days_held', 'entry_analysis'
        ]
        
        position_columns = [col.name for col in PaperPosition.__table__.columns]
        missing = [col for col in required_columns if col not in position_columns]
        
        if missing:
            print(f"❌ Missing columns: {missing}")
            return False
        else:
            print(f"✅ All {len(required_columns)} required columns present")
            print(f"   Total columns: {len(position_columns)}")
        
        # Validate PaperTrade
        print("\n" + "-"*70)
        print("Validating PaperTrade...")
        print("-"*70)
        
        required_columns = [
            'id', 'session_id', 'position_id', 'symbol',
            'entry_date', 'entry_price', 'shares', 'entry_value',
            'exit_date', 'exit_price', 'exit_value', 'exit_reason',
            'pnl', 'pnl_pct', 'days_held', 'r_multiple',
            'is_winner', 'met_target', 'hit_stop_loss',
            'recommendation_type', 'entry_confidence', 'entry_score_pct',
            'initial_risk_reward', 'target_price', 'stop_loss_price',
            'highest_price', 'max_unrealized_gain', 'max_unrealized_loss',
            'entry_analysis', 'exit_analysis'
        ]
        
        trade_columns = [col.name for col in PaperTrade.__table__.columns]
        missing = [col for col in required_columns if col not in trade_columns]
        
        if missing:
            print(f"❌ Missing columns: {missing}")
            return False
        else:
            print(f"✅ All {len(required_columns)} required columns present")
            print(f"   Total columns: {len(trade_columns)}")
        
        # Validate PaperTradeAnalytics
        print("\n" + "-"*70)
        print("Validating PaperTradeAnalytics...")
        print("-"*70)
        
        required_columns = [
            'id', 'session_id', 'period_type', 'period_start', 'period_end',
            'trades_count', 'winning_trades', 'losing_trades', 'win_rate_pct',
            'gross_profit', 'gross_loss', 'net_pnl', 'profit_factor',
            'avg_win', 'avg_loss', 'avg_r_multiple',
            'best_trade_pnl', 'worst_trade_pnl',
            'avg_hold_time_days', 'max_concurrent_positions',
            'starting_capital', 'ending_capital', 'period_return_pct',
            'max_drawdown_pct', 'exit_reasons_breakdown', 'insights'
        ]
        
        analytics_columns = [col.name for col in PaperTradeAnalytics.__table__.columns]
        missing = [col for col in required_columns if col not in analytics_columns]
        
        if missing:
            print(f"❌ Missing columns: {missing}")
            return False
        else:
            print(f"✅ All {len(required_columns)} required columns present")
            print(f"   Total columns: {len(analytics_columns)}")
        
        # Validate PaperTradingLog
        print("\n" + "-"*70)
        print("Validating PaperTradingLog...")
        print("-"*70)
        
        required_columns = [
            'id', 'session_id', 'timestamp', 'log_level', 'category',
            'symbol', 'message', 'details', 'position_id', 'trade_id'
        ]
        
        log_columns = [col.name for col in PaperTradingLog.__table__.columns]
        missing = [col for col in required_columns if col not in log_columns]
        
        if missing:
            print(f"❌ Missing columns: {missing}")
            return False
        else:
            print(f"✅ All {len(required_columns)} required columns present")
            print(f"   Total columns: {len(log_columns)}")
        
        # Validate UserSettings extension
        print("\n" + "-"*70)
        print("Validating UserSettings extension...")
        print("-"*70)
        
        required_columns = [
            'paper_trading_enabled',
            'paper_trading_capital',
            'paper_trading_max_positions',
            'paper_trading_risk_per_trade_pct'
        ]
        
        settings_columns = [col.name for col in UserSettings.__table__.columns]
        missing = [col for col in required_columns if col not in settings_columns]
        
        if missing:
            print(f"❌ Missing columns: {missing}")
            return False
        else:
            print(f"✅ All {len(required_columns)} paper trading columns present")
            print(f"   Total UserSettings columns: {len(settings_columns)}")
        
        # Validate table names
        print("\n" + "-"*70)
        print("Validating table names...")
        print("-"*70)
        
        expected_tables = {
            PaperTradingSession: 'paper_trading_sessions',
            PaperPosition: 'paper_positions',
            PaperTrade: 'paper_trades',
            PaperTradeAnalytics: 'paper_trade_analytics',
            PaperTradingLog: 'paper_trading_logs'
        }
        
        for model, expected_table in expected_tables.items():
            actual_table = model.__table__.name
            model_name = model.__name__
            if actual_table == expected_table:
                print(f"✅ {model_name}: {actual_table}")
            else:
                print(f"❌ {model_name}: Expected {expected_table}, got {actual_table}")
                return False
        
        # Validate foreign keys
        print("\n" + "-"*70)
        print("Validating foreign key relationships...")
        print("-"*70)
        
        # Check PaperPosition -> PaperTradingSession
        session_fk = None
        for fk in PaperPosition.__table__.foreign_keys:
            if 'paper_trading_sessions' in str(fk.column):
                session_fk = fk
                break
        
        if session_fk:
            print("✅ PaperPosition.session_id → PaperTradingSession.id")
        else:
            print("❌ PaperPosition.session_id foreign key not found")
            return False
        
        # Check PaperTrade -> PaperTradingSession
        trade_session_fk = None
        for fk in PaperTrade.__table__.foreign_keys:
            if 'paper_trading_sessions' in str(fk.column):
                trade_session_fk = fk
                break
        
        if trade_session_fk:
            print("✅ PaperTrade.session_id → PaperTradingSession.id")
        else:
            print("❌ PaperTrade.session_id foreign key not found")
            return False
        
        # Summary
        print("\n" + "="*70)
        print("  ✅ SCHEMA VALIDATION PASSED!")
        print("="*70)
        print("\nAll paper trading models are correctly defined:")
        print(f"  • 5 new tables created")
        print(f"  • 4 columns added to UserSettings")
        print(f"  • All relationships configured")
        print(f"  • All foreign keys defined")
        print("\nSchema is ready for database initialization!")
        
        return True
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nThis might be due to missing dependencies.")
        print("Try: pip install sqlalchemy")
        return False
    except Exception as e:
        print(f"\n❌ Validation Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = validate_model_structure()
    sys.exit(0 if success else 1)

