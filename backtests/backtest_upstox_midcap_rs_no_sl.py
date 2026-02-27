#!/usr/bin/env python3
"""
RS Overlay No SL — UPSTOX REAL DATA (Midcap 150 + Nifty 50)
=============================================================
Uses REAL Upstox brokerage daily candles with LOCAL CSV CACHING.
Period: July 2024 to July 2025
Strategy: RS Overlay + No Stop Loss + Dynamic Time-Stop
Data is cached in stock-market/data/upstox_cache/ so it's never re-downloaded.
"""
import sys, os, time as time_module, json, gzip
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

# Cache directory (saved locally so you never re-download)
CACHE_DIR = os.path.join(project_root, 'data', 'upstox_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# ============================================================
# NIFTY 50 + MIDCAP 150 UNIVERSE (200 stocks)
# ============================================================
# Nifty 50 Constituents
NIFTY_50 = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'ITC', 'SBIN',
    'BAJFINANCE', 'BHARTIARTL', 'KOTAKBANK', 'AXISBANK', 'ASIANPAINT',
    'MARUTI', 'HCLTECH', 'SUNPHARMA', 'TITAN', 'M&M', 'TRENT', 'BEL',
    'HAL', 'INDIGO', 'TVSMOTOR', 'WIPRO', 'ADANIPORTS', 'NTPC',
    'POWERGRID', 'ULTRACEMCO', 'ONGC', 'JSWSTEEL', 'TATAMOTORS',
    'BAJAJ-AUTO', 'COALINDIA', 'LT', 'HINDALCO', 'DRREDDY',
    'NESTLEIND', 'BAJAJFINSV', 'CIPLA', 'EICHERMOT', 'DIVISLAB',
    'GRASIM', 'APOLLOHOSP', 'HEROMOTOCO', 'TECHM', 'BRITANNIA',
    'TATASTEEL', 'SHRIRAMFIN', 'TATACONSUM', 'BPCL', 'SBILIFE'
]

# Nifty Midcap 150 Constituents (Partial — Top 100 by weight)
MIDCAP_150 = [
    'PERSISTENT', 'FEDERALBNK', 'MAXHEALTH', 'POLYCAB', 'OBEROIRLTY',
    'AUBANK', 'SUNDARMFIN', 'MPHASIS', 'COFORGE', 'PHOENIXLTD',
    'AUROPHARMA', 'CUMMINSIND', 'GODREJPROP', 'INDIANHOTL', 'JUBLFOOD',
    'THERMAX', 'CONCOR', 'VOLTAS', 'PRESTIGE', 'LTTS',
    'MUTHOOTFIN', 'KPITTECH', 'LICI', 'DIXON', 'IDFCFIRSTB',
    'ESCORTS', 'ASTRAL', 'NMDC', 'PAGEIND', 'DELHIVERY',
    'APLAPOLLO', 'LINDEINDIA', 'HONAUT', 'MRF', 'RELAXO',
    'BANKINDIA', 'SYNGENE', 'METROPOLIS', 'ATUL', 'BDL',
    'MARICO', 'POONAWALLA', 'SUPREMEIND', 'NAUKRI', 'ABCAPITAL',
    'CROMPTON', 'EMAMILTD', 'TATACHEM', 'NAM-INDIA', 'IDFC',
    'TATAELXSI', 'LALPATHLAB', 'SAIL', 'BHARATFORG', 'CHOLAFIN',
    'IRCTC', 'PETRONET', 'IPCALAB', 'DEEPAKNTR', 'BIOCON',
    'BATAINDIA', 'GMRINFRA', 'HDFCAMC', 'DEVYANI', 'KALYANKJIL',
    'LLOYDSME', 'IIFL', 'SUNTV', 'JKCEMENT', 'RAMCOCEM',
    'ZYDUSLIFE', 'BALKRISIND', 'MANAPPURAM', 'RECLTD', 'PFC',
    'DLF', 'AMBUJACEM', 'BHEL', 'JINDALSTEL', 'PNB',
    'VEDL', 'GAIL', 'TORNTPHARM', 'PIDILITIND', 'BANKBARODA',
    'HAVELLS', 'TVSMOTOR', 'INDIGO', 'TRENT', 'LICHSGFIN',
    'CANFINHOME', 'CENTRALBK', 'IRFC', 'NHPC', 'SJVN',
    'HUDCO', 'KEI', 'TIINDIA', 'SOLARINDS', 'JSWENERGY'
]

ALL_SYMBOLS = list(set(NIFTY_50 + MIDCAP_150))
print(f"Universe: {len(ALL_SYMBOLS)} unique stocks")

# Delivery costs
SLIPPAGE_PCT = 0.001
STT_PCT_DELIVERY = 0.001
BROKERAGE = 0.0
EXCH_TXN_CHARGE = 0.0000325
GST_PCT = 0.18
SEBI_TURNOVER = 0.000001
STAMP_DUTY_BUY = 0.00015

# ============================================================
# INSTRUMENT RESOLUTION (Auto-resolve symbol → ISIN)
# ============================================================
INSTRUMENT_CACHE_FILE = os.path.join(CACHE_DIR, 'nse_instruments.json')

def load_instrument_map():
    """Download and cache the Upstox instrument master, return symbol→instrument_key map."""
    if os.path.exists(INSTRUMENT_CACHE_FILE):
        age_hours = (time_module.time() - os.path.getmtime(INSTRUMENT_CACHE_FILE)) / 3600
        if age_hours < 24:
            with open(INSTRUMENT_CACHE_FILE, 'r') as f:
                return json.load(f)
    
    print("Downloading Upstox NSE instrument master...")
    url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz'
    r = requests.get(url, timeout=60)
    instruments = json.loads(gzip.decompress(r.content))
    
    eq_map = {}
    for i in instruments:
        if i.get('instrument_type') == 'EQ' and i.get('segment') == 'NSE_EQ':
            sym = i['trading_symbol']
            eq_map[sym] = i['instrument_key']
    
    with open(INSTRUMENT_CACHE_FILE, 'w') as f:
        json.dump(eq_map, f)
    
    print(f"  ✅ Cached {len(eq_map)} NSE EQ instrument keys")
    return eq_map

# ============================================================
# DATA FETCHING WITH LOCAL CSV CACHE
# ============================================================
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

def fetch_upstox_data(symbol: str, instrument_key: str) -> pd.DataFrame:
    """Fetch daily candles, cache locally as CSV."""
    cache_file = os.path.join(CACHE_DIR, f"{symbol}_{FROM_DATE}_{TO_DATE}.csv")
    
    # Check cache first
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, parse_dates=['date'], index_col='date')
        if len(df) > 50:
            return df
    
    # Fetch from API
    encoded_key = instrument_key.replace('|', '%7C')
    url = f"https://api.upstox.com/v2/historical-candle/{encoded_key}/day/{TO_DATE}/{FROM_DATE}"
    
    data = api_get(url)
    if not data or 'data' not in data or 'candles' not in data['data']:
        return pd.DataFrame()
    
    candles = data['data']['candles']
    if not candles:
        return pd.DataFrame()
    
    rows = []
    for c in candles:
        rows.append({
            'date': pd.Timestamp(c[0]),
            'open': float(c[1]), 'high': float(c[2]),
            'low': float(c[3]), 'close': float(c[4]),
            'volume': int(c[5])
        })
    
    df = pd.DataFrame(rows).sort_values('date').set_index('date')
    
    # Save to cache
    df.to_csv(cache_file)
    
    return df

def fetch_nifty_upstox() -> pd.DataFrame:
    """Fetch Nifty 50 index, cache locally."""
    cache_file = os.path.join(CACHE_DIR, f"NIFTY50_{FROM_DATE}_{TO_DATE}.csv")
    
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, parse_dates=['date'], index_col='date')
        if len(df) > 50:
            df['nifty_return_63d'] = df['close'].pct_change(periods=63)
            return df
    
    instrument_key = "NSE_INDEX%7CNifty%2050"
    url = f"https://api.upstox.com/v2/historical-candle/{instrument_key}/day/{TO_DATE}/{FROM_DATE}"
    data = api_get(url)
    
    if not data or 'data' not in data:
        return pd.DataFrame()
    
    rows = []
    for c in data['data']['candles']:
        rows.append({'date': pd.Timestamp(c[0]), 'close': float(c[4])})
    
    df = pd.DataFrame(rows).sort_values('date').set_index('date')
    df.to_csv(cache_file)
    df['nifty_return_63d'] = df['close'].pct_change(periods=63)
    return df

# ============================================================
# TRADE RECORDING
# ============================================================
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

# ============================================================
# MAIN BACKTEST ENGINE
# ============================================================
def run_backtest():
    all_trades = []
    
    # Step 1: Resolve instrument keys
    instrument_map = load_instrument_map()
    
    # Step 2: Fetch Nifty 50 baseline
    print("\nFetching Nifty 50 index...")
    nifty_df = fetch_nifty_upstox()
    if nifty_df.empty:
        print("Cannot proceed without Nifty data!")
        return
    print(f"  ✅ Nifty: {len(nifty_df)} candles")
    
    # Step 3: Process each stock
    stocks_processed = 0
    stocks_skipped = 0
    
    for symbol in sorted(ALL_SYMBOLS):
        if symbol not in instrument_map:
            stocks_skipped += 1
            continue
        
        instrument_key = instrument_map[symbol]
        
        print(f"  [{stocks_processed+1}/{len(ALL_SYMBOLS)}] {symbol}...", end=" ", flush=True)
        df = fetch_upstox_data(symbol, instrument_key)
        
        if len(df) < 100:
            print(f"skipped ({len(df)} candles)")
            stocks_skipped += 1
            continue
        
        # Add indicators
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['stock_return_63d'] = df['close'].pct_change(periods=63)
        
        stocks_processed += 1
        
        in_trade = False
        entry_price = 0.0
        entry_time = None
        target = 0.0
        days_in_trade = 0
        current_time_stop = HORIZON_DAYS
        
        for i in range(63, len(df) - 1):
            curr_date = df.index[i]
            next_date = df.index[i+1]
            curr_row = df.iloc[i]
            next_row = df.iloc[i+1]
            
            if in_trade:
                days_in_trade += 1
                
                # NO STOP LOSS
                
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
                            mode='balanced', timeframe='short', horizon='1month'
                        )
                        if "BUY" in analysis['recommendation'] or "HOLD" in analysis['recommendation']:
                            current_time_stop += 30
                            continue
                    except Exception:
                        pass
                    
                    exit_p = next_row['close'] * (1 - SLIPPAGE_PCT)
                    trade = record_trade(symbol, entry_time, next_date, entry_price, exit_p,
                                        f"Time Stop ({current_time_stop}d)")
                    if trade: all_trades.append(trade)
                    in_trade = False
                    continue
            
            if not in_trade:
                df_slice = df.iloc[: i + 1].copy()
                try:
                    analysis = analyze_stock(
                        symbol=f"{symbol}.NS",
                        df=df_slice.drop(columns=['ema_21', 'stock_return_63d'], errors='ignore'),
                        mode='balanced', timeframe='medium', horizon='3months'
                    )
                    rec = analysis['recommendation']
                    conf = analysis['confidence']
                    
                    if ("STRONG BUY" in rec or "BUY" == rec) and ("AVOID" not in rec and "WARNING" not in rec) and conf >= 70:
                        
                        # RS OVERLAY
                        has_rs = False
                        if not pd.isna(curr_row['stock_return_63d']) and not nifty_df.empty:
                            try:
                                nifty_idx = nifty_df.index.get_indexer([curr_date], method='pad')[0]
                                if nifty_idx != -1:
                                    nifty_ret = nifty_df.iloc[nifty_idx]['nifty_return_63d']
                                    if not pd.isna(nifty_ret) and curr_row['stock_return_63d'] > nifty_ret:
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
        
        # Close any open trade
        if in_trade:
            last_date = df.index[-1]
            exit_p = df['close'].iloc[-1] * (1 - SLIPPAGE_PCT)
            trade = record_trade(symbol, entry_time, last_date, entry_price, exit_p, "End of Backtest")
            if trade: all_trades.append(trade)
        
        print(f"done ({len([t for t in all_trades if t['symbol']==symbol])} trades)")
    
    # Results
    print(f"\n📊 Processed {stocks_processed} stocks, skipped {stocks_skipped}")
    
    if not all_trades:
        print("\nNo trades generated.")
        return
    
    trades_df = pd.DataFrame(all_trades)
    wins = trades_df[trades_df['win'] == 1]
    losses = trades_df[trades_df['win'] == 0]
    
    print("\n" + "="*60)
    print("🎯 UPSTOX REAL DATA — MIDCAP 150 + NIFTY 50 — RS + NO SL")
    print("="*60)
    print(f"Data Source: Upstox V2 API (cached to data/upstox_cache/)")
    print(f"Period: {FROM_DATE} to {TO_DATE}")
    print(f"Universe: {stocks_processed} stocks successfully processed")
    print(f"Capital Per Trade: ₹{CAPITAL_PER_TRADE:,.2f}")
    print("-" * 60)
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate:     {(len(wins)/len(trades_df))*100:.2f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Avg Days Held:{trades_df['days_held'].mean():.1f} days")
    print("-" * 60)
    print(f"Gross P&L:    ₹{trades_df['gross_pnl'].sum():,.2f}")
    print(f"Total Charges:₹{trades_df['charges'].sum():,.2f}")
    print(f"NET P&L:      ₹{trades_df['net_pnl'].sum():,.2f}")
    print("-" * 60)
    if len(wins) > 0:
        print(f"Avg Win:      ₹{wins['net_pnl'].mean():,.2f}")
    if len(losses) > 0:
        print(f"Avg Loss:     ₹{losses['net_pnl'].mean():,.2f}")
    print(f"Max Win:      ₹{trades_df['net_pnl'].max():,.2f}")
    print(f"Max Loss:     ₹{trades_df['net_pnl'].min():,.2f}")
    print("="*60)
    
    trades_df.to_csv('backtest_upstox_midcap_rs_no_sl_trades.csv', index=False)
    print(f"\nDetailed trades saved to 'backtest_upstox_midcap_rs_no_sl_trades.csv'")
    print(f"Cached data saved to: {CACHE_DIR}/")
    print(f"\nBreakdown by Reason:")
    print(trades_df['reason'].value_counts())
    
    print(f"\nTop 10 Trades by Net P&L:")
    print(trades_df.nlargest(10, 'net_pnl')[['symbol', 'entry_time', 'exit_time', 'net_pnl', 'reason']].to_string())

if __name__ == "__main__":
    run_backtest()
