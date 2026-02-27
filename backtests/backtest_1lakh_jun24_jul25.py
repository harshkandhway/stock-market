#!/usr/bin/env python3
"""
₹1 LAKH PORTFOLIO — No RS — June 2024 to July 2025
=====================================================
Extended period: 13 months. No RS filter. ₹20k × 5 slots.
Downloads Upstox data if not cached, otherwise uses cache.
"""
import sys, os, json, gzip, time as time_module
import pandas as pd
import numpy as np
import requests

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from src.cli.stock_analyzer_pro import analyze_stock
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/Trades/.env'))

ACCESS_TOKEN = os.getenv('UPSTOX_LIVE_TOKEN', '')
HEADERS = {'Accept': 'application/json', 'Authorization': f'Bearer {ACCESS_TOKEN}'}

STARTING_CAPITAL = 100000
PER_POSITION = 20000
HORIZON_DAYS = 63
FROM_DATE = '2024-06-01'
TO_DATE = '2025-07-01'
CACHE_DIR = os.path.join(project_root, 'data', 'upstox_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

SLIPPAGE_PCT = 0.001
STT_PCT_DELIVERY = 0.001
EXCH_TXN_CHARGE = 0.0000325
GST_PCT = 0.18
SEBI_TURNOVER = 0.000001
STAMP_DUTY_BUY = 0.00015

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
ALL_SYMBOLS = sorted(set(NIFTY_50 + MIDCAP_150))

# ============================================================
# INSTRUMENT RESOLUTION + DATA DOWNLOAD
# ============================================================
INSTRUMENT_CACHE = os.path.join(CACHE_DIR, 'nse_instruments.json')

def load_instrument_map():
    if os.path.exists(INSTRUMENT_CACHE):
        with open(INSTRUMENT_CACHE) as f:
            return json.load(f)
    url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz'
    r = requests.get(url, timeout=60)
    instruments = json.loads(gzip.decompress(r.content))
    eq_map = {i['trading_symbol']: i['instrument_key'] for i in instruments
              if i.get('instrument_type') == 'EQ' and i.get('segment') == 'NSE_EQ'}
    with open(INSTRUMENT_CACHE, 'w') as f:
        json.dump(eq_map, f)
    return eq_map

def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200: return r.json()
            elif r.status_code == 429: time_module.sleep(3)
            elif r.status_code == 401: return None
            else:
                if attempt == retries - 1: return None
        except:
            if attempt == retries - 1: return None
        time_module.sleep(0.3)
    return None

def fetch_data(symbol, instrument_key):
    cache_file = os.path.join(CACHE_DIR, f"{symbol}_{FROM_DATE}_{TO_DATE}.csv")
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, parse_dates=['date'], index_col='date')
        if len(df) > 50: return df
    
    encoded_key = instrument_key.replace('|', '%7C')
    url = f"https://api.upstox.com/v2/historical-candle/{encoded_key}/day/{TO_DATE}/{FROM_DATE}"
    data = api_get(url)
    if not data or 'data' not in data or 'candles' not in data['data']:
        return pd.DataFrame()
    
    rows = [{'date': pd.Timestamp(c[0]), 'open': float(c[1]), 'high': float(c[2]),
             'low': float(c[3]), 'close': float(c[4]), 'volume': int(c[5])}
            for c in data['data']['candles']]
    df = pd.DataFrame(rows).sort_values('date').set_index('date')
    df.to_csv(cache_file)
    return df

def fetch_nifty():
    cache_file = os.path.join(CACHE_DIR, f"NIFTY50_{FROM_DATE}_{TO_DATE}.csv")
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, parse_dates=['date'], index_col='date')
        if len(df) > 50:
            df['nifty_return_63d'] = df['close'].pct_change(periods=63)
            return df
    
    url = f"https://api.upstox.com/v2/historical-candle/NSE_INDEX%7CNifty%2050/day/{TO_DATE}/{FROM_DATE}"
    data = api_get(url)
    if not data or 'data' not in data: return pd.DataFrame()
    rows = [{'date': pd.Timestamp(c[0]), 'close': float(c[4])} for c in data['data']['candles']]
    df = pd.DataFrame(rows).sort_values('date').set_index('date')
    df.to_csv(cache_file)
    df['nifty_return_63d'] = df['close'].pct_change(periods=63)
    return df

def calc_costs(entry_price, exit_price, qty):
    turnover = (entry_price + exit_price) * qty
    stt = (entry_price * qty + exit_price * qty) * STT_PCT_DELIVERY
    exch_txn = turnover * EXCH_TXN_CHARGE
    gst = exch_txn * GST_PCT
    return stt + exch_txn + gst + turnover * SEBI_TURNOVER + (entry_price * qty) * STAMP_DUTY_BUY

# ============================================================
# MAIN
# ============================================================
def run_backtest():
    instrument_map = load_instrument_map()
    
    print("=" * 65)
    print(f"Loading data: {FROM_DATE} → {TO_DATE} (13 months)")
    print("=" * 65)
    
    nifty_df = fetch_nifty()
    print(f"  Nifty 50: {len(nifty_df)} candles")
    
    stock_data = {}
    for sym in ALL_SYMBOLS:
        if sym not in instrument_map: continue
        df = fetch_data(sym, instrument_map[sym])
        if len(df) < 100: continue
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['stock_return_63d'] = df['close'].pct_change(periods=63)
        stock_data[sym] = df
    print(f"  Loaded {len(stock_data)} stocks\n")
    
    # ========== PASS 1: Find ALL signals (NO RS filter) ==========
    print("=" * 65)
    print("PASS 1: Scanning for signals (NO RS filter, conf ≥ 70%)...")
    print("=" * 65)
    
    all_signals = []
    for idx, (symbol, df) in enumerate(sorted(stock_data.items())):
        print(f"  [{idx+1}/{len(stock_data)}] {symbol}...", end=" ", flush=True)
        count = 0
        for i in range(63, len(df) - 1):
            curr_date = df.index[i]
            next_date = df.index[i + 1]
            next_row = df.iloc[i + 1]
            
            df_slice = df.iloc[:i + 1].copy()
            try:
                analysis = analyze_stock(
                    symbol=f"{symbol}.NS",
                    df=df_slice.drop(columns=['ema_21', 'stock_return_63d'], errors='ignore'),
                    mode='balanced', timeframe='medium', horizon='3months'
                )
                rec = analysis['recommendation']
                conf = analysis['confidence']
                if ("STRONG BUY" in rec or "BUY" == rec) and ("AVOID" not in rec and "WARNING" not in rec) and conf >= 70:
                    all_signals.append({
                        'signal_date': curr_date, 'entry_date': next_date,
                        'symbol': symbol,
                        'entry_price': next_row['open'] * (1 + SLIPPAGE_PCT),
                        'target': analysis['target'],
                        'confidence': conf, 'composite': conf,
                    })
                    count += 1
            except: pass
        print(f"{count}")
    
    if not all_signals:
        print("\nNo signals!"); return
    
    sdf = pd.DataFrame(all_signals).sort_values('entry_date')
    print(f"\n  📊 Total signals: {len(sdf)}")
    print(f"  📅 Range: {sdf.iloc[0]['entry_date'].date()} → {sdf.iloc[-1]['entry_date'].date()}")
    
    # Show signal distribution by month
    sdf['month'] = sdf['entry_date'].dt.to_period('M')
    print(f"\n  📅 Signals by month:")
    for month, grp in sdf.groupby('month'):
        print(f"    {month}: {len(grp)} signals")
    
    # ========== PASS 2: Portfolio simulation ==========
    print("\n" + "=" * 65)
    print(f"PASS 2: ₹{STARTING_CAPITAL:,.0f} portfolio | ₹{PER_POSITION:,.0f}/position | {STARTING_CAPITAL//PER_POSITION} slots")
    print("=" * 65)
    
    cash = float(STARTING_CAPITAL)
    open_positions = {}
    closed_trades = []
    
    all_dates = set()
    for df in stock_data.values():
        all_dates.update(df.index.tolist())
    trading_dates = sorted(all_dates)[63:]
    
    signals_by_date = {}
    for _, sig in sdf.iterrows():
        d = sig['entry_date']
        if d not in signals_by_date: signals_by_date[d] = []
        signals_by_date[d].append(sig)
    
    for date_idx, curr_date in enumerate(trading_dates):
        next_date = trading_dates[date_idx + 1] if date_idx + 1 < len(trading_dates) else None
        
        to_close = []
        for sym, pos in open_positions.items():
            pos['days'] += 1
            df = stock_data[sym]
            if next_date is None or next_date not in df.index: continue
            next_row = df.loc[next_date]
            
            if next_row['high'] >= pos['target']:
                exit_p = pos['target'] * (1 - SLIPPAGE_PCT)
                charges = calc_costs(pos['entry_price'], exit_p, pos['qty'])
                gross = (exit_p - pos['entry_price']) * pos['qty']
                net = gross - charges
                cash += (pos['entry_price'] * pos['qty']) + net
                closed_trades.append({
                    'symbol': sym, 'entry_time': pos['entry_time'],
                    'exit_time': next_date, 'days_held': pos['days'],
                    'entry_price': pos['entry_price'], 'exit_price': exit_p,
                    'qty': pos['qty'], 'invested': pos['entry_price'] * pos['qty'],
                    'reason': 'Target Hit', 'gross_pnl': gross,
                    'charges': charges, 'net_pnl': net, 'win': 1 if net > 0 else 0
                })
                to_close.append(sym)
                print(f"  ✅ {sym:12s} TARGET HIT  {pos['days']:3d}d | ₹{net:+,.0f} | Cash: ₹{cash:,.0f}")
                continue
            
            if pos['days'] >= pos['time_stop']:
                extend = False
                if curr_date in df.index:
                    df_slice = df.loc[:curr_date].copy()
                    try:
                        a = analyze_stock(f"{sym}.NS",
                            df_slice.drop(columns=['ema_21', 'stock_return_63d'], errors='ignore'),
                            'balanced', 'short', '1month')
                        if "BUY" in a['recommendation'] or "HOLD" in a['recommendation']:
                            pos['time_stop'] += 30; extend = True
                    except: pass
                if not extend:
                    exit_p = next_row['close'] * (1 - SLIPPAGE_PCT)
                    charges = calc_costs(pos['entry_price'], exit_p, pos['qty'])
                    gross = (exit_p - pos['entry_price']) * pos['qty']
                    net = gross - charges
                    cash += (pos['entry_price'] * pos['qty']) + net
                    closed_trades.append({
                        'symbol': sym, 'entry_time': pos['entry_time'],
                        'exit_time': next_date, 'days_held': pos['days'],
                        'entry_price': pos['entry_price'], 'exit_price': exit_p,
                        'qty': pos['qty'], 'invested': pos['entry_price'] * pos['qty'],
                        'reason': f"Time Stop ({pos['time_stop']}d)",
                        'gross_pnl': gross, 'charges': charges, 'net_pnl': net,
                        'win': 1 if net > 0 else 0
                    })
                    to_close.append(sym)
                    print(f"  ⏰ {sym:12s} TIME STOP   {pos['days']:3d}d | ₹{net:+,.0f} | Cash: ₹{cash:,.0f}")
                    continue
        
        for sym in to_close:
            del open_positions[sym]
        
        if next_date and next_date in signals_by_date:
            day_signals = sorted(signals_by_date[next_date], key=lambda x: x['composite'], reverse=True)
            for sig in day_signals:
                sym = sig['symbol']
                if sym in open_positions: continue
                if cash < PER_POSITION: break
                entry_p = sig['entry_price']
                qty = int(PER_POSITION / entry_p)
                if qty == 0: continue
                invested = entry_p * qty
                cash -= invested
                open_positions[sym] = {
                    'entry_price': entry_p, 'entry_time': next_date,
                    'target': sig['target'], 'qty': qty,
                    'days': 0, 'time_stop': HORIZON_DAYS
                }
                print(f"  🟢 BUY {sym:12s} ₹{entry_p:>8.2f} x {qty:3d} = ₹{invested:>7,.0f} | Cash: ₹{cash:,.0f}")
    
    # Close remaining
    print(f"\n  📋 Closing {len(open_positions)} open positions...")
    for sym, pos in open_positions.items():
        df = stock_data[sym]
        exit_p = df['close'].iloc[-1] * (1 - SLIPPAGE_PCT)
        charges = calc_costs(pos['entry_price'], exit_p, pos['qty'])
        gross = (exit_p - pos['entry_price']) * pos['qty']
        net = gross - charges
        cash += (pos['entry_price'] * pos['qty']) + net
        closed_trades.append({
            'symbol': sym, 'entry_time': pos['entry_time'],
            'exit_time': df.index[-1], 'days_held': pos['days'],
            'entry_price': pos['entry_price'], 'exit_price': exit_p,
            'qty': pos['qty'], 'invested': pos['entry_price'] * pos['qty'],
            'reason': 'End of Backtest', 'gross_pnl': gross,
            'charges': charges, 'net_pnl': net, 'win': 1 if net > 0 else 0
        })
        m = "✅" if net > 0 else "❌"
        print(f"  {m} {sym:12s} END {pos['days']:3d}d | ₹{net:+,.0f}")
    
    # Results
    if not closed_trades:
        print("\nNo trades."); return
    
    tdf = pd.DataFrame(closed_trades)
    wins = tdf[tdf['win'] == 1]
    losses = tdf[tdf['win'] == 0]
    total_pnl = tdf['net_pnl'].sum()
    final = STARTING_CAPITAL + total_pnl
    
    print("\n" + "=" * 65)
    print(f"💰 ₹1L PORTFOLIO — NO RS — {FROM_DATE} to {TO_DATE}")
    print("=" * 65)
    print(f"Starting Capital:   ₹{STARTING_CAPITAL:>10,.0f}")
    print(f"Final Capital:      ₹{final:>10,.0f}")
    print(f"TOTAL RETURN:       ₹{total_pnl:>+10,.0f} ({(total_pnl/STARTING_CAPITAL)*100:+.2f}%)")
    print(f"Position Size:      ₹{PER_POSITION:,.0f} ({STARTING_CAPITAL//PER_POSITION} slots)")
    print("-" * 65)
    print(f"Total Trades:       {len(tdf)}")
    print(f"Win Rate:           {(len(wins)/len(tdf))*100:.1f}% ({len(wins)}W / {len(losses)}L)")
    print("-" * 65)
    print(f"Gross P&L:          ₹{tdf['gross_pnl'].sum():>+10,.0f}")
    print(f"Total Charges:      ₹{tdf['charges'].sum():>10,.0f}")
    print(f"NET P&L:            ₹{tdf['net_pnl'].sum():>+10,.0f}")
    print("-" * 65)
    if len(wins): print(f"Avg Win:            ₹{wins['net_pnl'].mean():>+10,.0f}")
    if len(losses): print(f"Avg Loss:           ₹{losses['net_pnl'].mean():>+10,.0f}")
    print(f"Max Win:            ₹{tdf['net_pnl'].max():>+10,.0f}")
    print(f"Max Loss:           ₹{tdf['net_pnl'].min():>+10,.0f}")
    print("=" * 65)
    
    print("\n📋 Trade Journal:")
    print("-" * 120)
    for _, t in tdf.sort_values('entry_time').iterrows():
        m = "✅" if t['win'] else "❌"
        print(f"  {m} {t['symbol']:12s} | {str(t['entry_time'])[:10]} → {str(t['exit_time'])[:10]} | {t['days_held']:3d}d | ₹{t['invested']:>7,.0f} | ₹{t['net_pnl']:>+7,.0f} | {t['reason']}")
    
    print(f"\n📊 By Exit Reason:")
    for r, g in tdf.groupby('reason'):
        print(f"  {r:20s}: {len(g)} trades | ₹{g['net_pnl'].sum():+,.0f}")
    
    tdf.to_csv('backtest_1lakh_jun24_jul25_trades.csv', index=False)
    print(f"\nSaved to 'backtest_1lakh_jun24_jul25_trades.csv'")

if __name__ == "__main__":
    run_backtest()
