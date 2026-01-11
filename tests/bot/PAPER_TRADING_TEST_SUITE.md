# Paper Trading System - Comprehensive Test Suite

## Overview

This test suite provides comprehensive coverage for the entire paper trading system, including:
- Market hours detection
- Portfolio management
- Trade execution
- Position monitoring
- Pending trades (queue system)
- Scheduler tasks
- Command and callback handlers
- End-to-end integration flows

## Test Files

### 1. `test_paper_trading_market_hours.py`
**Purpose:** Tests market hours service functionality

**Coverage:**
- Market open/closed detection
- Weekend handling
- Holiday recognition
- Timezone handling
- Next market open/close calculations
- All 2026 holidays

**Key Tests:**
- `test_is_market_open_weekday_during_hours` - Market open during trading hours
- `test_is_market_open_saturday` - Market closed on weekends
- `test_is_market_open_republic_day` - Holiday recognition
- `test_get_next_market_open_friday_after_hours` - Weekend skip logic
- `test_all_holidays_recognized` - All holidays validated

### 2. `test_paper_trading_services.py`
**Purpose:** Tests core paper trading services

**Coverage:**
- Paper portfolio service (position sizing, capital management)
- Paper trade execution service (entry/exit validation)
- Paper trading service (session management)
- Paper trade analysis service (performance metrics)

**Key Tests:**
- `test_calculate_position_size_1_percent_rule` - 1% risk rule
- `test_calculate_position_size_max_position_cap` - 20% position cap
- `test_validate_entry_duplicate_symbol` - Duplicate prevention
- `test_validate_entry_price_drift` - Price drift validation
- `test_analyze_winning_trades` - Winner analysis
- `test_analyze_losing_trades` - Loser analysis

### 3. `test_paper_trading_pending_trades.py`
**Purpose:** Tests pending trade queue system

**Coverage:**
- PendingPaperTrade model
- Queue functionality
- Execution of pending trades
- Edge cases (duplicates, inactive sessions, existing positions)

**Key Tests:**
- `test_create_pending_trade` - Model creation
- `test_queue_trade_when_market_closed` - Queue on market closed
- `test_execute_pending_trade_success` - Successful execution
- `test_execute_pending_trade_validation_fails` - Validation failure handling
- `test_execute_pending_trade_already_has_position` - Duplicate prevention
- `test_execute_multiple_pending_trades` - Batch execution

### 4. `test_paper_trading_handlers.py`
**Purpose:** Tests command and callback handlers

**Coverage:**
- Command handlers (`/papertrade start`, `status`, etc.)
- Callback handlers (button clicks)
- Market open/closed scenarios
- Error handling

**Key Tests:**
- `test_papertrade_start_command_new_session` - Start new session
- `test_papertrade_start_command_existing_session` - Prevent duplicates
- `test_papertrade_status_command` - Status display
- `test_handle_papertrade_stock_confirm_market_open` - Execute when open
- `test_handle_papertrade_stock_confirm_market_closed` - Queue when closed
- `test_handle_papertrade_stock_confirm_no_buy_signal` - Reject non-BUY signals

### 5. `test_paper_trading_scheduler.py`
**Purpose:** Tests scheduler tasks and timing

**Coverage:**
- Scheduler start/stop
- BUY execution task
- Position monitoring task
- Daily/weekly summary tasks
- Pending trades execution
- Market hours integration

**Key Tests:**
- `test_scheduler_start` - Scheduler initialization
- `test_execute_pending_trades_no_pending` - Empty queue handling
- `test_execute_buy_signals` - Signal execution
- `test_monitor_positions` - Position monitoring
- `test_run_position_monitoring_task_market_open` - Market open monitoring
- `test_run_position_monitoring_task_market_closed` - Market closed handling

### 6. `test_paper_trading_integration.py`
**Purpose:** Integration tests for trading flows

**Coverage:**
- Complete trading cycles
- Position limit enforcement
- Capital management
- Multi-position scenarios

**Key Tests:**
- `test_complete_trading_cycle` - Full cycle test
- `test_position_limit_enforcement` - Limit validation
- `test_capital_management` - Capital tracking

### 7. `test_paper_trading_comprehensive.py`
**Purpose:** End-to-end comprehensive tests

**Coverage:**
- Complete trading flows with real database
- Multiple positions
- Stop loss exits
- Capital tracking
- Session management

**Key Tests:**
- `test_complete_trading_cycle` - Full E2E cycle
- `test_multiple_positions_management` - Multi-position handling
- `test_stop_loss_exit` - Stop loss execution
- `test_capital_tracking` - Capital flow tracking

## Running Tests

### Run All Paper Trading Tests
```bash
# From project root
pytest tests/bot/test_paper_trading_*.py -v
```

### Run Specific Test File
```bash
pytest tests/bot/test_paper_trading_market_hours.py -v
```

### Run Specific Test
```bash
pytest tests/bot/test_paper_trading_market_hours.py::TestMarketHoursService::test_is_market_open_weekday_during_hours -v
```

### Run with Coverage
```bash
pytest tests/bot/test_paper_trading_*.py \
    --cov=src.bot.services.paper_trading \
    --cov=src.bot.services.market_hours_service \
    --cov=src.bot.services.paper_portfolio_service \
    --cov=src.bot.services.paper_trade_execution_service \
    --cov=src.bot.services.paper_trade_analysis_service \
    --cov=src.bot.services.paper_trading_scheduler \
    --cov-report=term-missing \
    --cov-report=html
```

### Use Test Runner Script
```bash
# Run all tests
python tests/bot/run_paper_trading_tests.py

# Run with coverage
python tests/bot/run_paper_trading_tests.py --coverage
```

## Test Coverage Goals

- **Market Hours Service:** 95%+ coverage
- **Portfolio Service:** 90%+ coverage
- **Execution Service:** 90%+ coverage
- **Trading Service:** 85%+ coverage
- **Analysis Service:** 85%+ coverage
- **Scheduler:** 80%+ coverage
- **Handlers:** 80%+ coverage

## Test Categories

### Unit Tests
- Individual service methods
- Model validation
- Calculation accuracy
- Edge cases

### Integration Tests
- Service interactions
- Database operations
- Multi-step flows

### End-to-End Tests
- Complete trading cycles
- Real database scenarios
- User interaction flows

## Test Fixtures

All tests use fixtures from `tests/conftest.py`:
- `test_db` - In-memory SQLite database
- `mock_user` - Mock Telegram user
- `mock_message` - Mock Telegram message
- `mock_query` - Mock callback query
- `mock_context` - Mock bot context

## Writing New Tests

When adding new functionality:

1. **Add unit tests** for new service methods
2. **Add integration tests** for service interactions
3. **Add handler tests** for new commands/callbacks
4. **Update comprehensive tests** for new flows
5. **Maintain coverage** above target thresholds

### Test Template
```python
@pytest.mark.asyncio
async def test_new_feature(self, test_db, test_user):
    """Test description"""
    # Arrange
    # ... setup ...
    
    # Act
    # ... execute ...
    
    # Assert
    # ... verify ...
```

## Known Issues

- Some async tests may require event loop configuration
- Database fixtures use in-memory SQLite (may differ from production)
- Market hours tests use fixed dates (update for new years)

## Maintenance

- Update holiday list in market hours tests annually
- Review and update test data for new requirements
- Maintain test coverage reports
- Update integration tests when APIs change

## Test Results

View test results:
- Console output (pytest default)
- HTML coverage report: `htmlcov/index.html`
- JUnit XML: `pytest --junitxml=results.xml`

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- Fast execution (< 2 minutes)
- No external dependencies
- Deterministic results
- Clear failure messages


