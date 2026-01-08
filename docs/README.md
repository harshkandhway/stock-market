# Stock Market Analyzer Pro

A professional-grade stock technical analysis tool using industry-standard indicators and risk management practices. Designed for traders and investors who want data-driven decision making with proper position sizing and risk controls.

**Developed by Harsh Kandhway**

**Main Tool:** `stock_analyzer_pro.py` - Professional analyzer with all advanced features (recommended for all use cases).

## Features

- **14+ Technical Indicators**: RSI, MACD, ADX, EMAs, Bollinger Bands, Stochastic, OBV, and more
- **Hard Filters**: Automatically blocks dangerous trades (e.g., RSI > 80, extreme overbought conditions)
- **Confidence Scoring**: 0-100% confidence level for each recommendation
- **3 Risk Modes**: Conservative, Balanced, and Aggressive with different risk/reward requirements
- **2 Timeframe Modes**: Short-term (1-4 weeks) and Medium-term (1-3 months) with optimized parameters
- **Position Sizing Calculator**: Professional 1% rule-based position sizing
- **Trailing Stop Strategies**: Dynamic stop loss management
- **Portfolio Analysis**: Rank stocks by confidence and get allocation suggestions
- **Risk/Reward Validation**: Ensures trades meet minimum R:R requirements

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install yahooquery ta pandas numpy
```

## Usage

### Basic Usage

**Recommended: Use Stock Analyzer Pro** (Professional version with advanced features)

Analyze default stocks (SILVERBEES.NS, GOLDBEES.NS):
```bash
python stock_analyzer_pro.py
```

Analyze a single stock:
```bash
python stock_analyzer_pro.py RELIANCE.NS
```

Analyze multiple stocks:
```bash
python stock_analyzer_pro.py TCS.NS INFY.NS WIPRO.NS
```

**Note:** The root-level `stock_analyzer_pro.py` is the main entry point. You can also use the direct path:
```bash
python src/cli/stock_analyzer_pro.py RELIANCE.NS
```

**Alternative: Basic Analyzer** (Simpler version without advanced risk management - not recommended)
```bash
python src/cli/stock_analyzer.py RELIANCE.NS
```

### Advanced Options

**Risk Modes:**
- `--mode conservative`: 0.5% risk/trade, 3:1 R:R minimum, fewer signals
- `--mode balanced`: 1% risk/trade, 2:1 R:R minimum (default)
- `--mode aggressive`: 2% risk/trade, 1.5:1 R:R minimum, more signals

**Timeframe Modes:**
- `--timeframe short`: Optimized for 1-4 week swing trades
- `--timeframe medium`: Optimized for 1-3 month position trades (default)

**Position Sizing:**
```bash
python stock_analyzer_pro.py RELIANCE.NS --capital 100000
```

**Portfolio Ranking:**
```bash
python stock_analyzer_pro.py TCS.NS INFY.NS WIPRO.NS --rank
```

**Portfolio Allocation:**
```bash
python stock_analyzer_pro.py TCS.NS INFY.NS WIPRO.NS --allocate --capital 500000
```

### Complete Examples

Conservative mode with short timeframe:
```bash
python stock_analyzer_pro.py RELIANCE.NS --mode conservative --timeframe short
```

Multiple stocks with ranking and allocation:
```bash
python stock_analyzer_pro.py TCS.NS INFY.NS WIPRO.NS --mode balanced --timeframe medium --rank --allocate --capital 500000
```

**Note:** All examples use `stock_analyzer_pro.py` - the professional analyzer with all advanced features including risk management, confidence scoring, and hard filters.

### Fetch Stock Tickers

To get a comprehensive list of Indian stock tickers:
```bash
python fetch_tickers.py
```

This will create `data/stock_tickers.csv` with all NSE and BSE stocks.

## Stock Symbol Format

- **NSE (National Stock Exchange)**: Add `.NS` suffix (e.g., `RELIANCE.NS`, `TCS.NS`)
- **BSE (Bombay Stock Exchange)**: Add `.BO` suffix (e.g., `RELIANCE.BO`)
- **US Stocks**: No suffix needed (e.g., `AAPL`, `MSFT`, `GOOGL`)

## Understanding the Output

### Recommendation Types

- **STRONG BUY**: High confidence (80%+), all filters passed
- **BUY**: Good confidence (65%+), favorable conditions
- **WEAK BUY**: Moderate confidence (55%+), some caution
- **HOLD**: Neutral conditions (40-50%)
- **WEAK SELL**: Moderate bearish (35%+)
- **SELL**: Bearish conditions (25%+)
- **STRONG SELL**: Very bearish (15%+)
- **BLOCKED**: Hard filters triggered, trade not recommended

### Confidence Levels

- **VERY HIGH**: 90-100%
- **HIGH**: 75-89%
- **MEDIUM**: 55-74%
- **LOW**: 35-54%
- **VERY LOW**: 0-34%

### Risk/Reward Ratio

The tool validates that each trade meets minimum risk/reward requirements:
- **Conservative**: Minimum 3:1 R:R
- **Balanced**: Minimum 2:1 R:R
- **Aggressive**: Minimum 1.5:1 R:R

If R:R is below the minimum, the trade is marked as invalid.

## Technical Indicators

### Trend Indicators (40% weight)
- Price vs Trend EMA (200/100 EMA)
- Price vs Medium EMA (50 EMA)
- EMA Alignment (Fast > Medium > Slow)
- ADX Trend Strength

### Momentum Indicators (35% weight)
- RSI Zone and Direction
- MACD Signal, Histogram, Zero Line
- Divergence Detection (RSI/MACD)

### Confirmation Indicators (25% weight)
- Volume Confirmation
- Volume Trend (OBV)
- Bollinger Band Position
- Support/Resistance Proximity

## Hard Filters

The tool automatically blocks trades when:

**Buy Blocked:**
- RSI > 80 (extremely overbought)
- Stochastic > 85
- Price above upper Bollinger Band
- Bearish divergence detected

**Sell Blocked:**
- RSI < 20 (extremely oversold)
- Stochastic < 15
- Price below lower Bollinger Band
- Bullish divergence detected

## Position Sizing

The tool uses the professional **1% Rule**:
- Never risk more than 1-2% of capital per trade (depending on mode)
- Position size = (Capital × Risk%) / (Entry - Stop Loss)
- Automatically calculates shares to buy and maximum loss

## Project Structure

```
stock-market/
├── src/                      # Source code
│   ├── core/                 # Core analysis modules
│   │   ├── config.py         # Configuration and thresholds
│   │   ├── indicators.py     # Technical indicator calculations
│   │   ├── signals.py        # Signal generation and scoring
│   │   ├── risk_management.py # Position sizing and risk management
│   │   └── output.py         # Report formatting
│   ├── cli/                  # Command-line interfaces
│   │   ├── stock_analyzer_pro.py # Main professional analyzer
│   │   ├── stock_analyzer.py # Basic analyzer
│   │   └── etf_analysis.py   # ETF-specific analysis
│   ├── data/                 # Data fetching utilities
│   │   └── fetch_stock_tickers.py
│   └── utils/                # Utility scripts
│       └── verify_calculations.py
├── data/                     # Data files
│   └── stock_tickers.csv     # List of Indian stock tickers
├── tests/                    # Unit tests
│   ├── test_indicators.py
│   ├── test_signals.py
│   ├── test_risk_management.py
│   └── (other test files)
├── docs/                     # Documentation
│   ├── README.md            # This file
│   └── AGENTS.md            # Agent guidelines
├── stock_analyzer_pro.py    # Main entry point (RECOMMENDED - Professional analyzer)
├── fetch_tickers.py         # Entry point for fetching tickers
└── requirements.txt         # Python dependencies
```

For detailed structure information, see `PROJECT_STRUCTURE.md` in the project root.

## Development

### Running Tests

The project includes comprehensive unit tests for all major components:

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_indicators.py

# Run with verbose output
python -m pytest tests/ -v

# Run with coverage report (requires pytest-cov)
python -m pytest tests/ --cov=. --cov-report=html
```

**Test Coverage:**
- `test_indicators.py` - Technical indicator calculations
- `test_signals.py` - Signal generation and scoring
- `test_risk_management.py` - Position sizing and risk management
- `test_config.py` - Configuration validation

**Note:** If you don't have pytest installed:
```bash
pip install pytest
```

### Code Style

- Python 3.9+ compatible
- Type hints required for all functions
- Docstrings required for all functions
- Follow PEP 8 style guide

## Limitations & Disclaimer

⚠️ **IMPORTANT DISCLAIMER:**

- This tool is for **educational purposes only**
- Past performance is **NOT** indicative of future results
- Always consult a SEBI-registered financial advisor before investing
- Never invest more than you can afford to lose
- Technical analysis is not a guarantee of future performance
- Use proper position sizing and risk management
- The tool relies on historical data and may not account for:
  - Breaking news
  - Market manipulation
  - Unusual events
  - Fundamental analysis factors

## License

This project is provided as-is for educational purposes.

## Support

For issues, questions, or contributions, please refer to the project repository.

## Version

Current Version: 2.0

---

**Remember**: The best traders often sit on their hands waiting for high-probability setups. Not every setup deserves your capital.

