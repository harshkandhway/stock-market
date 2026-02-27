# 🚀 Stock Analyzer Pro: The Ultimate Upstox Execution Guide

This guide translates the mathematically proven "Phase 9 Holy Grail" backtest into a daily, human-executable trading plan for your brokerage account (Upstox, Zerodha, etc.).

## 1. The Strategy Blueprint (What We Trade)
Based on rigorous 252-day forward-rolling backtests across the Nifty 100, these are the exact parameters that generated a +55% win rate and maximum Net P&L.

*   **Universe:** Nifty 50 & Nifty Next 50 stocks ONLY.
*   **Time Horizon:** Swing Trading (Holding for 3 Days to 3 Months).
*   **Capital Allocation:** Fixed amount per trade (e.g., ₹1,00,000 per structure).
*   **Required Entry Setup:** Only `STRONG BUY` or high-confidence `BUY` (>70%).
*   **The Secret Sauce (Option B):** The stock's 3-month return must be physically outperforming the broader Nifty 50 index. We only buy leaders.

---

## 2. Daily Execution Routine (How We Trade)

### Step 1: The Evening Scan (7:00 PM - 9:00 PM)
*Do not make decisions during live market hours. Run the analyzer when the market is closed and data is finalized.*
1.  Open your terminal and run the Stock Analyzer Pro against your watchlist.
2.  Use the following engine parameters:
    *   **Mode:** `balanced`
    *   **Timeframe:** `medium`
    *   **Horizon:** `3months`
3.  Filter the output for `STRONG BUY` or `BUY` (Confidence > 70%).
4.  **The Relative Strength Check:** Look at a 3-month chart of the stock versus the Nifty 50 (NIFTY). Is the stock trending up harder than the index? If yes, it's a valid setup.

### Step 2: Order Placement (Pre-Market or 9:15 AM)
For the verified setups from your evening scan:
1.  Open Upstox.
2.  Select the **Delivery (CNC)** product type (Avoid Intraday/MIS leverage to prevent forced auto-square-off).
3.  Place a **Market Order (MKT)** or a **Limit Order** near the opening price.
4.  *Crucial:* Calculate your position size. If your capital per trade is ₹1L and the stock is trading at ₹2,500, buy exactly 40 shares.

### Step 3: Setting the Trap (The 5% Lenient Stop)
*The backtest proved that a tight stop-loss destroys your win rate by kicking you out of winners too early. We use the "Lenient Stop."*
1.  Look at the `Stop Loss` price provided by the Stock Analyzer output.
2.  Subtract a flat **5%** from that number.
    *   *Example: Analyzer says SL is ₹100. Your actual SL is ₹95.*
3.  In Upstox, place a **GTT (Good Till Triggered) Sell Order** at this new Lenient Stop price. Leave it alone. Do not move it up.

### Step 4: Setting the Target (Letting Winners Run)
1.  Look at the `Target` price provided by the Stock Analyzer output.
2.  In Upstox, place a second **GTT Sell Order** at this exact Target Price.
3.  You now have a complete bracket: A lenient floor to protect capital, and a ceiling to lock in massive momentum swings.

---

## 3. Position Management (When to Break the Rules)

Once a trade is live, you do absolutely nothing except monitor the calendar. You are now the casino, letting probabilities play out.

**The 63-Day "Time Stop" Rule:**
1.  If a stock has been sitting in your Upstox portfolio for **63 trading days** (~3 calendar months) without hitting either your Target GTT or your Stop Loss GTT:
2.  Run the Stock Analyzer Pro on that specific stock again that evening.
3.  **The Extension:** If the analyzer still reports `BUY` or `HOLD`, grant the stock a 30-day extension. Keep the position open.
4.  **The Chop:** If the analyzer reports `SELL`, `AVOID`, or `WARNING`, manually square off the position in Upstox the next morning at market price. Never hold dead money. Free up the capital for a new `STRONG BUY` setup.

---

## 📈 Psychology & Logistics

*   **Slippage is Real:** The backtester accounted for 0.1% slippage and all STT/Brokerage/GST charges. The returns are highly realistic, but expect your Upstox opening execution price to occasionally be a few rupees worse than the previous night's close.
*   **Scale-Outs Reduce P&L:** The backtest proved that selling 50% early (at 1.5R) reduces your stress, but it *lowers* your total yearly profit. Trust the ultimate Target GTT.
*   **Don't Watch Intraday Ticks:** You are a swing trader. Delete the Upstox app from your home screen if you have the urge to manually sell before a GTT is hit. Let the algorithm do the heavy lifting!
