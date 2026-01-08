# Stock Market Analyzer Pro - Agent Guidelines

## Build & Run Commands

**Use Stock Analyzer Pro** (Professional version with all advanced features - RECOMMENDED)

```bash
pip install yahooquery ta pandas numpy       # Install dependencies

# Main entry point (RECOMMENDED)
python stock_analyzer_pro.py                 # Default (SILVERBEES.NS, GOLDBEES.NS)
python stock_analyzer_pro.py RELIANCE.NS    # Single stock analysis
python stock_analyzer_pro.py TCS.NS INFY.NS # Multiple stocks

# With options
python stock_analyzer_pro.py RELIANCE.NS --mode conservative --timeframe short
python stock_analyzer_pro.py TCS.NS --capital 100000
python stock_analyzer_pro.py INFY.NS WIPRO.NS --rank --allocate --capital 500000

# Or use direct path
python src/cli/stock_analyzer_pro.py RELIANCE.NS --mode balanced

# Fetch stock tickers
python fetch_tickers.py                     # Generate stock_tickers.csv
```

**Note:** Always use `stock_analyzer_pro.py` for professional analysis. The basic analyzer (`src/cli/stock_analyzer.py`) is a simpler alternative without advanced risk management features.

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
- `src/core/config.py` - Mode configurations, thresholds, signal weights
- `src/core/indicators.py` - Technical indicator calculations (14+ indicators)
- `src/core/signals.py` - Signal scoring, hard filters, confidence calculation
- `src/core/risk_management.py` - Position sizing, stops, targets, trailing stops
- `src/core/output.py` - Report formatting and display
- `src/cli/stock_analyzer_pro.py` - **Main professional CLI** (has all advanced features)
- `src/cli/stock_analyzer.py` - Basic analyzer (simpler version - not recommended)
- `stock_analyzer_pro.py` - **Root-level entry point** (RECOMMENDED - runs the professional analyzer)
- `fetch_tickers.py` - Root-level entry point for fetching tickers

**Important:** Always use `stock_analyzer_pro.py` (root level or `src/cli/`) for professional analysis with risk management, confidence scoring, and hard filters.

See `PROJECT_STRUCTURE.md` for complete folder structure.
