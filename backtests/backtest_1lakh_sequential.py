#!/usr/bin/env python3
"""
₹1 LAKH SEQUENTIAL PORTFOLIO — 2-PASS APPROACH
=================================================
Pass 1: Pre-compute ALL buy signals across ALL stocks (reuses the
        52-trade signal list from the parallel backtest's trade log).
Pass 2: Walk through the signals chronologically, deploying ₹1L
        into the best available signal, one at a time, compounding.
        
Uses cached Upstox data. Period: Jul 2024 → Jul 2025.
"""
import sys, os
import pandas as pd
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from src.cli.stock_analyzer_pro import analyze_stock

STARTING_CAPITAL = 100000
HORIZON_DAYS = 63
CACHE_DIR = os.path.join(project_root, 'data', 'upstox_cache')

# Cost structure
SLIPPAGE_PCT = 0.001
STT_PCT_DELIVERY = 0.001
BROKERAGE = 0.0
EXCH_TXN_CHARGE = 0.0000325
GST_PCT = 0.18
SEBI_TURNOVER = 0.000001
STAMP_DUTY_BUY = 0.00015

# Full universe
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

def calculate_costs(entry_price, exit_price, qty):
    turnover = (entry_price + exit_price) * qty
    stt = (entry_price * qty + exit_price * qty) * STT_PCT_DELIVERY
    exch_txn = turnover * EXCH_TXN_CHARGE
    gst = (BROKERAGE * 2 + exch_txn) * GST_PCT
    sebi = turnover * SEBI_TURNOVER
    stamp = (entry_price * qty) * STAMP_DUTY_BUY
    return stt + BROKERAGE * 2 + exch_txn + gst + sebi + stamp


def run_backtest():
    print("=" * 65)
    print("PASS 1: Pre-computing all buy signals across 143 stocks...")
    print("=" * 65)
    
    stock_data = load_cached_data()
    nifty_df = load_nifty()
    print(f"  Loaded {len(stock_data)} stocks + Nifty 50\n")
    
    # ========== PASS 1: Find ALL valid entry signals ==========
    all_signals = []
    
    for sym_idx, (symbol, df) in enumerate(sorted(stock_data.items())):
        print(f"  [{sym_idx+1}/{len(stock_data)}] Scanning {symbol}...", end=" ", flush=True)
        signal_count = 0
        
        for i in range(63, len(df) - 1):
            curr_date = df.index[i]
            next_date = df.index[i + 1]
            curr_row = df.iloc[i]
            next_row = df.iloc[i + 1]
            
            # RS check
            stock_ret = curr_row.get('stock_return_63d', np.nan)
            if pd.isna(stock_ret):
                continue
            try:
                nifty_idx = nifty_df.index.get_indexer([curr_date], method='pad')[0]
                if nifty_idx == -1: continue
                nifty_ret = nifty_df.iloc[nifty_idx]['nifty_return_63d']
                if pd.isna(nifty_ret) or stock_ret <= nifty_ret:
                    continue
                rs_score = stock_ret - nifty_ret
            except:
                continue
            
            # Analyzer check
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
                        'signal_date': curr_date,
                        'entry_date': next_date,
                        'symbol': symbol,
                        'entry_price': next_row['open'] * (1 + SLIPPAGE_PCT),
                        'target': analysis['target'],
                        'confidence': conf,
                        'rs_score': rs_score,
                        'composite': conf * (1 + rs_score),
                    })
                    signal_count += 1
            except:
                pass
        
        print(f"{signal_count} signals")
    
    if not all_signals:
        print("\nNo signals found!")
        return
    
    signals_df = pd.DataFrame(all_signals).sort_values('entry_date')
    print(f"\n  📊 Total raw signals found: {len(signals_df)}")
    print(f"  📅 First signal: {signals_df.iloc[0]['entry_date'].date()}")
    print(f"  📅 Last signal:  {signals_df.iloc[-1]['entry_date'].date()}")
    
    # ========== PASS 2: Sequential portfolio simulation ==========
    print("\n" + "=" * 65)
    print("PASS 2: Simulating ₹1L sequential portfolio (compounding)...")
    print("=" * 65)
    
    capital = STARTING_CAPITAL
    in_trade = False
    current_symbol = None
    entry_price = 0.0
    entry_time = None
    target = 0.0
    qty = 0
    days_in_trade = 0
    current_time_stop = HORIZON_DAYS
    exit_available_date = None  # Earliest date we can enter a new trade
    
    trades = []
    
    # Walk through each signal chronologically
    for _, sig in signals_df.iterrows():
        
        # Skip if we're currently in a trade
        if in_trade:
            continue
        
        # Skip if this signal is before we're available (after exiting previous trade)
        if exit_available_date and sig['entry_date'] < exit_available_date:
            continue
        
        # === ENTER THE TRADE ===
        symbol = sig['symbol']
        df = stock_data[symbol]
        entry_price = sig['entry_price']
        entry_time = sig['entry_date']
        target = sig['target']
        qty = int(capital / entry_price)
        if qty == 0:
            continue
        
        in_trade = True
        days_in_trade = 0
        current_time_stop = HORIZON_DAYS
        
        invested = entry_price * qty
        print(f"\n  🟢 Trade #{len(trades)+1}: BUY {symbol} | ₹{entry_price:.2f} x {qty} = ₹{invested:,.0f} | Target: ₹{target:.2f} | Conf: {sig['confidence']:.1f}% | RS: +{sig['rs_score']*100:.1f}%")
        
        # === SIMULATE THE TRADE ===
        entry_iloc = df.index.get_loc(entry_time) if entry_time in df.index else None
        if entry_iloc is None:
            in_trade = False
            continue
        
        trade_closed = False
        for j in range(entry_iloc, len(df) - 1):
            days_in_trade += 1
            next_date = df.index[j + 1]
            next_row = df.iloc[j + 1]
            
            # Target Hit
            if next_row['high'] >= target:
                exit_p = target * (1 - SLIPPAGE_PCT)
                charges = calculate_costs(entry_price, exit_p, qty)
                gross = (exit_p - entry_price) * qty
                net = gross - charges
                capital += net
                trades.append({
                    'trade_num': len(trades) + 1, 'symbol': symbol,
                    'entry_time': entry_time, 'exit_time': next_date,
                    'days_held': days_in_trade, 'entry_price': entry_price,
                    'exit_price': exit_p, 'qty': qty, 'reason': 'Target Hit',
                    'gross_pnl': gross, 'charges': charges, 'net_pnl': net,
                    'capital_after': capital, 'win': 1 if net > 0 else 0
                })
                print(f"  ✅ TARGET HIT in {days_in_trade}d | P&L: ₹{net:+,.0f} | Capital: ₹{capital:,.0f}")
                exit_available_date = next_date
                in_trade = False
                trade_closed = True
                break
            
            # Dynamic Time Stop
            if days_in_trade >= current_time_stop:
                curr_date_ts = df.index[j]
                df_slice = df.loc[:curr_date_ts].copy()
                extend = False
                try:
                    analysis = analyze_stock(
                        symbol=f"{symbol}.NS",
                        df=df_slice.drop(columns=['ema_21', 'stock_return_63d'], errors='ignore'),
                        mode='balanced', timeframe='short', horizon='1month'
                    )
                    if "BUY" in analysis['recommendation'] or "HOLD" in analysis['recommendation']:
                        current_time_stop += 30
                        extend = True
                        print(f"  ⏳ Day {days_in_trade}: {symbol} extended to {current_time_stop}d (engine says HOLD)")
                except:
                    pass
                
                if not extend:
                    exit_p = next_row['close'] * (1 - SLIPPAGE_PCT)
                    charges = calculate_costs(entry_price, exit_p, qty)
                    gross = (exit_p - entry_price) * qty
                    net = gross - charges
                    capital += net
                    trades.append({
                        'trade_num': len(trades) + 1, 'symbol': symbol,
                        'entry_time': entry_time, 'exit_time': next_date,
                        'days_held': days_in_trade,
                        'entry_price': entry_price, 'exit_price': exit_p,
                        'qty': qty, 'reason': f'Time Stop ({current_time_stop}d)',
                        'gross_pnl': gross, 'charges': charges, 'net_pnl': net,
                        'capital_after': capital, 'win': 1 if net > 0 else 0
                    })
                    print(f"  ⏰ TIME STOP ({current_time_stop}d) | P&L: ₹{net:+,.0f} | Capital: ₹{capital:,.0f}")
                    exit_available_date = next_date
                    in_trade = False
                    trade_closed = True
                    break
        
        # If trade didn't close, close at end of data
        if not trade_closed and in_trade:
            last_date = df.index[-1]
            exit_p = df['close'].iloc[-1] * (1 - SLIPPAGE_PCT)
            charges = calculate_costs(entry_price, exit_p, qty)
            gross = (exit_p - entry_price) * qty
            net = gross - charges
            capital += net
            trades.append({
                'trade_num': len(trades) + 1, 'symbol': symbol,
                'entry_time': entry_time, 'exit_time': last_date,
                'days_held': days_in_trade, 'entry_price': entry_price,
                'exit_price': exit_p, 'qty': qty, 'reason': 'End of Backtest',
                'gross_pnl': gross, 'charges': charges, 'net_pnl': net,
                'capital_after': capital, 'win': 1 if net > 0 else 0
            })
            print(f"  📋 END OF BACKTEST | P&L: ₹{net:+,.0f} | Capital: ₹{capital:,.0f}")
            exit_available_date = last_date  # Capital is locked until this date!
            in_trade = False
    
    # ========== FINAL REPORT ==========
    if not trades:
        print("\nNo trades executed.")
        return
    
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf['win'] == 1]
    losses = tdf[tdf['win'] == 0]
    total_return = capital - STARTING_CAPITAL
    total_pct = (total_return / STARTING_CAPITAL) * 100
    total_trading_days = tdf['days_held'].sum()
    
    print("\n" + "=" * 65)
    print("💰 ₹1 LAKH SEQUENTIAL PORTFOLIO — FINAL RESULTS")
    print("=" * 65)
    print(f"Starting Capital:   ₹{STARTING_CAPITAL:>10,.0f}")
    print(f"Ending Capital:     ₹{capital:>10,.0f}")
    print(f"TOTAL RETURN:       ₹{total_return:>+10,.0f} ({total_pct:+.2f}%)")
    print(f"Period:             Jul 2024 → Jul 2025 (Upstox data)")
    print("-" * 65)
    print(f"Total Trades:       {len(tdf)}")
    print(f"Win Rate:           {(len(wins)/len(tdf))*100:.1f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Days in Trades:     {total_trading_days} / 187 trading days")
    print(f"Capital Utilization:{(total_trading_days/187)*100:.0f}%")
    print("-" * 65)
    print(f"Gross P&L:          ₹{tdf['gross_pnl'].sum():>+10,.0f}")
    print(f"Total Charges:      ₹{tdf['charges'].sum():>10,.0f}")
    print(f"NET P&L:            ₹{tdf['net_pnl'].sum():>+10,.0f}")
    print("-" * 65)
    if len(wins) > 0:
        print(f"Avg Win:            ₹{wins['net_pnl'].mean():>+10,.0f} ({(wins['net_pnl'].mean()/STARTING_CAPITAL)*100:+.1f}%)")
    if len(losses) > 0:
        print(f"Avg Loss:           ₹{losses['net_pnl'].mean():>+10,.0f} ({(losses['net_pnl'].mean()/STARTING_CAPITAL)*100:+.1f}%)")
    print(f"Max Win:            ₹{tdf['net_pnl'].max():>+10,.0f}")
    print(f"Max Loss:           ₹{tdf['net_pnl'].min():>+10,.0f}")
    print("=" * 65)
    
    print("\n📋 Complete Trade Journal:")
    print("-" * 110)
    for _, t in tdf.iterrows():
        m = "✅" if t['win'] else "❌"
        print(f"  {m} #{t['trade_num']:2d} | {t['symbol']:12s} | {str(t['entry_time'])[:10]} → {str(t['exit_time'])[:10]} | {t['days_held']:3d}d | ₹{t['net_pnl']:>+9,.0f} | Capital: ₹{t['capital_after']:>10,.0f} | {t['reason']}")
    
    print(f"\n📈 Capital Growth Journey (₹{STARTING_CAPITAL:,.0f} → ₹{capital:,.0f}):")
    for _, t in tdf.iterrows():
        bar_len = max(0, int((t['capital_after'] - 90000) / 1000))
        bar = "█" * bar_len
        print(f"  #{t['trade_num']:2d} {t['symbol']:12s} ₹{t['capital_after']:>10,.0f} {bar}")
    
    tdf.to_csv('backtest_1lakh_sequential_trades.csv', index=False)
    print(f"\nSaved to 'backtest_1lakh_sequential_trades.csv'")

if __name__ == "__main__":
    run_backtest()
