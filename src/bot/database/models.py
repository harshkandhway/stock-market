"""
Database Models for Stock Analyzer Pro Bot
SQLAlchemy ORM models for users, watchlists, alerts, portfolios, etc.
"""

from datetime import datetime
from typing import Optional, List
import json

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

Base = declarative_base()


class User(Base):
    """User model - stores Telegram user information"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10), default='en')
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    watchlist = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    portfolio = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    scheduled_reports = relationship("ScheduledReport", back_populates="user", cascade="all, delete-orphan")
    activity = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.telegram_id} - {self.username}>"


class UserSettings(Base):
    """User settings model - stores user preferences"""
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    risk_mode = Column(String(20), default='balanced')  # conservative, balanced, aggressive
    timeframe = Column(String(20), default='medium')  # short, medium
    investment_horizon = Column(String(20), default='3months')  # 1week, 2weeks, 1month, 3months, 6months, 1year
    default_capital = Column(Float, default=100000.0)
    timezone = Column(String(50), default='Asia/Kolkata')
    notifications_enabled = Column(Boolean, default=True)
    # Daily BUY alerts subscription
    daily_buy_alerts_enabled = Column(Boolean, default=False, index=True)
    daily_buy_alert_time = Column(String(10), default='09:00')  # HH:MM format in user's timezone
    last_daily_alert_sent = Column(DateTime, nullable=True)  # Track when alert was last sent successfully
    
    # Relationship
    user = relationship("User", back_populates="settings")
    
    def __repr__(self):
        return f"<UserSettings user_id={self.user_id} mode={self.risk_mode} horizon={self.investment_horizon}>"


class Watchlist(Base):
    """Watchlist model - stores user watchlists"""
    __tablename__ = 'watchlist'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    
    # Ensure unique symbol per user
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uix_user_symbol'),
        Index('ix_watchlist_user_symbol', 'user_id', 'symbol'),
    )
    
    # Relationship
    user = relationship("User", back_populates="watchlist")
    
    def __repr__(self):
        return f"<Watchlist user_id={self.user_id} symbol={self.symbol}>"


class Alert(Base):
    """Alert model - stores price and technical alerts"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # price, signal, technical, pattern, custom
    condition_type = Column(String(50), nullable=False)  # above, below, crosses, change
    threshold_value = Column(Float)
    condition_params = Column(Text)  # JSON string for complex conditions
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime)
    last_checked = Column(DateTime)
    trigger_count = Column(Integer, default=0)
    
    # Relationship
    user = relationship("User", back_populates="alerts")
    
    @hybrid_property
    def params(self):
        """Get condition params as dict"""
        if self.condition_params:
            try:
                return json.loads(self.condition_params)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @params.setter
    def params(self, value):
        """Set condition params from dict"""
        if value:
            self.condition_params = json.dumps(value)
        else:
            self.condition_params = None
    
    def __repr__(self):
        return f"<Alert id={self.id} user_id={self.user_id} symbol={self.symbol} type={self.alert_type}>"


class Portfolio(Base):
    """Portfolio model - stores user portfolios"""
    __tablename__ = 'portfolio'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    shares = Column(Float, nullable=False)
    avg_buy_price = Column(Float, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text)
    
    # Ensure unique symbol per user
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uix_portfolio_user_symbol'),
        Index('ix_portfolio_user_symbol', 'user_id', 'symbol'),
    )
    
    # Relationships
    user = relationship("User", back_populates="portfolio")
    transactions = relationship("PortfolioTransaction", back_populates="portfolio", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Portfolio user_id={self.user_id} symbol={self.symbol} shares={self.shares}>"


class PortfolioTransaction(Base):
    """Portfolio transaction model - stores buy/sell transactions"""
    __tablename__ = 'portfolio_transactions'
    
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolio.id', ondelete='CASCADE'), nullable=False, index=True)
    transaction_type = Column(String(10), nullable=False)  # buy, sell
    shares = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    
    # Relationship
    portfolio = relationship("Portfolio", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction portfolio_id={self.portfolio_id} type={self.transaction_type} shares={self.shares}>"


class ScheduledReport(Base):
    """Scheduled report model - stores scheduled analysis reports"""
    __tablename__ = 'scheduled_reports'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    report_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    frequency = Column(String(100), nullable=False)  # e.g., "09:00" for daily, "Monday 09:00" for weekly
    symbols = Column(Text)  # JSON list of symbols
    is_active = Column(Boolean, default=True, index=True)
    last_sent = Column(DateTime)
    next_scheduled = Column(DateTime)
    
    # Relationship
    user = relationship("User", back_populates="scheduled_reports")
    
    @hybrid_property
    def symbol_list(self):
        """Get symbols as list"""
        if self.symbols:
            try:
                return json.loads(self.symbols)
            except json.JSONDecodeError:
                return []
        return []
    
    @symbol_list.setter
    def symbol_list(self, value):
        """Set symbols from list"""
        if value:
            self.symbols = json.dumps(value)
        else:
            self.symbols = None
    
    def __repr__(self):
        return f"<ScheduledReport user_id={self.user_id} type={self.report_type}>"


class AnalysisCache(Base):
    """Analysis cache model - caches analysis results"""
    __tablename__ = 'analysis_cache'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), nullable=False, index=True)
    mode = Column(String(20), nullable=False)
    timeframe = Column(String(20), nullable=False)
    analysis_data = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Ensure unique cache per symbol+mode+timeframe
    __table_args__ = (
        UniqueConstraint('symbol', 'mode', 'timeframe', name='uix_cache_key'),
        Index('ix_cache_expires', 'expires_at'),
    )
    
    @hybrid_property
    def data(self):
        """Get analysis data as dict"""
        if self.analysis_data:
            try:
                return json.loads(self.analysis_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @data.setter
    def data(self, value):
        """Set analysis data from dict"""
        if value:
            self.analysis_data = json.dumps(value, default=str)
        else:
            self.analysis_data = None
    
    def is_expired(self):
        """Check if cache is expired"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<Cache symbol={self.symbol} mode={self.mode} expires={self.expires_at}>"


class UserActivity(Base):
    """User activity model - logs user commands for rate limiting and analytics"""
    __tablename__ = 'user_activity'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    command = Column(String(100), nullable=False, index=True)
    parameters = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes for rate limiting queries
    __table_args__ = (
        Index('ix_activity_user_time', 'user_id', 'created_at'),
        Index('ix_activity_command_time', 'command', 'created_at'),
    )
    
    # Relationship
    user = relationship("User", back_populates="activity")
    
    def __repr__(self):
        return f"<Activity user_id={self.user_id} command={self.command}>"


class DailyBuySignal(Base):
    """Daily BUY signal model - stores BUY signals from daily analysis"""
    __tablename__ = 'daily_buy_signals'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), nullable=False, index=True)
    analysis_date = Column(DateTime, nullable=False, index=True)  # Date when analysis was done
    recommendation = Column(String(100), nullable=False)
    recommendation_type = Column(String(20), nullable=False)  # BUY, STRONG BUY, WEAK BUY
    confidence = Column(Float, nullable=False)
    overall_score_pct = Column(Float, nullable=False)
    risk_reward = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    target = Column(Float)
    stop_loss = Column(Float)
    analysis_data = Column(Text)  # JSON string with full analysis
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Ensure unique signal per symbol per day
    __table_args__ = (
        UniqueConstraint('symbol', 'analysis_date', name='uix_symbol_date'),
        Index('ix_daily_buy_date', 'analysis_date'),
        Index('ix_daily_buy_type', 'recommendation_type'),
    )
    
    @hybrid_property
    def data(self):
        """Get analysis data as dict"""
        if self.analysis_data:
            try:
                return json.loads(self.analysis_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @data.setter
    def data(self, value):
        """Set analysis data from dict"""
        if value:
            self.analysis_data = json.dumps(value, default=str)
        else:
            self.analysis_data = None
    
    def __repr__(self):
        return f"<DailyBuySignal symbol={self.symbol} date={self.analysis_date} type={self.recommendation_type}>"


class PendingAlert(Base):
    """Pending alert model - tracks failed alerts that need retry"""
    __tablename__ = 'pending_alerts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    target_time = Column(DateTime, nullable=False)  # When alert should have been sent
    retry_count = Column(Integer, default=0)  # Number of retry attempts
    error_message = Column(Text)  # Last error message
    created_at = Column(DateTime, default=datetime.now, index=True)
    last_retry_at = Column(DateTime, nullable=True)  # When last retry was attempted
    
    # Ensure one pending alert per user
    __table_args__ = (
        UniqueConstraint('user_id', name='uix_pending_alert_user'),
        Index('ix_pending_alert_user', 'user_id'),
        Index('ix_pending_alert_created', 'created_at'),
    )
    
    # Relationship
    user = relationship("User", backref="pending_alerts")
    
    def __repr__(self):
        return f"<PendingAlert user_id={self.user_id} telegram_id={self.telegram_id} retry_count={self.retry_count}>"


# =============================================================================
# Helper Functions
# =============================================================================

def create_tables(engine):
    """Create all tables in the database"""
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """Drop all tables from the database"""
    Base.metadata.drop_all(engine)
