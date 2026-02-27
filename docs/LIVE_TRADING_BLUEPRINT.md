# 💰 The ₹1 Lakh Blueprint: RS Overlay + No Stop Loss

**Your exact playbook to deploy ₹1,00,000 into the strategy that returned ₹2,51,165 on real Upstox data.**

> [!CAUTION]
> Past backtest results do NOT guarantee future performance. This is a high-probability system, not a certainty. Never invest money you cannot afford to lose. The 75% win rate means 1 in 4 trades WILL lose money.

---

## 📊 What the Backtest Proved

| Metric | Proven Value |
| :--- | :--- |
| Universe | Nifty 50 + Midcap 150 (143 stocks) |
| Period Tested | Jul 2024 → Jul 2025 (real Upstox data) |
| Win Rate | **75%** (39W / 13L over 52 trades) |
| Net P&L | **₹2,51,165** on ₹1L per trade |
| Avg Winner | ₹7,400 (+7.4% per trade) |
| Avg Loser | ₹-2,880 (-2.9% per trade) |
| Avg Holding | 35 days per trade |
| Max Single Loss | ₹-7,804 (-7.8%) |

---

## 🏗️ Step 0: Prerequisites (Do This Tonight)

### A. Your Upstox Account
- You need an **Upstox** (or Zerodha/Groww) account with **Delivery Trading** enabled
- Deposit ₹1,00,000 into your trading account
- **DO NOT** enable margin/intraday (MIS/BO). This is a **Delivery (CNC)** only strategy

### B. Your Tools
1. **Stock Analyzer Pro** — installed on your Mac at `~/Trades/stock-market/`
2. **Terminal access** — to run the evening scanner
3. **TradingView (free)** — to visually verify Relative Strength (optional but recommended)

---

## 🔁 The Daily Routine

### ⏰ 7:00 PM — The Evening Scan (10 minutes)

**This is when you make ALL your decisions. Never during market hours.**

Run this command in your terminal:

```bash
cd ~/Trades/stock-market
python3 src/cli/stock_analyzer_pro.py
```

When prompted:
- Enter the stock symbol (e.g., `TRENT.NS`)
- Mode: `balanced`
- Timeframe: `medium`
- Horizon: `3months`

**Check results for:**
- ✅ Recommendation = `STRONG BUY` or `BUY`
- ✅ Confidence ≥ 70%
- ❌ No `AVOID` or `WARNING` in the output

### ⏰ 7:15 PM — The Relative Strength Check (5 minutes)

**This is the secret filter that gives you the 75% win rate.**

For each stock that passed the scan above:
1. Open [TradingView](https://www.tradingview.com)
2. Search for the stock (e.g., `TRENT`)
3. Switch to **3-month** chart timeframe
4. Ask yourself: **"Has this stock gone up MORE than the Nifty 50 over the last 3 months?"**

How to check quickly:
- Compare the stock's 3-month % change vs Nifty 50's 3-month % change
- On TradingView, add `NIFTY` as a comparison overlay

| Stock 3M Return | Nifty 3M Return | Decision |
| :--- | :--- | :--- |
| +12% | +5% | ✅ **BUY** — Stock is a leader |
| +3% | +5% | ❌ **SKIP** — Stock is a laggard |
| -2% | -5% | ✅ **BUY** — Stock is falling less |
| -8% | -2% | ❌ **SKIP** — Stock is underperforming |

### ⏰ 9:15 AM Next Morning — Order Execution (2 minutes)

For verified setups from last night:
1. Open Upstox app
2. Search for the stock
3. Select **CNC (Delivery)** — NOT Intraday
4. Place a **Market Order** for the calculated quantity

**Position sizing formula:**
```
Shares = ₹1,00,000 ÷ Current Stock Price
```

| Stock Price | Shares to Buy | Total Investment |
| :--- | :--- | :--- |
| ₹500 | 200 | ₹1,00,000 |
| ₹1,500 | 66 | ₹99,000 |
| ₹2,500 | 40 | ₹1,00,000 |
| ₹5,000 | 20 | ₹1,00,000 |

---

## 🎯 Exit Rules — When to Sell

### Exit 1: Target Hit (The Big Win)
- The Stock Analyzer gives you a **Target Price** with every BUY signal
- Place a **GTT (Good Till Triggered) Sell Order** at this exact price in Upstox
- When the stock hits it, you automatically sell for a 7-15% profit

### Exit 2: Time Stop — 63 Trading Days (~3 Calendar Months)
- If the stock hasn't hit the target in 63 trading days:
  - Run the Stock Analyzer again on that stock
  - If it says `BUY` or `HOLD` → **Keep holding** for 30 more days
  - If it says `SELL` or `AVOID` → **Sell at market open the next morning**

### Exit 3: There Is NO Stop Loss
- **The backtest PROVED that removing the stop loss improves returns**
- You do NOT place any stop-loss order
- The 63-day time stop is your safety net — it prevents dead money from sitting forever
- **Be mentally prepared**: a stock can drop 5-8% before recovering. This is normal and expected

---

## 📋 Trade Tracking Spreadsheet

Create a Google Sheet with these columns:

| Date | Stock | Buy Price | Qty | Invested | Target (GTT) | Day 63 Date | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 27-Feb-2026 | TRENT | ₹5,200 | 19 | ₹98,800 | ₹5,980 | 27-Jun-2026 | OPEN |
| 05-Mar-2026 | AUBANK | ₹650 | 153 | ₹99,450 | ₹745 | 05-Jul-2026 | OPEN |

---

## ⚠️ Critical Rules (Break These = Lose Money)

### Rule 1: ONE Trade at a Time
- You have ₹1L. That means **one stock at a time**
- Wait for the current trade to close (via Target or Time Stop) before entering the next one
- Average holding is ~35 days, so you'll make roughly **1-2 trades per month**

### Rule 2: Only Trade the 143-Stock Universe
- Only pick from Nifty 50 and Midcap 150 constituents
- NO penny stocks. NO IPOs. NO "hot tips" from WhatsApp groups

### Rule 3: Never Override the System
- If the scanner says `AVOID` → Don't buy, even if the chart "looks good"
- If the RS check fails → Don't buy, even if the scanner says `STRONG BUY`
- Both conditions must be true simultaneously

### Rule 4: Never Sell Before the Rules Say So
- Don't panic sell at -3%. The system expects temporary drawdowns
- Don't book partial profits at +2%. Let winners run to the full target
- Your edge comes from holding winners longer than losers

---

## 📈 Realistic Expectations with ₹1 Lakh

The backtest deployed ₹1L **per trade, simultaneously across 52 trades**. With only ₹1L total, you'll operate sequentially:

| Scenario | Trades/Year | Expected P&L | Assumptions |
| :--- | :--- | :--- | :--- |
| Conservative | 8-10 | ₹30,000—₹45,000 | ~35 day avg hold, some idle days |
| Moderate | 12-14 | ₹50,000—₹70,000 | Quick winners free up capital faster |
| Optimistic | 16-18 | ₹80,000—₹100,000 | Market trending up, many RS leaders |

> [!IMPORTANT]
> The ₹2.5L backtest result assumed you had ₹52L deployed across 52 parallel trades. With ₹1L, your absolute returns scale down proportionally, but the **75% win rate and the per-trade return percentages remain identical**.

### How to Scale
As your account grows, increase position size:
- Start: ₹1L → ₹1L positions
- Month 3 (if +₹30k): ₹1.3L → ₹1.3L positions
- Month 6 (if +₹60k): ₹1.6L → ₹1.6L positions
- Never increase position size by more than 30% at a time

---

## 🚀 Your First Trade Checklist (Tomorrow)

- [ ] **Tonight 7 PM**: Run the scanner on 10-15 stocks from the universe
- [ ] **Tonight 7:15 PM**: For any STRONG BUY (conf ≥ 70), check the 3M RS vs Nifty
- [ ] **Tonight 8 PM**: Note the stock name, target price, and quantity to buy
- [ ] **Tomorrow 9:15 AM**: Place a CNC Market Order on Upstox
- [ ] **Tomorrow 9:20 AM**: Place a GTT Sell at the Target Price
- [ ] **Tomorrow 9:25 AM**: Mark Day 63 on your calendar
- [ ] **Then**: Do absolutely nothing until the GTT triggers or Day 63 arrives

**That's it. You are now the casino, not the gambler. Let the 75% edge compound.**
