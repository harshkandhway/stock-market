#!/usr/bin/env python3
"""
₹1 LAKH PORTFOLIO BACKTEST — Split Across Multiple Positions
==============================================================
Realistic simulation:
  - Total capital: ₹1,00,000
  - Per-position size: ₹20,000 (5 slots)
  - When a signal fires AND a slot is free, deploy ₹20k into that stock
  - Each position runs independently until Target Hit / Time Stop
  - When a position closes, that ₹20k (+ profit or - loss) returns to cash
  - Cash is re-deployed into new signals as slots free up

Uses pre-computed signals from the cached Upstox data.
"""
import sys, os
import pandas as pd
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from src.cli.stock_analyzer_pro import analyze_stock

STARTING_CAPITAL = 100000
PER_POSITION = 20000   # ₹20k per stock = 5 slots max
HORIZON_DAYS = 63
CACHE_DIR = os.path.join(project_root, 'data', 'upstox_cache')

# Costs
SLIPPAGE_PCT = 0.001
STT_PCT_DELIVERY = 0.001
BROKERAGE = 0.0
EXCH_TXN_CHARGE = 0.0000325
GST_PCT = 0.18
SEBI_TURNOVER = 0.000001
STAMP_DUTY_BUY = 0.00015

# Universe
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

def load_cached_data():
    stock_data = {}
    for symbol in ALL_SYMBOLS:
        f = os.path.join(CACHE_DIR, f"{symbol}_2024-07-01_2025-07-01.csv")
        if not os.path.exists(f): continue
        df = pd.read_csv(f, parse_dates=['date'], index_col='date')
        if len(df) < 100: continue
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['stock_return_63d'] = df['close'].pct_change(periods=63)
        stock_data[symbol] = df
    return stock_data

def load_nifty():
    f = os.path.join(CACHE_DIR, "NIFTY50_2024-07-01_2025-07-01.csv")
    df = pd.read_csv(f, parse_dates=['date'], index_col='date')
    df['nifty_return_63d'] = df['close'].pct_change(periods=63)
    return df

def calc_costs(entry_price, exit_price, qty):
    turnover = (entry_price + exit_price) * qty
    stt = (entry_price * qty + exit_price * qty) * STT_PCT_DELIVERY
    exch_txn = turnover * EXCH_TXN_CHARGE
    gst = (BROKERAGE * 2 + exch_txn) * GST_PCT
    sebi = turnover * SEBI_TURNOVER
    stamp = (entry_price * qty) * STAMP_DUTY_BUY
    return stt + BROKERAGE * 2 + exch_txn + gst + sebi + stamp

def run_backtest():
    print("=" * 65)
    print("PASS 1: Pre-computing all buy signals...")
    print("=" * 65)
    
    stock_data = load_cached_data()
    nifty_df = load_nifty()
    print(f"  Loaded {len(stock_data)} stocks + Nifty 50\n")
    
    # ========== PASS 1: Find ALL signals ==========
    all_signals = []
    for sym_idx, (symbol, df) in enumerate(sorted(stock_data.items())):
        print(f"  [{sym_idx+1}/{len(stock_data)}] {symbol}...", end=" ", flush=True)
        count = 0
        for i in range(63, len(df) - 1):
            curr_date = df.index[i]
            next_date = df.index[i + 1]
            curr_row = df.iloc[i]
            next_row = df.iloc[i + 1]
            
            stock_ret = curr_row.get('stock_return_63d', np.nan)
            if pd.isna(stock_ret): continue
            try:
                nidx = nifty_df.index.get_indexer([curr_date], method='pad')[0]
                if nidx == -1: continue
                nifty_ret = nifty_df.iloc[nidx]['nifty_return_63d']
                if pd.isna(nifty_ret) or stock_ret <= nifty_ret: continue
                rs = stock_ret - nifty_ret
            except: continue
            
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
                        'confidence': conf, 'rs_score': rs,
                        'composite': conf * (1 + rs),
                    })
                    count += 1
            except: pass
        print(f"{count}")
    
    if not all_signals:
        print("\nNo signals!"); return
    
    sdf = pd.DataFrame(all_signals).sort_values('entry_date')
    print(f"\n  📊 Total signals: {len(sdf)}")
    print(f"  📅 Range: {sdf.iloc[0]['entry_date'].date()} → {sdf.iloc[-1]['entry_date'].date()}")
    
    # ========== PASS 2: Portfolio simulation ==========
    print("\n" + "=" * 65)
    print(f"PASS 2: ₹{STARTING_CAPITAL:,.0f} portfolio | ₹{PER_POSITION:,.0f}/position | {STARTING_CAPITAL//PER_POSITION} slots")
    print("=" * 65)
    
    cash = float(STARTING_CAPITAL)
    open_positions = {}  # symbol -> {entry_price, entry_time, target, qty, days, time_stop}
    closed_trades = []
    
    # Build unified trading calendar
    all_dates = set()
    for df in stock_data.values():
        all_dates.update(df.index.tolist())
    trading_dates = sorted(all_dates)[63:]
    
    # Group signals by entry_date for efficient lookup
    signals_by_date = {}
    for _, sig in sdf.iterrows():
        d = sig['entry_date']
        if d not in signals_by_date:
            signals_by_date[d] = []
        signals_by_date[d].append(sig)
    
    for date_idx, curr_date in enumerate(trading_dates):
        next_date = trading_dates[date_idx + 1] if date_idx + 1 < len(trading_dates) else None
        
        # ---- CHECK OPEN POSITIONS ----
        to_close = []
        for sym, pos in open_positions.items():
            pos['days'] += 1
            df = stock_data[sym]
            
            if next_date is None or next_date not in df.index:
                continue
            
            next_row = df.loc[next_date]
            
            # Target Hit
            if next_row['high'] >= pos['target']:
                exit_p = pos['target'] * (1 - SLIPPAGE_PCT)
                charges = calc_costs(pos['entry_price'], exit_p, pos['qty'])
                gross = (exit_p - pos['entry_price']) * pos['qty']
                net = gross - charges
                cash += (pos['entry_price'] * pos['qty']) + net  # Return invested + P&L
                closed_trades.append({
                    'symbol': sym, 'entry_time': pos['entry_time'],
                    'exit_time': next_date, 'days_held': pos['days'],
                    'entry_price': pos['entry_price'], 'exit_price': exit_p,
                    'qty': pos['qty'], 'invested': pos['entry_price'] * pos['qty'],
                    'reason': 'Target Hit', 'gross_pnl': gross,
                    'charges': charges, 'net_pnl': net,
                    'win': 1 if net > 0 else 0
                })
                to_close.append(sym)
                print(f"  ✅ {sym:12s} TARGET HIT  {pos['days']:3d}d | ₹{net:+,.0f}")
                continue
            
            # Time Stop
            if pos['days'] >= pos['time_stop']:
                extend = False
                if curr_date in df.index:
                    df_slice = df.loc[:curr_date].copy()
                    try:
                        analysis = analyze_stock(
                            symbol=f"{sym}.NS",
                            df=df_slice.drop(columns=['ema_21', 'stock_return_63d'], errors='ignore'),
                            mode='balanced', timeframe='short', horizon='1month'
                        )
                        if "BUY" in analysis['recommendation'] or "HOLD" in analysis['recommendation']:
                            pos['time_stop'] += 30
                            extend = True
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
                    print(f"  ⏰ {sym:12s} TIME STOP   {pos['days']:3d}d | ₹{net:+,.0f}")
                    continue
        
        for sym in to_close:
            del open_positions[sym]
        
        # ---- ENTER NEW POSITIONS ----
        if next_date and next_date in signals_by_date:
            # Sort by composite score (best signals first)
            day_signals = sorted(signals_by_date[next_date], key=lambda x: x['composite'], reverse=True)
            
            for sig in day_signals:
                sym = sig['symbol']
                
                # Skip if already holding this stock
                if sym in open_positions:
                    continue
                
                # Check if we have enough cash for a position
                if cash < PER_POSITION:
                    break
                
                entry_p = sig['entry_price']
                qty = int(PER_POSITION / entry_p)
                if qty == 0:
                    continue
                
                invested = entry_p * qty
                cash -= invested
                
                open_positions[sym] = {
                    'entry_price': entry_p, 'entry_time': next_date,
                    'target': sig['target'], 'qty': qty,
                    'days': 0, 'time_stop': HORIZON_DAYS
                }
                print(f"  🟢 BUY {sym:12s} ₹{entry_p:>8.2f} x {qty:3d} = ₹{invested:>7,.0f} | Target: ₹{sig['target']:.2f} | Cash left: ₹{cash:,.0f}")
    
    # Close remaining open positions at end of backtest
    print(f"\n  📋 Closing {len(open_positions)} open positions at end of backtest...")
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
            'charges': charges, 'net_pnl': net,
            'win': 1 if net > 0 else 0
        })
        marker = "✅" if net > 0 else "❌"
        print(f"  {marker} {sym:12s} END         {pos['days']:3d}d | ₹{net:+,.0f}")
    
    # ========== RESULTS ==========
    if not closed_trades:
        print("\nNo trades."); return
    
    tdf = pd.DataFrame(closed_trades)
    wins = tdf[tdf['win'] == 1]
    losses = tdf[tdf['win'] == 0]
    total_pnl = tdf['net_pnl'].sum()
    final_capital = STARTING_CAPITAL + total_pnl
    
    print("\n" + "=" * 65)
    print(f"💰 ₹{STARTING_CAPITAL:,.0f} PORTFOLIO — ₹{PER_POSITION:,.0f}/position — RESULTS")
    print("=" * 65)
    print(f"Starting Capital:   ₹{STARTING_CAPITAL:>10,.0f}")
    print(f"Final Capital:      ₹{final_capital:>10,.0f}")
    print(f"TOTAL RETURN:       ₹{total_pnl:>+10,.0f} ({(total_pnl/STARTING_CAPITAL)*100:+.2f}%)")
    print(f"Period:             Jul 2024 → Jul 2025 (Upstox data)")
    print(f"Position Size:      ₹{PER_POSITION:,.0f} ({STARTING_CAPITAL//PER_POSITION} slots)")
    print("-" * 65)
    print(f"Total Trades:       {len(tdf)}")
    print(f"Win Rate:           {(len(wins)/len(tdf))*100:.1f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Max Positions Held: —")
    print("-" * 65)
    print(f"Gross P&L:          ₹{tdf['gross_pnl'].sum():>+10,.0f}")
    print(f"Total Charges:      ₹{tdf['charges'].sum():>10,.0f}")
    print(f"NET P&L:            ₹{tdf['net_pnl'].sum():>+10,.0f}")
    print("-" * 65)
    if len(wins) > 0:
        print(f"Avg Win:            ₹{wins['net_pnl'].mean():>+10,.0f}")
    if len(losses) > 0:
        print(f"Avg Loss:           ₹{losses['net_pnl'].mean():>+10,.0f}")
    print(f"Max Win:            ₹{tdf['net_pnl'].max():>+10,.0f}")
    print(f"Max Loss:           ₹{tdf['net_pnl'].min():>+10,.0f}")
    print("=" * 65)
    
    print("\n📋 Trade Journal:")
    print("-" * 120)
    for _, t in tdf.sort_values('entry_time').iterrows():
        m = "✅" if t['win'] else "❌"
        print(f"  {m} {t['symbol']:12s} | {str(t['entry_time'])[:10]} → {str(t['exit_time'])[:10]} | {t['days_held']:3d}d | ₹{t['invested']:>7,.0f} invested | ₹{t['net_pnl']:>+7,.0f} | {t['reason']}")
    
    print(f"\n📊 Summary by Exit Reason:")
    for reason, grp in tdf.groupby('reason'):
        print(f"  {reason:20s}: {len(grp)} trades | ₹{grp['net_pnl'].sum():+,.0f} total P&L")
    
    tdf.to_csv('backtest_1lakh_portfolio_trades.csv', index=False)
    print(f"\nSaved to 'backtest_1lakh_portfolio_trades.csv'")

if __name__ == "__main__":
    run_backtest()
