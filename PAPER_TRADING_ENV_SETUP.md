# Paper Trading Environment Variables

Add these variables to your `.env` file for paper trading configuration:

```env
# =============================================================================
# PAPER TRADING SETTINGS
# =============================================================================

# Enable/disable paper trading system
PAPER_TRADING_ENABLED=true

# Default virtual capital (₹5,00,000)
PAPER_TRADING_DEFAULT_CAPITAL=500000

# Maximum concurrent positions (10-20 range, default: 15)
PAPER_TRADING_DEFAULT_MAX_POSITIONS=15

# Risk per trade percentage (default: 1.0%)
PAPER_TRADING_DEFAULT_RISK_PCT=1.0

# Position monitoring interval in seconds (default: 300 = 5 minutes)
PAPER_TRADING_MONITOR_INTERVAL=300

# Maximum position size as percentage of total capital (default: 20%)
PAPER_TRADING_MAX_POSITION_SIZE_PCT=20

# Execution timing (IST)
PAPER_TRADING_BUY_EXECUTION_TIME=09:20
PAPER_TRADING_DAILY_SUMMARY_TIME=16:00
PAPER_TRADING_WEEKLY_SUMMARY_TIME=18:00
PAPER_TRADING_POSITION_REBALANCE_TIME=11:00

# Price movement tolerance for entry (% deviation from signal price)
PAPER_TRADING_ENTRY_PRICE_TOLERANCE=3.0
```

## Default Values

If not specified in `.env`, the system uses these defaults:

- **Capital:** ₹500,000
- **Max Positions:** 15
- **Risk Per Trade:** 1.0%
- **Monitor Interval:** 5 minutes (300 seconds)
- **Max Position Size:** 20% of capital
- **Buy Execution:** 9:20 AM IST
- **Daily Summary:** 4:00 PM IST
- **Weekly Summary:** Sunday 6:00 PM IST
- **Rebalancing:** 11:00 AM IST
- **Price Tolerance:** 3.0%

## Notes

- All times are in IST (India Standard Time)
- Capital is in Indian Rupees (₹)
- Position limits are enforced per session
- Risk percentage applies to each trade (1% rule)


