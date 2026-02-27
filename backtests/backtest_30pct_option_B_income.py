#!/usr/bin/env python3
"""
OPTION B: THE OPTIONS INCOME PROXY (30% Yield Pursuit)
======================================================
Simulates Covered Call selling.
Goal: Generate yield even if the stock goes nowhere.
Rules:
- Entry: Standard BUY / STRONG BUY.
- On entry: Cash balance increases by 2% of position size immediately (Premium collected).
- Exit Target: Stock climbs +3.0%. Total profit = 5%.
- Exit Stop: 63-day Time Stop.
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

STARTING_CAPITAL = 200000
HORIZON_DAYS = 63
TARGET_PCT = 0.03 # Max stock profit allowed
PREMIUM_PCT = 0.02 # Sold option premium

FROM_DATE = '2024-06-01'
TO_DATE = '2025-07-01'
TARGET_UNIVERSE_SIZE = 250
CACHE_DIR = os.path.join(project_root, 'data', 'upstox_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

SLIPPAGE_PCT = 0.001
STT_PCT_DELIVERY = 0.001
EXCH_TXN_CHARGE = 0.0000325
GST_PCT = 0.18
SEBI_TURNOVER = 0.000001
STAMP_DUTY_BUY = 0.00015

def position_size(confidence, capital):
    if confidence >= 80: return 40000
    elif confidence >= 70: return 25000
    else: return 15000

PRIORITY_STOCKS = [
    # Nifty 50
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'ITC', 'SBIN',
    'BAJFINANCE', 'BHARTIARTL', 'KOTAKBANK', 'AXISBANK', 'ASIANPAINT',
    'MARUTI', 'HCLTECH', 'SUNPHARMA', 'TITAN', 'M&M', 'TRENT', 'BEL',
    'HAL', 'INDIGO', 'TVSMOTOR', 'WIPRO', 'ADANIPORTS', 'NTPC',
    'POWERGRID', 'ULTRACEMCO', 'ONGC', 'JSWSTEEL', 'TATAMOTORS',
    'BAJAJ-AUTO', 'COALINDIA', 'LT', 'HINDALCO', 'DRREDDY',
    'NESTLEIND', 'BAJAJFINSV', 'CIPLA', 'EICHERMOT', 'DIVISLAB',
    'GRASIM', 'APOLLOHOSP', 'HEROMOTOCO', 'TECHM', 'BRITANNIA',
    'TATASTEEL', 'SHRIRAMFIN', 'TATACONSUM', 'BPCL', 'SBILIFE',
    # Midcap 150
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
]

INSTRUMENT_CACHE = os.path.join(CACHE_DIR, 'nse_instruments.json')

def load_instrument_map():
    if os.path.exists(INSTRUMENT_CACHE):
        with open(INSTRUMENT_CACHE) as f: return json.load(f)
    url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz'
    r = requests.get(url, timeout=60)
    instruments = json.loads(gzip.decompress(r.content))
    eq_map = {i['trading_symbol']: i['instrument_key'] for i in instruments
              if i.get('instrument_type') == 'EQ' and i.get('segment') == 'NSE_EQ'}
    with open(INSTRUMENT_CACHE, 'w') as f: json.dump(eq_map, f)
    return eq_map

def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200: return r.json()
            elif r.status_code == 429: time_module.sleep(3)
            else:
                if attempt == retries - 1: return None
        except:
            if attempt == retries - 1: return None
        time_module.sleep(0.3)
    return None

def fetch_data(symbol, instrument_key):
    f = os.path.join(CACHE_DIR, f"{symbol}_{FROM_DATE}_{TO_DATE}.csv")
    if os.path.exists(f):
        df = pd.read_csv(f, parse_dates=['date'], index_col='date')
        if len(df) > 50: return df
    encoded = instrument_key.replace('|', '%7C')
    url = f"https://api.upstox.com/v2/historical-candle/{encoded}/day/{TO_DATE}/{FROM_DATE}"
    data = api_get(url)
    if not data or 'data' not in data or 'candles' not in data['data']: return pd.DataFrame()
    rows = [{'date': pd.Timestamp(c[0]), 'open': float(c[1]), 'high': float(c[2]),
             'low': float(c[3]), 'close': float(c[4]), 'volume': int(c[5])}
            for c in data['data']['candles']]
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values('date').set_index('date')
    df.to_csv(f)
    return df

def calc_costs(ep, xp, qty):
    t = (ep + xp) * qty
    return (ep*qty+xp*qty)*STT_PCT_DELIVERY + t*EXCH_TXN_CHARGE*(1+GST_PCT) + t*SEBI_TURNOVER + ep*qty*STAMP_DUTY_BUY

def passes_momentum(df, i):
    # Same filter to only buy decent stocks.
    if i < 21: return False
    row = df.iloc[i]
    if row['close'] <= row.get('ema_21', 0): return False
    if row['volume'] < df['volume'].iloc[max(0,i-20):i].mean(): return False
    return True

def run_backtest():
    instrument_map = load_instrument_map()
    universe = []
    seen = set()
    for sym in PRIORITY_STOCKS:
        s = sym.upper()
        if s not in seen and s in instrument_map:
            universe.append(s)
            seen.add(s)
            
    if len(universe) < TARGET_UNIVERSE_SIZE:
        for sym in sorted(instrument_map.keys()):
            if sym not in seen and len(universe) < TARGET_UNIVERSE_SIZE:
                universe.append(sym)
                seen.add(sym)
                
    print("=" * 65)
    print(f"OPTION B: INCOME PROXY ({len(universe)} STOCKS)")
    print("=" * 65)
    
    stock_data = {}
    for idx, sym in enumerate(universe):
        df = fetch_data(sym, instrument_map[sym])
        if df is None or len(df) < 100: continue
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        stock_data[sym] = df
        
    all_signals = []
    for idx, (symbol, df) in enumerate(sorted(stock_data.items())):
        for i in range(63, len(df) - 1):
            curr_date = df.index[i]
            next_date = df.index[i + 1]
            next_row = df.iloc[i + 1]
            if not passes_momentum(df, i): continue
            
            df_slice = df.iloc[:i + 1].copy()
            try:
                analysis = analyze_stock(f"{symbol}.NS", df_slice.drop(columns=['ema_21'], errors='ignore'), 'balanced', 'medium', '3months')
                rec = analysis['recommendation']
                conf = analysis['confidence']
                if ("STRONG BUY" in rec or "BUY" == rec) and ("AVOID" not in rec and "WARNING" not in rec) and conf >= 60:
                    ep = next_row['open'] * (1 + SLIPPAGE_PCT)
                    all_signals.append({
                        'signal_date': curr_date, 'entry_date': next_date,
                        'symbol': symbol, 'entry_price': ep,
                        'target': ep * (1 + TARGET_PCT),
                        'confidence': conf, 'composite': conf,
                    })
            except: pass
            
    if not all_signals: return
    sdf = pd.DataFrame(all_signals).sort_values('entry_date')
    
    cash = float(STARTING_CAPITAL)
    open_positions = {}
    closed_trades = []
    
    all_dates = set()
    for df in stock_data.values(): all_dates.update(df.index.tolist())
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
            nr = df.loc[next_date]
            
            # Check target (assigned)
            if nr['high'] >= pos['target']:
                xp = pos['target'] * (1 - SLIPPAGE_PCT)
                ch = calc_costs(pos['entry_price'], xp, pos['qty'])
                g = (xp - pos['entry_price']) * pos['qty']
                # Add stock gain + originally received premium to get net pnl
                n = g - ch + pos['premium_received']
                cash += (pos['entry_price'] * pos['qty']) + g - ch
                closed_trades.append({'symbol': sym, 'entry_time': pos['entry_time'], 'exit_time': next_date, 'days_held': pos['days'], 'entry_price': pos['entry_price'], 'exit_price': xp, 'qty': pos['qty'], 'invested': pos['entry_price']*pos['qty'], 'reason': 'Target Hit (Called Away)', 'net_pnl': n, 'win': 1})
                to_close.append(sym)
                continue
                
            # Check time stop
            if pos['days'] >= HORIZON_DAYS:
                xp = nr['close'] * (1 - SLIPPAGE_PCT)
                ch = calc_costs(pos['entry_price'], xp, pos['qty'])
                g = (xp - pos['entry_price']) * pos['qty']
                n = g - ch + pos['premium_received']
                cash += (pos['entry_price'] * pos['qty']) + g - ch
                closed_trades.append({'symbol': sym, 'entry_time': pos['entry_time'], 'exit_time': next_date, 'days_held': pos['days'], 'entry_price': pos['entry_price'], 'exit_price': xp, 'qty': pos['qty'], 'invested': pos['entry_price']*pos['qty'], 'reason': f"Time Stop ({HORIZON_DAYS}d)", 'net_pnl': n, 'win': 1 if n > 0 else 0})
                to_close.append(sym)
                
        for sym in to_close: del open_positions[sym]
        
        if next_date and next_date in signals_by_date:
            day_sigs = sorted(signals_by_date[next_date], key=lambda x: x['composite'], reverse=True)
            for sig in day_sigs:
                sym = sig['symbol']
                if sym in open_positions: continue
                alloc = min(position_size(sig['confidence'], STARTING_CAPITAL), cash)
                if alloc < 3000: continue
                ep = sig['entry_price']; qty = int(alloc / ep)
                if qty == 0: continue
                
                inv = ep * qty
                prem = inv * PREMIUM_PCT
                cash = cash - inv + prem # Collect premium into cash immediately
                
                open_positions[sym] = {
                    'entry_price': ep, 'entry_time': next_date,
                    'target': sig['target'], 'premium_received': prem,
                    'qty': qty, 'days': 0
                }
                
    for sym, pos in open_positions.items():
        df = stock_data[sym]
        xp = df['close'].iloc[-1] * (1 - SLIPPAGE_PCT)
        ch = calc_costs(pos['entry_price'], xp, pos['qty'])
        g = (xp - pos['entry_price']) * pos['qty']
        n = g - ch + pos['premium_received']
        cash += (pos['entry_price'] * pos['qty']) + g - ch
        closed_trades.append({'symbol': sym, 'entry_time': pos['entry_time'], 'exit_time': df.index[-1], 'days_held': pos['days'], 'entry_price': pos['entry_price'], 'exit_price': xp, 'qty': pos['qty'], 'invested': pos['entry_price']*pos['qty'], 'reason': "End of Backtest", 'net_pnl': n, 'win': 1 if n > 0 else 0})
        
    tdf = pd.DataFrame(closed_trades)
    pnl = tdf['net_pnl'].sum()
    print(f"\n💰 B: INCOME PROXY (COVERED CALLS) | RETURN: ₹{pnl:+,.0f} | TRADES: {len(tdf)} | WIN RATE: {len(tdf[tdf['win']==1])/len(tdf)*100:.1f}%")
    tdf.to_csv('option_b_trades.csv', index=False)

if __name__ == "__main__": run_backtest()
