#!/usr/bin/env python3
"""
TWIN SHORT ENGINE BACKTEST
===========================
Short-selling backtest using the dedicated short_analyzer_pro engine.
Based on the Option E hybrid shell, adapted for shorts.

Strategy:
  1. Momentum filter: Price < EMA-21, RSI 30-60, Volume > 20d avg
  2. Short signal: analyze_stock_short() → SHORT / STRONG SHORT (conf >= 60%)
  3. Entry: Short at next day's open (+ slippage)
  4. Exit: Target hit (price drops) → trailing stop, or time stop (30d)
  5. P&L: (entry_price - exit_price) * qty
  6. Tighter sizing: shorts carry unlimited risk → conservative positions

Period: June 2024 → July 2025 | Cached Upstox data | ₹2 Lakh capital
"""
import sys, os, json, gzip, time as time_module
import pandas as pd
import numpy as np
import requests

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from src.cli.short_analyzer_pro import analyze_stock_short
from src.core.market_regime import detect_market_regime, get_regime_for_date, get_regime_summary
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/Trades/.env'))

ACCESS_TOKEN = os.getenv('UPSTOX_LIVE_TOKEN', '')
HEADERS = {'Accept': 'application/json', 'Authorization': f'Bearer {ACCESS_TOKEN}'}

# ── Configuration ──────────────────────────────────────────────────────
STARTING_CAPITAL = 200000
HORIZON_DAYS     = 30       # Shorts shouldn't be held long
TRAIL_PCT        = 0.05     # 5% trailing stop after target hit
MAX_LOSS_PCT     = 0.10     # 10% hard stop-loss per trade (circuit breaker)
FROM_DATE        = '2024-06-01'
TO_DATE          = '2025-07-01'
CONFIDENCE_MIN   = 60       # Minimum confidence for entry
NIFTY_SYMBOL     = 'NIFTY50' # For regime detection

CACHE_DIR = os.path.join(project_root, 'data', 'upstox_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# ── Costs (F&O-approximate: lower STT, high margin) ───────────────────
SLIPPAGE_PCT      = 0.001
STT_PCT           = 0.0001      # F&O STT is lower than delivery
EXCH_TXN_CHARGE   = 0.0000325
GST_PCT           = 0.18
SEBI_TURNOVER     = 0.000001
STAMP_DUTY        = 0.00015

# ── Position sizing (conservative for shorts) ─────────────────────────
def position_size(confidence, capital):
    """Conservative sizing — shorts carry unlimited risk."""
    if confidence >= 80:
        return min(30000, capital * 0.25)   # Max ₹30k (vs ₹35k for longs)
    elif confidence >= 70:
        return min(20000, capital * 0.18)   # Max ₹20k
    else:
        return min(12000, capital * 0.12)   # Max ₹12k

# ── Universe (same Nifty 50 + Midcap 150) ─────────────────────────────
NIFTY_50 = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'ITC', 'SBIN',
    'BAJFINANCE', 'BHARTIARTL', 'KOTAKBANK', 'AXISBANK', 'ASIANPAINT',
    'MARUTI', 'HCLTECH', 'SUNPHARMA', 'TITAN', 'M&M', 'TRENT', 'BEL',
    'HAL', 'INDIGO', 'TVSMOTOR', 'WIPRO', 'ADANIPORTS', 'NTPC',
    'POWERGRID', 'ULTRACEMCO', 'ONGC', 'JSWSTEEL', 'TATAMOTORS',
    'BAJAJ-AUTO', 'COALINDIA', 'LT', 'HINDALCO', 'DRREDDY',
    'NESTLEIND', 'BAJAJFINSV', 'CIPLA', 'EICHERMOT', 'DIVISLAB',
    'GRASIM', 'APOLLOHOSP', 'HEROMOTOCO', 'TECHM', 'BRITANNIA',
    'TATASTEEL', 'SHRIRAMFIN', 'TATACONSUM', 'BPCL', 'SBILIFE',
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
    'HUDCO', 'KEI', 'TIINDIA', 'SOLARINDS', 'JSWENERGY',
]
ALL_SYMBOLS = sorted(set(NIFTY_50 + MIDCAP_150))

# ── Data helpers ───────────────────────────────────────────────────────
INSTRUMENT_CACHE = os.path.join(CACHE_DIR, 'nse_instruments.json')

def load_instrument_map():
    if os.path.exists(INSTRUMENT_CACHE):
        with open(INSTRUMENT_CACHE) as f:
            return json.load(f)
    url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz'
    r = requests.get(url, timeout=60)
    instruments = json.loads(gzip.decompress(r.content))
    eq_map = {
        i['trading_symbol']: i['instrument_key']
        for i in instruments
        if i.get('instrument_type') == 'EQ' and i.get('segment') == 'NSE_EQ'
    }
    with open(INSTRUMENT_CACHE, 'w') as f:
        json.dump(eq_map, f)
    return eq_map

def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                time_module.sleep(3)
            else:
                if attempt == retries - 1:
                    return None
        except Exception:
            if attempt == retries - 1:
                return None
        time_module.sleep(0.3)
    return None

def fetch_data(symbol, instrument_key):
    f = os.path.join(CACHE_DIR, f"{symbol}_{FROM_DATE}_{TO_DATE}.csv")
    if os.path.exists(f):
        df = pd.read_csv(f, parse_dates=['date'], index_col='date')
        if len(df) > 50:
            return df
    encoded = instrument_key.replace('|', '%7C')
    url = f"https://api.upstox.com/v2/historical-candle/{encoded}/day/{TO_DATE}/{FROM_DATE}"
    data = api_get(url)
    if not data or 'data' not in data or 'candles' not in data['data']:
        return pd.DataFrame()
    rows = [
        {'date': pd.Timestamp(c[0]), 'open': float(c[1]), 'high': float(c[2]),
         'low': float(c[3]), 'close': float(c[4]), 'volume': int(c[5])}
        for c in data['data']['candles']
    ]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values('date').set_index('date')
    df.to_csv(f)
    return df

# ── Cost calculation ───────────────────────────────────────────────────
def calc_costs(entry_price, exit_price, qty):
    turnover = (entry_price + exit_price) * qty
    stt = (entry_price * qty + exit_price * qty) * STT_PCT
    exch_txn = turnover * EXCH_TXN_CHARGE
    gst = exch_txn * GST_PCT
    sebi = turnover * SEBI_TURNOVER
    stamp = (entry_price * qty) * STAMP_DUTY
    return stt + exch_txn + gst + sebi + stamp

# ── Technical helpers ──────────────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def passes_momentum_short(df, i):
    """
    Short momentum filter — looking for confirmed weakness:
      1. Price < EMA-21  (confirmed downtrend)
      2. RSI 30-60       (not oversold bounce risk, not too strong)
      3. Volume > 20d avg (interest in the move)
    """
    if i < 21:
        return False
    row = df.iloc[i]

    # Price below EMA-21 → downtrend
    ema21 = row.get('ema_21', 0)
    if ema21 == 0 or row['close'] >= ema21:
        return False

    # RSI between 30-60
    rsi = row.get('rsi_14', 50)
    if rsi < 30 or rsi > 60:
        return False

    # Volume above 20-day average
    vol_20d = df['volume'].iloc[max(0, i - 20):i].mean()
    if row['volume'] < vol_20d:
        return False

    return True


# ══════════════════════════════════════════════════════════════════════
# MAIN BACKTEST
# ══════════════════════════════════════════════════════════════════════

def run_backtest():
    instrument_map = load_instrument_map()

    print("=" * 65)
    print(f"TWIN SHORT ENGINE BACKTEST — {FROM_DATE} -> {TO_DATE}")
    print("=" * 65)
    print(f"  Capital: {STARTING_CAPITAL:,.0f} | Conf >= {CONFIDENCE_MIN}% | Horizon: {HORIZON_DAYS}d")
    print(f"  Momentum: Price < EMA-21, RSI 30-60, Vol > 20d avg")
    print()

    # ── Load data ──────────────────────────────────────────────────────
    stock_data = {}
    for sym in ALL_SYMBOLS:
        if sym not in instrument_map:
            continue
        df = fetch_data(sym, instrument_map[sym])
        if df is None or len(df) < 100:
            continue
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['rsi_14'] = compute_rsi(df['close'], 14)
        stock_data[sym] = df
    print(f"  Loaded {len(stock_data)} stocks\n")

    # ── V2: Fetch NIFTY50 Market Regime ─────────────────────────
    print("  Fetching NIFTY50 for Market Regime Detection...")
    nifty_df = pd.DataFrame()
    nifty_cache_file = os.path.join(CACHE_DIR, f"NIFTY50_{FROM_DATE}_{TO_DATE}.csv")
    if os.path.exists(nifty_cache_file):
        nifty_df = pd.read_csv(nifty_cache_file, parse_dates=['date'], index_col='date')
    else:
        nifty_df = fetch_data("NIFTY50", "NSE_INDEX|Nifty 50")
        
    if not nifty_df.empty:
        nifty_regime = detect_market_regime(nifty_df)
        print("  Regime detection active.\n")
    else:
        print("  WARNING: Nifty50 unavailable, regime detection disabled.\n")
        nifty_regime = {}

    # ══ PASS 1: Generate short signals ════════════════════════════════
    print("=" * 65)
    print("PASS 1: Short signals (conf >= 60% + short momentum filter)...")
    print("=" * 65)

    all_signals = []
    for idx, (symbol, df) in enumerate(sorted(stock_data.items())):
        print(f"  [{idx+1}/{len(stock_data)}] {symbol}...", end=" ", flush=True)
        count = 0
        for i in range(63, len(df) - 1):
            curr_date = df.index[i]
            next_date = df.index[i + 1]
            next_row  = df.iloc[i + 1]

            if not passes_momentum_short(df, i):
                continue

            df_slice = df.iloc[:i + 1].copy()
            
            # V2: Get current market regime
            current_regime = get_regime_for_date(nifty_regime, curr_date) if nifty_regime else None
            mkt_reg_str = current_regime.get('regime', 'neutral') if current_regime else 'neutral'
            
            try:
                analysis = analyze_stock_short(
                    symbol=f"{symbol}.NS",
                    df=df_slice.drop(columns=['ema_21', 'rsi_14'], errors='ignore'),
                    mode='balanced', timeframe='medium', horizon='1month',
                    market_regime=mkt_reg_str
                )
                rec  = analysis['recommendation']
                conf = analysis['confidence']

                # Capture SHORT signals only
                if ('SHORT' in rec) and ('AVOID' not in rec) and conf >= CONFIDENCE_MIN:
                    # Entry price: short at next day's open + slippage (hurts on short)
                    ep = next_row['open'] * (1 - SLIPPAGE_PCT)
                    target = analysis['target']

                    # Sanity: target must be below entry
                    if target >= ep:
                        target = ep * 0.97  # fallback: 3% downside target

                    all_signals.append({
                        'signal_date': curr_date,
                        'entry_date': next_date,
                        'symbol': symbol,
                        'entry_price': ep,
                        'target': target,
                        'confidence': conf,
                        'composite': conf,
                        'recommendation': rec,
                    })
                    count += 1
            except Exception:
                pass
        print(f"{count}")

    if not all_signals:
        print("\nNo short signals generated!")
        return

    sdf = pd.DataFrame(all_signals).sort_values('entry_date')
    print(f"\n  Total short signals: {len(sdf)}")
    print(f"  Range: {sdf.iloc[0]['entry_date'].date()} -> {sdf.iloc[-1]['entry_date'].date()}")

    sdf['month'] = sdf['entry_date'].dt.to_period('M')
    print(f"\n  Signals by month:")
    for month, grp in sdf.groupby('month'):
        print(f"    {month}: {len(grp)} signals")

    # ══ PASS 2: Portfolio simulation ══════════════════════════════════
    print("\n" + "=" * 65)
    print(f"PASS 2: {STARTING_CAPITAL:,.0f} portfolio | Short positions | Trailing stops")
    print("=" * 65)

    cash = float(STARTING_CAPITAL)
    open_positions = {}
    closed_trades  = []

    all_dates = set()
    for df in stock_data.values():
        all_dates.update(df.index.tolist())
    trading_dates = sorted(all_dates)[63:]

    signals_by_date = {}
    for _, sig in sdf.iterrows():
        d = sig['entry_date']
        if d not in signals_by_date:
            signals_by_date[d] = []
        signals_by_date[d].append(sig)

    for date_idx, curr_date in enumerate(trading_dates):
        next_date = trading_dates[date_idx + 1] if date_idx + 1 < len(trading_dates) else None

        # ── Check open positions ──────────────────────────────────────
        to_close = []
        for sym, pos in open_positions.items():
            pos['days'] += 1
            df = stock_data[sym]
            if next_date is None or next_date not in df.index:
                continue
            nr = df.loc[next_date]

            # === V2: MAX LOSS CIRCUIT BREAKER ===
            if nr['high'] >= pos['max_loss_stop']:
                xp = pos['max_loss_stop'] * (1 + SLIPPAGE_PCT)
                charges = calc_costs(pos['entry_price'], xp, pos['qty'])
                gross = (pos['entry_price'] - xp) * pos['qty']
                net = gross - charges
                cash += pos['invested'] + net
                closed_trades.append({
                    'symbol': sym, 'entry_time': pos['entry_time'],
                    'exit_time': next_date, 'days_held': pos['days'],
                    'entry_price': pos['entry_price'], 'exit_price': xp,
                    'qty': pos['qty'], 'invested': pos['invested'],
                    'reason': f'Max Loss Stop ({int(MAX_LOSS_PCT*100)}%)', 'gross_pnl': gross,
                    'charges': charges, 'net_pnl': net,
                    'win': 0,
                })
                to_close.append(sym)
                pct = (1 - xp / pos['entry_price']) * 100
                print(f"  MAX_LOSS {sym:12s} {pos['days']:3d}d | {net:+,.0f} ({pct:+.1f}%) | Cash: {cash:,.0f}")
                continue

            # === TRAILING STOP MODE (short version) ===
            if pos['trailing']:
                # Track trough (lowest price = best for short)
                if nr['low'] < pos['trough_price']:
                    pos['trough_price'] = nr['low']
                    pos['trail_stop'] = pos['trough_price'] * (1 + TRAIL_PCT)

                # Cover if price rises above trail stop
                if nr['high'] >= pos['trail_stop']:
                    xp = pos['trail_stop'] * (1 + SLIPPAGE_PCT)
                    charges = calc_costs(pos['entry_price'], xp, pos['qty'])
                    gross = (pos['entry_price'] - xp) * pos['qty']
                    net = gross - charges
                    cash += pos['invested'] + net
                    closed_trades.append({
                        'symbol': sym, 'entry_time': pos['entry_time'],
                        'exit_time': next_date, 'days_held': pos['days'],
                        'entry_price': pos['entry_price'], 'exit_price': xp,
                        'qty': pos['qty'], 'invested': pos['invested'],
                        'reason': 'Trailing Stop', 'gross_pnl': gross,
                        'charges': charges, 'net_pnl': net,
                        'win': 1 if net > 0 else 0,
                    })
                    to_close.append(sym)
                    pct = (1 - xp / pos['entry_price']) * 100
                    print(f"  TRAIL {sym:12s} {pos['days']:3d}d | {net:+,.0f} ({pct:+.1f}%) | Cash: {cash:,.0f}")
                    continue

                # Time stop even in trailing mode
                if pos['days'] >= HORIZON_DAYS:
                    xp = nr['close'] * (1 + SLIPPAGE_PCT)
                    charges = calc_costs(pos['entry_price'], xp, pos['qty'])
                    gross = (pos['entry_price'] - xp) * pos['qty']
                    net = gross - charges
                    cash += pos['invested'] + net
                    closed_trades.append({
                        'symbol': sym, 'entry_time': pos['entry_time'],
                        'exit_time': next_date, 'days_held': pos['days'],
                        'entry_price': pos['entry_price'], 'exit_price': xp,
                        'qty': pos['qty'], 'invested': pos['invested'],
                        'reason': 'Time+Trail', 'gross_pnl': gross,
                        'charges': charges, 'net_pnl': net,
                        'win': 1 if net > 0 else 0,
                    })
                    to_close.append(sym)
                    print(f"  TIME+TRAIL {sym:12s} {pos['days']:3d}d | {net:+,.0f} | Cash: {cash:,.0f}")
                    continue
                continue

            # === NORMAL MODE (waiting for target) ===
            # Short target hit: price drops BELOW target
            if nr['low'] <= pos['target']:
                pos['trailing'] = True
                pos['trough_price'] = min(nr['low'], pos['target'])
                pos['trail_stop'] = pos['trough_price'] * (1 + TRAIL_PCT)
                pct = (1 - pos['target'] / pos['entry_price']) * 100
                print(f"  TARGET {sym:12s} {pos['days']:3d}d -> Now TRAILING (+{pct:.1f}% short gain)")
                continue

            # Time stop
            if pos['days'] >= HORIZON_DAYS:
                xp = nr['close'] * (1 + SLIPPAGE_PCT)
                charges = calc_costs(pos['entry_price'], xp, pos['qty'])
                gross = (pos['entry_price'] - xp) * pos['qty']
                net = gross - charges
                cash += pos['invested'] + net
                closed_trades.append({
                    'symbol': sym, 'entry_time': pos['entry_time'],
                    'exit_time': next_date, 'days_held': pos['days'],
                    'entry_price': pos['entry_price'], 'exit_price': xp,
                    'qty': pos['qty'], 'invested': pos['invested'],
                    'reason': f'Time Stop ({HORIZON_DAYS}d)', 'gross_pnl': gross,
                    'charges': charges, 'net_pnl': net,
                    'win': 1 if net > 0 else 0,
                })
                to_close.append(sym)
                pct = (1 - xp / pos['entry_price']) * 100
                print(f"  TIME {sym:12s} {pos['days']:3d}d | {net:+,.0f} ({pct:+.1f}%) | Cash: {cash:,.0f}")

        for sym in to_close:
            del open_positions[sym]

        # ── Enter new SHORT positions ─────────────────────────────────
        if next_date and next_date in signals_by_date:
            # --- V2: REGIME GATE ---
            # Gate rule: Only allow entries if Nifty50 is in confirmed bearish downtrend:
            # i.e., days_below >= 3 and rsi <= 60. ('short_allowed' already does this in market_regime.py)
            current_regime = get_regime_for_date(nifty_regime, curr_date) if nifty_regime else None
            
            # If regime data is available and says do not short, skip the entire day's signals
            if current_regime and not current_regime.get('short_allowed', False):
                continue
                
            day_sigs = sorted(signals_by_date[next_date],
                              key=lambda x: x['composite'], reverse=True)
            for sig in day_sigs:
                sym = sig['symbol']
                if sym in open_positions:
                    continue

                total_deployed = sum(p['invested'] for p in open_positions.values())
                alloc = position_size(sig['confidence'], cash + total_deployed)
                if cash < alloc or alloc < 3000:
                    continue

                ep  = sig['entry_price']
                qty = int(alloc / ep)
                if qty == 0:
                    continue
                invested = ep * qty
                cash -= invested

                open_positions[sym] = {
                    'entry_price': ep, 'entry_time': next_date,
                    'target': sig['target'], 'qty': qty,
                    'invested': invested,
                    'days': 0, 'trailing': False,
                    'trough_price': ep, 'trail_stop': ep * (1 + TRAIL_PCT),
                    'max_loss_stop': ep * (1 + MAX_LOSS_PCT)
                }
                tier = "SS" if sig['confidence'] >= 80 else "S " if sig['confidence'] >= 70 else "WS"
                tgt_pct = (1 - sig['target'] / ep) * 100
                print(f"  [{tier}] SHORT {sym:12s} {ep:>8.2f} x {qty:3d} = {invested:>7,.0f} | Conf: {sig['confidence']:.0f}% | Tgt: -{tgt_pct:.1f}% | Cash: {cash:,.0f}")

    # ── Close remaining positions ─────────────────────────────────────
    print(f"\n  Closing {len(open_positions)} open short positions...")
    for sym, pos in open_positions.items():
        df = stock_data[sym]
        xp = df['close'].iloc[-1] * (1 + SLIPPAGE_PCT)
        charges = calc_costs(pos['entry_price'], xp, pos['qty'])
        gross = (pos['entry_price'] - xp) * pos['qty']
        net = gross - charges
        cash += pos['invested'] + net
        trail_note = " (was trailing)" if pos['trailing'] else ""
        closed_trades.append({
            'symbol': sym, 'entry_time': pos['entry_time'],
            'exit_time': df.index[-1], 'days_held': pos['days'],
            'entry_price': pos['entry_price'], 'exit_price': xp,
            'qty': pos['qty'], 'invested': pos['invested'],
            'reason': f'End of Backtest{trail_note}', 'gross_pnl': gross,
            'charges': charges, 'net_pnl': net, 'win': 1 if net > 0 else 0,
        })
        m = "W" if net > 0 else "L"
        print(f"  [{m}] {sym:12s} END {pos['days']:3d}d | {net:+,.0f}{trail_note}")

    # ══ RESULTS ═══════════════════════════════════════════════════════
    if not closed_trades:
        print("\nNo trades executed.")
        return

    tdf     = pd.DataFrame(closed_trades)
    wins    = tdf[tdf['win'] == 1]
    losses  = tdf[tdf['win'] == 0]
    total_pnl = tdf['net_pnl'].sum()
    final   = STARTING_CAPITAL + total_pnl

    print("\n" + "=" * 65)
    print("TWIN SHORT ENGINE — FINAL RESULTS")
    print("=" * 65)
    print(f"Starting Capital:   {STARTING_CAPITAL:>10,.0f}")
    print(f"Final Capital:      {final:>10,.0f}")
    print(f"TOTAL RETURN:       {total_pnl:>+10,.0f} ({(total_pnl / STARTING_CAPITAL) * 100:+.2f}%)")
    print(f"Period:             {FROM_DATE} -> {TO_DATE}")
    print(f"Strategy:           Short Engine | Conf>={CONFIDENCE_MIN}% | Momentum | Trailing")
    print("-" * 65)
    print(f"Total Trades:       {len(tdf)}")
    if len(tdf) > 0:
        print(f"Win Rate:           {(len(wins) / len(tdf)) * 100:.1f}% ({len(wins)}W / {len(losses)}L)")
    print("-" * 65)
    print(f"Gross P&L:          {tdf['gross_pnl'].sum():>+10,.0f}")
    print(f"Total Charges:      {tdf['charges'].sum():>10,.0f}")
    print(f"NET P&L:            {tdf['net_pnl'].sum():>+10,.0f}")
    print("-" * 65)
    if len(wins):
        print(f"Avg Win:            {wins['net_pnl'].mean():>+10,.0f}")
    if len(losses):
        print(f"Avg Loss:           {losses['net_pnl'].mean():>+10,.0f}")
    print(f"Max Win:            {tdf['net_pnl'].max():>+10,.0f}")
    print(f"Max Loss:           {tdf['net_pnl'].min():>+10,.0f}")
    if len(tdf) > 0:
        print(f"Avg Days Held:      {tdf['days_held'].mean():.1f}")
    print("=" * 65)

    print("\nTrade Journal:")
    print("-" * 130)
    for _, t in tdf.sort_values('entry_time').iterrows():
        m = "W" if t['win'] else "L"
        pct = (1 - t['exit_price'] / t['entry_price']) * 100
        print(f"  [{m}] {t['symbol']:12s} | {str(t['entry_time'])[:10]} -> {str(t['exit_time'])[:10]} | {t['days_held']:3d}d | {t['invested']:>7,.0f} | {t['net_pnl']:>+8,.0f} ({pct:+.1f}%) | {t['reason']}")

    print(f"\nBy Exit Reason:")
    for r, g in tdf.groupby('reason'):
        print(f"  {r:30s}: {len(g)} trades | {g['net_pnl'].sum():+,.0f}")

    out_csv = os.path.join(project_root, 'backtest_twin_short_trades.csv')
    tdf.to_csv(out_csv, index=False)
    print(f"\nSaved to '{out_csv}'")


if __name__ == "__main__":
    run_backtest()
