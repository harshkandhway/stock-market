# Bot Production Testing Plan

## Overview
This document outlines a comprehensive testing strategy to make the Telegram bot production-ready. The plan is organized by priority, component, and test type.

**Status**: 🟡 In Progress  
**Last Updated**: 2026-01-09  
**Target Completion**: Before Production Release

---

## Testing Strategy

### Test Types
1. **Unit Tests**: Test individual functions/methods in isolation
2. **Integration Tests**: Test interactions between components
3. **End-to-End Tests**: Test complete user workflows
4. **Error Handling Tests**: Test error scenarios and edge cases
5. **Performance Tests**: Test response times and resource usage
6. **Security Tests**: Test authorization, input validation, SQL injection

### Priority Levels
- 🔴 **CRITICAL**: Must pass before production (blocking issues)
- 🟠 **HIGH**: Should pass before production (major features)
- 🟡 **MEDIUM**: Important but not blocking (nice-to-have features)
- 🟢 **LOW**: Can be deferred (minor improvements)

---

## Phase 1: Critical Database Tests 🔴

### 1.1 Database Models Tests
**File**: `tests/test_bot_database_models.py`

#### Test Cases:
- [ ] **test_user_model_creation**
  - Create user with all required fields
  - Verify relationships (settings, watchlist, alerts, portfolio)
  - Test cascade deletes
  - Test unique constraint on telegram_id

- [ ] **test_user_settings_model**
  - Create default settings for new user
  - Update settings and verify persistence
  - Test relationship with User model

- [ ] **test_alert_model**
  - Create alert with all types (price, rsi, signal_change)
  - Test `params` hybrid property (get/set)
  - Verify condition_params JSON serialization
  - Test relationships with User

- [ ] **test_watchlist_model**
  - Add/remove symbols
  - Test unique constraint (user_id, symbol)
  - Verify relationship with User

- [ ] **test_portfolio_model**
  - Create portfolio entries
  - Test calculations and relationships

- [ ] **test_analysis_cache_model**
  - Cache creation and expiration
  - Cache retrieval and validation

### 1.2 Database Operations Tests
**File**: `tests/test_bot_database_operations.py`

#### Test Cases:
- [ ] **test_get_or_create_user**
  - Create new user
  - Retrieve existing user
  - Update user information
  - Create default settings for new user

- [ ] **test_user_settings_operations**
  - Get user settings
  - Update risk mode, timeframe, horizon, capital
  - Reset settings to defaults
  - Handle missing settings gracefully

- [ ] **test_watchlist_operations**
  - Add symbol to watchlist
  - Remove symbol from watchlist
  - Get user watchlist
  - Handle duplicate additions
  - Handle removal of non-existent symbols

- [ ] **test_alert_operations**
  - Create price alert (above/below)
  - Create RSI alert
  - Create signal change alert
  - Get user alerts (active/all)
  - Delete alert
  - Clear all alerts
  - Update alert status
  - Update alert last_checked timestamp
  - **CRITICAL**: Verify `telegram_id` vs `user_id` usage
  - **CRITICAL**: Verify `condition_params` vs `condition_data` usage

- [ ] **test_portfolio_operations**
  - Add portfolio entry
  - Update portfolio entry
  - Get user portfolio
  - Delete portfolio entry

- [ ] **test_analysis_cache_operations**
  - Store analysis cache
  - Retrieve valid cache
  - Handle expired cache
  - Clear cache

### 1.3 Database Relationship Tests
**File**: `tests/test_bot_database_relationships.py`

#### Test Cases:
- [ ] **test_user_cascade_deletes**
  - Delete user → settings deleted
  - Delete user → watchlist deleted
  - Delete user → alerts deleted
  - Delete user → portfolio deleted

- [ ] **test_alert_user_relationship**
  - Create alert and verify user relationship
  - Access `alert.user.telegram_id` (not `alert.user_id`)
  - Test eager loading with joinedload

- [ ] **test_watchlist_user_relationship**
  - Verify user relationship in watchlist queries

---

## Phase 2: Critical Handler Tests 🔴

### 2.1 Command Handler Tests
**File**: `tests/test_bot_handlers_commands.py`

#### Start/Help Handlers:
- [ ] **test_start_command**
  - New user welcome message
  - Existing user welcome message
  - Verify user creation in database
  - Test authorization check

- [ ] **test_help_command**
  - Display all available commands
  - Format verification

- [ ] **test_menu_command**
  - Display main menu
  - Keyboard buttons present

- [ ] **test_unknown_command**
  - Handle unknown commands gracefully
  - Provide helpful error message

#### Analyze Handlers:
- [ ] **test_analyze_command_valid_symbol**
  - Valid symbol analysis
  - Verify analysis format
  - Check database cache usage
  - Verify inline keyboard buttons

- [ ] **test_analyze_command_invalid_symbol**
  - Invalid symbol handling
  - Error message format

- [ ] **test_analyze_command_missing_symbol**
  - Usage instructions
  - Example format

- [ ] **test_quick_analyze_command**
  - Quick analysis format
  - Reduced information display

#### Watchlist Handlers:
- [ ] **test_watchlist_command_empty**
  - Empty watchlist message
  - Add symbol instructions

- [ ] **test_watchlist_command_with_symbols**
  - Display watchlist
  - Format verification
  - Action buttons present

#### Settings Handlers:
- [ ] **test_settings_command**
  - Display current settings
  - Settings menu keyboard

- [ ] **test_setmode_command**
  - Update risk mode
  - Verify database update
  - Success message

- [ ] **test_settimeframe_command**
  - Update timeframe
  - Verify database update

- [ ] **test_sethorizon_command**
  - Update investment horizon
  - Verify database update

- [ ] **test_setcapital_command**
  - Update capital
  - Input validation
  - Verify database update

- [ ] **test_reset_settings_command**
  - Reset to defaults
  - Verify all settings reset

#### Alert Handlers:
- [ ] **test_alerts_command_empty**
  - Empty alerts message

- [ ] **test_alerts_command_with_alerts**
  - Display all alerts
  - Format verification
  - Delete buttons present

- [ ] **test_alert_command_valid_symbol**
  - Show alert type selection
  - Keyboard present

- [ ] **test_alert_command_invalid_symbol**
  - Error message
  - Validation

- [ ] **test_deletealert_command**
  - Delete alert by ID
  - Success/error messages
  - Verify database deletion

- [ ] **test_clearalerts_command**
  - Clear all alerts
  - Confirmation flow
  - Verify database cleanup

#### Compare Handler:
- [ ] **test_compare_command**
  - Compare two symbols
  - Format verification
  - Handle invalid symbols

#### Search Handler:
- [ ] **test_search_command**
  - Search for symbols
  - Results display
  - No results handling

#### Backtest Handler:
- [ ] **test_backtest_command**
  - Run backtest
  - Results format
  - Error handling

#### Portfolio Handler:
- [ ] **test_portfolio_command**
  - Display portfolio
  - Empty portfolio handling

#### Schedule Handler:
- [ ] **test_schedule_command**
  - Schedule report
  - Display scheduled reports

### 2.2 Callback Handler Tests
**File**: `tests/test_bot_handlers_callbacks.py`

#### Test Cases:
- [ ] **test_handle_callback_query_invalid_format**
  - Invalid callback data format
  - Error handling

- [ ] **test_watchlist_callbacks**
  - `watchlist_add` callback
  - `watchlist_remove` callback
  - `watchlist_menu` callback
  - Verify database operations

- [ ] **test_alert_callbacks**
  - `alert_menu` callback
  - `alert_price` callback
  - `alert_rsi` callback
  - `alert_signal` callback
  - **CRITICAL**: Verify alert creation with correct parameters
  - **CRITICAL**: Test `telegram_id` vs `user_id` usage
  - `alert_delete` callback
  - `alert_clear` callback

- [ ] **test_settings_callbacks**
  - `settings_mode` callback
  - `settings_timeframe` callback
  - `settings_horizon` callback
  - Verify database updates

- [ ] **test_analyze_callbacks**
  - `analyze_quick` callback
  - `analyze_full` callback
  - `analyze_watchlist` callback

- [ ] **test_backtest_callbacks**
  - `backtest_run` callback
  - Results display

- [ ] **test_compare_callbacks**
  - `compare_symbols` callback

---

## Phase 3: Critical Service Tests 🔴

### 3.1 Alert Service Tests
**File**: `tests/test_bot_alert_service.py`

#### Test Cases:
- [ ] **test_alert_service_initialization**
  - Service starts correctly
  - Bot instance stored

- [ ] **test_check_all_alerts_query**
  - Query all active alerts
  - Eager load user relationship
  - **CRITICAL**: Verify `joinedload(Alert.user)` usage

- [ ] **test_check_price_alert_above**
  - Price above threshold triggers
  - Price below threshold doesn't trigger
  - **CRITICAL**: Use `alert.params` not `alert.condition`

- [ ] **test_check_price_alert_below**
  - Price below threshold triggers
  - Price above threshold doesn't trigger

- [ ] **test_check_rsi_alert_overbought**
  - RSI > 70 triggers
  - RSI < 70 doesn't trigger
  - **CRITICAL**: Use `alert.params` not `alert.condition`

- [ ] **test_check_rsi_alert_oversold**
  - RSI < 30 triggers
  - RSI > 30 doesn't trigger

- [ ] **test_check_signal_change_alert_first_check**
  - First check stores recommendation
  - Doesn't trigger on first check
  - **CRITICAL**: Verify `condition_params` update in database

- [ ] **test_check_signal_change_alert_change_detected**
  - Recommendation change triggers alert
  - Updates last_recommendation in database
  - **CRITICAL**: Verify proper database session handling

- [ ] **test_check_signal_change_alert_no_change**
  - Same recommendation doesn't trigger
  - Updates last_checked timestamp

- [ ] **test_send_alert_notification_price**
  - Format price alert message
  - **CRITICAL**: Use `alert.user.telegram_id` not `alert.user_id`
  - Send to correct user

- [ ] **test_send_alert_notification_rsi**
  - Format RSI alert message
  - Include current RSI value

- [ ] **test_send_alert_notification_signal_change**
  - Format signal change message
  - Include new recommendation and confidence

- [ ] **test_alert_service_error_handling**
  - Handle API errors gracefully
  - Continue checking other alerts on error
  - Log errors appropriately

- [ ] **test_alert_deactivation_on_trigger**
  - Alert deactivated after trigger
  - Trigger count incremented
  - Triggered_at timestamp set

### 3.2 Analysis Service Tests
**File**: `tests/test_bot_analysis_service.py`

#### Test Cases:
- [ ] **test_analyze_stock_success**
  - Valid symbol analysis
  - Returns correct structure
  - Includes all required fields

- [ ] **test_analyze_stock_invalid_symbol**
  - Invalid symbol handling
  - Error message format

- [ ] **test_get_current_price**
  - Valid symbol price retrieval
  - Invalid symbol handling

- [ ] **test_analysis_caching**
  - Cache creation
  - Cache retrieval
  - Cache expiration

### 3.3 Backtest Service Tests
**File**: `tests/test_bot_backtest_service.py`

#### Test Cases:
- [ ] **test_backtest_execution**
  - Valid parameters
  - Results format
  - Performance metrics

- [ ] **test_backtest_error_handling**
  - Invalid parameters
  - API errors

### 3.4 Report Service Tests
**File**: `tests/test_bot_report_service.py`

#### Test Cases:
- [ ] **test_scheduled_report_creation**
  - Create scheduled report
  - Verify database storage

- [ ] **test_scheduled_report_sending**
  - Send scheduled reports
  - Handle multiple users

---

## Phase 4: Critical Utility Tests 🔴

### 4.1 Validator Tests
**File**: `tests/test_bot_validators.py`

#### Test Cases:
- [ ] **test_validate_stock_symbol_valid**
  - Valid NSE symbols (RELIANCE.NS, TCS.NS)
  - Valid BSE symbols
  - Returns (True, None)

- [ ] **test_validate_stock_symbol_invalid**
  - Invalid formats
  - Missing exchange suffix
  - Returns (False, error_message)

- [ ] **test_validate_price_valid**
  - Valid price values
  - Positive numbers
  - Decimal values

- [ ] **test_validate_price_invalid**
  - Negative prices
  - Zero prices
  - Non-numeric values
  - Returns (False, error_message)

- [ ] **test_parse_command_args**
  - Single argument
  - Multiple arguments
  - Empty arguments
  - Whitespace handling

### 4.2 Formatter Tests
**File**: `tests/test_bot_formatters.py`

#### Test Cases:
- [ ] **test_format_success**
  - Success message format
  - Emoji inclusion

- [ ] **test_format_error**
  - Error message format
  - Emoji inclusion

- [ ] **test_format_warning**
  - Warning message format

- [ ] **test_format_watchlist**
  - Empty watchlist format
  - Watchlist with symbols format

- [ ] **test_format_alert**
  - Price alert format
  - RSI alert format
  - Signal change alert format

- [ ] **test_chunk_message**
  - Long message splitting
  - Telegram message length limits (4096 chars)

### 4.3 Keyboard Tests
**File**: `tests/test_bot_keyboards.py`

#### Test Cases:
- [ ] **test_create_watchlist_menu_keyboard**
  - Correct buttons
  - Callback data format

- [ ] **test_create_alert_type_keyboard**
  - Alert type buttons
  - Symbol in callback data

- [ ] **test_create_settings_menu_keyboard**
  - Settings options
  - Current values displayed

- [ ] **test_create_back_button**
  - Back button creation
  - Correct callback data

---

## Phase 5: Integration Tests 🔴

### 5.1 End-to-End Workflow Tests
**File**: `tests/test_bot_e2e_workflows.py`

#### Test Cases:
- [ ] **test_complete_analysis_workflow**
  1. User sends `/start`
  2. User sends `/analyze RELIANCE.NS`
  3. User clicks "Add to Watchlist"
  4. User sends `/watchlist`
  5. Verify watchlist contains symbol

- [ ] **test_complete_alert_workflow**
  1. User sends `/analyze NIFTYBEES.NS`
  2. User clicks "Set Alert" → "Signal Change"
  3. Verify alert created in database
  4. Simulate signal change
  5. Verify alert triggers
  6. Verify notification sent

- [ ] **test_complete_settings_workflow**
  1. User sends `/settings`
  2. User clicks "Risk Mode" → "Aggressive"
  3. Verify database update
  4. User sends `/settings`
  5. Verify new mode displayed

- [ ] **test_complete_watchlist_workflow**
  1. User sends `/watchlist`
  2. User clicks "Add Symbol"
  3. User enters symbol
  4. Verify symbol added
  5. User clicks "Remove" on symbol
  6. Verify symbol removed

### 5.2 Database-Handler Integration Tests
**File**: `tests/test_bot_database_handler_integration.py`

#### Test Cases:
- [ ] **test_handler_database_consistency**
  - Handlers use correct database functions
  - **CRITICAL**: Verify `telegram_id` usage throughout
  - **CRITICAL**: Verify `user_id` only for foreign keys

- [ ] **test_alert_creation_integration**
  - Handler creates alert
  - Service can query alert
  - Alert has correct user relationship

- [ ] **test_user_creation_integration**
  - Handler creates user
  - Settings created automatically
  - User can be queried by telegram_id

---

## Phase 6: Error Handling & Edge Cases 🟠

### 6.1 Error Handling Tests
**File**: `tests/test_bot_error_handling.py`

#### Test Cases:
- [ ] **test_database_connection_errors**
  - Handle database unavailable
  - Graceful error messages
  - Service continues operating

- [ ] **test_api_errors**
  - Handle yfinance API errors
  - Handle network timeouts
  - Retry logic

- [ ] **test_telegram_api_errors**
  - Handle rate limits
  - Handle blocked users
  - Handle message too long

- [ ] **test_invalid_user_input**
  - Malformed commands
  - Invalid symbols
  - Invalid prices
  - SQL injection attempts

- [ ] **test_missing_data_errors**
  - Missing user settings
  - Missing cache data
  - Missing stock data

### 6.2 Edge Case Tests
**File**: `tests/test_bot_edge_cases.py`

#### Test Cases:
- [ ] **test_concurrent_alert_checks**
  - Multiple alerts checked simultaneously
  - No race conditions
  - Database consistency

- [ ] **test_large_watchlist**
  - 100+ symbols in watchlist
  - Performance acceptable
  - Message chunking works

- [ ] **test_many_alerts**
  - 50+ active alerts
  - All checked within interval
  - Performance acceptable

- [ ] **test_special_characters**
  - Symbols with special characters
  - User names with special characters
  - Message formatting

- [ ] **test_unicode_handling**
  - Unicode symbols
  - Unicode in messages
  - Database storage

---

## Phase 7: Performance Tests 🟡

### 7.1 Performance Benchmarks
**File**: `tests/test_bot_performance.py`

#### Test Cases:
- [ ] **test_alert_check_performance**
  - 100 alerts checked in < 30 seconds
  - Database queries optimized
  - No N+1 query problems

- [ ] **test_analysis_response_time**
  - Analysis completes in < 10 seconds
  - Caching improves performance

- [ ] **test_database_query_performance**
  - User queries < 100ms
  - Alert queries < 200ms
  - Watchlist queries < 100ms

- [ ] **test_message_sending_performance**
  - Messages sent in < 2 seconds
  - Batch operations efficient

---

## Phase 8: Security Tests 🟠

### 8.1 Security Validation Tests
**File**: `tests/test_bot_security.py`

#### Test Cases:
- [ ] **test_authorization_checks**
  - Unauthorized users blocked
  - Admin-only commands protected
  - User data isolation

- [ ] **test_sql_injection_prevention**
  - SQL injection attempts fail
  - Parameterized queries used
  - Input sanitization

- [ ] **test_input_validation**
  - Malicious input rejected
  - XSS prevention
  - Command injection prevention

- [ ] **test_user_data_isolation**
  - Users can't access other users' data
  - Alerts isolated by user
  - Watchlist isolated by user

---

## Phase 9: Scheduler & Background Tasks 🟠

### 9.1 Scheduler Tests
**File**: `tests/test_bot_scheduler.py`

#### Test Cases:
- [ ] **test_alert_scheduler_startup**
  - Scheduler starts on bot init
  - Jobs registered correctly
  - Interval configured correctly

- [ ] **test_alert_scheduler_execution**
  - Jobs execute on schedule
  - No duplicate executions
  - Error handling doesn't stop scheduler

- [ ] **test_scheduled_reports_execution**
  - Reports sent on schedule
  - Multiple users handled
  - Timezone handling

- [ ] **test_scheduler_shutdown**
  - Graceful shutdown
  - Jobs stopped correctly

---

## Phase 10: Configuration & Environment Tests 🟡

### 10.1 Configuration Tests
**File**: `tests/test_bot_configuration.py`

#### Test Cases:
- [ ] **test_config_validation**
  - Required config present
  - Config values valid
  - Environment variables loaded

- [ ] **test_database_config**
  - Database URL valid
  - Connection successful
  - Migrations applied

- [ ] **test_telegram_config**
  - Bot token valid
  - Admin IDs configured
  - Rate limits configured

---

## Test Execution Plan

### Step 1: Setup Test Infrastructure
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock

# Create test database
python -m src.bot.database.db init_db --test

# Run initial test suite
pytest tests/ -v
```

### Step 2: Execute Tests by Phase

#### Phase 1: Database Tests (Priority: CRITICAL)
```bash
pytest tests/test_bot_database_*.py -v --cov=src/bot/database
```
**Expected**: 100% pass rate, >80% coverage

#### Phase 2: Handler Tests (Priority: CRITICAL)
```bash
pytest tests/test_bot_handlers_*.py -v --cov=src/bot/handlers
```
**Expected**: 100% pass rate, >80% coverage

#### Phase 3: Service Tests (Priority: CRITICAL)
```bash
pytest tests/test_bot_*_service.py -v --cov=src/bot/services
```
**Expected**: 100% pass rate, >80% coverage

#### Phase 4: Utility Tests (Priority: CRITICAL)
```bash
pytest tests/test_bot_utils.py -v --cov=src/bot/utils
```
**Expected**: 100% pass rate, >90% coverage

#### Phase 5: Integration Tests (Priority: CRITICAL)
```bash
pytest tests/test_bot_e2e_*.py tests/test_bot_*_integration.py -v
```
**Expected**: 100% pass rate

#### Phase 6-10: Additional Tests
```bash
pytest tests/test_bot_*.py -v --cov=src/bot
```
**Expected**: >95% pass rate, >75% overall coverage

### Step 3: Continuous Testing
```bash
# Run all tests before commits
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src/bot --cov-report=html

# Run specific test file
pytest tests/test_bot_alert_service.py -v

# Run tests matching pattern
pytest tests/ -k "alert" -v
```

---

## Known Issues to Test

### Critical Issues Fixed (Verify in Tests)
1. ✅ `alert.condition` → `alert.params` (8 occurrences)
2. ✅ `alert.user_id` → `alert.user.telegram_id` for sending messages
3. ✅ `condition_data` → `condition_params` in Alert model
4. ✅ Signal change alert database updates
5. ✅ Eager loading of user relationship in alert queries

### Potential Issues to Test
- [ ] All callback handlers use correct parameter names
- [ ] All database functions use `telegram_id` correctly
- [ ] All alert operations use `condition_params` correctly
- [ ] All user relationships loaded efficiently
- [ ] No hardcoded user IDs or test data in production code

---

## Test Coverage Goals

### Minimum Coverage (Production Ready)
- **Database Layer**: >90%
- **Handlers**: >85%
- **Services**: >85%
- **Utils**: >90%
- **Overall**: >80%

### Target Coverage (Ideal)
- **Database Layer**: >95%
- **Handlers**: >90%
- **Services**: >90%
- **Utils**: >95%
- **Overall**: >85%

---

## Test Data Management

### Test Database
- Use separate test database (`bot_test.db`)
- Reset database before each test suite
- Use fixtures for common test data

### Mocking Strategy
- Mock external APIs (yfinance, Telegram)
- Use real database for integration tests
- Mock time-dependent functions (datetime)

---

## Test Checklist Before Production

### Pre-Production Checklist
- [ ] All CRITICAL tests passing (100%)
- [ ] All HIGH priority tests passing (>95%)
- [ ] Code coverage >80%
- [ ] No known blocking issues
- [ ] All error scenarios tested
- [ ] Performance benchmarks met
- [ ] Security tests passing
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Documentation updated

### Production Readiness Criteria
- ✅ All Phase 1-5 tests passing
- ✅ >80% code coverage
- ✅ No critical bugs
- ✅ Performance acceptable
- ✅ Security validated
- ✅ Error handling robust

---

## Maintenance Plan

### Ongoing Testing
1. **Before each release**: Run full test suite
2. **After bug fixes**: Add regression tests
3. **Weekly**: Run performance benchmarks
4. **Monthly**: Review and update test coverage

### Test Maintenance
- Update tests when features change
- Remove obsolete tests
- Add tests for new features
- Review test coverage quarterly

---

## Notes

### Test Environment
- Use test Telegram bot token
- Use test database
- Mock external services
- Use test data files

### Test Execution Time
- Unit tests: < 1 minute
- Integration tests: < 5 minutes
- Full suite: < 10 minutes

### Continuous Integration
- Run tests on every commit
- Block merges if tests fail
- Generate coverage reports
- Track test metrics

---

## Contact & Support

For questions about this testing plan:
- Review test files in `tests/` directory
- Check test execution logs
- Review coverage reports
- Update this document as needed

---

**Last Updated**: 2026-01-09  
**Next Review**: After Phase 1 completion

