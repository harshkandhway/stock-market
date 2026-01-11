"""
Template Test File for Bot Database Operations
Copy this file and rename to test_bot_database_operations.py

This file contains critical tests for database operations,
focusing on the issues we've identified:
- telegram_id vs user_id usage
- condition_params vs condition_data
- Alert model relationships
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.bot.database.db import (
    get_db_context,
    get_or_create_user,
    get_user_settings,
    update_user_settings,
    add_to_watchlist,
    remove_from_watchlist,
    get_user_watchlist,
    create_alert,
    get_user_alerts,
    delete_alert,
    update_alert_status,
    update_alert_last_checked,
    clear_user_alerts
)
from src.bot.database.models import User, Alert, Watchlist, UserSettings


class TestDatabaseOperations:
    """Test database operations with focus on critical issues"""
    
    @pytest.fixture
    def test_db(self):
        """Create test database session"""
        # TODO: Set up test database
        # Use in-memory SQLite or separate test database
        with get_db_context() as db:
            yield db
    
    @pytest.fixture
    def test_user(self, test_db):
        """Create test user"""
        return get_or_create_user(
            test_db,
            telegram_id=123456,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
    
    # ========================================================================
    # CRITICAL: User Operations - telegram_id vs user_id
    # ========================================================================
    
    def test_get_or_create_user_creates_with_telegram_id(self, test_db):
        """CRITICAL: Verify user creation uses telegram_id"""
        user = get_or_create_user(
            test_db,
            telegram_id=789012,
            username="newuser"
        )
        
        assert user.telegram_id == 789012  # Telegram ID
        assert user.id is not None  # Database primary key
        assert user.username == "newuser"
        assert user.settings is not None  # Default settings created
    
    def test_get_or_create_user_retrieves_existing(self, test_db, test_user):
        """Verify existing user retrieval"""
        user = get_or_create_user(
            test_db,
            telegram_id=123456,
            username="updated_username"
        )
        
        assert user.id == test_user.id  # Same user
        assert user.telegram_id == 123456
        assert user.username == "updated_username"  # Updated
    
    def test_user_settings_created_automatically(self, test_db):
        """Verify default settings created for new user"""
        user = get_or_create_user(
            test_db,
            telegram_id=999999,
            username="settings_test"
        )
        
        assert user.settings is not None
        assert user.settings.risk_mode == 'balanced'  # Default
        assert user.settings.timeframe == 'medium'  # Default
    
    # ========================================================================
    # CRITICAL: Alert Operations - Parameter Names
    # ========================================================================
    
    def test_create_alert_uses_telegram_id_not_user_id(self, test_db, test_user):
        """CRITICAL: create_alert must accept telegram_id, not user_id"""
        alert = create_alert(
            db=test_db,
            telegram_id=123456,  # ✅ CORRECT: telegram_id
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        assert alert is not None
        assert alert.user_id == test_user.id  # Foreign key to users.id
        assert alert.user.telegram_id == 123456  # For sending messages
        assert alert.symbol == 'RELIANCE.NS'
    
    def test_create_alert_stores_condition_params(self, test_db, test_user):
        """CRITICAL: Alert stores condition_data as condition_params"""
        condition_data = {'operator': '>', 'value': 100.0}
        
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='TCS.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data=condition_data
        )
        
        # Verify condition_params (database field) contains JSON
        assert alert.condition_params is not None
        assert isinstance(alert.condition_params, str)  # JSON string
        
        # Verify params property (hybrid property) works
        params = alert.params
        assert isinstance(params, dict)
        assert params['operator'] == '>'
        assert params['value'] == 100.0
    
    def test_create_signal_change_alert(self, test_db, test_user):
        """CRITICAL: Test signal change alert creation"""
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='NIFTYBEES.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data={}  # Empty initially, will store last_recommendation
        )
        
        assert alert.alert_type == 'signal_change'
        assert alert.condition_type == 'change'
        assert alert.params == {}  # Initially empty
    
    def test_create_rsi_alert(self, test_db, test_user):
        """Test RSI alert creation"""
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='INFY.NS',
            alert_type='rsi',
            condition_type='below',
            threshold_value=30.0,
            condition_data={'operator': '<', 'value': 30}
        )
        
        assert alert.alert_type == 'rsi'
        assert alert.condition_type == 'below'
        assert alert.threshold_value == 30.0
        assert alert.params['value'] == 30
    
    def test_get_user_alerts_returns_correct_alerts(self, test_db, test_user):
        """Verify get_user_alerts returns alerts for correct user"""
        # Create alerts for test user
        alert1 = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        # Create another user and alert
        other_user = get_or_create_user(test_db, telegram_id=999999)
        alert2 = create_alert(
            db=test_db,
            telegram_id=999999,
            symbol='TCS.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=200.0,
            condition_data={'operator': '>', 'value': 200.0}
        )
        
        # Get alerts for test user
        alerts = get_user_alerts(test_db, telegram_id=123456)
        
        assert len(alerts) == 1
        assert alerts[0].id == alert1.id
        assert alerts[0].symbol == 'RELIANCE.NS'
        # Verify other user's alert not included
        assert alert2.id not in [a.id for a in alerts]
    
    def test_alert_user_relationship_accessible(self, test_db, test_user):
        """CRITICAL: Verify alert.user relationship works correctly"""
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        # CRITICAL: Must use alert.user.telegram_id for sending messages
        assert alert.user is not None
        assert alert.user.telegram_id == 123456  # ✅ For sending messages
        assert alert.user_id == test_user.id  # Foreign key (database)
        
        # Verify we can access user properties
        assert alert.user.username == "testuser"
        assert alert.user.settings is not None
    
    def test_delete_alert(self, test_db, test_user):
        """Test alert deletion"""
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        alert_id = alert.id
        
        # Delete alert
        result = delete_alert(test_db, telegram_id=123456, alert_id=alert_id)
        assert result is True
        
        # Verify alert deleted
        alerts = get_user_alerts(test_db, telegram_id=123456)
        assert alert_id not in [a.id for a in alerts]
    
    def test_update_alert_status(self, test_db, test_user):
        """Test alert status update"""
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        assert alert.is_active is True
        
        # Deactivate alert
        update_alert_status(test_db, alert.id, is_active=False)
        test_db.refresh(alert)
        
        assert alert.is_active is False
    
    def test_update_alert_last_checked(self, test_db, test_user):
        """Test alert last_checked timestamp update"""
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        assert alert.last_checked is None
        
        # Update last checked
        update_alert_last_checked(test_db, alert.id)
        test_db.refresh(alert)
        
        assert alert.last_checked is not None
        assert isinstance(alert.last_checked, datetime)
    
    def test_clear_user_alerts(self, test_db, test_user):
        """Test clearing all user alerts"""
        # Create multiple alerts
        for symbol in ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']:
            create_alert(
                db=test_db,
                telegram_id=123456,
                symbol=symbol,
                alert_type='price',
                condition_type='above',
                threshold_value=100.0,
                condition_data={'operator': '>', 'value': 100.0}
            )
        
        alerts_before = get_user_alerts(test_db, telegram_id=123456)
        assert len(alerts_before) == 3
        
        # Clear all alerts
        count = clear_user_alerts(test_db, telegram_id=123456)
        assert count == 3
        
        # Verify all alerts deleted
        alerts_after = get_user_alerts(test_db, telegram_id=123456)
        assert len(alerts_after) == 0
    
    # ========================================================================
    # Watchlist Operations
    # ========================================================================
    
    def test_add_to_watchlist(self, test_db, test_user):
        """Test adding symbol to watchlist"""
        result = add_to_watchlist(test_db, telegram_id=123456, symbol='RELIANCE.NS')
        assert result is True
        
        watchlist = get_user_watchlist(test_db, telegram_id=123456)
        assert len(watchlist) == 1
        assert watchlist[0].symbol == 'RELIANCE.NS'
    
    def test_remove_from_watchlist(self, test_db, test_user):
        """Test removing symbol from watchlist"""
        # Add first
        add_to_watchlist(test_db, telegram_id=123456, symbol='RELIANCE.NS')
        
        # Remove
        result = remove_from_watchlist(test_db, telegram_id=123456, symbol='RELIANCE.NS')
        assert result is True
        
        watchlist = get_user_watchlist(test_db, telegram_id=123456)
        assert len(watchlist) == 0
    
    def test_watchlist_duplicate_prevention(self, test_db, test_user):
        """Test that duplicate symbols are not added"""
        add_to_watchlist(test_db, telegram_id=123456, symbol='RELIANCE.NS')
        add_to_watchlist(test_db, telegram_id=123456, symbol='RELIANCE.NS')
        
        watchlist = get_user_watchlist(test_db, telegram_id=123456)
        assert len(watchlist) == 1  # Only one entry
    
    # ========================================================================
    # Edge Cases & Error Handling
    # ========================================================================
    
    def test_create_alert_nonexistent_user(self, test_db):
        """Test alert creation for non-existent user"""
        # Should return None or raise appropriate error
        alert = create_alert(
            db=test_db,
            telegram_id=999999,  # Non-existent user
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        # Should return None if user doesn't exist
        assert alert is None
    
    def test_get_user_alerts_nonexistent_user(self, test_db):
        """Test getting alerts for non-existent user"""
        alerts = get_user_alerts(test_db, telegram_id=999999)
        assert alerts == []
    
    def test_delete_nonexistent_alert(self, test_db, test_user):
        """Test deleting non-existent alert"""
        result = delete_alert(test_db, telegram_id=123456, alert_id=99999)
        assert result is False
    
    def test_alert_params_json_handling(self, test_db, test_user):
        """Test that params property handles JSON correctly"""
        complex_data = {
            'operator': '>',
            'value': 100.0,
            'last_recommendation': 'BUY',
            'metadata': {'source': 'test'}
        }
        
        alert = create_alert(
            db=test_db,
            telegram_id=123456,
            symbol='RELIANCE.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data=complex_data
        )
        
        # Verify round-trip JSON
        params = alert.params
        assert params['operator'] == '>'
        assert params['value'] == 100.0
        assert params['last_recommendation'] == 'BUY'
        assert params['metadata']['source'] == 'test'
        
        # Update params
        params['last_recommendation'] = 'SELL'
        alert.params = params
        test_db.commit()
        test_db.refresh(alert)
        
        # Verify update
        updated_params = alert.params
        assert updated_params['last_recommendation'] == 'SELL'


# ========================================================================
# Integration Tests
# ========================================================================

class TestDatabaseIntegration:
    """Integration tests for database operations"""
    
    def test_user_alert_lifecycle(self, test_db):
        """Test complete user-alert lifecycle"""
        # 1. Create user
        user = get_or_create_user(test_db, telegram_id=111111, username="lifecycle_test")
        
        # 2. Create alert
        alert = create_alert(
            db=test_db,
            telegram_id=111111,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        # 3. Verify relationship
        assert alert.user.telegram_id == 111111
        assert user.alerts[0].id == alert.id
        
        # 4. Get alerts
        alerts = get_user_alerts(test_db, telegram_id=111111)
        assert len(alerts) == 1
        
        # 5. Update alert
        update_alert_status(test_db, alert.id, is_active=False)
        
        # 6. Delete alert
        delete_alert(test_db, telegram_id=111111, alert_id=alert.id)
        
        # 7. Verify deletion
        alerts = get_user_alerts(test_db, telegram_id=111111)
        assert len(alerts) == 0

