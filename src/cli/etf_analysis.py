"""
ETF Analysis Tool
Analyzes ETF performance using technical indicators

Author: Harsh Kandhway
"""

from yahooquery import Ticker
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange

# Fetch 3-month data for short-term analysis using Yahoo Finance API via yahooquery
tickers = ['SILVERBEES.NS', 'GOLDBEES.NS']
data = {}
for symbol in tickers:
    ticker = Ticker(symbol)
    df = ticker.history(period='3mo', interval='1d')
    if df.empty or 'close' not in df.columns:
        print(f"No data for {symbol}")
        continue
    # yahooquery returns multi-index, flatten it
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index(level=0, drop=True)
    data[symbol] = df

recommendations = {}
for ticker, df in data.items():
    close = df['close']

    # RSI (14-day)
    rsi_indicator = RSIIndicator(close)
    rsi = rsi_indicator.rsi()
    latest_rsi = rsi.iloc[-1] if not rsi.empty else 50

    # MACD
    macd_indicator = MACD(close)
    macd_line = macd_indicator.macd()
    signal_line = macd_indicator.macd_signal()
    hist = macd_indicator.macd_diff()
    latest_hist = hist.iloc[-1] if not hist.empty else 0

    # Momentum: % change over last 10 days
    if len(close) >= 10:
        momentum = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100
    else:
        momentum = 0

    # ATR for volatility-based targets and stoplosses
    atr_indicator = AverageTrueRange(df['high'], df['low'], close)
    atr = atr_indicator.average_true_range()
    latest_atr = atr.iloc[-1] if not atr.empty else close.iloc[-1] * 0.02  # fallback 2%

    # Buy signals: oversold RSI, bullish MACD, strong momentum
    buy_signals = 0
    if latest_rsi < 40:
        buy_signals += 1
    if latest_hist > 0:
        buy_signals += 1
    if momentum > 3:  # adjusted for short-term
        buy_signals += 1

    if buy_signals >= 2:
        rec = 'Buy'
        target = close.iloc[-1] + 2 * latest_atr
        stoploss = close.iloc[-1] - 1.5 * latest_atr
    elif buy_signals == 1:
        rec = 'Hold'
        target = close.iloc[-1] + 1 * latest_atr
        stoploss = close.iloc[-1] - 1 * latest_atr
    else:
        rec = 'Sell'
        target = close.iloc[-1] - 2 * latest_atr
        stoploss = close.iloc[-1] + 1.5 * latest_atr

    recommendations[ticker] = {
        'price': close.iloc[-1],
        'rsi': latest_rsi,
        'macd_hist': latest_hist,
        'momentum': momentum,
        'atr': latest_atr,
        'recommendation': rec,
        'target': target,
        'stoploss': stoploss
    }

# Balanced short-term plan
silver_rec = recommendations.get('SILVERBEES.NS', {}).get('recommendation', 'Hold')
gold_rec = recommendations.get('GOLDBEES.NS', {}).get('recommendation', 'Hold')

if silver_rec == 'Buy' and gold_rec == 'Buy':
    plan = 'Balanced: Allocate 50% to Silver ETF, 50% to Gold ETF for optimal short-term growth.'
elif silver_rec == 'Buy':
    plan = 'Aggressive-balanced: Allocate 60% to Silver ETF for momentum, 40% to Gold ETF for stability.'
elif gold_rec == 'Buy':
    plan = 'Conservative-balanced: Allocate 60% to Gold ETF for safety, 40% to Silver ETF for upside.'
else:
    plan = 'Neutral: Hold both or consider rebalancing; market shows caution signals.'

print(f"Short-term Balanced Investment Plan (as of Jan 8, 2026): {plan}")
print("\n" + "="*80)
print("DETAILED ANALYSIS")
print("="*80)
for ticker, info in recommendations.items():
    print(f"\n{ticker}")
    print(f"  Current Price: ₹{info['price']:.2f}")
    print(f"  RSI (14-day): {info['rsi']:.2f} {'(Overbought)' if info['rsi'] > 70 else '(Oversold)' if info['rsi'] < 30 else '(Neutral)'}")
    print(f"  MACD Histogram: {info['macd_hist']:.4f} {'(Bullish)' if info['macd_hist'] > 0 else '(Bearish)'}")
    print(f"  10-Day Momentum: {info['momentum']:.2f}%")
    print(f"  ATR (Volatility): ₹{info['atr']:.2f}")
    print(f"  ─────────────────────────────────")
    print(f"  RECOMMENDATION: {info['recommendation']}")
    print(f"  TARGET PRICE:   ₹{info['target']:.2f} ({((info['target'] - info['price']) / info['price'] * 100):+.2f}%)")
    print(f"  STOPLOSS:       ₹{info['stoploss']:.2f} ({((info['stoploss'] - info['price']) / info['price'] * 100):+.2f}%)")

print("\n" + "="*80)
print("DISCLAIMER: This is technical analysis for short-term (1-3 months).")
print("Past performance is not indicative of future results.")
print("Always consult a financial advisor before investing.")
print("="*80)