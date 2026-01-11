# Tests Directory

This directory contains all test files organized by category for better maintainability and navigation.

## 📁 Test Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration and fixtures
├── __init__.py                  # Package initialization
│
├── core/                        # Core module tests (10 files)
│   ├── test_config.py
│   ├── test_indicators.py
│   ├── test_signals.py
│   ├── test_risk_management.py
│   ├── test_output.py
│   ├── test_data_validation.py
│   ├── test_calculation_accuracy.py
│   ├── test_position_size_capital_constraint.py
│   └── test_real_market_data.py
│
├── bot/                         # Bot-related tests (15+ files)
│   ├── test_bot_alert_service.py
│   ├── test_bot_callbacks.py
│   ├── test_bot_database_handler_integration.py
│   ├── test_bot_database_operations.py
│   ├── test_bot_database_operations_template.py
│   ├── test_bot_error_handling.py
│   ├── test_bot_handlers_callbacks.py
│   ├── test_bot_handlers_commands.py
│   ├── test_bot_handlers_features.py
│   ├── test_bot_integration.py
│   ├── test_bot_utils_formatters.py
│   ├── test_bot_utils_keyboards.py
│   ├── test_bot_utils_validators.py
│   ├── test_analysis_service.py
│   ├── test_backtest_service.py
│   ├── test_portfolio_service.py
│   ├── test_cli.py
│   ├── test_360one_fix.py
│   └── test_daily_buy_alerts.py
│
├── integration/                 # Integration tests (3 files)
│   ├── test_handlers.py
│   ├── test_all_stocks_comprehensive.py
│   └── test_coalindia.py
│
├── validation/                  # Validation and verification tests (5 files)
│   ├── test_detailed_validation.py
│   ├── test_final_verification.py
│   ├── test_fix_verification.py
│   ├── test_professional_alignment.py
│   └── test_recommendation_logic.py
│
├── reports/                     # Test output reports
│   └── test_report_*.txt        # Generated test reports
│
└── utils/                       # Test utilities
    └── run_async_tests.py       # Async test runner
```

## 🧪 Running Tests

### Run All Tests
```bash
# From project root
pytest tests/

# Or with coverage
pytest tests/ --cov=src --cov-report=html
```

### Run Tests by Category

**Core Module Tests:**
```bash
pytest tests/core/
```

**Bot Tests:**
```bash
pytest tests/bot/
```

**Integration Tests:**
```bash
pytest tests/integration/
```

**Validation Tests:**
```bash
pytest tests/validation/
```

### Run Specific Test Files
```bash
# Single test file
pytest tests/core/test_indicators.py

# Specific test function
pytest tests/core/test_indicators.py::test_rsi_calculation
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=src --cov-report=term-missing
```

## 📊 Test Categories

### Core Tests (`tests/core/`)
Tests for core analysis modules:
- **test_config.py** - Configuration validation
- **test_indicators.py** - Technical indicator calculations
- **test_signals.py** - Signal generation and scoring
- **test_risk_management.py** - Position sizing and risk management
- **test_output.py** - Report formatting
- **test_data_validation.py** - Data validation
- **test_calculation_accuracy.py** - Calculation verification
- **test_position_size_capital_constraint.py** - Position sizing edge cases
- **test_real_market_data.py** - Real market data testing

### Bot Tests (`tests/bot/`)
Tests for Telegram bot functionality:
- **Handler Tests** - Command and callback handlers
- **Service Tests** - Analysis, alert, portfolio services
- **Database Tests** - Database operations and models
- **Utility Tests** - Formatters, keyboards, validators
- **Integration Tests** - Bot integration scenarios
- **Error Handling** - Error handling and edge cases

### Integration Tests (`tests/integration/`)
End-to-end integration tests:
- **test_handlers.py** - Handler integration
- **test_all_stocks_comprehensive.py** - Comprehensive stock testing
- **test_coalindia.py** - Specific stock integration test

### Validation Tests (`tests/validation/`)
Validation and verification tests:
- **test_detailed_validation.py** - Detailed validation scenarios
- **test_final_verification.py** - Final verification checks
- **test_fix_verification.py** - Fix verification
- **test_professional_alignment.py** - Professional alignment validation
- **test_recommendation_logic.py** - Recommendation logic validation

## 🔧 Test Utilities

### `tests/utils/run_async_tests.py`
Utility script for running async tests. Usage:
```bash
python tests/utils/run_async_tests.py
```

## 📝 Test Reports

Test output reports are stored in `tests/reports/`:
- `test_report_*.txt` - Generated test reports with timestamps

## 🎯 Test Coverage Goals

- **Core Modules:** 90%+ coverage
- **Bot Handlers:** 85%+ coverage
- **Services:** 80%+ coverage
- **Integration:** Critical paths covered

## 📋 Writing New Tests

When adding new tests:

1. **Place in appropriate directory:**
   - Core module tests → `tests/core/`
   - Bot tests → `tests/bot/`
   - Integration tests → `tests/integration/`
   - Validation tests → `tests/validation/`

2. **Follow naming convention:**
   - Test files: `test_*.py`
   - Test functions: `test_*`
   - Test classes: `Test*`

3. **Use fixtures from `conftest.py`:**
   - Database fixtures
   - Mock data fixtures
   - Common test utilities

4. **Add docstrings:**
   - Describe what the test validates
   - Include expected behavior

## 🐛 Debugging Tests

### Run with PDB (Python Debugger)
```bash
pytest tests/ --pdb
```

### Run with Print Statements
```bash
pytest tests/ -s
```

### Run Specific Test with Verbose Output
```bash
pytest tests/core/test_indicators.py::test_rsi_calculation -v -s
```

## 📚 Related Documentation

- **Testing Plan:** See `docs/testing/TESTING_PLAN.md`
- **Test Results:** See `docs/testing/` for test results and analysis
- **Coverage Reports:** Generated in `htmlcov/` after running with `--cov-report=html`

## 🔄 Test Organization History

Tests were reorganized from scattered files in root directory to this structured format for:
- Better maintainability
- Easier navigation
- Clear categorization
- Improved test discovery

---

*Last updated: January 2025*


