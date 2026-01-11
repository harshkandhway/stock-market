# 📱 Telegram Paper Trading Setup Guide

## ✅ System Status

**All systems are ready!**

- ✅ Database migrated (5 tables + 4 columns)
- ✅ 14 BUY signals generated and saved
- ✅ Configuration verified
- ✅ Log directories created
- ✅ Services tested and working

---

## 🚀 Quick Start in Telegram

### Step 1: Enable Paper Trading for Your User

First, you need to enable paper trading for your Telegram user ID. Run this command:

```bash
python3 -c "
from src.bot.database.db import get_db_context, get_or_create_user
from src.bot.database.models import UserSettings

# Replace with YOUR Telegram ID (get it from @userinfobot on Telegram)
YOUR_TELEGRAM_ID = 746097421  # Your ID from the database

with get_db_context() as db:
    user = get_or_create_user(db, YOUR_TELEGRAM_ID)
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    
    if not settings:
        # Create settings if they don't exist
        settings = UserSettings(
            user_id=user.id,
            paper_trading_enabled=True,
            paper_trading_capital=500000.0,
            paper_trading_max_positions=15,
            paper_trading_risk_per_trade_pct=1.0
        )
        db.add(settings)
    else:
        settings.paper_trading_enabled = True
        settings.paper_trading_capital = 500000.0
        settings.paper_trading_max_positions = 15
        settings.paper_trading_risk_per_trade_pct = 1.0
    
    db.commit()
    print(f'✅ Paper trading enabled for user {YOUR_TELEGRAM_ID}')
    print(f'   Capital: ₹{settings.paper_trading_capital:,.2f}')
    print(f'   Max Positions: {settings.paper_trading_max_positions}')
    print(f'   Risk Per Trade: {settings.paper_trading_risk_per_trade_pct}%')
"
```

**Note:** Your Telegram ID is `746097421` (from the database). If you want to use a different ID, get it from @userinfobot on Telegram.

---

### Step 2: Start Paper Trading Session

In Telegram, send this command:

```
/papertrade start
```

**Expected Response:**
```
🟢 Paper Trading Session Started!

Initial Capital: ₹500,000.00
Max Positions: 15
Risk Per Trade: 1.0%

System will automatically:
• Execute BUY signals at 9:20 AM IST
• Monitor positions every 5 minutes during market hours
• Send daily summary at 4:00 PM IST
• Send weekly summary on Sundays

Use /papertrade status to check positions anytime.
```

---

### Step 3: Check Your Status

```
/papertrade status
```

**Expected Response:**
```
📊 PAPER TRADING STATUS

━━━━━━━━━━━━━━━━━━━━
SESSION OVERVIEW
━━━━━━━━━━━━━━━━━━━━
Started: 2026-01-11 16:57 IST
Days Active: 0

━━━━━━━━━━━━━━━━━━━━
CAPITAL
━━━━━━━━━━━━━━━━━━━━
Initial: ₹500,000.00
Current: ₹500,000.00
Available: ₹500,000.00
Deployed: ₹0.00 (0.0%)

Total P&L: ₹+0.00 (0.00%)
Unrealized P&L: ₹+0.00

━━━━━━━━━━━━━━━━━━━━
PERFORMANCE
━━━━━━━━━━━━━━━━━━━━
Total Trades: 0
Win Rate: 0.0% (0W / 0L)

Total Profit: ₹0.00
Total Loss: ₹0.00
Profit Factor: 0.00

Max Drawdown: 0.00%

Use /papertrade performance for detailed metrics
Use /papertrade history for trade history
```

---

### Step 4: View Settings

```
/papertrade settings
```

**Expected Response:**
```
⚙️ Paper Trading Settings

Virtual Capital: ₹500,000.00
Max Positions: 15
Risk Per Trade: 1.0%
Enabled: Yes

Settings can be modified via database or admin panel.
```

---

## 📊 Available Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `/papertrade start` | Start a new paper trading session |
| `/papertrade stop` | Stop current session (closes all positions) |
| `/papertrade status` | View current portfolio and P&L |
| `/papertrade history [N]` | View last N trades (default: 10) |
| `/papertrade performance` | Detailed performance metrics |
| `/papertrade insights` | System improvement recommendations |
| `/papertrade reset` | Reset session (with confirmation) |
| `/papertrade settings` | View paper trading configuration |

### Examples

```
/papertrade history 20    # View last 20 trades
/papertrade performance   # Detailed metrics
/papertrade insights      # Recommendations (needs 10+ trades)
```

---

## ⏰ Automated Schedule

The system automatically runs these tasks:

| Time | Task | Description |
|------|------|-------------|
| **9:20 AM IST** | Execute BUY Signals | Processes all BUY signals from daily analysis |
| **Every 5 min** (9:15 AM - 3:30 PM) | Monitor Positions | Checks stop-loss, targets, trailing stops |
| **4:00 PM IST** | Daily Summary | Sends performance report |
| **Sunday 6:00 PM IST** | Weekly Summary | Comprehensive weekly analysis |

---

## 📈 Current Signals Ready

You have **14 BUY signals** ready to be executed:

1. **HINDALCO.NS** - BUY @ ₹900.95 (Confidence: 78%)
2. **AXISBANK.NS** - BUY @ ₹1,272.00 (Confidence: 77%)
3. **ICICIBANK.NS** - BUY @ ₹1,404.30 (Confidence: 76%)
4. **NESTLEIND.NS** - BUY @ ₹1,299.10 (Confidence: 76%)
5. **COALINDIA.NS** - BUY @ ₹418.35 (Confidence: 75%)
6. **M&M.NS** - BUY @ ₹3,677.30 (Confidence: 75%)
7. **WIPRO.NS** - BUY @ ₹261.95 (Confidence: 74%)
8. **TATASTEEL.NS** - BUY @ ₹178.40 (Confidence: 73%)
9. **MARUTI.NS** - BUY @ ₹16,501.00 (Confidence: 72%)
10. **SBIN.NS** - BUY @ ₹1,000.50 (Confidence: 68%)
11. **BPCL.NS** - BUY @ ₹354.15 (Confidence: 67%)
12. **BAJAJ-AUTO.NS** - BUY @ ₹9,562.50 (Confidence: 65%)
13. **KOTAKBANK.NS** - BUY @ ₹2,126.80 (Confidence: 61%)
14. **HCLTECH.NS** - BUY @ ₹1,661.40 (Confidence: 60%)

**Note:** Signals will be executed automatically at **9:20 AM IST** during market hours, or you can manually trigger execution (see below).

---

## 🔧 Manual Testing (Optional)

If you want to test immediately (outside market hours), you can manually trigger BUY execution:

```bash
python3 -c "
import asyncio
from src.bot.database.db import get_db_context
from src.bot.services.paper_trading_service import get_paper_trading_service

async def test_buy_execution():
    with get_db_context() as db:
        service = get_paper_trading_service(db)
        result = await service.execute_buy_signals()
        
        print(f'✅ BUY signal execution complete!')
        print(f'   Sessions processed: {result[\"sessions_processed\"]}')
        print(f'   Signals found: {result[\"signals_found\"]}')
        print(f'   Positions opened: {result[\"positions_opened\"]}')
        print(f'   Skipped: {result[\"skipped\"]}')

asyncio.run(test_buy_execution())
"
```

**Warning:** This will only execute if:
- Market is open (9:15 AM - 3:30 PM IST, Mon-Fri)
- You have an active session
- Position limits are not exceeded
- Capital is available

---

## 📝 What Happens Next

### When Market Opens (9:15 AM IST)

1. **9:20 AM:** System executes BUY signals
   - Checks each signal from `daily_buy_signals` table
   - Validates entry conditions
   - Calculates position size (1% risk rule)
   - Opens positions
   - Sends Telegram alerts for each trade

2. **Every 5 Minutes:** Position monitoring
   - Checks current prices
   - Updates trailing stops
   - Exits if stop-loss hit
   - Exits if target reached
   - Exits if trailing stop triggered

3. **4:00 PM:** Daily summary sent
   - Total P&L
   - Win rate
   - Top performers
   - Recommendations

### Example Trade Alert

When a position is opened, you'll receive:

```
🟢 PAPER TRADE ENTRY

Symbol: ICICIBANK.NS
Type: BUY
Entry Price: ₹1,404.30
Shares: 35
Position Value: ₹49,150.50

Risk Management:
Target: ₹1,532.08 (+9.1%)
Stop Loss: ₹1,366.25 (-2.7%)
Risk/Reward: 3.36:1

Confidence: 76%
Entry Score: 85%
```

---

## 🎯 Monitoring Your Performance

### Daily Checks

1. **Morning (9:30 AM):** Check `/papertrade status` after signals execute
2. **During Day:** Monitor positions (optional)
3. **Evening (4:00 PM):** Review daily summary

### Weekly Review

- Use `/papertrade insights` after 10+ trades
- Review weekly summary on Sundays
- Analyze winning/losing patterns

---

## 🚨 Important Notes

1. **Market Hours Only:** Trading only happens during NSE/BSE hours (9:15 AM - 3:30 PM IST, Mon-Fri)

2. **Position Limits:** Maximum 15 concurrent positions (configurable)

3. **Capital Management:** Each trade risks 1% of capital (configurable)

4. **Signal Source:** Uses signals from `daily_buy_signals` table (generated by daily analysis)

5. **Logs:** All actions logged in `logs/paper_trading/` directory

---

## 📊 Performance Metrics Tracked

- **Win Rate:** Percentage of winning trades
- **Profit Factor:** Gross profit / Gross loss
- **R-Multiple:** Profit/Loss as multiple of initial risk
- **Average Hold Time:** Days positions are held
- **Maximum Drawdown:** Largest peak-to-trough decline
- **Total Return:** Absolute and percentage returns

---

## 🔍 Troubleshooting

### No Signals Executed

1. Check if market is open: Market hours are 9:15 AM - 3:30 PM IST
2. Verify signals exist: Check `daily_buy_signals` table
3. Check session status: Use `/papertrade status`
4. Review logs: Check `logs/paper_trading/errors.log`

### Bot Not Responding

1. Check if bot is running: `ps aux | grep bot`
2. Review bot logs: `logs/bot.log`
3. Check database connection
4. Verify Telegram token in `.env`

### Positions Not Opening

1. Check capital availability: Use `/papertrade status`
2. Verify position limits (max 15)
3. Review entry validation errors in logs
4. Check if signals are BLOCKED (hard filters)

---

## ✅ Next Steps

1. ✅ Enable paper trading for your user (run the Python command above)
2. ✅ Start the bot (if not already running)
3. ✅ Send `/papertrade start` in Telegram
4. ✅ Wait for 9:20 AM IST (or test manually)
5. ✅ Monitor with `/papertrade status`
6. ✅ Review daily summary at 4:00 PM IST

---

## 📞 Support

If you encounter issues:

1. Check logs in `logs/paper_trading/`
2. Verify database has signals: `python3 -c "from src.bot.database.db import get_db_context; from src.bot.database.models import DailyBuySignal; from datetime import datetime; db = get_db_context().__enter__(); today = datetime.utcnow().replace(hour=0); print(f'Signals: {db.query(DailyBuySignal).filter(DailyBuySignal.analysis_date >= today).count()}')"`
3. Review error messages in Telegram
4. Check market hours status

---

**🎉 You're all set! Start paper trading and let the system learn from its trades!**


