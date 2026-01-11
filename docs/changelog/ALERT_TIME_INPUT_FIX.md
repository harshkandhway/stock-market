# Alert Time Input Fix

## Issue
The custom alert time input feature was showing `{settings.timezone}` as literal text instead of the actual timezone value.

## Root Cause
1. **Line 769**: The string was not an f-string, so `{settings.timezone}` was not interpolated.
2. **Line 1197**: `settings.timezone` was accessed after the database session closed, which could cause issues.

## Fixes Applied

### Fix 1: F-string for timezone display (Line 762-772)
**Before**:
```python
await query.edit_message_text(
    "*🕐 SET CUSTOM ALERT TIME*\n\n"
    ...
    "Time is in your timezone: {settings.timezone}\n\n"  # ❌ Not interpolated
    ...
)
```

**After**:
```python
user_timezone = getattr(settings, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
await query.edit_message_text(
    f"*🕐 SET CUSTOM ALERT TIME*\n\n"
    ...
    f"Time is in your timezone: {user_timezone}\n\n"  # ✅ Properly interpolated
    ...
)
```

### Fix 2: Extract timezone before session closes (Line 1189-1197)
**Before**:
```python
with get_db_context() as db:
    settings = get_user_settings(db, user_id)
    update_user_settings(db, user_id, daily_buy_alert_time=time_str)

# Session closed here
await update.message.reply_text(
    f"... ({settings.timezone}) ..."  # ❌ Accessing after session close
)
```

**After**:
```python
with get_db_context() as db:
    settings = get_user_settings(db, user_id)
    user_timezone = getattr(settings, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
    update_user_settings(db, user_id, daily_buy_alert_time=time_str)

# Session closed, but timezone already extracted
await update.message.reply_text(
    f"... ({user_timezone}) ..."  # ✅ Using extracted value
)
```

## Status
✅ **FIXED**: 
- Timezone now displays correctly in the prompt message
- Timezone extracted before session closes
- Handler properly registered in bot.py

## Testing
To test:
1. Go to `/settings` → "🔔 Daily BUY Alerts"
2. Click "🕐 Set Custom Time"
3. Verify the message shows your actual timezone (not `{settings.timezone}`)
4. Enter a time like `09:00`
5. Verify it saves and shows confirmation with correct timezone

---

**The custom alert time input feature should now work correctly!**

