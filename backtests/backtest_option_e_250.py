#!/usr/bin/env python3
"""
OPTION E v2: 250-STOCK UNIVERSE
================================
Same hybrid strategy but with ~250 stocks instead of 143.
Dynamically picks top NSE equities from instrument master.

Strategy: Conf≥60% + Momentum + Kelly + Trailing Stop
Capital: ₹1,00,000 | Period: June 2024 → July 2025
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
TRAIL_PCT = 0.05
FROM_DATE = '2024-06-01'
TO_DATE = '2025-07-01'
TARGET_UNIVERSE_SIZE = 500
CACHE_DIR = os.path.join(project_root, 'data', 'upstox_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

SLIPPAGE_PCT = 0.001
STT_PCT_DELIVERY = 0.001
EXCH_TXN_CHARGE = 0.0000325
GST_PCT = 0.18
SEBI_TURNOVER = 0.000001
STAMP_DUTY_BUY = 0.00015

def position_size(confidence, capital):
    """Sweet spot: balance between capturing signals and amplifying winners."""
    if confidence >= 80: return 40000   # High conviction = ₹40k
    elif confidence >= 70: return 25000  # Good signal = ₹25k
    else: return 15000                   # Decent signal = ₹15k

# Known Nifty 50 + Midcap 150 + Next 50 + popular Smallcap stocks
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
    'TATAELXSI', 'LALPATHLAB', 'SAIL', 'BHARATFORG', 'CHOLAFIN',
    'IRCTC', 'PETRONET', 'IPCALAB', 'DEEPAKNTR', 'BIOCON',
    'BATAINDIA', 'GMRINFRA', 'HDFCAMC', 'DEVYANI', 'KALYANKJIL',
    'LLOYDSME', 'IIFL', 'SUNTV', 'JKCEMENT', 'RAMCOCEM',
    'ZYDUSLIFE', 'BALKRISIND', 'MANAPPURAM', 'RECLTD', 'PFC',
    'DLF', 'AMBUJACEM', 'BHEL', 'JINDALSTEL', 'PNB',
    'VEDL', 'GAIL', 'TORNTPHARM', 'PIDILITIND', 'BANKBARODA',
    'HAVELLS', 'LICHSGFIN', 'CANFINHOME', 'CENTRALBK', 'IRFC',
    'NHPC', 'SJVN', 'HUDCO', 'KEI', 'TIINDIA', 'SOLARINDS', 'JSWENERGY',
    # Nifty Next 50 additions
    'SIEMENS', 'ABB', 'GODREJCP', 'DABUR', 'PIIND', 'BERGEPAINT',
    'COLPAL', 'BOSCHLTD', 'TATAPOWER', 'ZOMATO', 'PAYTM',
    'MOTHERSON', 'BANDHANBNK', 'IDEA', 'ZEEL', 'NYKAA',
    'DMART', 'SRF', 'LUPIN', 'IOC', 'HINDPETRO',
    'UPL', 'CANBK', 'YESBANK', 'UNIONBANK', 'INDIANB',
    # Popular Smallcap/Thematic additions
    'LICI', 'ANGELONE', 'CAMPUS', 'HAPPSTMNDS', 'TANLA',
    'RATNAMANI', 'GRINDWELL', 'KAJARIACER', 'FINEORG', 'CEATLTD',
    'RAYMOND', 'NAVINFLUOR', 'GRAPHITE', 'TATACOMM', 'TATAPOWER',
    'STARHEALTH', 'POLICYBZR', 'PVRINOX', 'IEX', 'MCX',
    'BSE', 'CDSL', 'IREDA', 'SUZLON', 'NHPC',
    'OFSS', 'POLYCAB', 'CLEAN', 'SJVN', 'JSWINFRA',
    'CAMS', 'UTIAMC', 'WHIRLPOOL', 'SAPPHIRE', 'VBL',
    'TATATECH', 'COCHINSHIP', 'GRSE', 'MAZAGONDOCK', 'GARDENREACH',
    'FLUOROCHEM', 'AAVAS', 'EXIDEIND', 'AIAENG', 'CARBORUNIV',
    'CHAMBLFERT', 'COROMANDEL', 'EIDPARRY', 'ELGIEQUIP', 'EMCURE',
    'FINPIPE', 'GLENMARK', 'GNFC', 'GPPL', 'GSPL',
    'HATSUN', 'HINDCOPPER', 'BLUEDART', 'CENTURYTEX', 'CGPOWER',
]

# Instrument helpers
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

def fetch_nifty():
    f = os.path.join(CACHE_DIR, f"NIFTY50_{FROM_DATE}_{TO_DATE}.csv")
    if os.path.exists(f):
        df = pd.read_csv(f, parse_dates=['date'], index_col='date')
        if len(df) > 50: return df
    url = f"https://api.upstox.com/v2/historical-candle/NSE_INDEX%7CNifty%2050/day/{TO_DATE}/{FROM_DATE}"
    data = api_get(url)
    if not data or 'data' not in data: return pd.DataFrame()
    rows = [{'date': pd.Timestamp(c[0]), 'close': float(c[4])} for c in data['data']['candles']]
    df = pd.DataFrame(rows).sort_values('date').set_index('date')
    df.to_csv(f)
    return df

def calc_costs(ep, xp, qty):
    t = (ep + xp) * qty
    return (ep*qty+xp*qty)*STT_PCT_DELIVERY + t*EXCH_TXN_CHARGE*(1+GST_PCT) + t*SEBI_TURNOVER + ep*qty*STAMP_DUTY_BUY

def compute_rsi(series, period=14):
    d = series.diff()
    g = d.where(d > 0, 0).rolling(window=period).mean()
    l = (-d.where(d < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + g / l.replace(0, np.nan)))

def passes_momentum(df, i):
    if i < 21: return False
    row = df.iloc[i]
    if row['close'] <= row.get('ema_21', 0): return False
    if row['volume'] < df['volume'].iloc[max(0,i-20):i].mean(): return False
    rsi = row.get('rsi_14', 50)
    if rsi < 40 or rsi > 65: return False
    return True

def run_backtest():
    instrument_map = load_instrument_map()
    
    # Build universe: priority stocks first, then fill to 250 from instrument master
    universe = []
    seen = set()
    for sym in PRIORITY_STOCKS:
        s = sym.upper()
        if s not in seen and s in instrument_map:
            universe.append(s)
            seen.add(s)
    
    # Fill remaining slots from instrument master
    if len(universe) < TARGET_UNIVERSE_SIZE:
        for sym in sorted(instrument_map.keys()):
            if sym not in seen and len(universe) < TARGET_UNIVERSE_SIZE:
                universe.append(sym)
                seen.add(sym)
    
    print("=" * 65)
    print(f"OPTION E v2: {len(universe)}-STOCK UNIVERSE")
    print(f"Period: {FROM_DATE} → {TO_DATE}")
    print("=" * 65)
    
    # Download data
    print(f"\n📥 Loading/downloading data for {len(universe)} stocks...")
    nifty_df = fetch_nifty()
    
    stock_data = {}
    downloaded = 0
    for idx, sym in enumerate(universe):
        if (idx + 1) % 50 == 0:
            print(f"  ... {idx+1}/{len(universe)} loaded ({downloaded} downloaded from API)")
        df = fetch_data(sym, instrument_map[sym])
        if df is None or len(df) < 100: continue
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['rsi_14'] = compute_rsi(df['close'], 14)
        stock_data[sym] = df
        if not os.path.exists(os.path.join(CACHE_DIR, f"{sym}_{FROM_DATE}_{TO_DATE}.csv")):
            downloaded += 1
    
    print(f"  ✅ Loaded {len(stock_data)} stocks (of {len(universe)} attempted)")
    
    # PASS 1: Signals
    print(f"\n{'='*65}")
    print(f"PASS 1: Scanning {len(stock_data)} stocks (conf≥60% + momentum)...")
    print("=" * 65)
    
    all_signals = []
    for idx, (symbol, df) in enumerate(sorted(stock_data.items())):
        print(f"  [{idx+1}/{len(stock_data)}] {symbol}...", end=" ", flush=True)
        count = 0
        for i in range(63, len(df) - 1):
            curr_date = df.index[i]
            next_date = df.index[i + 1]
            next_row = df.iloc[i + 1]
            
            if not passes_momentum(df, i): continue
            
            df_slice = df.iloc[:i + 1].copy()
            try:
                analysis = analyze_stock(
                    symbol=f"{symbol}.NS",
                    df=df_slice.drop(columns=['ema_21', 'rsi_14'], errors='ignore'),
                    mode='balanced', timeframe='medium', horizon='3months'
                )
                rec = analysis['recommendation']
                conf = analysis['confidence']
                if ("STRONG BUY" in rec or "BUY" == rec) and ("AVOID" not in rec and "WARNING" not in rec) and conf >= 60:
                    all_signals.append({
                        'signal_date': curr_date, 'entry_date': next_date,
                        'symbol': symbol,
                        'entry_price': next_row['open'] * (1 + SLIPPAGE_PCT),
                        'target': analysis['target'],
                        'confidence': conf, 'composite': conf,
                        'is_multibagger': analysis.get('is_multibagger_setup', False)
                    })
                    count += 1
            except: pass
        print(f"{count}")
    
    if not all_signals:
        print("\nNo signals!"); return
    
    sdf = pd.DataFrame(all_signals).sort_values('entry_date')
    print(f"\n  📊 Total signals: {len(sdf)}")
    print(f"  📅 Range: {sdf.iloc[0]['entry_date'].date()} → {sdf.iloc[-1]['entry_date'].date()}")
    sdf['month'] = sdf['entry_date'].dt.to_period('M')
    print(f"\n  📅 Signals by month:")
    for month, grp in sdf.groupby('month'):
        print(f"    {month}: {len(grp)} signals")
    
    # PASS 2: Portfolio
    print(f"\n{'='*65}")
    print(f"PASS 2: ₹{STARTING_CAPITAL:,.0f} | Kelly sizing | Trailing stops")
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
            nr = df.loc[next_date]
            
            if pos['trailing']:
                if nr['high'] > pos['peak_price']:
                    pos['peak_price'] = nr['high']
                    pos['trail_stop'] = pos['peak_price'] * (1 - TRAIL_PCT)
                if nr['low'] <= pos['trail_stop']:
                    xp = pos['trail_stop'] * (1 - SLIPPAGE_PCT)
                    ch = calc_costs(pos['entry_price'], xp, pos['qty'])
                    g = (xp - pos['entry_price']) * pos['qty']; n = g - ch
                    cash += (pos['entry_price'] * pos['qty']) + n
                    closed_trades.append({'symbol': sym, 'entry_time': pos['entry_time'],
                        'exit_time': next_date, 'days_held': pos['days'],
                        'entry_price': pos['entry_price'], 'exit_price': xp,
                        'qty': pos['qty'], 'invested': pos['entry_price']*pos['qty'],
                        'reason': 'Trailing Stop', 'gross_pnl': g, 'charges': ch,
                        'net_pnl': n, 'win': 1 if n > 0 else 0})
                    to_close.append(sym)
                    pct = (xp/pos['entry_price']-1)*100
                    print(f"  🔄 {sym:12s} TRAIL  {pos['days']:3d}d | ₹{n:+,.0f} ({pct:+.1f}%) | Cash: ₹{cash:,.0f}")
                    continue
                if pos['days'] >= pos['time_stop']:
                    xp = nr['close'] * (1 - SLIPPAGE_PCT)
                    ch = calc_costs(pos['entry_price'], xp, pos['qty'])
                    g = (xp - pos['entry_price']) * pos['qty']; n = g - ch
                    cash += (pos['entry_price'] * pos['qty']) + n
                    closed_trades.append({'symbol': sym, 'entry_time': pos['entry_time'],
                        'exit_time': next_date, 'days_held': pos['days'],
                        'entry_price': pos['entry_price'], 'exit_price': xp,
                        'qty': pos['qty'], 'invested': pos['entry_price']*pos['qty'],
                        'reason': 'Time+Trail', 'gross_pnl': g, 'charges': ch,
                        'net_pnl': n, 'win': 1 if n > 0 else 0})
                    to_close.append(sym)
                    print(f"  ⏰ {sym:12s} T+TRAIL {pos['days']:3d}d | ₹{n:+,.0f} | Cash: ₹{cash:,.0f}")
                    continue
                continue
            
            if nr['high'] >= pos['target'] and not pos.get('is_multibagger', False):
                pos['trailing'] = True
                pos['peak_price'] = max(nr['high'], pos['target'])
                pos['trail_stop'] = pos['peak_price'] * (1 - TRAIL_PCT)
                print(f"  🎯 {sym:12s} TARGET  {pos['days']:3d}d → TRAILING")
                continue
            
            # ── Phase 14: Multibagger Handling ──
            # If it's a multibagger, we ignore the target and time stop, just trailing by 30% to ride the mega-trend.
            if pos.get('is_multibagger', False):
                if nr['high'] > pos['peak_price']:
                    pos['peak_price'] = nr['high']
                    # Use a very wide trailing stop for multibaggers (e.g., 20%) to avoid getting shaken out
                    pos['trail_stop'] = pos['peak_price'] * (1 - 0.20)
                
                # Check multibagger trailing stop (down 20% from peak)
                if nr['low'] <= pos['trail_stop']:
                    xp = pos['trail_stop'] * (1 - SLIPPAGE_PCT)
                    ch = calc_costs(pos['entry_price'], xp, pos['qty'])
                    g = (xp - pos['entry_price']) * pos['qty']; n = g - ch
                    cash += (pos['entry_price'] * pos['qty']) + n
                    closed_trades.append({'symbol': sym, 'entry_time': pos['entry_time'],
                        'exit_time': next_date, 'days_held': pos['days'],
                        'entry_price': pos['entry_price'], 'exit_price': xp,
                        'qty': pos['qty'], 'invested': pos['entry_price']*pos['qty'],
                        'reason': 'Multibagger Trail (20%)', 'gross_pnl': g, 'charges': ch,
                        'net_pnl': n, 'win': 1 if n > 0 else 0})
                    to_close.append(sym)
                    pct = (xp/pos['entry_price']-1)*100
                    print(f"  🚀 {sym:12s} MB_TRAIL {pos['days']:3d}d | ₹{n:+,.0f} ({pct:+.1f}%) | Cash: ₹{cash:,.0f}")
                    continue
                # Multibaggers IGNORE the 63-day time stop!
                continue
            
            if pos['days'] >= pos['time_stop']:
                extend = False
                if curr_date in df.index:
                    ds = df.loc[:curr_date].copy()
                    try:
                        a = analyze_stock(f"{sym}.NS",
                            ds.drop(columns=['ema_21','rsi_14'], errors='ignore'),
                            'balanced', 'short', '1month')
                        if "BUY" in a['recommendation'] or "HOLD" in a['recommendation']:
                            pos['time_stop'] += 30; extend = True
                    except: pass
                if not extend:
                    xp = nr['close'] * (1 - SLIPPAGE_PCT)
                    ch = calc_costs(pos['entry_price'], xp, pos['qty'])
                    g = (xp - pos['entry_price']) * pos['qty']; n = g - ch
                    cash += (pos['entry_price'] * pos['qty']) + n
                    closed_trades.append({'symbol': sym, 'entry_time': pos['entry_time'],
                        'exit_time': next_date, 'days_held': pos['days'],
                        'entry_price': pos['entry_price'], 'exit_price': xp,
                        'qty': pos['qty'], 'invested': pos['entry_price']*pos['qty'],
                        'reason': f"Time Stop ({pos['time_stop']}d)",
                        'gross_pnl': g, 'charges': ch, 'net_pnl': n,
                        'win': 1 if n > 0 else 0})
                    to_close.append(sym)
                    print(f"  ⏰ {sym:12s} TSTOP   {pos['days']:3d}d | ₹{n:+,.0f} | Cash: ₹{cash:,.0f}")
        
        for sym in to_close: del open_positions[sym]
        
        if next_date and next_date in signals_by_date:
            day_sigs = sorted(signals_by_date[next_date], key=lambda x: x['composite'], reverse=True)
            for sig in day_sigs:
                sym = sig['symbol']
                if sym in open_positions: continue
                alloc = position_size(sig['confidence'],
                    cash + sum(p['entry_price']*p['qty'] for p in open_positions.values()))
                alloc = min(alloc, cash)
                if alloc < 3000: continue
                ep = sig['entry_price']; qty = int(alloc / ep)
                if qty == 0: continue
                inv = ep * qty; cash -= inv
                is_mb = sig.get('is_multibagger', False)
                open_positions[sym] = {
                    'entry_price': ep, 'entry_time': next_date,
                    'target': sig['target'], 'qty': qty,
                    'days': 0, 'time_stop': HORIZON_DAYS,
                    'trailing': False, 'peak_price': ep, 'trail_stop': ep * (1 - 0.20) if is_mb else 0,
                    'is_multibagger': is_mb
                }
                t = "🚀" if is_mb else "🔥" if sig['confidence'] >= 80 else "🟢" if sig['confidence'] >= 70 else "🟡"
                print(f"  {t} BUY {sym:12s} ₹{ep:>8.2f} x {qty:3d} = ₹{inv:>7,.0f} | Conf:{sig['confidence']:.0f}% | Cash:₹{cash:,.0f}")
    
    print(f"\n  📋 Closing {len(open_positions)} open positions...")
    for sym, pos in open_positions.items():
        df = stock_data[sym]
        xp = df['close'].iloc[-1] * (1 - SLIPPAGE_PCT)
        ch = calc_costs(pos['entry_price'], xp, pos['qty'])
        g = (xp - pos['entry_price']) * pos['qty']; n = g - ch
        cash += (pos['entry_price'] * pos['qty']) + n
        tn = " (trailing)" if pos['trailing'] else ""
        closed_trades.append({'symbol': sym, 'entry_time': pos['entry_time'],
            'exit_time': df.index[-1], 'days_held': pos['days'],
            'entry_price': pos['entry_price'], 'exit_price': xp,
            'qty': pos['qty'], 'invested': pos['entry_price']*pos['qty'],
            'reason': f"End of Backtest{tn}", 'gross_pnl': g, 'charges': ch,
            'net_pnl': n, 'win': 1 if n > 0 else 0})
        m = "✅" if n > 0 else "❌"
        print(f"  {m} {sym:12s} END {pos['days']:3d}d | ₹{n:+,.0f}{tn}")
    
    if not closed_trades: print("\nNo trades."); return
    tdf = pd.DataFrame(closed_trades)
    w = tdf[tdf['win']==1]; l = tdf[tdf['win']==0]
    pnl = tdf['net_pnl'].sum(); final = STARTING_CAPITAL + pnl
    
    print(f"\n{'='*65}")
    print(f"💰 OPTION E v2: {len(stock_data)}-STOCK UNIVERSE — RESULTS")
    print("=" * 65)
    print(f"Starting Capital:   ₹{STARTING_CAPITAL:>10,.0f}")
    print(f"Final Capital:      ₹{final:>10,.0f}")
    print(f"TOTAL RETURN:       ₹{pnl:>+10,.0f} ({(pnl/STARTING_CAPITAL)*100:+.2f}%)")
    print(f"Period:             {FROM_DATE} → {TO_DATE}")
    print(f"Universe:           {len(stock_data)} stocks")
    print(f"Strategy:           Conf≥60% + Momentum + Kelly + Trail")
    print("-" * 65)
    print(f"Total Trades:       {len(tdf)}")
    print(f"Win Rate:           {(len(w)/len(tdf))*100:.1f}% ({len(w)}W / {len(l)}L)")
    print("-" * 65)
    print(f"Gross P&L:          ₹{tdf['gross_pnl'].sum():>+10,.0f}")
    print(f"Total Charges:      ₹{tdf['charges'].sum():>10,.0f}")
    print(f"NET P&L:            ₹{tdf['net_pnl'].sum():>+10,.0f}")
    print("-" * 65)
    if len(w): print(f"Avg Win:            ₹{w['net_pnl'].mean():>+10,.0f}")
    if len(l): print(f"Avg Loss:           ₹{l['net_pnl'].mean():>+10,.0f}")
    print(f"Max Win:            ₹{tdf['net_pnl'].max():>+10,.0f}")
    print(f"Max Loss:           ₹{tdf['net_pnl'].min():>+10,.0f}")
    print("=" * 65)
    
    print("\n📋 Trade Journal:")
    print("-" * 130)
    for _, t in tdf.sort_values('entry_time').iterrows():
        m = "✅" if t['win'] else "❌"
        print(f"  {m} {t['symbol']:12s} | {str(t['entry_time'])[:10]} → {str(t['exit_time'])[:10]} | {t['days_held']:3d}d | ₹{t['invested']:>7,.0f} | ₹{t['net_pnl']:>+8,.0f} | {t['reason']}")
    
    print(f"\n📊 By Exit Reason:")
    for r, g in tdf.groupby('reason'):
        print(f"  {r:30s}: {len(g)} trades | ₹{g['net_pnl'].sum():+,.0f}")
    
    tdf.to_csv('backtest_option_e_250_trades.csv', index=False)
    print(f"\nSaved to 'backtest_option_e_250_trades.csv'")

if __name__ == "__main__":
    run_backtest()
