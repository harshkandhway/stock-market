# ORCHESTRATION PLAN: The 30% Yield Pursuit

## Overview
The "Long-Only Daily Swing" strategy hit a mathematical ceiling of ~10% annualized due to a 9-month market correction where it correctly sat in cash. To achieve the user's minimum 20-30% yield target, we must backtest three fundamentally different paradigms: Option A (Short-Seller), Option B (Covered Call / Options Seller proxy), and Option C (Breakout Scalper).

## Phase 1: Planning (Current)
This document outlines the architectural implementation for all three backtests.

## Phase 2: Implementation (Pending Approval)

We will use the existing Option E v2 codebase (`backtest_option_e_250.py`) as the framework (handling Upstox data, caching, Kelly sizing) and branch it into three distinct scripts:

### 1. `backtest_30pct_option_A_short.py` (The Short-Seller)
**Goal:** Make money during market corrections to eliminate the 9-month cash drag.
**Architecture:**
- **Signal Logic:** Add logic to identify "SELL" or "STRONG SELL" from `analyze_stock()`.
- **Momentum Filter (Inverted):** RSI > 60 (overbought), Price < 21-EMA (downtrend).
- **Execution:** Enter short on open, cover at target or 5% trailing stop above the trough.

### 2. `backtest_30pct_option_B_income.py` (The Options/Income Proxy)
**Goal:** Mathematically generate yield even if the stock goes absolutely nowhere.
**Architecture:**
- Since we don't have historical option chain data integrated fully for backtesting selling, we will simulate a **Covered Call** strategy.
- **Signal Logic:** Buy the underlying stock on a standard BUY signal.
- **Income Logic:** Instantly collect a theoretical 2% cash premium upfront (simulating selling a 30-day Call). 
- **Exit Logic:** If the stock drops, the 2% cushions the fall. If it blasts off, we are capped at the target. This turns a flat market into an income generator.

### 3. `backtest_30pct_option_C_scalp.py` (The Rapid Breakout)
**Goal:** Capital velocity. Don't wait 60 days for 15%. Wait 3 days for 3%.
**Architecture:**
- **Signal Logic:** Standard STRONG BUY outputs.
- **Exit Logic (The Change):** Hard target at +3.0%. Hard stop loss at -1.5%. Time stop at exactly 5 days.
- **Sizing:** Higher turnover means we can risk a bit more per trade since capital frees up every 3-5 days.

## Phase 3: Validation & Reporting
- Execute all three scripts over the same 2024-06 to 2025-07 period.
- Compare Total Return, Win Rate, and Maximum Drawdown against the 10% benchmark.
- Synthesize an orchestration report.

## Verification Required
- Since this involves financial modeling, we will ensure strict SLIPPAGE and CHARGES are applied to prevent artificial inflation of scalping profits.

---
**Status:** Awaiting User Approval to generate the 3 scripts.
