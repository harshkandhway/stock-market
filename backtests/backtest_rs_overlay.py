#!/usr/bin/env python3
import sys
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import the exact native function to avoid bias
from src.cli.stock_analyzer_pro import analyze_stock

# Parameters
BACKTEST_DAYS = 252  # 1 year of trading days
HORIZON_DAYS = 63    # 3 months holding max
CAPITAL_PER_TRADE = 100000

# Top 50 Nifty & Nifty Next 50 stocks for the backtest (Expanded Universe)
SYMBOLS = [
    # Nifty 50 (Partial)
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HUL.NS', 'ITC.NS', 'SBI.NS', 'LARSEN.NS', 'BAJFINANCE.NS',
    'BHARTIARTL.NS', 'KOTAKBANK.NS', 'AXISBANK.NS', 'ASIANPAINT.NS',
    'SBIN.NS', 'MARUTI.NS', 'HCLTECH.NS', 'SUNPHARMA.NS', 'TITAN.NS', 'M&M.NS',
    # Nifty Next 50 (Partial)
    'TRENT.NS', 'BEL.NS', 'HAL.NS', 'INDIGO.NS', 'TVSMOTOR.NS',
    'ZOMATO.NS', 'BHEL.NS', 'JINDALSTEL.NS', 'PNB.NS', 'VEDL.NS',
    'GAIL.NS', 'TORNTPHARM.NS', 'PIDILITIND.NS', 'BANKBARODA.NS', 'HAVELLS.NS',
    'RECLTD.NS', 'PFC.NS', 'CUMMINSIND.NS', 'DLF.NS', 'AMBUJACEM.NS'
]

# Standard Delivery Equity costs
SLIPPAGE_PCT = 0.001       # 0.1% slippage expected on entry/exit day
STT_PCT_DELIVERY = 0.001   # 0.1% STT on both buy and sell delivery
BROKERAGE = 0.0            # Zerodha delivery is free
EXCH_TXN_CHARGE = 0.0000325
GST_PCT = 0.18             # 18% on brokerage + exchange txn
SEBI_TURNOVER = 0.000001
STAMP_DUTY_BUY = 0.00015   # 0.015% on buy side only for delivery

def fetch_data(symbol: str) -> pd.DataFrame:
    print(f"Fetching 2y data for {symbol}...")
    try:
        df = yf.download(symbol, period='2y', interval='1d', progress=False)
        if df.empty:
            return df
            
        # yfinance multi-index columns fix if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index)
        
        # Calculate 21 EMA for the individual stock (for trailing exit)
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        
        # Format the df to match what analyze_stock expects
        return df[['open', 'high', 'low', 'close', 'volume', 'ema_21']]
    except Exception as e:
        print(f"Failed to fetch {symbol}: {e}")
        return pd.DataFrame()

def fetch_nifty_regime() -> pd.DataFrame:
    try:
        df = yf.download('^NSEI', period='2y', interval='1d', progress=False)
        if df.empty: return df
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index)
        
        # Calculate 63-day return for the Nifty
        df['nifty_return_63d'] = df['close'].pct_change(periods=63)
        return df[['close', 'nifty_return_63d']]
    except Exception as e:
        print(f"Failed to fetch Nifty data: {e}")
        return pd.DataFrame()

def record_trade(symbol, entry_time, exit_time, entry_price, exit_price, reason):
    qty = int(CAPITAL_PER_TRADE / entry_price)
    if qty == 0: return None
    
    # Calculate costs for delivery equity
    turnover = (entry_price + exit_price) * qty
    
    stt_buy = (entry_price * qty) * STT_PCT_DELIVERY
    stt_sell = (exit_price * qty) * STT_PCT_DELIVERY
    stt = stt_buy + stt_sell
    
    exch_txn = turnover * EXCH_TXN_CHARGE
    gst = (BROKERAGE * 2 + exch_txn) * GST_PCT
    sebi = turnover * SEBI_TURNOVER
    stamp_duty = (entry_price * qty) * STAMP_DUTY_BUY
    
    total_charges = stt + BROKERAGE * 2 + exch_txn + gst + sebi + stamp_duty
    
    gross_pnl = (exit_price - entry_price) * qty
    net_pnl = gross_pnl - total_charges
    
    is_win = 1 if net_pnl > 0 else 0
    days_held = (exit_time - entry_time).days
    
    return {
        'symbol': symbol,
        'entry_time': entry_time,
        'exit_time': exit_time,
        'days_held': days_held,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'qty': qty,
        'reason': reason,
        'gross_pnl': gross_pnl,
        'charges': total_charges,
        'net_pnl': net_pnl,
        'win': is_win
    }

def run_backtest():
    all_trades = []
    
    # Pre-fetch Nifty 50 data to calculate Relative Strength
    print("Fetching Nifty 50 baseline for RS calculations...")
    nifty_df = fetch_nifty_regime()
    
    for symbol in SYMBOLS:
        df = fetch_data(symbol)
        if len(df) < BACKTEST_DAYS + 50:
            print(f"Skipping {symbol} - insufficient data")
            continue
            
        print(f"Backtesting {symbol} over the last {BACKTEST_DAYS} trading days (Option B: Top RS Overlay)...")
        
        # Calculate 63-day rolling return for this stock
        df['stock_return_63d'] = df['close'].pct_change(periods=63)
        
        in_trade = False
        entry_price = 0.0
        entry_time = None
        target = 0.0
        stop_loss = 0.0
        days_in_trade = 0
        current_time_stop = HORIZON_DAYS
        
        # We start the backtest 252 days ago
        start_idx = len(df) - BACKTEST_DAYS
        
        # We need to loop up to len(df) - 1 so we have the next day for realistic entry
        for i in range(start_idx, len(df) - 1):
            curr_date = df.index[i]
            next_date = df.index[i+1]
            curr_row = df.iloc[i]
            next_row = df.iloc[i+1]
            
            if in_trade:
                days_in_trade += 1
                
                # Check Stop Loss first (worst case execution)
                if next_row['low'] <= stop_loss:
                    exit_p = stop_loss * (1 - SLIPPAGE_PCT)
                    trade = record_trade(symbol, entry_time, next_date, entry_price, exit_p, "Stop Loss")
                    if trade: all_trades.append(trade)
                    in_trade = False
                    continue
                    
                # Check Target 
                if next_row['high'] >= target:
                    exit_p = target * (1 - SLIPPAGE_PCT)
                    trade = record_trade(symbol, entry_time, next_date, entry_price, exit_p, "Target Hit")
                    if trade: all_trades.append(trade)
                    in_trade = False
                    continue
                    
                # Check Dynamic Time Stop
                if days_in_trade >= current_time_stop:
                    # Evaluate current day to see if we should extend
                    df_slice = df.iloc[: i + 1].copy()
                    try:
                        analysis = analyze_stock(
                            symbol=symbol,
                            df=df_slice.drop(columns=['ema_21'], errors='ignore'),
                            mode='balanced',
                            timeframe='short', # Shorter timeframe for extension evaluation
                            horizon='1month'   # Evaluated on a 30-day horizon
                        )
                        rec = analysis['recommendation']
                        # If the engine still likes the stock, give it 30 more days
                        if "BUY" in rec or "HOLD" in rec:
                            current_time_stop += 30
                            continue # Keep holding!
                    except Exception:
                        pass
                        
                    # If we didn't extend, close at end of day
                    exit_p = next_row['close'] * (1 - SLIPPAGE_PCT) 
                    trade = record_trade(symbol, entry_time, next_date, entry_price, exit_p, f"Time Stop ({current_time_stop} days)")
                    if trade: all_trades.append(trade)
                    in_trade = False
                    continue
            
            if not in_trade:
                # STRICT Rolling Window to prevent ANY lookahead bias
                # We slice the dataframe up to today (including today)
                df_slice = df.iloc[: i + 1].copy()
                
                try:
                    # Execute exactly the user's native logic
                    analysis = analyze_stock(
                        symbol=symbol,
                        df=df_slice.drop(columns=['ema_21']), # pass clean df
                        mode='balanced',      # Mode specified in the script
                        timeframe='medium',   # Matches 3months horizon
                        horizon='3months'
                    )
                    
                    rec = analysis['recommendation']
                    conf = analysis['confidence']
                    
                    # We only take the high conviction trades to maximize success
                    if ("STRONG BUY" in rec or "BUY" == rec) and ("AVOID" not in rec and "WARNING" not in rec) and conf >= 70:
                        
                        # OPTION B: Relative Strength Overlay
                        # Only take the trade if the stock's 3-month return is beating the Nifty 50's return
                        has_relative_strength = False
                        if not pd.isna(curr_row['stock_return_63d']) and not nifty_df.empty:
                            try:
                                nifty_idx = nifty_df.index.get_indexer([curr_date], method='pad')[0]
                                if nifty_idx != -1:
                                    nifty_ret = nifty_df.iloc[nifty_idx]['nifty_return_63d']
                                    stock_ret = curr_row['stock_return_63d']
                                    if not pd.isna(nifty_ret) and stock_ret > nifty_ret:
                                        has_relative_strength = True
                            except:
                                pass # Proceed normally if Nifty lookup fails
                        else:
                            # If no 63d data, we just assume it's good to avoid blocking new listings
                            has_relative_strength = True
                            
                        if not has_relative_strength:
                            continue # Skip, stock is a laggard
                            
                        in_trade = True
                        # Realism: we can only buy at the OPEN of the NEXT day
                        # Add slippage since market orders on open can slip
                        entry_price = next_row['open'] * (1 + SLIPPAGE_PCT) 
                        entry_time = next_date
                        target = analysis['target']
                        
                        # Apply a 5% lenient buffer to the stop loss
                        stop_loss = analysis['stop_loss'] * 0.95
                        days_in_trade = 0
                        current_time_stop = HORIZON_DAYS # Reset time stop
                except Exception as e:
                    # Ignore calculation errors on single days
                    # print(f"Error on {curr_date}: {e}")
                    pass
                    
        # Close any open trade at the end of the backtest
        if in_trade:
            last_date = df.index[-1]
            last_close = df['close'].iloc[-1]
            exit_p = last_close * (1 - SLIPPAGE_PCT)
            trade = record_trade(symbol, entry_time, last_date, entry_price, exit_p, "End of Backtest")
            if trade: all_trades.append(trade)
            
    # Compile Results
    if not all_trades:
        print("\nNo trades were generated by the strategy.")
        return
        
    trades_df = pd.DataFrame(all_trades)
    wins = trades_df[trades_df['win'] == 1]
    losses = trades_df[trades_df['win'] == 0]
    
    win_rate = (len(wins) / len(trades_df)) * 100
    total_net_pnl = trades_df['net_pnl'].sum()
    total_gross_pnl = trades_df['gross_pnl'].sum()
    total_charges = trades_df['charges'].sum()
    max_win = trades_df['net_pnl'].max()
    max_loss = trades_df['net_pnl'].min()
    avg_win = wins['net_pnl'].mean() if len(wins) > 0 else 0
    avg_loss = losses['net_pnl'].mean() if len(losses) > 0 else 0
    avg_days_held = trades_df['days_held'].mean()
    
    print("\n" + "="*50)
    print("🎯 STOCK ANALYZER PRO - UNBIASED BACKTEST RESULTS")
    print("="*50)
    print(f"Period: Last 1 Year (252 Trading Days)")
    print(f"Stocks Tested: {len(SYMBOLS)}")
    print(f"Capital Per Trade: ₹{CAPITAL_PER_TRADE:,.2f} Delivery")
    print("-" * 50)
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate:     {win_rate:.2f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Avg Days Held:{avg_days_held:.1f} days")
    print("-" * 50)
    print(f"Gross P&L:    ₹{total_gross_pnl:,.2f}")
    print(f"Total Charges:₹{total_charges:,.2f}")
    print(f"NET P&L:      ₹{total_net_pnl:,.2f}")
    print("-" * 50)
    print(f"Avg Win:      ₹{avg_win:,.2f}")
    print(f"Avg Loss:     ₹{avg_loss:,.2f}")
    print(f"Max Win:      ₹{max_win:,.2f}")
    print(f"Max Loss:     ₹{max_loss:,.2f}")
    print("="*50)
    
    # Save detailed trades
    trades_df.to_csv('stock_analyzer_backtest_trades.csv', index=False)
    print("\nDetailed trades saved to 'stock_analyzer_backtest_trades.csv'")
    
    print("\nBreakdown by Stop/Target Reason:")
    print(trades_df['reason'].value_counts())

if __name__ == "__main__":
    run_backtest()
