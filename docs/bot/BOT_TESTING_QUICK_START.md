# Bot Testing Quick Start Guide

## Quick Setup

```bash
# 1. Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock

# 2. Verify installation
pytest --version

# 3. Run existing tests
pytest tests/ -v

# 4. Check coverage
pytest tests/ --cov=src/bot --cov-report=term-missing
```

## Test Execution Order (Recommended)

### Day 1: Database Tests (CRITICAL)
```bash
# Create test files
touch tests/test_bot_database_models.py
touch tests/test_bot_database_operations.py
touch tests/test_bot_database_relationships.py

# Run tests
pytest tests/test_bot_database_*.py -v
```

### Day 2: Handler Tests (CRITICAL)
```bash
# Create test files
touch tests/test_bot_handlers_commands.py
touch tests/test_bot_handlers_callbacks.py

# Run tests
pytest tests/test_bot_handlers_*.py -v
```

### Day 3: Service Tests (CRITICAL)
```bash
# Create test files
touch tests/test_bot_alert_service.py
touch tests/test_bot_analysis_service.py

# Run tests
pytest tests/test_bot_*_service.py -v
```

### Day 4: Utility Tests (CRITICAL)
```bash
# Create test files
touch tests/test_bot_validators.py
touch tests/test_bot_formatters.py
touch tests/test_bot_keyboards.py

# Run tests
pytest tests/test_bot_*.py -v
```

### Day 5: Integration Tests (CRITICAL)
```bash
# Create test files
touch tests/test_bot_e2e_workflows.py
touch tests/test_bot_database_handler_integration.py

# Run tests
pytest tests/test_bot_*_integration.py tests/test_bot_e2e_*.py -v
```

## Common Test Patterns

### Database Test Pattern
```python
import pytest
from src.bot.database.db import get_db_context, get_or_create_user
from src.bot.database.models import User, Alert

def test_create_user():
    with get_db_context() as db:
        user = get_or_create_user(db, telegram_id=123456, username="test")
        assert user.telegram_id == 123456
        assert user.username == "test"
        assert user.settings is not None
```

### Handler Test Pattern
```python
import pytest
from unittest.mock import Mock, AsyncMock
from telegram import Update, Message, User, Chat
from src.bot.handlers.start import start_command

@pytest.mark.asyncio
async def test_start_command():
    update = Mock(spec=Update)
    update.message = Mock(spec=Message)
    update.message.from_user = Mock(spec=User)
    update.message.from_user.id = 123456
    update.message.reply_text = AsyncMock()
    
    context = Mock()
    
    await start_command(update, context)
    
    assert update.message.reply_text.called
```

### Service Test Pattern
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.bot.services.alert_service import AlertService

@pytest.mark.asyncio
async def test_check_price_alert():
    bot = Mock()
    service = AlertService(bot)
    
    # Create mock alert
    alert = Mock()
    alert.alert_type = 'price'
    alert.params = {'operator': '>', 'value': 100.0}
    alert.symbol = 'RELIANCE.NS'
    
    with patch('src.bot.services.alert_service.get_current_price', return_value=150.0):
        result = await service._check_price_alert(alert)
        assert result is True
```

## Critical Test Cases to Write First

### 1. Database: Alert Creation
```python
def test_create_alert_with_correct_parameters():
    """CRITICAL: Verify alert creation uses correct parameter names"""
    with get_db_context() as db:
        user = get_or_create_user(db, telegram_id=123456)
        alert = create_alert(
            db=db,
            telegram_id=123456,  # NOT user_id
            symbol='RELIANCE.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data={}  # Will be stored as condition_params
        )
        assert alert.user_id == user.id  # Foreign key
        assert alert.user.telegram_id == 123456  # For sending messages
        assert alert.condition_params is not None
```

### 2. Service: Alert Checking
```python
@pytest.mark.asyncio
async def test_alert_service_uses_params_not_condition():
    """CRITICAL: Verify alert service uses alert.params not alert.condition"""
    bot = Mock()
    service = AlertService(bot)
    
    alert = Mock()
    alert.alert_type = 'price'
    alert.params = {'operator': '>', 'value': 100.0}  # Correct
    alert.condition = None  # Should not be used
    
    # Should not raise AttributeError
    result = await service._check_price_alert(alert)
```

### 3. Service: User Relationship
```python
@pytest.mark.asyncio
async def test_alert_notification_uses_telegram_id():
    """CRITICAL: Verify notifications use telegram_id not user_id"""
    bot = Mock()
    bot.send_message = AsyncMock()
    service = AlertService(bot)
    
    alert = Mock()
    alert.user = Mock()
    alert.user.telegram_id = 123456  # For sending
    alert.user_id = 1  # Database foreign key
    
    await service._send_alert_notification(alert)
    
    bot.send_message.assert_called_with(
        chat_id=123456,  # telegram_id, not user_id
        text=Mock(),
        parse_mode='Markdown'
    )
```

## Running Specific Tests

```bash
# Run single test file
pytest tests/test_bot_database_models.py -v

# Run single test function
pytest tests/test_bot_database_models.py::test_user_model_creation -v

# Run tests matching pattern
pytest tests/ -k "alert" -v

# Run with coverage
pytest tests/test_bot_alert_service.py --cov=src/bot/services/alert_service -v

# Run with output
pytest tests/ -v -s

# Run and stop on first failure
pytest tests/ -x

# Run last failed tests
pytest tests/ --lf
```

## Debugging Failed Tests

```bash
# Run with verbose output and print statements
pytest tests/ -v -s

# Run with pdb debugger on failure
pytest tests/ --pdb

# Run with detailed traceback
pytest tests/ -vv

# Show local variables on failure
pytest tests/ -l
```

## Test Coverage

```bash
# Generate coverage report
pytest tests/ --cov=src/bot --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser

# Check coverage for specific module
pytest tests/ --cov=src/bot/database --cov-report=term-missing
```

## Common Issues & Solutions

### Issue: Database locked
**Solution**: Use separate test database
```python
# In conftest.py
@pytest.fixture
def test_db():
    # Use in-memory SQLite for tests
    engine = create_engine('sqlite:///:memory:')
    # ...
```

### Issue: Async test failures
**Solution**: Use pytest-asyncio
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    # Your async test
    pass
```

### Issue: Mock not working
**Solution**: Patch at correct location
```python
# Patch where it's used, not where it's defined
with patch('src.bot.services.alert_service.get_current_price'):
    # ...
```

## Next Steps

1. Start with Phase 1 (Database Tests)
2. Write tests for each component
3. Run tests frequently
4. Fix issues as they're found
5. Aim for >80% coverage before production

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- Main testing plan: `BOT_PRODUCTION_TESTING_PLAN.md`

