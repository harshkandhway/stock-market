# Project Structure

This document explains the folder structure of the Stock Market Analyzer Pro project.

## Overview

```
stock-market/
├── src/                          # Source code
│   ├── core/                     # Core analysis modules
│   │   ├── __init__.py          # Package initialization
│   │   ├── config.py            # Configuration (risk modes, timeframes, thresholds)
│   │   ├── indicators.py        # Technical indicator calculations
│   │   ├── signals.py           # Signal generation and scoring
│   │   ├── risk_management.py   # Position sizing, stops, targets
│   │   └── output.py            # Report formatting and display
│   │
│   ├── cli/                      # Command-line interface scripts
│   │   ├── __init__.py
│   │   ├── stock_analyzer_pro.py # Main professional analyzer
│   │   ├── stock_analyzer.py     # Basic analyzer
│   │   └── etf_analysis.py      # ETF-specific analysis
│   │
│   ├── data/                     # Data fetching utilities
│   │   ├── __init__.py
│   │   └── fetch_stock_tickers.py # Fetch stock tickers from NSE/BSE
│   │
│   └── utils/                    # Utility scripts
│       ├── __init__.py
│       └── verify_calculations.py # Calculation verification tool
│
├── data/                         # Data files
│   └── stock_tickers.csv         # List of Indian stock tickers (NSE & BSE)
│
├── tests/                        # Unit tests
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_indicators.py
│   ├── test_signals.py
│   ├── test_risk_management.py
│   ├── test_calculation_accuracy.py
│   ├── test_data_validation.py
│   ├── test_position_size_capital_constraint.py
│   └── test_real_market_data.py
│
├── docs/                         # Documentation
│   ├── README.md                 # Main documentation
│   ├── AGENTS.md                 # Agent guidelines
│   ├── FIXES_SUMMARY.md          # Fixes and improvements
│   ├── RCA_ANALYSIS.md           # Root cause analysis
│   ├── REAL_MARKET_TEST_RESULTS.md
│   └── REAL_MARKET_TESTING_SUMMARY.md
│
├── stock_analyzer_pro.py        # Main entry point (RECOMMENDED - Professional analyzer)
├── fetch_tickers.py             # Entry point for fetching tickers
├── requirements.txt             # Python dependencies
└── PROJECT_STRUCTURE.md         # This file
```

## Flow of Execution

### 1. **Entry Points** (Root Level)
- `stock_analyzer_pro.py` - **Main entry point** for professional stock analysis (RECOMMENDED)
- `fetch_tickers.py` - Entry point for fetching stock tickers

### 2. **Core Analysis Flow** (`src/core/`)
1. **config.py** - Defines all configuration:
   - Risk modes (conservative, balanced, aggressive)
   - Timeframe configs (short, medium)
   - Signal weights and thresholds
   - Hard filters

2. **indicators.py** - Calculates technical indicators:
   - EMAs, SMAs
   - RSI, MACD, ADX
   - Bollinger Bands, ATR
   - Support/Resistance levels
   - Fibonacci levels
   - Volume indicators

3. **signals.py** - Generates trading signals:
   - Trend signals
   - Momentum signals
   - Confirmation signals
   - Hard filter checks
   - Confidence calculation
   - Recommendation determination

4. **risk_management.py** - Manages risk:
   - Position sizing
   - Stop loss calculation
   - Target price calculation
   - Risk/reward validation
   - Trailing stops
   - Portfolio allocation

5. **output.py** - Formats and displays results:
   - Full analysis reports
   - Summary tables
   - Portfolio rankings
   - Portfolio allocations

### 3. **CLI Scripts** (`src/cli/`)
- `stock_analyzer_pro.py` - **Professional analyzer** with all advanced features (RECOMMENDED)
- `stock_analyzer.py` - Basic analyzer (simpler version - not recommended)
- `etf_analysis.py` - ETF-specific analysis

### 4. **Data Management** (`src/data/`)
- `fetch_stock_tickers.py` - Fetches comprehensive list of Indian stocks from NSE/BSE

### 5. **Utilities** (`src/utils/`)
- `verify_calculations.py` - Verifies calculation accuracy

## Usage Examples

### Analyze Stocks
```bash
# From project root (RECOMMENDED)
python stock_analyzer_pro.py RELIANCE.NS TCS.NS

# Or directly
python src/cli/stock_analyzer_pro.py RELIANCE.NS --mode conservative
```

### Fetch Stock Tickers
```bash
# From project root
python fetch_tickers.py

# Or directly
python src/data/fetch_stock_tickers.py --output data/stock_tickers.csv
```

### Run Tests
```bash
python -m pytest tests/
# or
python -m unittest discover tests
```

## Key Design Principles

1. **Separation of Concerns**: Each module has a single, clear responsibility
2. **Modularity**: Core modules can be imported and used independently
3. **Testability**: All modules have corresponding test files
4. **Maintainability**: Clear folder structure makes it easy to find and modify code
5. **Extensibility**: Easy to add new indicators, signals, or risk management strategies

## Import Structure

All imports use absolute paths from the `src` package:

```python
from src.core.config import RISK_MODES, TIMEFRAME_CONFIGS
from src.core.indicators import calculate_all_indicators
from src.core.signals import calculate_all_signals
from src.core.risk_management import calculate_position_size
```

This ensures that:
- Code works regardless of where it's called from
- Imports are explicit and clear
- No circular dependencies
- Easy to understand module relationships

