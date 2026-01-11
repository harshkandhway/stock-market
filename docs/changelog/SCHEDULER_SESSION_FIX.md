# Scheduler Session Fix

## Issue
SQLAlchemy DetachedInstanceError in scheduler's notification checker:
```
DetachedInstanceError: Parent instance <User> is not bound to a Session; 
lazy load operation of attribute 'settings' cannot proceed
```

## Root Cause
The scheduler was accessing `user.settings` after the database session was closed, causing a detached instance error.

**Problematic Code**:
```python
with get_db_context() as db:
    users = get_subscribed_users_for_daily_buy_alerts(db)

# Session is closed here, but we try to access user.settings
for user in users:
    settings = user.settings  # ❌ DetachedInstanceError
```

## Fix Applied
**File**: `src/bot/services/scheduler_service.py` (lines 273-308)

**Solution**: Access settings within the session context by querying directly:

```python
with get_db_context() as db:
    users = get_subscribed_users_for_daily_buy_alerts(db)
    
    for user in users:
        # Query settings directly within session
        settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        
        if not settings or not settings.daily_buy_alerts_enabled:
            continue
        
        # Access settings fields within session
        alert_time_str = settings.daily_buy_alert_time or '09:00'
        user_timezone = settings.timezone or DEFAULT_TIMEZONE
        # ... rest of logic
```

## Status
✅ **FIXED**: Settings are now accessed within the session context, preventing DetachedInstanceError.

---

**This fix ensures the scheduler can properly check user alert times without session errors.**

