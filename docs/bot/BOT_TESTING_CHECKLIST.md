# Telegram Bot Testing Checklist

Use this checklist to systematically test all bot features before production deployment.

---

## 🚀 Pre-Testing Setup

- [ ] Install all dependencies: `pip install -r requirements_bot.txt`
- [ ] Create `.env` file with valid credentials
- [ ] Initialize database: `python -c "from src.bot.database.db import init_db; init_db()"`
- [ ] Verify database created: Check `data/bot.db` exists
- [ ] Start bot: `python bot_runner.py`
- [ ] Verify bot responds to commands in Telegram

---

## 👤 Basic Commands

### `/start` Command
- [ ] Send `/start` to bot
- [ ] Verify welcome message appears
- [ ] Verify inline keyboard shows up
- [ ] Verify user created in database
- [ ] Send `/start` again (test existing user)

### `/help` Command
- [ ] Send `/help`
- [ ] Verify all commands listed
- [ ] Verify formatting is correct
- [ ] Verify no duplicate commands

### `/about` Command
- [ ] Send `/about`
- [ ] Verify bot information displays
- [ ] Verify version number shows

### `/menu` Command
- [ ] Send `/menu`
- [ ] Verify main menu keyboard appears
- [ ] Verify all buttons present

---

## 📊 Analysis Commands

### `/analyze SYMBOL`
- [ ] `/analyze RELIANCE.NS` (valid Indian stock)
- [ ] Verify analysis completes
- [ ] Verify all sections present:
  - [ ] Current price
  - [ ] Market regime
  - [ ] Key indicators (RSI, MACD, Volume, ADX)
  - [ ] Recommendation
  - [ ] Confidence score
  - [ ] Entry price
  - [ ] Targets (conservative, recommended, aggressive)
  - [ ] Stop loss
  - [ ] Risk/Reward ratio
  - [ ] Top reasoning points
- [ ] Verify action buttons appear
- [ ] Try invalid symbol: `/analyze INVALID`
- [ ] Verify error message for invalid symbol
- [ ] Try empty command: `/analyze`
- [ ] Verify usage message

### `/quick SYMBOL`
- [ ] `/quick TCS.NS`
- [ ] Verify quick summary shows
- [ ] Verify less detail than full analysis
- [ ] Verify recommendation and key metrics
- [ ] Try invalid symbol

### `/compare SYMBOL1 SYMBOL2 ...`
- [ ] `/compare RELIANCE.NS TCS.NS` (2 stocks)
- [ ] Verify comparison table shows
- [ ] Verify both stocks in table
- [ ] `/compare RELIANCE.NS TCS.NS INFY.NS` (3 stocks)
- [ ] `/compare` with 5 stocks (max)
- [ ] Try with 6+ stocks (should error)
- [ ] Try with 1 stock (should error)
- [ ] Try with invalid symbols
- [ ] Try with duplicate symbols

---

## ⭐ Watchlist Commands

### `/watchlist` (View)
- [ ] Send `/watchlist` when empty
- [ ] Verify "empty watchlist" message
- [ ] Add some stocks first
- [ ] Send `/watchlist` again
- [ ] Verify list shows with buttons
- [ ] Verify current prices displayed

### `/watchlist add SYMBOL`
- [ ] `/watchlist add RELIANCE.NS`
- [ ] Verify success message
- [ ] `/watchlist` to confirm added
- [ ] Add same stock again (test duplicate)
- [ ] Verify warning about duplicate
- [ ] Add 20 stocks (test limit)
- [ ] Try adding 21st stock (should error)
- [ ] Try invalid symbol

### `/watchlist remove SYMBOL`
- [ ] `/watchlist remove RELIANCE.NS`
- [ ] Verify success message
- [ ] `/watchlist` to confirm removed
- [ ] Try removing stock not in list
- [ ] Verify warning message

### `/watchlist analyze`
- [ ] Add 3-5 stocks to watchlist
- [ ] `/watchlist analyze`
- [ ] Verify progress message
- [ ] Verify comparison table shows
- [ ] Verify all stocks analyzed
- [ ] Check with empty watchlist
- [ ] Check with 20 stocks (stress test)

### `/watchlist clear`
- [ ] `/watchlist clear`
- [ ] Verify confirmation dialog
- [ ] Click "Yes" to confirm
- [ ] Verify watchlist cleared
- [ ] `/watchlist` to verify empty
- [ ] Try clearing empty watchlist

---

## 🔔 Alert Commands

### `/alerts` (View)
- [ ] Send `/alerts` when no alerts
- [ ] Verify "no alerts" message
- [ ] Create some alerts first
- [ ] `/alerts` again
- [ ] Verify all alerts listed
- [ ] Verify delete buttons present

### `/alert SYMBOL`
- [ ] `/alert RELIANCE.NS`
- [ ] Verify alert type menu shows
- [ ] Verify current price displayed
- [ ] Click "Price Alert" button
- [ ] Enter target price (e.g., `2500`)
- [ ] Verify alert created
- [ ] Click "RSI Alert" button
- [ ] Verify overbought/oversold alerts created
- [ ] Click "Signal Change Alert" button
- [ ] Verify signal alert created
- [ ] Try with invalid symbol

### `/deletealert ID`
- [ ] Create an alert
- [ ] Note its ID from `/alerts`
- [ ] `/deletealert <ID>`
- [ ] Verify alert deleted
- [ ] `/alerts` to confirm gone
- [ ] Try deleting non-existent ID
- [ ] Try deleting another user's alert (if testing with multiple users)

### `/clearalerts`
- [ ] Create multiple alerts
- [ ] `/clearalerts`
- [ ] Verify confirmation dialog
- [ ] Click "Yes"
- [ ] Verify all alerts cleared
- [ ] Try on empty alert list

### Alert Notifications (Background Service)
- [ ] Create price alert with reachable target
- [ ] Wait for alert check cycle (5 minutes)
- [ ] Verify notification received
- [ ] Verify alert auto-disabled after trigger
- [ ] Create RSI alert
- [ ] Wait for check (may take longer)
- [ ] Create signal change alert
- [ ] Change conditions to trigger it

---

## ⚙️ Settings Commands

### `/settings`
- [ ] Send `/settings`
- [ ] Verify current settings displayed
- [ ] Verify inline keyboard with options
- [ ] Note current values

### `/setmode MODE`
- [ ] `/setmode conservative`
- [ ] Verify success message
- [ ] `/settings` to confirm change
- [ ] `/setmode moderate`
- [ ] `/setmode aggressive`
- [ ] Try invalid mode: `/setmode invalid`
- [ ] Verify error message
- [ ] Test setting via inline keyboard

### `/settimeframe TIMEFRAME`
- [ ] `/settimeframe 1d`
- [ ] Verify success message
- [ ] `/settimeframe 1wk`
- [ ] `/settimeframe 1mo`
- [ ] Try invalid: `/settimeframe 5m`
- [ ] Test via inline keyboard

### `/setcapital AMOUNT`
- [ ] `/setcapital 100000`
- [ ] Verify success message
- [ ] `/setcapital 500000`
- [ ] Try minimum: `/setcapital 10000`
- [ ] Try below minimum: `/setcapital 5000` (should error)
- [ ] Try maximum: `/setcapital 10000000`
- [ ] Try above maximum (should error)
- [ ] Try invalid: `/setcapital abc`

### `/resetsettings`
- [ ] Change multiple settings
- [ ] `/resetsettings`
- [ ] Verify confirmation dialog
- [ ] Click "Yes"
- [ ] Verify all settings reset to defaults
- [ ] `/settings` to confirm

### Settings Persistence
- [ ] Change settings
- [ ] Restart bot
- [ ] `/settings` to verify settings persisted
- [ ] Run `/analyze` to verify settings applied

---

## 💼 Portfolio Commands

### `/portfolio`
- [ ] Send `/portfolio`
- [ ] Verify "coming soon" message
- [ ] Verify helpful alternatives suggested

---

## 🔘 Callback Query Handlers (Inline Buttons)

### Analysis Action Buttons
- [ ] `/analyze RELIANCE.NS`
- [ ] Click "Add to Watchlist" button
- [ ] Verify stock added
- [ ] Click "Set Alert" button
- [ ] Verify alert menu shows
- [ ] Click "Refresh Analysis" button
- [ ] Verify analysis refreshes

### Watchlist Buttons
- [ ] `/watchlist`
- [ ] Click "Analyze All" button
- [ ] Verify analysis starts
- [ ] Click stock symbol button
- [ ] Verify quick analysis or menu

### Settings Buttons
- [ ] `/settings`
- [ ] Click "Risk Mode" button
- [ ] Verify mode selection menu
- [ ] Select a mode
- [ ] Verify setting changed
- [ ] Test all setting buttons

### Alert Type Buttons
- [ ] `/alert RELIANCE.NS`
- [ ] Click each alert type button
- [ ] Verify correct flow for each type

### Navigation Buttons
- [ ] Click "Back" buttons
- [ ] Verify correct navigation
- [ ] Click "Close" button
- [ ] Verify message deleted

---

## 🔄 Integration Tests

### Watchlist → Analysis Flow
- [ ] Add stocks to watchlist
- [ ] Analyze watchlist
- [ ] Verify user settings applied
- [ ] Verify results formatted correctly

### Analysis → Watchlist → Alert Flow
- [ ] Analyze a stock
- [ ] Add to watchlist
- [ ] Create alert for same stock
- [ ] Verify all data consistent

### Settings → Analysis Flow
- [ ] Set mode to "conservative"
- [ ] Analyze a stock
- [ ] Verify conservative filters applied
- [ ] Change to "aggressive"
- [ ] Analyze same stock
- [ ] Verify different results/thresholds

### Alert Lifecycle
- [ ] Create price alert
- [ ] Verify appears in `/alerts`
- [ ] Wait for check cycle
- [ ] Verify notification received
- [ ] Verify alert disabled
- [ ] Verify not in `/alerts` anymore

---

## ⚡ Performance Tests

### Response Time
- [ ] Measure time for `/analyze` (should be < 5s)
- [ ] Measure time for `/compare` 5 stocks (should be < 15s)
- [ ] Measure time for `/watchlist analyze` with 10 stocks (should be < 30s)

### Concurrent Users
- [ ] Test with 2 users simultaneously
- [ ] Both run analyses
- [ ] Verify no conflicts
- [ ] Verify separate watchlists
- [ ] Verify separate settings

### Database Performance
- [ ] Create 20 watchlist items
- [ ] Create 20 alerts
- [ ] Run multiple queries
- [ ] Check for slow operations

---

## 🐛 Error Handling Tests

### Network Errors
- [ ] Disconnect internet
- [ ] Try `/analyze RELIANCE.NS`
- [ ] Verify friendly error message
- [ ] Reconnect and verify recovery

### Invalid Input
- [ ] Send random text (not a command)
- [ ] Verify unknown command message
- [ ] Send `/analyze` with gibberish symbol
- [ ] Verify validation error
- [ ] Send malformed callback data (manually if possible)

### Database Errors
- [ ] Delete `data/bot.db` while running
- [ ] Try operations
- [ ] Verify error handling
- [ ] Restart and verify recovery

### API Rate Limits
- [ ] Run many analyses rapidly
- [ ] Watch for rate limit errors
- [ ] Verify error messages helpful

---

## 🔐 Security Tests

### Authorization
- [ ] If admin IDs configured:
  - [ ] Test with authorized user
  - [ ] Test with unauthorized user
  - [ ] Verify access denied message

### Data Isolation
- [ ] Create user A and user B
- [ ] User A creates watchlist
- [ ] User B tries to access A's data
- [ ] Verify isolation

### Input Validation
- [ ] Try SQL injection in symbol: `/analyze '; DROP TABLE users;--`
- [ ] Verify sanitization
- [ ] Try XSS in symbol
- [ ] Try very long inputs (1000+ chars)

---

## 📱 User Experience Tests

### Message Formatting
- [ ] Check all messages for proper Markdown
- [ ] Verify emojis display correctly
- [ ] Verify no formatting errors
- [ ] Check message chunking for long outputs

### Button Labels
- [ ] Verify all buttons have clear labels
- [ ] Verify no button text truncation
- [ ] Verify logical button grouping

### Error Messages
- [ ] Verify all errors are user-friendly
- [ ] Verify errors suggest next steps
- [ ] Verify no technical jargon

### Help/Guidance
- [ ] Verify empty states have helpful messages
- [ ] Verify examples provided where appropriate
- [ ] Verify tips and hints useful

---

## 📊 Data Consistency Tests

### Settings Persistence
- [ ] Change settings
- [ ] Run analysis
- [ ] Check settings still correct
- [ ] Restart bot
- [ ] Verify settings persisted

### Watchlist Persistence
- [ ] Add stocks to watchlist
- [ ] Restart bot
- [ ] Verify watchlist intact
- [ ] Verify order preserved

### Alert Persistence
- [ ] Create alerts
- [ ] Restart bot
- [ ] Verify alerts still active
- [ ] Wait for check cycle
- [ ] Verify notifications still work

---

## 🔍 Edge Cases

### Empty States
- [ ] Empty watchlist operations
- [ ] Empty alert list operations
- [ ] No analysis cache

### Maximum Limits
- [ ] 20 stocks in watchlist
- [ ] 20+ alerts (test MAX_ALERTS_PER_USER)
- [ ] Very long stock symbols
- [ ] Very large capital amounts

### Special Characters
- [ ] Symbols with dots (RELIANCE.NS)
- [ ] Symbols with hyphens
- [ ] Unicode in messages

### Timing Issues
- [ ] Run commands while analysis in progress
- [ ] Create alert while checking alerts
- [ ] Rapid-fire commands

---

## 🚦 Bot Lifecycle Tests

### Startup
- [ ] Start bot
- [ ] Verify database initialized
- [ ] Verify alert service starts
- [ ] Verify scheduler starts
- [ ] Check logs for errors

### Runtime
- [ ] Run for extended period (hours)
- [ ] Monitor memory usage
- [ ] Monitor CPU usage
- [ ] Check for memory leaks
- [ ] Verify alert checks continue

### Shutdown
- [ ] Stop bot (Ctrl+C)
- [ ] Verify graceful shutdown
- [ ] Verify no data corruption
- [ ] Verify alert service stops
- [ ] Verify scheduler stops cleanly

### Restart
- [ ] Restart bot
- [ ] Verify all services resume
- [ ] Verify data intact
- [ ] Verify pending alerts work

---

## ✅ Final Checks

### Logging
- [ ] Verify logs created in `logs/bot.log`
- [ ] Check log level appropriate
- [ ] Verify no sensitive data logged
- [ ] Verify errors logged with stack traces

### Documentation
- [ ] README updated
- [ ] Commands documented
- [ ] Setup instructions accurate
- [ ] Troubleshooting guide helpful

### Configuration
- [ ] All .env variables documented
- [ ] Defaults sensible
- [ ] No hardcoded secrets

### Code Quality
- [ ] No TODO comments left
- [ ] No debug print statements
- [ ] Type hints on all functions
- [ ] Docstrings complete

---

## 📝 Test Results Template

```markdown
## Test Session: [Date]
**Tester:** [Name]
**Bot Version:** 1.0.0
**Environment:** [Development/Production]

### Summary
- Total Tests: __
- Passed: __
- Failed: __
- Skipped: __

### Failed Tests
1. [Test Name] - [Reason] - [Priority: High/Medium/Low]
2. ...

### Issues Found
1. [Issue Description] - [Severity] - [Steps to Reproduce]
2. ...

### Notes
[Any additional observations]
```

---

## 🎯 Priority Testing Areas

**Before First User:**
1. ✅ Basic commands (/start, /help, /analyze)
2. ✅ Watchlist add/remove
3. ✅ Settings persistence
4. ✅ Alert creation
5. ✅ Error handling

**Before Public Release:**
1. ✅ All callback handlers
2. ✅ Alert notifications working
3. ✅ Multi-user support
4. ✅ Performance acceptable
5. ✅ Security validated
6. ✅ Documentation complete

---

**Happy Testing! 🚀**
