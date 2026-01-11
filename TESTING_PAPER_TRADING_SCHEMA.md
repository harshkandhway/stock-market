# Testing Paper Trading Database Schema

## Overview
This document explains how to test the paper trading database schema that was created in Phase 1.

## Prerequisites
1. Python 3.8+ installed
2. Virtual environment activated (if using one)
3. Dependencies installed: `pip install -r requirements.txt -r requirements_bot.txt`

## Database Schema Created

### New Tables (5)
1. **paper_trading_sessions** - Tracks overall trading sessions
2. **paper_positions** - Manages open positions
3. **paper_trades** - Historical record of completed trades
4. **paper_trade_analytics** - Aggregate performance metrics
5. **paper_trading_logs** - Complete audit trail

### Extended Tables
- **user_settings** - Added 4 new columns:
  - `paper_trading_enabled` (BOOLEAN, default: False)
  - `paper_trading_capital` (FLOAT, default: 500000.0)
  - `paper_trading_max_positions` (INTEGER, default: 15)
  - `paper_trading_risk_per_trade_pct` (FLOAT, default: 1.0)

## Testing Steps

### Step 1: Initialize Database
```bash
cd /Users/harshkandhway/Downloads/stock-market
python3 -c "from src.bot.database.db import init_db; init_db()"
```

This will:
- Create all tables (including new paper trading tables)
- Run migrations to add paper trading columns to `user_settings`
- Print success messages for each migration

### Step 2: Run Test Script
```bash
python3 test_paper_trading_schema.py
```

The test script will:
1. ✅ Verify all 5 paper trading tables are created
2. ✅ Verify UserSettings has 4 new columns
3. ✅ Create sample data:
   - Test user with paper trading settings
   - Paper trading session
   - Sample BUY signal
   - Open position (RELIANCE.NS)
   - Completed trade (TCS.NS)
   - Daily analytics record
   - Log entries
4. ✅ Verify data integrity and relationships
5. ✅ Print summary statistics

### Step 3: Manual Verification (Optional)

#### Check Tables in Database
```python
from src.bot.database.db import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()

# Should include:
# - paper_trading_sessions
# - paper_positions
# - paper_trades
# - paper_trade_analytics
# - paper_trading_logs

print("Paper Trading Tables:")
for table in tables:
    if 'paper' in table:
        print(f"  ✅ {table}")
```

#### Check UserSettings Columns
```python
from src.bot.database.db import engine
from sqlalchemy import inspect

inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('user_settings')]

paper_trading_columns = [
    'paper_trading_enabled',
    'paper_trading_capital',
    'paper_trading_max_positions',
    'paper_trading_risk_per_trade_pct'
]

print("Paper Trading Columns in user_settings:")
for col in paper_trading_columns:
    if col in columns:
        print(f"  ✅ {col}")
    else:
        print(f"  ❌ {col} - MISSING!")
```

#### Query Sample Data
```python
from src.bot.database.db import get_db_context
from src.bot.database.models import (
    PaperTradingSession,
    PaperPosition,
    PaperTrade,
    PaperTradeAnalytics,
    PaperTradingLog
)

with get_db_context() as db:
    # Check sessions
    sessions = db.query(PaperTradingSession).all()
    print(f"Sessions: {len(sessions)}")
    
    # Check positions
    positions = db.query(PaperPosition).all()
    print(f"Positions: {len(positions)}")
    
    # Check trades
    trades = db.query(PaperTrade).all()
    print(f"Trades: {len(trades)}")
    
    # Check analytics
    analytics = db.query(PaperTradeAnalytics).all()
    print(f"Analytics: {len(analytics)}")
    
    # Check logs
    logs = db.query(PaperTradingLog).all()
    print(f"Logs: {len(logs)}")
```

## Expected Test Results

### Table Creation
```
✅ paper_trading_sessions
✅ paper_positions
✅ paper_trades
✅ paper_trade_analytics
✅ paper_trading_logs
```

### UserSettings Columns
```
✅ paper_trading_enabled
✅ paper_trading_capital
✅ paper_trading_max_positions
✅ paper_trading_risk_per_trade_pct
```

### Sample Data Created
- 1 User with paper trading settings
- 1 Paper trading session (₹500,000 capital)
- 1 Open position (RELIANCE.NS)
- 1 Completed trade (TCS.NS, +₹6,500)
- 1 Daily analytics record
- 2 Log entries

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'sqlalchemy'"
**Solution:** Install dependencies:
```bash
pip install -r requirements.txt -r requirements_bot.txt
```

### Issue: "Table already exists" errors
**Solution:** The tables are already created. This is normal if you've run init_db() before.

### Issue: Migration warnings
**Solution:** Check if columns already exist. The migration function checks before adding columns, so warnings are usually safe to ignore.

### Issue: Foreign key constraint errors
**Solution:** Ensure parent tables (users, daily_buy_signals) exist before creating child records.

## Next Steps

After successful schema testing:
1. ✅ Phase 1 Complete - Database foundation ready
2. ➡️ Proceed to Phase 2: Core Services Implementation
   - Paper Portfolio Service
   - Paper Trade Execution Service
   - Paper Trading Service (Orchestrator)
   - Paper Trade Analysis Service

## Database Schema Summary

### Relationships
```
User (1) ──→ (N) PaperTradingSession
PaperTradingSession (1) ──→ (N) PaperPosition
PaperTradingSession (1) ──→ (N) PaperTrade
PaperTradingSession (1) ──→ (N) PaperTradeAnalytics
PaperTradingSession (1) ──→ (N) PaperTradingLog
PaperPosition (1) ──→ (1) PaperTrade
DailyBuySignal (1) ──→ (N) PaperPosition
```

### Key Indexes
- `paper_trading_sessions`: `user_id`, `is_active`
- `paper_positions`: `session_id`, `symbol`, `is_open`
- `paper_trades`: `session_id`, `is_winner`, `pnl`, `exit_reason`
- `paper_trade_analytics`: `session_id`, `period_type`, `period_start`
- `paper_trading_logs`: `session_id`, `timestamp`, `log_level`, `category`

## Files Modified/Created

### Created
- `src/bot/services/market_hours_service.py` - Market hours detection
- `test_paper_trading_schema.py` - Schema test script

### Modified
- `src/bot/database/models.py` - Added 5 new table models
- `src/bot/database/db.py` - Updated `migrate_database()` function

---

**Status:** ✅ Phase 1 Complete - Ready for Phase 2 Implementation


