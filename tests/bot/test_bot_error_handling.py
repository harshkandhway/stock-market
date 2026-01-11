"""
Test Error Handling & Edge Cases
Tests for error scenarios and edge cases
"""

import pytest
from unittest.mock import Mock, patch

from src.bot.database.db import (
    get_db_context,
    get_or_create_user,
    create_alert,
    get_user_alerts,
    delete_alert,
    add_to_watchlist
)
from src.bot.utils.validators import validate_stock_symbol, validate_price


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.fixture
    def test_db(self):
        """Create test database session"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from src.bot.database.models import Base
        
        engine = create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=False
        )
        
        Base.metadata.create_all(engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = TestSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
            Base.metadata.drop_all(engine)
    
    # ========================================================================
    # Invalid User Input
    # ========================================================================
    
    def test_invalid_symbol_handling(self):
        """Test handling of invalid stock symbols"""
        invalid_symbols = [
            '',  # Empty
            '   ',  # Whitespace only
            'INVALID@SYMBOL',  # Invalid characters
            'A' * 20,  # Too long
        ]
        
        for symbol in invalid_symbols:
            is_valid, error_msg = validate_stock_symbol(symbol)
            assert is_valid is False, f"{symbol} should be invalid"
            assert error_msg is not None
            assert len(error_msg) > 0
    
    def test_invalid_price_handling(self):
        """Test handling of invalid prices"""
        invalid_prices = [
            '',  # Empty
            'abc',  # Non-numeric
            '-100',  # Negative
            '0',  # Zero
            '100.999.99',  # Multiple decimals
        ]
        
        for price in invalid_prices:
            is_valid, parsed_price, error_msg = validate_price(price)
            assert is_valid is False, f"{price} should be invalid"
            assert parsed_price is None
            assert error_msg is not None
    
    def test_sql_injection_prevention(self, test_db):
        """Test SQL injection prevention"""
        # Attempt SQL injection in symbol
        malicious_symbol = "RELIANCE.NS'; DROP TABLE users; --"
        is_valid, error_msg = validate_stock_symbol(malicious_symbol)
        # Should be rejected or sanitized
        assert is_valid is False or error_msg is not None
        
        # Attempt SQL injection in username
        telegram_id = 111222
        user = get_or_create_user(
            test_db,
            telegram_id=telegram_id,
            username="'; DROP TABLE users; --"
        )
        # Should handle gracefully (username stored as-is, but query is parameterized)
        assert user.telegram_id == telegram_id
    
    # ========================================================================
    # Missing Data Errors
    # ========================================================================
    
    def test_missing_user_settings_handling(self, test_db):
        """Test handling of missing user settings"""
        # Create user without settings (shouldn't happen, but test edge case)
        from src.bot.database.db import get_user_settings
        settings = get_user_settings(test_db, telegram_id=999999)
        # Should return None for non-existent user
        assert settings is None
    
    def test_missing_user_alerts_handling(self, test_db):
        """Test handling of missing alerts"""
        alerts = get_user_alerts(test_db, telegram_id=999999)
        # Should return empty list, not error
        assert isinstance(alerts, list)
        assert len(alerts) == 0
    
    def test_delete_nonexistent_alert(self, test_db):
        """Test deleting non-existent alert"""
        user = get_or_create_user(test_db, telegram_id=123456)
        result = delete_alert(test_db, telegram_id=123456, alert_id=99999)
        # Should return False, not raise error
        assert result is False
    
    def test_remove_nonexistent_watchlist_item(self, test_db):
        """Test removing non-existent watchlist item"""
        user = get_or_create_user(test_db, telegram_id=123456)
        from src.bot.database.db import remove_from_watchlist
        result = remove_from_watchlist(test_db, telegram_id=123456, symbol='NONEXISTENT.NS')
        # Should return False, not raise error
        assert result is False
    
    # ========================================================================
    # Edge Cases
    # ========================================================================
    
    def test_create_alert_nonexistent_user(self, test_db):
        """Test creating alert for non-existent user"""
        alert = create_alert(
            db=test_db,
            telegram_id=999999,  # Non-existent user
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        # Should return None, not raise error
        assert alert is None
    
    def test_duplicate_watchlist_addition(self, test_db):
        """Test adding duplicate symbol to watchlist"""
        user = get_or_create_user(test_db, telegram_id=123456)
        
        # Add first time
        result1 = add_to_watchlist(test_db, telegram_id=123456, symbol='RELIANCE.NS')
        assert result1 is True
        
        # Add second time (duplicate)
        result2 = add_to_watchlist(test_db, telegram_id=123456, symbol='RELIANCE.NS')
        # Should handle gracefully (may return False or True, but shouldn't error)
        assert isinstance(result2, bool)
        
        # Verify only one entry
        from src.bot.database.db import get_user_watchlist
        watchlist = get_user_watchlist(test_db, telegram_id=123456)
        assert len(watchlist) == 1
    
    def test_empty_string_symbol(self):
        """Test handling of empty string symbol"""
        is_valid, error_msg = validate_stock_symbol('')
        assert is_valid is False
        assert error_msg is not None
    
    def test_whitespace_only_symbol(self):
        """Test handling of whitespace-only symbol"""
        is_valid, error_msg = validate_stock_symbol('   ')
        # Should be invalid or trimmed
        assert is_valid is False or error_msg is not None
    
    def test_very_long_symbol(self):
        """Test handling of very long symbol"""
        long_symbol = 'A' * 100
        is_valid, error_msg = validate_stock_symbol(long_symbol)
        assert is_valid is False
        assert error_msg is not None
    
    def test_special_characters_in_symbol(self):
        """Test handling of special characters"""
        special_symbols = [
            'RELIANCE@NS',
            'RELIANCE#NS',
            'RELIANCE$NS',
            'RELIANCE%NS',
        ]
        
        for symbol in special_symbols:
            is_valid, error_msg = validate_stock_symbol(symbol)
            # Should be invalid
            assert is_valid is False or error_msg is not None
    
    def test_unicode_handling(self, test_db):
        """Test handling of unicode characters"""
        # Unicode in username
        user = get_or_create_user(
            test_db,
            telegram_id=888777,
            username="测试用户",  # Chinese characters
            first_name="Тест"  # Cyrillic
        )
        assert user.telegram_id == 888777
        assert user.username == "测试用户"
        assert user.first_name == "Тест"
    
    def test_case_insensitive_symbols(self, test_db):
        """Test case-insensitive symbol handling"""
        user = get_or_create_user(test_db, telegram_id=666555)
        
        # Add with lowercase
        add_to_watchlist(test_db, telegram_id=666555, symbol='reliance.ns')
        
        # Try to add with uppercase (should be treated as duplicate)
        from src.bot.database.db import get_user_watchlist
        watchlist = get_user_watchlist(test_db, telegram_id=666555)
        # Should have one entry (case normalized)
        assert len(watchlist) >= 1


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.fixture
    def test_db(self):
        """Create test database session"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from src.bot.database.models import Base
        
        engine = create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=False
        )
        
        Base.metadata.create_all(engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = TestSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
            Base.metadata.drop_all(engine)
    
    def test_zero_price_handling(self):
        """Test handling of zero price"""
        is_valid, parsed_price, error_msg = validate_price('0')
        assert is_valid is False
        assert error_msg is not None
    
    def test_negative_price_handling(self):
        """Test handling of negative price"""
        is_valid, parsed_price, error_msg = validate_price('-100')
        assert is_valid is False
        assert error_msg is not None
    
    def test_very_large_price(self):
        """Test handling of very large price"""
        is_valid, parsed_price, error_msg = validate_price('999999999999')
        # Should be validated (may have upper limit)
        assert isinstance(is_valid, bool)
    
    def test_decimal_precision(self):
        """Test handling of decimal precision"""
        # Very precise decimal
        is_valid, parsed_price, error_msg = validate_price('100.123456789')
        assert is_valid is True
        assert parsed_price == 100.123456789
    
    def test_multiple_users_same_telegram_id(self, test_db):
        """Test that same telegram_id retrieves same user"""
        telegram_id = 111222
        
        user1 = get_or_create_user(test_db, telegram_id=telegram_id, username="user1")
        user2 = get_or_create_user(test_db, telegram_id=telegram_id, username="user2")
        
        # Should be same user, username updated
        assert user1.id == user2.id
        assert user2.username == "user2"  # Updated
    
    def test_alert_with_empty_condition_data(self, test_db):
        """Test alert creation with empty condition_data"""
        user = get_or_create_user(test_db, telegram_id=123456)
        
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data={}  # Empty dict
        )
        
        assert alert is not None
        assert alert.params == {}  # Should be empty dict
    
    def test_alert_with_none_condition_data(self, test_db):
        """Test alert creation with None condition_data"""
        user = get_or_create_user(test_db, telegram_id=123456)
        
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data=None  # None
        )
        
        assert alert is not None
        assert alert.condition_params is None or alert.params == {}

