#!/usr/bin/env python3
"""
Stock Analyzer Pro Backtester — NO STOP LOSS
=============================================
Strategy: V1 Baseline with NO stop loss protection
- Entry: STRONG BUY / BUY (conf >= 70) → Buy at next day's open
- Stop: NONE — trades ride freely
- Target: Engine target
- Time Stop: Hard 63-day exit (no extensions)
- Purpose: Experimental — testing if removing SL improves returns
"""
import sys
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.cli.stock_analyzer_pro import analyze_stock

# Parameters
BACKTEST_DAYS = 252  # 1 year of trading days
HORIZON_DAYS = 63    # 3 months holding max
CAPITAL_PER_TRADE = 100000

# Nifty 50 + Nifty Next 50 (Expanded Universe)
SYMBOLS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HUL.NS', 'ITC.NS', 'SBI.NS', 'LARSEN.NS', 'BAJFINANCE.NS',
    'BHARTIARTL.NS', 'KOTAKBANK.NS', 'AXISBANK.NS', 'ASIANPAINT.NS',
    'SBIN.NS', 'MARUTI.NS', 'HCLTECH.NS', 'SUNPHARMA.NS', 'TITAN.NS', 'M&M.NS',
    'TRENT.NS', 'BEL.NS', 'HAL.NS', 'INDIGO.NS', 'TVSMOTOR.NS',
    'ZOMATO.NS', 'BHEL.NS', 'JINDALSTEL.NS', 'PNB.NS', 'VEDL.NS',
    'GAIL.NS', 'TORNTPHARM.NS', 'PIDILITIND.NS', 'BANKBARODA.NS', 'HAVELLS.NS',
    'RECLTD.NS', 'PFC.NS', 'CUMMINSIND.NS', 'DLF.NS', 'AMBUJACEM.NS'
]

# Delivery Equity costs (Zerodha)
SLIPPAGE_PCT = 0.001
STT_PCT_DELIVERY = 0.001
BROKERAGE = 0.0
EXCH_TXN_CHARGE = 0.0000325
GST_PCT = 0.18
SEBI_TURNOVER = 0.000001
STAMP_DUTY_BUY = 0.00015

def fetch_data(symbol: str) -> pd.DataFrame:
    print(f"Fetching 2y data for {symbol}...")
    try:
        df = yf.download(symbol, period='2y', interval='1d', progress=False)
        if df.empty:
            return df
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index)
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        return df[['open', 'high', 'low', 'close', 'volume', 'ema_21']]
    except Exception as e:
        print(f"Failed to fetch {symbol}: {e}")
        return pd.DataFrame()

def record_trade(symbol, entry_time, exit_time, entry_price, exit_price, reason):
    qty = int(CAPITAL_PER_TRADE / entry_price)
    if qty == 0: return None
    turnover = (entry_price + exit_price) * qty
    stt = (entry_price * qty + exit_price * qty) * STT_PCT_DELIVERY
    exch_txn = turnover * EXCH_TXN_CHARGE
    gst = (BROKERAGE * 2 + exch_txn) * GST_PCT
    sebi = turnover * SEBI_TURNOVER
    stamp_duty = (entry_price * qty) * STAMP_DUTY_BUY
    total_charges = stt + BROKERAGE * 2 + exch_txn + gst + sebi + stamp_duty
    gross_pnl = (exit_price - entry_price) * qty
    net_pnl = gross_pnl - total_charges
    return {
        'symbol': symbol, 'entry_time': entry_time, 'exit_time': exit_time,
        'days_held': (exit_time - entry_time).days,
        'entry_price': entry_price, 'exit_price': exit_price, 'qty': qty,
        'reason': reason, 'gross_pnl': gross_pnl, 'charges': total_charges,
        'net_pnl': net_pnl, 'win': 1 if net_pnl > 0 else 0
    }

def run_backtest():
    all_trades = []
    
    for symbol in SYMBOLS:
        df = fetch_data(symbol)
        if len(df) < BACKTEST_DAYS + 50:
            print(f"Skipping {symbol} - insufficient data")
            continue
            
        print(f"Backtesting {symbol} (No Stop Loss)...")
        
        in_trade = False
        entry_price = 0.0
        entry_time = None
        target = 0.0
        days_in_trade = 0
        
        start_idx = len(df) - BACKTEST_DAYS
        
        for i in range(start_idx, len(df) - 1):
            curr_date = df.index[i]
            next_date = df.index[i+1]
            curr_row = df.iloc[i]
            next_row = df.iloc[i+1]
            
            if in_trade:
                days_in_trade += 1
                
                # NO STOP LOSS — trade rides freely
                
                if next_row['high'] >= target:
                    exit_p = target * (1 - SLIPPAGE_PCT)
                    trade = record_trade(symbol, entry_time, next_date, entry_price, exit_p, "Target Hit")
                    if trade: all_trades.append(trade)
                    in_trade = False
                    continue
                    
                # Hard 63-day time stop (no extensions)
                if days_in_trade >= HORIZON_DAYS:
                    exit_p = next_row['close'] * (1 - SLIPPAGE_PCT) 
                    trade = record_trade(symbol, entry_time, next_date, entry_price, exit_p, f"Time Stop ({HORIZON_DAYS} days)")
                    if trade: all_trades.append(trade)
                    in_trade = False
                    continue
            
            if not in_trade:
                df_slice = df.iloc[: i + 1].copy()
                try:
                    analysis = analyze_stock(
                        symbol=symbol,
                        df=df_slice.drop(columns=['ema_21']),
                        mode='balanced',
                        timeframe='medium',
                        horizon='3months'
                    )
                    rec = analysis['recommendation']
                    conf = analysis['confidence']
                    
                    if ("STRONG BUY" in rec or "BUY" == rec) and ("AVOID" not in rec and "WARNING" not in rec) and conf >= 70:
                        in_trade = True
                        entry_price = next_row['open'] * (1 + SLIPPAGE_PCT) 
                        entry_time = next_date
                        target = analysis['target']
                        days_in_trade = 0
                except Exception:
                    pass
                    
        if in_trade:
            last_date = df.index[-1]
            last_close = df['close'].iloc[-1]
            exit_p = last_close * (1 - SLIPPAGE_PCT)
            trade = record_trade(symbol, entry_time, last_date, entry_price, exit_p, "End of Backtest")
            if trade: all_trades.append(trade)
            
    # Results
    if not all_trades:
        print("\nNo trades were generated by the strategy.")
        return
        
    trades_df = pd.DataFrame(all_trades)
    wins = trades_df[trades_df['win'] == 1]
    losses = trades_df[trades_df['win'] == 0]
    
    print("\n" + "="*50)
    print("🎯 BACKTEST RESULTS — NO STOP LOSS")
    print("="*50)
    print(f"Period: Last 1 Year ({BACKTEST_DAYS} Trading Days)")
    print(f"Stocks Tested: {len(SYMBOLS)}")
    print(f"Capital Per Trade: ₹{CAPITAL_PER_TRADE:,.2f}")
    print("-" * 50)
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate:     {(len(wins)/len(trades_df))*100:.2f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Avg Days Held:{trades_df['days_held'].mean():.1f} days")
    print("-" * 50)
    print(f"Gross P&L:    ₹{trades_df['gross_pnl'].sum():,.2f}")
    print(f"Total Charges:₹{trades_df['charges'].sum():,.2f}")
    print(f"NET P&L:      ₹{trades_df['net_pnl'].sum():,.2f}")
    print("-" * 50)
    print(f"Avg Win:      ₹{wins['net_pnl'].mean():,.2f}" if len(wins) > 0 else "Avg Win: N/A")
    print(f"Avg Loss:     ₹{losses['net_pnl'].mean():,.2f}" if len(losses) > 0 else "Avg Loss: N/A")
    print(f"Max Win:      ₹{trades_df['net_pnl'].max():,.2f}")
    print(f"Max Loss:     ₹{trades_df['net_pnl'].min():,.2f}")
    print("="*50)
    
    trades_df.to_csv('backtest_no_stoploss_trades.csv', index=False)
    print("\nDetailed trades saved to 'backtest_no_stoploss_trades.csv'")
    print("\nBreakdown by Reason:")
    print(trades_df['reason'].value_counts())

if __name__ == "__main__":
    run_backtest()
