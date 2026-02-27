#!/usr/bin/env python3
"""
RS Overlay No SL — UPSTOX REAL DATA VALIDATION
================================================
Uses REAL Upstox brokerage daily candles (not Yahoo Finance)
Period: July 2024 to July 2025
Strategy: RS Overlay + No Stop Loss + Dynamic Time-Stop
"""
import sys, os, time as time_module
import pandas as pd
import requests
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from src.cli.stock_analyzer_pro import analyze_stock

# ============================================================
# UPSTOX CONFIG
# ============================================================
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/Trades/.env'))
ACCESS_TOKEN = os.getenv('UPSTOX_LIVE_TOKEN', '')

HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Bearer {ACCESS_TOKEN}'
}

# Backtest parameters
FROM_DATE = '2024-07-01'
TO_DATE   = '2025-07-01'
HORIZON_DAYS = 63
CAPITAL_PER_TRADE = 100000

# ISIN mapping for Nifty 50 + Next 50 stocks (Upstox uses NSE_EQ|ISIN format)
SYMBOL_ISIN_MAP = {
    'RELIANCE':    'INE002A01018',
    'TCS':         'INE467B01029',
    'HDFCBANK':    'INE040A01034',
    'INFY':        'INE009A01021',
    'ICICIBANK':   'INE090A01021',
    'ITC':         'INE154A01025',
    'SBIN':        'INE062A01020',
    'BAJFINANCE':  'INE296A01024',
    'BHARTIARTL':  'INE397D01024',
    'KOTAKBANK':   'INE237A01028',
    'AXISBANK':    'INE238A01034',
    'ASIANPAINT':  'INE021A01026',
    'MARUTI':      'INE585B01010',
    'HCLTECH':     'INE860A01027',
    'SUNPHARMA':   'INE044A01036',
    'TITAN':       'INE280A01028',
    'M&M':         'INE101A01026',
    'TRENT':       'INE849A01020',
    'BEL':         'INE263A01024',
    'HAL':         'INE066F01020',
    'INDIGO':      'INE646L01027',
    'TVSMOTOR':    'INE494B01023',
    'BHEL':        'INE257A01026',
    'JINDALSTEL':  'INE220G01021',
    'PNB':         'INE160A01022',
    'VEDL':        'INE205A01025',
    'GAIL':        'INE129A01019',
    'TORNTPHARM':  'INE685A01028',
    'PIDILITIND':  'INE318A01026',
    'BANKBARODA':  'INE028A01039',
    'HAVELLS':     'INE176B01034',
    'RECLTD':      'INE020B01018',
    'PFC':         'INE134E01011',
    'CUMMINSIND':  'INE298A01020',
    'DLF':         'INE271C01023',
    'AMBUJACEM':   'INE079A01024',
}

# Delivery Equity costs (Upstox charges same as Zerodha for delivery)
SLIPPAGE_PCT = 0.001
STT_PCT_DELIVERY = 0.001
BROKERAGE = 0.0
EXCH_TXN_CHARGE = 0.0000325
GST_PCT = 0.18
SEBI_TURNOVER = 0.000001
STAMP_DUTY_BUY = 0.00015

def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                time_module.sleep(3)
            elif r.status_code == 401:
                print(f"  ❌ AUTH ERROR: Token expired!")
                return None
            else:
                if attempt == retries - 1:
                    return None
        except Exception:
            if attempt == retries - 1:
                return None
        time_module.sleep(0.3)
    return None

def fetch_upstox_data(symbol: str, isin: str) -> pd.DataFrame:
    """Fetch daily candles from the Upstox V2 Historical Candle API."""
    instrument_key = f"NSE_EQ%7C{isin}"
    url = f"https://api.upstox.com/v2/historical-candle/{instrument_key}/day/{TO_DATE}/{FROM_DATE}"
    
    print(f"  Fetching Upstox data for {symbol} ({isin})...")
    data = api_get(url)
    
    if not data or 'data' not in data or 'candles' not in data['data']:
        print(f"  ❌ Failed to fetch {symbol}")
        return pd.DataFrame()
    
    candles = data['data']['candles']
    if not candles:
        return pd.DataFrame()
    
    # Candle format: [date, open, high, low, close, volume, oi]
    rows = []
    for c in candles:
        rows.append({
            'date': pd.Timestamp(c[0]),
            'open': float(c[1]),
            'high': float(c[2]),
            'low': float(c[3]),
            'close': float(c[4]),
            'volume': int(c[5])
        })
    
    df = pd.DataFrame(rows)
    df = df.sort_values('date').set_index('date')
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    print(f"    ✅ {len(df)} candles loaded ({df.index[0].date()} to {df.index[-1].date()})")
    return df

def fetch_nifty_upstox() -> pd.DataFrame:
    """Fetch Nifty 50 index daily candles from Upstox."""
    instrument_key = "NSE_INDEX%7CNifty%2050"
    url = f"https://api.upstox.com/v2/historical-candle/{instrument_key}/day/{TO_DATE}/{FROM_DATE}"
    
    print("Fetching Nifty 50 index from Upstox...")
    data = api_get(url)
    
    if not data or 'data' not in data:
        print("❌ Failed to fetch Nifty 50 index")
        return pd.DataFrame()
    
    candles = data['data']['candles']
    rows = []
    for c in candles:
        rows.append({
            'date': pd.Timestamp(c[0]),
            'close': float(c[4])
        })
    
    df = pd.DataFrame(rows).sort_values('date').set_index('date')
    df['nifty_return_63d'] = df['close'].pct_change(periods=63)
    print(f"  ✅ Nifty: {len(df)} candles loaded")
    return df

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
    
    # Fetch Nifty 50 baseline for RS comparison
    nifty_df = fetch_nifty_upstox()
    if nifty_df.empty:
        print("Cannot proceed without Nifty data!")
        return
    
    for symbol, isin in SYMBOL_ISIN_MAP.items():
        df = fetch_upstox_data(symbol, isin)
        if len(df) < 100:
            print(f"  Skipping {symbol} - insufficient data ({len(df)} candles)")
            continue
        
        # Calculate 63-day rolling return for RS comparison
        df['stock_return_63d'] = df['close'].pct_change(periods=63)
        
        print(f"  Backtesting {symbol} (Upstox | RS Overlay | No SL)...")
        
        in_trade = False
        entry_price = 0.0
        entry_time = None
        target = 0.0
        days_in_trade = 0
        current_time_stop = HORIZON_DAYS
        
        for i in range(63, len(df) - 1):  # Start after 63 days for RS calc
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
                
                # Dynamic Time Stop
                if days_in_trade >= current_time_stop:
                    df_slice = df.iloc[: i + 1].copy()
                    try:
                        analysis = analyze_stock(
                            symbol=f"{symbol}.NS",
                            df=df_slice.drop(columns=['ema_21', 'stock_return_63d'], errors='ignore'),
                            mode='balanced',
                            timeframe='short',
                            horizon='1month'
                        )
                        rec = analysis['recommendation']
                        if "BUY" in rec or "HOLD" in rec:
                            current_time_stop += 30
                            continue
                    except Exception:
                        pass
                    
                    exit_p = next_row['close'] * (1 - SLIPPAGE_PCT)
                    trade = record_trade(symbol, entry_time, next_date, entry_price, exit_p, 
                                        f"Time Stop ({current_time_stop} days)")
                    if trade: all_trades.append(trade)
                    in_trade = False
                    continue
            
            if not in_trade:
                df_slice = df.iloc[: i + 1].copy()
                try:
                    analysis = analyze_stock(
                        symbol=f"{symbol}.NS",
                        df=df_slice.drop(columns=['ema_21', 'stock_return_63d'], errors='ignore'),
                        mode='balanced',
                        timeframe='medium',
                        horizon='3months'
                    )
                    rec = analysis['recommendation']
                    conf = analysis['confidence']
                    
                    if ("STRONG BUY" in rec or "BUY" == rec) and ("AVOID" not in rec and "WARNING" not in rec) and conf >= 70:
                        
                        # RS OVERLAY: Stock must be beating Nifty 50
                        has_rs = False
                        if not pd.isna(curr_row['stock_return_63d']) and not nifty_df.empty:
                            try:
                                nifty_idx = nifty_df.index.get_indexer([curr_date], method='pad')[0]
                                if nifty_idx != -1:
                                    nifty_ret = nifty_df.iloc[nifty_idx]['nifty_return_63d']
                                    stock_ret = curr_row['stock_return_63d']
                                    if not pd.isna(nifty_ret) and stock_ret > nifty_ret:
                                        has_rs = True
                            except:
                                pass
                        else:
                            has_rs = True
                        
                        if not has_rs:
                            continue
                        
                        in_trade = True
                        entry_price = next_row['open'] * (1 + SLIPPAGE_PCT)
                        entry_time = next_date
                        target = analysis['target']
                        days_in_trade = 0
                        current_time_stop = HORIZON_DAYS
                except Exception:
                    pass
        
        # Close any open trade at backtest end
        if in_trade:
            last_date = df.index[-1]
            last_close = df['close'].iloc[-1]
            exit_p = last_close * (1 - SLIPPAGE_PCT)
            trade = record_trade(symbol, entry_time, last_date, entry_price, exit_p, "End of Backtest")
            if trade: all_trades.append(trade)
    
    # Results
    if not all_trades:
        print("\nNo trades were generated.")
        return
    
    trades_df = pd.DataFrame(all_trades)
    wins = trades_df[trades_df['win'] == 1]
    losses = trades_df[trades_df['win'] == 0]
    
    print("\n" + "="*55)
    print("🎯 UPSTOX REAL DATA — RS OVERLAY + NO SL BACKTEST")
    print("="*55)
    print(f"Data Source: Upstox V2 Historical Candle API")
    print(f"Period: {FROM_DATE} to {TO_DATE}")
    print(f"Stocks Tested: {len(SYMBOL_ISIN_MAP)}")
    print(f"Capital Per Trade: ₹{CAPITAL_PER_TRADE:,.2f}")
    print("-" * 55)
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate:     {(len(wins)/len(trades_df))*100:.2f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Avg Days Held:{trades_df['days_held'].mean():.1f} days")
    print("-" * 55)
    print(f"Gross P&L:    ₹{trades_df['gross_pnl'].sum():,.2f}")
    print(f"Total Charges:₹{trades_df['charges'].sum():,.2f}")
    print(f"NET P&L:      ₹{trades_df['net_pnl'].sum():,.2f}")
    print("-" * 55)
    print(f"Avg Win:      ₹{wins['net_pnl'].mean():,.2f}" if len(wins) > 0 else "Avg Win: N/A")
    print(f"Avg Loss:     ₹{losses['net_pnl'].mean():,.2f}" if len(losses) > 0 else "Avg Loss: N/A")
    print(f"Max Win:      ₹{trades_df['net_pnl'].max():,.2f}")
    print(f"Max Loss:     ₹{trades_df['net_pnl'].min():,.2f}")
    print("="*55)
    
    trades_df.to_csv('backtest_upstox_rs_no_sl_trades.csv', index=False)
    print("\nDetailed trades saved to 'backtest_upstox_rs_no_sl_trades.csv'")
    print("\nBreakdown by Reason:")
    print(trades_df['reason'].value_counts())

if __name__ == "__main__":
    run_backtest()
