"""
Test Database-Handler Integration
Critical tests for integration between handlers and database operations
"""

import pytest
from unittest.mock import Mock, patch

from src.bot.database.db import (
    get_db_context,
    get_or_create_user,
    create_alert,
    get_user_alerts,
    add_to_watchlist,
    get_user_watchlist
)


class TestDatabaseHandlerIntegration:
    """Test integration between handlers and database"""
    
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
    # CRITICAL: Handler-Database Consistency
    # ========================================================================
    
    def test_handler_database_consistency_telegram_id(self, test_db):
        """CRITICAL: Verify handlers use telegram_id consistently"""
        # Simulate handler creating user
        telegram_id = 123456
        user = get_or_create_user(test_db, telegram_id=telegram_id, username="testuser")
        
        # Verify user can be retrieved by telegram_id (as handlers do)
        from src.bot.database.db import get_user_settings
        settings = get_user_settings(test_db, telegram_id=telegram_id)
        assert settings is not None
        
        # Verify alerts can be retrieved by telegram_id
        alerts = get_user_alerts(test_db, telegram_id=telegram_id)
        assert isinstance(alerts, list)
    
    def test_alert_creation_integration(self, test_db):
        """CRITICAL: Test alert creation flow (handler → database → service)"""
        # Step 1: Handler creates user (simulated)
        telegram_id = 123456
        user = get_or_create_user(test_db, telegram_id=telegram_id, username="testuser")
        
        # Step 2: Handler creates alert (simulated)
        alert = create_alert(
            db=test_db,
            telegram_id=telegram_id,  # ✅ Handler uses telegram_id
            symbol='NIFTYBEES.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data={}
        )
        
        assert alert is not None
        
        # Step 3: Service can query alert (simulated)
        from sqlalchemy.orm import joinedload
        from src.bot.database.models import Alert
        
        # Service query with eager loading
        service_alert = test_db.query(Alert).options(joinedload(Alert.user)).filter(
            Alert.id == alert.id
        ).first()
        
        assert service_alert is not None
        assert service_alert.user.telegram_id == telegram_id  # ✅ Service can access telegram_id
        assert service_alert.user_id == user.id  # Foreign key relationship
    
    def test_user_creation_integration(self, test_db):
        """Test user creation flow with automatic settings"""
        # Handler creates user
        telegram_id = 789012
        user = get_or_create_user(
            test_db,
            telegram_id=telegram_id,
            username="integration_test",
            first_name="Integration",
            last_name="Test"
        )
        
        # Verify user created
        assert user.telegram_id == telegram_id
        assert user.username == "integration_test"
        
        # Verify settings created automatically
        assert user.settings is not None
        assert user.settings.risk_mode == 'balanced'  # Default
        
        # Verify user can be queried by telegram_id (as handlers do)
        from src.bot.database.db import get_user_settings
        settings = get_user_settings(test_db, telegram_id=telegram_id)
        assert settings is not None
        assert settings.user_id == user.id
    
    def test_watchlist_integration(self, test_db):
        """Test watchlist operations integration"""
        # Create user
        telegram_id = 111222
        user = get_or_create_user(test_db, telegram_id=telegram_id)
        
        # Handler adds to watchlist
        result = add_to_watchlist(test_db, telegram_id=telegram_id, symbol='RELIANCE.NS')
        assert result is True
        
        # Handler retrieves watchlist
        watchlist = get_user_watchlist(test_db, telegram_id=telegram_id)
        assert len(watchlist) == 1
        assert watchlist[0].symbol == 'RELIANCE.NS'
        assert watchlist[0].user_id == user.id  # Foreign key
    
    def test_alert_user_relationship_integration(self, test_db):
        """CRITICAL: Test alert-user relationship in integration context"""
        # Create user
        telegram_id = 333444
        user = get_or_create_user(test_db, telegram_id=telegram_id)
        
        # Create alert (as handler would)
        alert = create_alert(
            db=test_db,
            telegram_id=telegram_id,
            symbol='TCS.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        
        # Service accesses alert with user relationship
        from sqlalchemy.orm import joinedload
        from src.bot.database.models import Alert
        
        service_alert = test_db.query(Alert).options(joinedload(Alert.user)).filter(
            Alert.id == alert.id
        ).first()
        
        # CRITICAL: Service can access telegram_id for notifications
        assert service_alert.user.telegram_id == telegram_id
        assert service_alert.user_id == user.id
        
        # Verify all relationships work
        assert service_alert.user.settings is not None
        assert len(user.alerts) == 1
        assert user.alerts[0].id == alert.id
    
    def test_multiple_alerts_integration(self, test_db):
        """Test multiple alerts for same user"""
        telegram_id = 555666
        user = get_or_create_user(test_db, telegram_id=telegram_id)
        
        # Create multiple alerts
        symbols = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']
        for symbol in symbols:
            create_alert(
                db=test_db,
                telegram_id=telegram_id,
                symbol=symbol,
                alert_type='price',
                condition_type='above',
                threshold_value=100.0,
                condition_data={'operator': '>', 'value': 100.0}
            )
        
        # Retrieve all alerts
        alerts = get_user_alerts(test_db, telegram_id=telegram_id)
        assert len(alerts) == 3
        
        # Verify all belong to same user
        for alert in alerts:
            assert alert.user_id == user.id
            assert alert.user.telegram_id == telegram_id
    
    def test_alert_params_integration(self, test_db):
        """CRITICAL: Test alert params property in integration"""
        telegram_id = 777888
        user = get_or_create_user(test_db, telegram_id=telegram_id)
        
        # Create alert with complex data
        complex_data = {
            'last_recommendation': 'BUY',
            'metadata': {'source': 'handler'}
        }
        
        alert = create_alert(
            db=test_db,
            telegram_id=telegram_id,
            symbol='NIFTYBEES.NS',
            alert_type='signal_change',
            condition_type='change',
            condition_data=complex_data
        )
        
        # Service accesses params
        params = alert.params
        assert params['last_recommendation'] == 'BUY'
        assert params['metadata']['source'] == 'handler'
        
        # Service updates params
        params['last_recommendation'] = 'SELL'
        alert.params = params
        test_db.commit()
        test_db.refresh(alert)
        
        # Verify update persisted
        updated_params = alert.params
        assert updated_params['last_recommendation'] == 'SELL'


class TestDataFlowIntegration:
    """Test data flow through handler → database → service"""
    
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
    
    def test_complete_alert_lifecycle(self, test_db):
        """Test complete alert lifecycle: create → query → update → delete"""
        telegram_id = 999888
        
        # 1. Create user
        user = get_or_create_user(test_db, telegram_id=telegram_id)
        
        # 2. Create alert
        alert = create_alert(
            db=test_db,
            telegram_id=telegram_id,
            symbol='RELIANCE.NS',
            alert_type='price',
            condition_type='above',
            threshold_value=100.0,
            condition_data={'operator': '>', 'value': 100.0}
        )
        alert_id = alert.id
        
        # 3. Query alert
        alerts = get_user_alerts(test_db, telegram_id=telegram_id)
        assert len(alerts) == 1
        assert alerts[0].id == alert_id
        
        # 4. Update alert (as service would)
        from src.bot.database.db import update_alert_status, update_alert_last_checked
        update_alert_status(test_db, alert_id, is_active=False)
        update_alert_last_checked(test_db, alert_id)
        
        test_db.refresh(alert)
        assert alert.is_active is False
        assert alert.last_checked is not None
        
        # 5. Delete alert
        from src.bot.database.db import delete_alert
        result = delete_alert(test_db, telegram_id=telegram_id, alert_id=alert_id)
        assert result is True
        
        # 6. Verify deletion
        alerts = get_user_alerts(test_db, telegram_id=telegram_id)
        assert len(alerts) == 0

