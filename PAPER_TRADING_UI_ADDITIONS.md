# Paper Trading UI Additions

## ✅ Changes Made

### 1. Main Menu Button
- **Added:** "📈 Paper Trading" button to main menu
- **Location:** Replaces "📅 Schedule Reports" in the main menu row
- **Action:** Opens paper trading menu when clicked

### 2. Analysis Action Keyboard
- **Added:** "📈 Paper Trade This" button
- **Location:** After analyzing any stock
- **Action:** Allows paper trading a specific stock directly from analysis results

### 3. Watchlist Menu
- **Added:** "📈 Paper Trade All" button
- **Location:** In watchlist menu
- **Action:** Paper trades all stocks in your watchlist

### 4. Paper Trading Menu
- **Added:** New dedicated paper trading menu with buttons:
  - ▶️ Start Session
  - ⏹️ Stop Session
  - 📊 Status
  - 📜 History
  - 📈 Trade All BUY Signals
  - ⭐ Trade Watchlist
  - 📈 Performance
  - 💡 Insights
  - ⚙️ Settings
  - ◀️ Back to Menu

## 📋 New Keyboard Functions

### In `src/bot/utils/keyboards.py`:

1. **`create_paper_trading_menu_keyboard()`**
   - Creates main paper trading menu (ReplyKeyboardMarkup)

2. **`create_paper_trade_stock_keyboard(symbol)`**
   - Creates inline keyboard for paper trading a specific stock
   - Includes confirmation and info buttons

3. **`create_paper_trade_buy_signals_keyboard()`**
   - Creates inline keyboard for trading all BUY signals
   - Includes confirmation and view signals options

4. **`create_paper_trade_watchlist_keyboard()`**
   - Creates inline keyboard for trading all watchlist stocks
   - Includes confirmation and view watchlist options

5. **`create_paper_trading_main_keyboard()`**
   - Creates inline keyboard with all paper trading options
   - Used for callback-based navigation

## 🎯 User Flows

### Flow 1: Paper Trade a Specific Stock
1. User analyzes a stock (`/analyze RELIANCE.NS`)
2. Sees "📈 Paper Trade This" button in analysis results
3. Clicks button → Confirmation dialog
4. Confirms → Stock is paper traded

### Flow 2: Paper Trade All BUY Signals
1. User clicks "📈 Paper Trading" in main menu
2. Sees "📈 Trade All BUY Signals" button
3. Clicks button → Confirmation dialog
4. Confirms → All BUY signals from daily analysis are traded

### Flow 3: Paper Trade Watchlist
1. User goes to watchlist (`/watchlist`)
2. Sees "📈 Paper Trade All" button
3. Clicks button → Confirmation dialog
4. Confirms → All stocks in watchlist are paper traded

## 🔧 Implementation Details

### Config Changes (`src/bot/config.py`):
- Updated `MAIN_MENU_BUTTONS` to include "📈 Paper Trading"
- Updated `ANALYSIS_ACTION_BUTTONS` to include "📈 Paper Trade This"
- Updated `WATCHLIST_MENU_BUTTONS` to include "📈 Paper Trade All"
- Added `PAPER_TRADING_MENU_BUTTONS` configuration
- Updated `HELP_MESSAGE` to include paper trading commands

### Bot Handler Changes (`src/bot/bot.py`):
- Added "📈 Paper Trading" button route to `/papertrade` command
- Integrated paper trading handler for menu button clicks

## 📱 Button Callback Data

The following callback data patterns are used:

- `papertrade_stock:{symbol}` - Paper trade specific stock
- `papertrade_stock_confirm:{symbol}` - Confirm paper trade for stock
- `papertrade_buy_signals` - Trade all BUY signals menu
- `papertrade_buy_signals_confirm` - Confirm trade all BUY signals
- `papertrade_watchlist` - Trade watchlist menu
- `papertrade_watchlist_confirm` - Confirm trade all watchlist stocks
- `papertrade_menu` - Paper trading main menu
- `papertrade_info` - Information about paper trading
- `papertrade_buy_signals_info` - Info about BUY signals trading
- `papertrade_watchlist_info` - Info about watchlist trading

## ⚠️ Next Steps (For Implementation)

These buttons are now available in the UI, but you'll need to implement the callback handlers in `src/bot/handlers/callbacks.py` to handle:

1. `papertrade_stock:{symbol}` - Execute paper trade for a stock
2. `papertrade_buy_signals_confirm` - Execute trades for all BUY signals
3. `papertrade_watchlist_confirm` - Execute trades for all watchlist stocks

These handlers should:
- Check if user has active paper trading session
- Validate market hours (for BUY signals)
- Execute trades using `PaperTradingService`
- Send confirmation messages
- Handle errors gracefully

## 📝 Example Handler Implementation

```python
# In src/bot/handlers/callbacks.py

async def handle_papertrade_stock(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
    """Handle paper trading a specific stock"""
    user_id = update.effective_user.id
    
    with get_db_context() as db:
        trading_service = get_paper_trading_service(db)
        active_session = await trading_service.get_active_session(user_id)
        
        if not active_session:
            await update.callback_query.answer("Please start a paper trading session first!")
            return
        
        # Execute trade for this stock
        # ... implementation ...
```

## ✅ Summary

All UI elements are now in place:
- ✅ Main menu button
- ✅ Analysis action button
- ✅ Watchlist button
- ✅ Paper trading menu
- ✅ All keyboard functions created
- ✅ Bot routing configured
- ✅ Help message updated

**Next:** Implement the callback handlers to make these buttons functional!


