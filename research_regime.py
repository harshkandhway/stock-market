import pandas as pd
import numpy as np
import os

CACHE_DIR = "data/upstox_cache"
f = os.path.join(CACHE_DIR, "NIFTY50_2024-06-01_2025-07-01.csv")

if not os.path.exists(f):
    print("File not found")
    exit(1)

df = pd.read_csv(f, parse_dates=['date'], index_col='date')
# Ensure df sorted by date
df = df.sort_index()

# Strip timezone if present
df.index = df.index.tz_localize(None)

# MAs
df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

# RSI 14
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss.replace(0, np.nan)
df['rsi_14'] = 100 - (100 / (1 + rs))

# MACD (12, 26, 9)
ema_12 = df['close'].ewm(span=12, adjust=False).mean()
ema_26 = df['close'].ewm(span=26, adjust=False).mean()
df['macd'] = ema_12 - ema_26
df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
df['macd_hist'] = df['macd'] - df['macd_signal']

# Print specific dates
start = pd.Timestamp("2025-03-01")
end = pd.Timestamp("2025-04-30")

sub_df = df.loc[start:end]

print("Date       | Close    | EMA-21   | EMA-50   | RSI 14 | MACD Hist |")
print("-" * 65)
for index, row in sub_df.iterrows():
    print(f"{index.date()} | {row['close']:8.2f} | {row['ema_21']:8.2f} | {row['ema_50']:8.2f} | {row['rsi_14']:6.2f} | {row['macd_hist']:9.2f} |")
