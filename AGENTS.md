# Stock Market Analyzer Pro - Agent Guidelines

## Build & Run Commands
```bash
pip install yahooquery ta pandas numpy       # Install dependencies
python3 stock_analyzer_pro.py                # Default (SILVERBEES.NS, GOLDBEES.NS)
python3 stock_analyzer_pro.py RELIANCE.NS    # Single stock analysis
python3 stock_analyzer_pro.py TCS.NS INFY.NS # Multiple stocks

# With options
python3 stock_analyzer_pro.py RELIANCE.NS --mode conservative --timeframe short
python3 stock_analyzer_pro.py TCS.NS --capital 100000
python3 stock_analyzer_pro.py INFY.NS WIPRO.NS --rank --allocate --capital 500000
```

## Risk Modes
- **conservative**: 0.5% risk/trade, 3:1 R:R min, fewer signals, maximum protection
- **balanced**: 1% risk/trade, 2:1 R:R min, standard professional approach
- **aggressive**: 2% risk/trade, 1.5:1 R:R min, more signals, experienced traders

## Timeframe Modes
- **short**: 1-4 weeks (RSI-9, EMA-9/21/50/100, faster indicators)
- **medium**: 1-3 months (RSI-14, EMA-20/50/100/200, standard indicators)

## Code Style
- **Python 3.9+** compatible (use `Optional[]` not `|` union types)
- **Imports**: stdlib → third-party → local (separated by blank lines)
- **Types**: Required for all function params and returns
- **Docstrings**: Required for all functions (triple quotes, one-line summary)
- **Error handling**: try/except with specific exceptions, return empty DataFrame on failure

## Data Sources
- **Yahoo Finance API** via `yahooquery` library (NOT yfinance)
- Ticker format: NSE=`.NS`, BSE=`.BO`, US=no suffix (e.g., `AAPL`)
- Always flatten MultiIndex DataFrames from yahooquery responses

## File Structure
- `config.py` - Mode configurations, thresholds, signal weights
- `indicators.py` - Technical indicator calculations (14+ indicators)
- `signals.py` - Signal scoring, hard filters, confidence calculation
- `risk_management.py` - Position sizing, stops, targets, trailing stops
- `output.py` - Report formatting and display
- `stock_analyzer_pro.py` - Main CLI entry point
