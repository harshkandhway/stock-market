"""
Database Connection and Session Management
Handles SQLAlchemy engine, session creation, and database initialization

Author: Harsh Kandhway
"""

import os
import sys
from typing import Generator, Optional, List, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.bot.database.models import Base, User, UserSettings, DailyBuySignal
from src.bot.config import DATABASE_URL
from datetime import datetime


def safe_print(message: str):
    """Print message safely, handling encoding errors on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: replace emojis with plain text for Windows console
        message_plain = message.replace('✅', '[OK]').replace('❌', '[ERROR]').replace('⚠️', '[WARNING]')
        print(message_plain)


# Create engine
# For SQLite, use StaticPool to avoid threading issues
engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {},
    poolclass=StaticPool if 'sqlite' in DATABASE_URL else None,
    echo=False  # Set to True for SQL logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Get database session
    
    Usage:
        with get_db() as db:
            user = db.query(User).first()
    
    Or in async context:
        db = next(get_db())
        try:
            user = db.query(User).first()
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions
    
    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db():
    """
    Initialize database - create all tables
    """
    # Ensure data directory exists
    if 'sqlite' in DATABASE_URL:
        db_path = DATABASE_URL.replace('sqlite:///', '')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Run migrations to add new columns
    migrate_database()
    
    safe_print("✅ Database initialized successfully!")


def migrate_database():
    """
    Run migrations to add new columns to existing tables.
    SQLite doesn't support ADD COLUMN IF NOT EXISTS, so we check first.
    """
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(engine)
        
        # Check if user_settings table exists
        if 'user_settings' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('user_settings')]
            
            # Add investment_horizon column if it doesn't exist
            if 'investment_horizon' not in columns:
                with engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE user_settings ADD COLUMN investment_horizon VARCHAR(20) DEFAULT '3months'"
                    ))
                    conn.commit()
                    safe_print("✅ Added investment_horizon column")
            
            # Add daily_buy_alerts_enabled column if it doesn't exist
            if 'daily_buy_alerts_enabled' not in columns:
                with engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE user_settings ADD COLUMN daily_buy_alerts_enabled BOOLEAN DEFAULT 0"
                    ))
                    conn.commit()
                    safe_print("✅ Added daily_buy_alerts_enabled column")
            
            # Add daily_buy_alert_time column if it doesn't exist
            if 'daily_buy_alert_time' not in columns:
                with engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE user_settings ADD COLUMN daily_buy_alert_time VARCHAR(10) DEFAULT '09:00'"
                    ))
                    conn.commit()
                    safe_print("✅ Added daily_buy_alert_time column")
            
            # Add last_daily_alert_sent column if it doesn't exist (for tracking alert status)
            if 'last_daily_alert_sent' not in columns:
                with engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE user_settings ADD COLUMN last_daily_alert_sent DATETIME"
                    ))
                    conn.commit()
                    safe_print("✅ Added last_daily_alert_sent column")
            
            # Remove beginner_mode column if it exists (deprecated - using unified formatter)
            if 'beginner_mode' in columns:
                with engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE user_settings DROP COLUMN beginner_mode"
                    ))
                    conn.commit()
                    safe_print("✅ Removed deprecated beginner_mode column")
    
    except Exception as e:
        safe_print(f"⚠️ Migration warning: {e}")


def drop_db():
    """
    Drop all tables from database
    WARNING: This will delete all data!
    """
    Base.metadata.drop_all(bind=engine)
    safe_print("⚠️ All tables dropped!")


def reset_db():
    """
    Reset database - drop and recreate all tables
    WARNING: This will delete all data!
    """
    drop_db()
    init_db()
    safe_print("✅ Database reset complete!")


# =============================================================================
# USER MANAGEMENT
# =============================================================================

def get_or_create_user(
    db: Session,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: Optional[str] = None
) -> User:
    """
    Get existing user or create new user with default settings
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        username: Telegram username (optional)
        first_name: User's first name (optional)
        last_name: User's last name (optional)
        language_code: User's language code (optional)
    
    Returns:
        User object
    """
    # Try to get existing user
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if user:
        # Update user info if provided
        if username is not None:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if language_code is not None:
            user.language_code = language_code
        
        # Update last_active
        from datetime import datetime
        user.last_active = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        return user
    
    # Create new user
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code or 'en'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create default settings for new user
    settings = UserSettings(
        user_id=user.id,
        risk_mode='balanced',
        timeframe='medium',
        timezone='Asia/Kolkata',
        notifications_enabled=True
    )
    db.add(settings)
    db.commit()
    
    safe_print(f"✅ New user created: {telegram_id} ({username})")
    
    return user


def get_user_settings(db: Session, telegram_id: int) -> Optional[UserSettings]:
    """
    Get user settings by Telegram ID
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
    
    Returns:
        UserSettings object or None if not found
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return None
    
    return db.query(UserSettings).filter(UserSettings.user_id == user.id).first()


def update_user_settings(
    db: Session,
    telegram_id: int,
    **kwargs
) -> Optional[UserSettings]:
    """
    Update user settings
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        **kwargs: Settings to update (risk_mode, timeframe, default_capital, etc.)
    
    Returns:
        Updated UserSettings object or None if user not found
    """
    settings = get_user_settings(db, telegram_id)
    if not settings:
        return None
    
    # Update provided settings
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    
    return settings


# =============================================================================
# WATCHLIST MANAGEMENT
# =============================================================================

def get_user_watchlist(db: Session, telegram_id: int) -> List:
    """
    Get user's watchlist by Telegram ID
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
    
    Returns:
        List of Watchlist objects
    """
    from src.bot.database.models import User, Watchlist
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return []
    
    return db.query(Watchlist).filter(Watchlist.user_id == user.id).order_by(Watchlist.added_at.desc()).all()


def add_to_watchlist(db: Session, telegram_id: int, symbol: str, notes: Optional[str] = None) -> bool:
    """
    Add symbol to user's watchlist
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        symbol: Stock symbol to add
        notes: Optional notes
    
    Returns:
        True if added, False if already exists
    """
    from src.bot.database.models import User, Watchlist
    from sqlalchemy.exc import IntegrityError
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return False
    
    # Check if already exists
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == user.id,
        Watchlist.symbol == symbol.upper()
    ).first()
    
    if existing:
        return False
    
    # Add new watchlist item
    watchlist_item = Watchlist(
        user_id=user.id,
        symbol=symbol.upper(),
        notes=notes
    )
    db.add(watchlist_item)
    
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def remove_from_watchlist(db: Session, telegram_id: int, symbol: str) -> bool:
    """
    Remove symbol from user's watchlist
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        symbol: Stock symbol to remove
    
    Returns:
        True if removed, False if not found
    """
    from src.bot.database.models import User, Watchlist
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return False
    
    watchlist_item = db.query(Watchlist).filter(
        Watchlist.user_id == user.id,
        Watchlist.symbol == symbol.upper()
    ).first()
    
    if not watchlist_item:
        return False
    
    db.delete(watchlist_item)
    db.commit()
    return True


# =============================================================================
# ALERT MANAGEMENT
# =============================================================================

def create_alert(
    db: Session,
    telegram_id: int,
    symbol: str,
    alert_type: str,
    condition_type: str,
    threshold_value: Optional[float] = None,
    condition_data: Optional[Dict] = None
) -> Optional[Any]:
    """
    Create a new alert
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        symbol: Stock symbol
        alert_type: Type of alert (price, signal, technical, etc.)
        condition_type: Condition type (above, below, equals, etc.)
        threshold_value: Threshold value if applicable
        condition_data: Additional condition data as JSON
    
    Returns:
        Alert object or None if failed
    """
    from src.bot.database.models import User, Alert
    import json
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return None
    
    alert = Alert(
        user_id=user.id,
        symbol=symbol.upper(),
        alert_type=alert_type,
        condition_type=condition_type,
        threshold_value=threshold_value,
        condition_params=json.dumps(condition_data) if condition_data else None
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return alert


def get_user_alerts(db: Session, telegram_id: int, active_only: bool = True) -> List:
    """
    Get user's alerts
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        active_only: Only return active alerts
    
    Returns:
        List of Alert objects
    """
    from src.bot.database.models import User, Alert
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return []
    
    query = db.query(Alert).filter(Alert.user_id == user.id)
    
    if active_only:
        query = query.filter(Alert.is_active == True)
    
    return query.order_by(Alert.created_at.desc()).all()


def delete_alert(db: Session, telegram_id: int, alert_id: int) -> bool:
    """
    Delete an alert
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        alert_id: Alert ID to delete
    
    Returns:
        True if deleted, False if not found
    """
    from src.bot.database.models import User, Alert
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return False
    
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user.id
    ).first()
    
    if not alert:
        return False
    
    db.delete(alert)
    db.commit()
    return True


def update_alert_status(db: Session, alert_id: int, is_active: bool) -> bool:
    """
    Update alert active status
    
    Args:
        db: Database session
        alert_id: Alert ID
        is_active: New active status
    
    Returns:
        True if updated, False if not found
    """
    from src.bot.database.models import Alert
    
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return False
    
    alert.is_active = is_active
    db.commit()
    return True


def update_alert_last_checked(db: Session, alert_id: int) -> bool:
    """
    Update alert's last checked timestamp
    
    Args:
        db: Database session
        alert_id: Alert ID
    
    Returns:
        True if updated, False if not found
    """
    from src.bot.database.models import Alert
    from datetime import datetime
    
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return False
    
    alert.last_checked = datetime.utcnow()
    db.commit()
    return True


def clear_user_alerts(db: Session, telegram_id: int) -> int:
    """
    Clear all alerts for a user
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
    
    Returns:
        Number of alerts deleted
    """
    from src.bot.database.models import User, Alert
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return 0
    
    count = db.query(Alert).filter(Alert.user_id == user.id).delete()
    db.commit()
    return count


# =============================================================================
# PORTFOLIO MANAGEMENT
# =============================================================================

def get_user_portfolio(db: Session, telegram_id: int) -> List:
    """
    Get user's portfolio positions
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
    
    Returns:
        List of Portfolio objects
    """
    from src.bot.database.models import User, Portfolio
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return []
    
    return db.query(Portfolio).filter(Portfolio.user_id == user.id).order_by(Portfolio.added_at.desc()).all()


def add_portfolio_position(
    db: Session,
    telegram_id: int,
    symbol: str,
    shares: float,
    avg_buy_price: float,
    notes: Optional[str] = None
) -> Optional[Any]:
    """
    Add or update a portfolio position
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        symbol: Stock symbol
        shares: Number of shares
        avg_buy_price: Average buy price per share
        notes: Optional notes
    
    Returns:
        Portfolio object or None if failed
    """
    from src.bot.database.models import User, Portfolio
    from datetime import datetime
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return None
    
    symbol = symbol.upper().strip()
    
    # Check if position already exists
    existing = db.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.symbol == symbol
    ).first()
    
    if existing:
        # Update existing position (weighted average for price)
        total_cost = (existing.shares * existing.avg_buy_price) + (shares * avg_buy_price)
        total_shares = existing.shares + shares
        new_avg_price = total_cost / total_shares if total_shares > 0 else avg_buy_price
        
        existing.shares = total_shares
        existing.avg_buy_price = new_avg_price
        existing.updated_at = datetime.utcnow()
        if notes:
            existing.notes = notes
        
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new position
        position = Portfolio(
            user_id=user.id,
            symbol=symbol,
            shares=shares,
            avg_buy_price=avg_buy_price,
            notes=notes
        )
        
        db.add(position)
        db.commit()
        db.refresh(position)
        return position


def remove_portfolio_position(db: Session, telegram_id: int, symbol: str) -> bool:
    """
    Remove a portfolio position
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        symbol: Stock symbol to remove
    
    Returns:
        True if removed, False if not found
    """
    from src.bot.database.models import User, Portfolio
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return False
    
    symbol = symbol.upper().strip()
    
    position = db.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.symbol == symbol
    ).first()
    
    if not position:
        return False
    
    db.delete(position)
    db.commit()
    return True


def update_portfolio_position(
    db: Session,
    telegram_id: int,
    symbol: str,
    shares: Optional[float] = None,
    avg_buy_price: Optional[float] = None,
    notes: Optional[str] = None
) -> Optional[Any]:
    """
    Update a portfolio position
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        symbol: Stock symbol
        shares: New number of shares (optional)
        avg_buy_price: New average buy price (optional)
        notes: New notes (optional)
    
    Returns:
        Updated Portfolio object or None if not found
    """
    from src.bot.database.models import User, Portfolio
    from datetime import datetime
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return None
    
    symbol = symbol.upper().strip()
    
    position = db.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.symbol == symbol
    ).first()
    
    if not position:
        return None
    
    if shares is not None:
        position.shares = shares
    if avg_buy_price is not None:
        position.avg_buy_price = avg_buy_price
    if notes is not None:
        position.notes = notes
    
    position.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(position)
    
    return position


# =============================================================================
# SCHEDULED REPORTS MANAGEMENT
# =============================================================================

def get_user_scheduled_reports(db: Session, telegram_id: int, active_only: bool = True) -> List:
    """
    Get user's scheduled reports
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        active_only: Only return active reports
    
    Returns:
        List of ScheduledReport objects
    """
    from src.bot.database.models import User, ScheduledReport
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return []
    
    query = db.query(ScheduledReport).filter(ScheduledReport.user_id == user.id)
    
    if active_only:
        query = query.filter(ScheduledReport.is_active == True)
    
    return query.order_by(ScheduledReport.created_at.desc()).all()


def create_scheduled_report(
    db: Session,
    telegram_id: int,
    report_type: str,
    frequency: str,
    symbols: Optional[List[str]] = None
) -> Optional[Any]:
    """
    Create a new scheduled report
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        report_type: Type of report (watchlist, portfolio, combined)
        frequency: Frequency string (e.g., "09:00" for daily, "Monday 09:00" for weekly)
        symbols: Optional list of symbols (for custom reports)
    
    Returns:
        ScheduledReport object or None if failed
    """
    from src.bot.database.models import User, ScheduledReport
    import json
    from datetime import datetime
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return None
    
    report = ScheduledReport(
        user_id=user.id,
        report_type=report_type,
        frequency=frequency,
        symbols=json.dumps(symbols) if symbols else None,
        is_active=True
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return report


def delete_scheduled_report(db: Session, telegram_id: int, report_id: int) -> bool:
    """
    Delete a scheduled report
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        report_id: Report ID to delete
    
    Returns:
        True if deleted, False if not found
    """
    from src.bot.database.models import User, ScheduledReport
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return False
    
    report = db.query(ScheduledReport).filter(
        ScheduledReport.id == report_id,
        ScheduledReport.user_id == user.id
    ).first()
    
    if not report:
        return False
    
    db.delete(report)
    db.commit()
    return True


def update_scheduled_report_status(db: Session, report_id: int, is_active: bool) -> bool:
    """
    Update scheduled report active status
    
    Args:
        db: Database session
        report_id: Report ID
        is_active: New active status
    
    Returns:
        True if updated, False if not found
    """
    from src.bot.database.models import ScheduledReport
    
    report = db.query(ScheduledReport).filter(ScheduledReport.id == report_id).first()
    if not report:
        return False
    
    report.is_active = is_active
    db.commit()
    return True


def get_all_active_scheduled_reports(db: Session) -> List:
    """
    Get all active scheduled reports (for scheduler)
    
    Args:
        db: Database session
    
    Returns:
        List of active ScheduledReport objects
    """
    from src.bot.database.models import ScheduledReport
    
    return db.query(ScheduledReport).filter(
        ScheduledReport.is_active == True
    ).all()


def get_subscribed_users_for_daily_buy_alerts(db: Session) -> List[User]:
    """
    Get all users subscribed to daily BUY alerts
    
    Args:
        db: Database session
    
    Returns:
        List of User objects with daily_buy_alerts_enabled = True
    """
    return db.query(User).join(UserSettings).filter(
        UserSettings.daily_buy_alerts_enabled == True
    ).all()


def get_pending_alerts(db: Session) -> List:
    """
    Get all pending alerts that need retry
    
    Args:
        db: Database session
    
    Returns:
        List of PendingAlert objects
    """
    from src.bot.database.models import PendingAlert
    return db.query(PendingAlert).all()


def get_pending_alert_by_user_id(db: Session, user_id: int):
    """
    Get pending alert for a specific user
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        PendingAlert object or None
    """
    from src.bot.database.models import PendingAlert
    return db.query(PendingAlert).filter(PendingAlert.user_id == user_id).first()


def create_pending_alert(
    db: Session,
    user_id: int,
    telegram_id: int,
    target_time: datetime,
    error_message: str = None
):
    """
    Create or update a pending alert
    
    Args:
        db: Database session
        user_id: User ID
        telegram_id: Telegram user ID
        target_time: When alert should have been sent
        error_message: Error message (optional)
    
    Returns:
        PendingAlert object
    """
    from src.bot.database.models import PendingAlert
    
    # Check if pending alert already exists
    pending = db.query(PendingAlert).filter(PendingAlert.user_id == user_id).first()
    
    if pending:
        # Update existing
        pending.telegram_id = telegram_id
        pending.target_time = target_time
        pending.error_message = error_message
        pending.last_retry_at = datetime.now()
    else:
        # Create new
        pending = PendingAlert(
            user_id=user_id,
            telegram_id=telegram_id,
            target_time=target_time,
            error_message=error_message,
            retry_count=0
        )
        db.add(pending)
    
    db.commit()
    db.refresh(pending)
    return pending


def delete_pending_alert(db: Session, user_id: int) -> bool:
    """
    Delete a pending alert (when successfully sent)
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        True if deleted, False if not found
    """
    from src.bot.database.models import PendingAlert
    
    pending = db.query(PendingAlert).filter(PendingAlert.user_id == user_id).first()
    if pending:
        db.delete(pending)
        db.commit()
        return True
    return False


def increment_pending_alert_retry(db: Session, user_id: int) -> Optional[int]:
    """
    Increment retry count for a pending alert
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        New retry count or None if not found
    """
    from src.bot.database.models import PendingAlert
    
    pending = db.query(PendingAlert).filter(PendingAlert.user_id == user_id).first()
    if pending:
        pending.retry_count += 1
        pending.last_retry_at = datetime.now()
        db.commit()
        db.refresh(pending)
        return pending.retry_count
    return None


def get_today_buy_signals(db: Session) -> List:
    """
    Get today's BUY signals from database
    
    Args:
        db: Database session
    
    Returns:
        List of DailyBuySignal objects from today
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.query(DailyBuySignal).filter(
        DailyBuySignal.analysis_date >= today
    ).order_by(
        DailyBuySignal.confidence.desc(),
        DailyBuySignal.overall_score_pct.desc()
    ).all()


# =============================================================================
# DATABASE STATS
# =============================================================================

def get_database_stats(db: Session) -> dict:
    """
    Get database statistics
    
    Returns:
        Dictionary with database stats
    """
    from src.bot.database.models import (
        User, Watchlist, Alert, Portfolio, ScheduledReport, UserActivity
    )
    
    stats = {
        'total_users': db.query(User).count(),
        'active_users': db.query(User).filter(User.is_active == True).count(),
        'admin_users': db.query(User).filter(User.is_admin == True).count(),
        'total_watchlist_items': db.query(Watchlist).count(),
        'total_alerts': db.query(Alert).count(),
        'active_alerts': db.query(Alert).filter(Alert.is_active == True).count(),
        'total_portfolio_positions': db.query(Portfolio).count(),
        'total_scheduled_reports': db.query(ScheduledReport).count(),
        'active_scheduled_reports': db.query(ScheduledReport).filter(ScheduledReport.is_active == True).count(),
        'total_activity_logs': db.query(UserActivity).count(),
    }
    
    return stats


def cleanup_expired_cache(db: Session) -> int:
    """
    Delete expired cache entries
    
    Args:
        db: Database session
    
    Returns:
        Number of deleted entries
    """
    from datetime import datetime
    from src.bot.database.models import AnalysisCache
    
    count = db.query(AnalysisCache).filter(
        AnalysisCache.expires_at < datetime.utcnow()
    ).delete()
    
    db.commit()
    
    return count


def cleanup_old_activity(db: Session, days: int = 30) -> int:
    """
    Delete activity logs older than specified days
    
    Args:
        db: Database session
        days: Delete logs older than this many days
    
    Returns:
        Number of deleted entries
    """
    from datetime import datetime, timedelta
    from src.bot.database.models import UserActivity
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    count = db.query(UserActivity).filter(
        UserActivity.created_at < cutoff_date
    ).delete()
    
    db.commit()
    
    return count


# =============================================================================
# DATABASE MIGRATION HELPERS
# =============================================================================

def check_database_exists() -> bool:
    """
    Check if database file exists (for SQLite)
    
    Returns:
        True if database exists, False otherwise
    """
    if 'sqlite' in DATABASE_URL:
        db_path = DATABASE_URL.replace('sqlite:///', '')
        return os.path.exists(db_path)
    # For other databases, assume they exist
    return True


def get_database_size() -> str:
    """
    Get database file size (for SQLite)
    
    Returns:
        Human-readable database size
    """
    if 'sqlite' in DATABASE_URL:
        db_path = DATABASE_URL.replace('sqlite:///', '')
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            
            # Convert to human-readable format
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            
            return f"{size_bytes:.2f} TB"
    
    return "Unknown"


# =============================================================================
# TESTING AND DIAGNOSTICS
# =============================================================================

def test_connection() -> bool:
    """
    Test database connection
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_db_context() as db:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
        safe_print("✅ Database connection successful!")
        return True
    except Exception as e:
        safe_print(f"❌ Database connection failed: {e}")
        return False


def print_database_info():
    """
    Print database information and statistics
    """
    print("\n" + "="*60)
    print("DATABASE INFORMATION")
    print("="*60)
    print(f"Database URL: {DATABASE_URL}")
    print(f"Database Exists: {check_database_exists()}")
    print(f"Database Size: {get_database_size()}")
    
    if test_connection():
        try:
            with get_db_context() as db:
                stats = get_database_stats(db)
                
                print("\n" + "-"*60)
                print("DATABASE STATISTICS")
                print("-"*60)
                for key, value in stats.items():
                    print(f"{key.replace('_', ' ').title()}: {value}")
                print("-"*60)
        except Exception as e:
            print(f"Could not retrieve stats: {e}")
    
    print("="*60 + "\n")


if __name__ == '__main__':
    # Test database functionality
    print("Testing database module...")
    print_database_info()
    
    # Initialize database if it doesn't exist
    if not check_database_exists():
        print("\nDatabase doesn't exist. Initializing...")
        init_db()
        print_database_info()
