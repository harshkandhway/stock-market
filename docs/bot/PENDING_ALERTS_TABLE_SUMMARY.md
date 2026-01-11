# Pending Alerts Database Table Implementation

## Table Created: `pending_alerts`

The `pending_alerts` table has been created in the database to persistently track failed alerts that need retry.

### Table Structure

```sql
CREATE TABLE pending_alerts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    telegram_id INTEGER NOT NULL,
    target_time DATETIME NOT NULL,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_retry_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id),
    INDEX (user_id),
    INDEX (created_at)
);
```

### Fields

- **id**: Primary key
- **user_id**: Foreign key to users table
- **telegram_id**: Telegram user ID (for quick access)
- **target_time**: When the alert should have been sent
- **retry_count**: Number of retry attempts (max 10)
- **error_message**: Last error message
- **created_at**: When the pending alert was created
- **last_retry_at**: When the last retry was attempted

### Database Functions

1. **`get_pending_alerts(db)`**: Get all pending alerts
2. **`get_pending_alert_by_user_id(db, user_id)`**: Get pending alert for a specific user
3. **`create_pending_alert(db, user_id, telegram_id, target_time, error_message)`**: Create or update pending alert
4. **`delete_pending_alert(db, user_id)`**: Delete pending alert (when successfully sent)
5. **`increment_pending_alert_retry(db, user_id)`**: Increment retry count

### How It Works

1. **On Alert Failure**: Alert is saved to `pending_alerts` table
2. **Retry Checker**: Every 2 minutes, reads from `pending_alerts` table
3. **Retry Logic**: Retries all pending alerts up to 10 times
4. **On Success**: Alert removed from `pending_alerts` table
5. **On Max Retries**: Alert removed from `pending_alerts` table

### Benefits

✅ **Persistent**: Survives bot restarts
✅ **Trackable**: Can query pending alerts from database
✅ **Reliable**: No data loss if bot crashes
✅ **Auditable**: Full history of retry attempts

### Status

✅ **Table Created**: `pending_alerts` table exists in database
✅ **Functions Implemented**: All database functions ready
✅ **Scheduler Updated**: Uses database instead of in-memory dict

---

**The pending alerts are now stored in the database for persistent retry!**

