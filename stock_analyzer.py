#!/usr/bin/env python3
"""
Stock Analyzer - Technical Analysis Tool
Provides buy/sell recommendations with target prices and stop losses
Works with any stock ticker supported by Yahoo Finance
"""

import sys
from yahooquery import Ticker
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands

def fetch_data(symbol: str, period: str = '3mo') -> pd.DataFrame:
    """Fetch historical data from Yahoo Finance"""
    try:
        ticker = Ticker(symbol)
        df = ticker.history(period=period, interval='1d')
        
        if isinstance(df, str):  # Error message returned
            print(f"Error fetching {symbol}: {df}")
            return pd.DataFrame()
        
        if df.empty or 'close' not in df.columns:
            print(f"No data available for {symbol}")
            return pd.DataFrame()
        
        # Flatten multi-index if present
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index(level=0, drop=True)
        
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()

def analyze_stock(symbol: str, df: pd.DataFrame) -> dict:
    """Perform technical analysis on stock data"""
    close = df['close']
    high = df['high']
    low = df['low']
    
    # Calculate indicators
    # RSI (14-day) - measures momentum
    rsi_indicator = RSIIndicator(close, window=14)
    rsi = rsi_indicator.rsi()
    latest_rsi = rsi.iloc[-1] if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else 50
    
    # MACD (12, 26, 9) - trend following
    macd_indicator = MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd_indicator.macd()
    signal_line = macd_indicator.macd_signal()
    macd_hist = macd_indicator.macd_diff()
    latest_macd_hist = macd_hist.iloc[-1] if len(macd_hist) > 0 and not pd.isna(macd_hist.iloc[-1]) else 0
    
    # Check for MACD crossover (bullish signal)
    macd_crossover = False
    if len(macd_hist) >= 2:
        macd_crossover = macd_hist.iloc[-1] > 0 and macd_hist.iloc[-2] <= 0
    
    # EMA (20-day) - short-term trend
    ema20 = EMAIndicator(close, window=20).ema_indicator()
    latest_ema20 = ema20.iloc[-1] if len(ema20) > 0 and not pd.isna(ema20.iloc[-1]) else close.iloc[-1]
    
    # SMA (50-day) - medium-term trend
    sma50 = SMAIndicator(close, window=50).sma_indicator()
    latest_sma50 = sma50.iloc[-1] if len(sma50) > 0 and not pd.isna(sma50.iloc[-1]) else close.iloc[-1]
    
    # ATR (14-day) - volatility for targets/stoplosses
    atr_indicator = AverageTrueRange(high, low, close, window=14)
    atr = atr_indicator.average_true_range()
    latest_atr = atr.iloc[-1] if len(atr) > 0 and not pd.isna(atr.iloc[-1]) else close.iloc[-1] * 0.02
    
    # Bollinger Bands - volatility and mean reversion
    bb = BollingerBands(close, window=20, window_dev=2)
    bb_upper = bb.bollinger_hband().iloc[-1]
    bb_lower = bb.bollinger_lband().iloc[-1]
    bb_middle = bb.bollinger_mavg().iloc[-1]
    
    # Stochastic Oscillator - overbought/oversold
    stoch = StochasticOscillator(high, low, close, window=14, smooth_window=3)
    stoch_k = stoch.stoch().iloc[-1] if len(stoch.stoch()) > 0 else 50
    stoch_d = stoch.stoch_signal().iloc[-1] if len(stoch.stoch_signal()) > 0 else 50
    
    # Momentum: % change over last 10 days
    if len(close) >= 10:
        momentum_10d = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100
    else:
        momentum_10d = 0
    
    # 52-week high/low from available data
    high_52w = high.max()
    low_52w = low.min()
    current_price = close.iloc[-1]
    
    # Support and Resistance levels
    recent_highs = high.tail(20).max()
    recent_lows = low.tail(20).min()
    
    # Volume analysis
    volume = df['volume'] if 'volume' in df.columns else pd.Series([0])
    avg_volume = volume.tail(20).mean()
    latest_volume = volume.iloc[-1]
    volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1
    
    # Scoring system for recommendation
    buy_score = 0
    sell_score = 0
    
    # RSI signals
    if latest_rsi < 30:
        buy_score += 2  # Oversold - strong buy signal
    elif latest_rsi < 40:
        buy_score += 1  # Approaching oversold
    elif latest_rsi > 70:
        sell_score += 2  # Overbought - strong sell signal
    elif latest_rsi > 60:
        sell_score += 1  # Approaching overbought
    
    # MACD signals
    if latest_macd_hist > 0:
        buy_score += 1
        if macd_crossover:
            buy_score += 1  # Bullish crossover - strong signal
    else:
        sell_score += 1
    
    # Price vs Moving Averages
    if current_price > latest_ema20:
        buy_score += 1
    else:
        sell_score += 1
    
    if current_price > latest_sma50:
        buy_score += 1
    else:
        sell_score += 1
    
    # Momentum
    if momentum_10d > 5:
        buy_score += 2
    elif momentum_10d > 2:
        buy_score += 1
    elif momentum_10d < -5:
        sell_score += 2
    elif momentum_10d < -2:
        sell_score += 1
    
    # Stochastic
    if stoch_k < 20:
        buy_score += 1  # Oversold
    elif stoch_k > 80:
        sell_score += 1  # Overbought
    
    # Volume confirmation
    if volume_ratio > 1.5 and momentum_10d > 0:
        buy_score += 1  # High volume on uptrend
    elif volume_ratio > 1.5 and momentum_10d < 0:
        sell_score += 1  # High volume on downtrend
    
    # Determine recommendation
    net_score = buy_score - sell_score
    
    if net_score >= 4:
        recommendation = 'STRONG BUY'
        target = current_price + 3 * latest_atr
        stoploss = current_price - 1.5 * latest_atr
    elif net_score >= 2:
        recommendation = 'BUY'
        target = current_price + 2 * latest_atr
        stoploss = current_price - 1.5 * latest_atr
    elif net_score >= 1:
        recommendation = 'WEAK BUY'
        target = current_price + 1.5 * latest_atr
        stoploss = current_price - 1.5 * latest_atr
    elif net_score <= -4:
        recommendation = 'STRONG SELL'
        target = current_price - 3 * latest_atr
        stoploss = current_price + 1.5 * latest_atr
    elif net_score <= -2:
        recommendation = 'SELL'
        target = current_price - 2 * latest_atr
        stoploss = current_price + 1.5 * latest_atr
    elif net_score <= -1:
        recommendation = 'WEAK SELL'
        target = current_price - 1.5 * latest_atr
        stoploss = current_price + 1.5 * latest_atr
    else:
        recommendation = 'HOLD'
        target = current_price + 1 * latest_atr
        stoploss = current_price - 1 * latest_atr
    
    # Risk-Reward Ratio
    reward = abs(target - current_price)
    risk = abs(current_price - stoploss)
    risk_reward = reward / risk if risk > 0 else 0
    
    return {
        'symbol': symbol,
        'price': current_price,
        'rsi': latest_rsi,
        'macd_hist': latest_macd_hist,
        'macd_crossover': macd_crossover,
        'ema20': latest_ema20,
        'sma50': latest_sma50,
        'momentum_10d': momentum_10d,
        'atr': latest_atr,
        'stoch_k': stoch_k,
        'stoch_d': stoch_d,
        'bb_upper': bb_upper,
        'bb_lower': bb_lower,
        'bb_middle': bb_middle,
        'high_52w': high_52w,
        'low_52w': low_52w,
        'support': recent_lows,
        'resistance': recent_highs,
        'volume_ratio': volume_ratio,
        'buy_score': buy_score,
        'sell_score': sell_score,
        'net_score': net_score,
        'recommendation': recommendation,
        'target': target,
        'stoploss': stoploss,
        'risk_reward': risk_reward
    }

def print_analysis(analysis: dict):
    """Print formatted analysis results"""
    print(f"\n{'='*80}")
    print(f"  {analysis['symbol']} - TECHNICAL ANALYSIS")
    print(f"{'='*80}")
    
    print(f"\n  PRICE DATA")
    print(f"  {'─'*40}")
    print(f"  Current Price:     ₹{analysis['price']:.2f}")
    print(f"  52-Week High:      ₹{analysis['high_52w']:.2f}")
    print(f"  52-Week Low:       ₹{analysis['low_52w']:.2f}")
    print(f"  Support Level:     ₹{analysis['support']:.2f}")
    print(f"  Resistance Level:  ₹{analysis['resistance']:.2f}")
    
    print(f"\n  TECHNICAL INDICATORS")
    print(f"  {'─'*40}")
    
    # RSI with interpretation
    rsi_status = 'OVERBOUGHT' if analysis['rsi'] > 70 else 'OVERSOLD' if analysis['rsi'] < 30 else 'NEUTRAL'
    print(f"  RSI (14-day):      {analysis['rsi']:.2f} ({rsi_status})")
    
    # MACD with interpretation
    macd_status = 'BULLISH' if analysis['macd_hist'] > 0 else 'BEARISH'
    crossover_note = ' [CROSSOVER!]' if analysis['macd_crossover'] else ''
    print(f"  MACD Histogram:    {analysis['macd_hist']:.4f} ({macd_status}){crossover_note}")
    
    # Moving Averages
    ema_status = 'ABOVE' if analysis['price'] > analysis['ema20'] else 'BELOW'
    sma_status = 'ABOVE' if analysis['price'] > analysis['sma50'] else 'BELOW'
    print(f"  EMA (20-day):      ₹{analysis['ema20']:.2f} (Price {ema_status})")
    print(f"  SMA (50-day):      ₹{analysis['sma50']:.2f} (Price {sma_status})")
    
    # Momentum
    print(f"  10-Day Momentum:   {analysis['momentum_10d']:+.2f}%")
    
    # Stochastic
    stoch_status = 'OVERBOUGHT' if analysis['stoch_k'] > 80 else 'OVERSOLD' if analysis['stoch_k'] < 20 else 'NEUTRAL'
    print(f"  Stochastic %K:     {analysis['stoch_k']:.2f} ({stoch_status})")
    
    # Bollinger Bands
    print(f"  Bollinger Bands:   ₹{analysis['bb_lower']:.2f} - ₹{analysis['bb_upper']:.2f}")
    
    # ATR
    print(f"  ATR (Volatility):  ₹{analysis['atr']:.2f} ({analysis['atr']/analysis['price']*100:.2f}%)")
    
    # Volume
    vol_status = 'HIGH' if analysis['volume_ratio'] > 1.5 else 'LOW' if analysis['volume_ratio'] < 0.5 else 'NORMAL'
    print(f"  Volume Ratio:      {analysis['volume_ratio']:.2f}x ({vol_status})")
    
    print(f"\n  SCORING")
    print(f"  {'─'*40}")
    print(f"  Buy Score:         {analysis['buy_score']}")
    print(f"  Sell Score:        {analysis['sell_score']}")
    print(f"  Net Score:         {analysis['net_score']:+d}")
    
    print(f"\n  {'='*40}")
    print(f"  RECOMMENDATION:    {analysis['recommendation']}")
    print(f"  {'='*40}")
    
    target_pct = (analysis['target'] - analysis['price']) / analysis['price'] * 100
    stoploss_pct = (analysis['stoploss'] - analysis['price']) / analysis['price'] * 100
    
    print(f"  TARGET PRICE:      ₹{analysis['target']:.2f} ({target_pct:+.2f}%)")
    print(f"  STOPLOSS:          ₹{analysis['stoploss']:.2f} ({stoploss_pct:+.2f}%)")
    print(f"  RISK/REWARD RATIO: 1:{analysis['risk_reward']:.2f}")
    
    print(f"\n{'='*80}")

def main():
    """Main function to run stock analysis"""
    # Default tickers or from command line
    if len(sys.argv) > 1:
        tickers = sys.argv[1:]
    else:
        tickers = ['SILVERBEES.NS', 'GOLDBEES.NS']
    
    print("\n" + "="*80)
    print("  STOCK ANALYZER - Technical Analysis Tool")
    print("  Date: Jan 8, 2026")
    print("="*80)
    
    results = []
    
    for symbol in tickers:
        print(f"\nFetching data for {symbol}...")
        df = fetch_data(symbol)
        
        if df.empty:
            continue
        
        analysis = analyze_stock(symbol, df)
        results.append(analysis)
        print_analysis(analysis)
    
    # Summary for multiple stocks
    if len(results) > 1:
        print("\n" + "="*80)
        print("  SUMMARY")
        print("="*80)
        print(f"\n  {'Symbol':<20} {'Price':>10} {'Recommendation':<15} {'Target':>10} {'Stoploss':>10}")
        print(f"  {'-'*65}")
        for r in results:
            print(f"  {r['symbol']:<20} ₹{r['price']:>8.2f} {r['recommendation']:<15} ₹{r['target']:>8.2f} ₹{r['stoploss']:>8.2f}")
    
    print("\n" + "="*80)
    print("  DISCLAIMER")
    print("="*80)
    print("  This is technical analysis for short-term trading (1-3 months).")
    print("  Past performance is not indicative of future results.")
    print("  Always consult a financial advisor before investing.")
    print("  Use proper position sizing and risk management.")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
