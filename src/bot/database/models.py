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

    # Paper Trading Settings (using .env defaults)
    paper_trading_enabled = Column(Boolean, default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_ENABLED']).PAPER_TRADING_ENABLED)
    paper_trading_default_capital = Column(Float, default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_DEFAULT_CAPITAL']).PAPER_TRADING_DEFAULT_CAPITAL)
    paper_trading_max_positions = Column(Integer, default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_DEFAULT_MAX_POSITIONS']).PAPER_TRADING_DEFAULT_MAX_POSITIONS)
    paper_trading_risk_percentage = Column(Float, default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_DEFAULT_RISK_PCT']).PAPER_TRADING_DEFAULT_RISK_PCT)
    paper_trading_monitor_interval_seconds = Column(Integer, default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_MONITOR_INTERVAL']).PAPER_TRADING_MONITOR_INTERVAL)
    paper_trading_max_position_size_pct = Column(Float, default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_MAX_POSITION_SIZE_PCT']).PAPER_TRADING_MAX_POSITION_SIZE_PCT)
    paper_trading_buy_execution_time = Column(String(5), default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_BUY_EXECUTION_TIME']).PAPER_TRADING_BUY_EXECUTION_TIME)
    paper_trading_daily_summary_time = Column(String(5), default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_DAILY_SUMMARY_TIME']).PAPER_TRADING_DAILY_SUMMARY_TIME)
    paper_trading_weekly_summary_time = Column(String(5), default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_WEEKLY_SUMMARY_TIME']).PAPER_TRADING_WEEKLY_SUMMARY_TIME)
    paper_trading_position_rebalance_time = Column(String(5), default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_POSITION_REBALANCE_TIME']).PAPER_TRADING_POSITION_REBALANCE_TIME)
    paper_trading_entry_price_tolerance_pct = Column(Float, default=lambda: __import__('src.bot.config', fromlist=['PAPER_TRADING_ENTRY_PRICE_TOLERANCE']).PAPER_TRADING_ENTRY_PRICE_TOLERANCE)

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
# PAPER TRADING MODELS
# =============================================================================

class PaperTradingSession(Base):
    """Paper trading session model - tracks overall paper trading session"""
    __tablename__ = 'paper_trading_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Session Status
    is_active = Column(Boolean, default=True, index=True)
    session_start = Column(DateTime, default=datetime.utcnow, nullable=False)
    session_end = Column(DateTime, nullable=True)

    # Capital Management
    initial_capital = Column(Float, default=500000.0, nullable=False)  # ₹5 lakhs
    current_capital = Column(Float, default=500000.0, nullable=False)
    peak_capital = Column(Float, default=500000.0, nullable=False)

    # Position Management
    max_positions = Column(Integer, default=15, nullable=False)  # 10-20 range
    current_positions = Column(Integer, default=0, nullable=False)

    # Performance Summary
    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    losing_trades = Column(Integer, default=0, nullable=False)
    total_profit = Column(Float, default=0.0, nullable=False)
    total_loss = Column(Float, default=0.0, nullable=False)
    max_drawdown_pct = Column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="paper_trading_sessions")
    positions = relationship("PaperPosition", back_populates="session", cascade="all, delete-orphan")
    trades = relationship("PaperTrade", back_populates="session", cascade="all, delete-orphan")
    analytics = relationship("PaperTradeAnalytics", back_populates="session", cascade="all, delete-orphan")
    logs = relationship("PaperTradingLog", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PaperTradingSession id={self.id} user_id={self.user_id} active={self.is_active} capital={self.current_capital}>"


class PaperPosition(Base):
    """Paper position model - tracks currently open positions"""
    __tablename__ = 'paper_positions'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('paper_trading_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    signal_id = Column(Integer, ForeignKey('daily_buy_signals.id', ondelete='SET NULL'), nullable=True)

    # Entry Details
    entry_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    entry_price = Column(Float, nullable=False)
    shares = Column(Float, nullable=False)
    position_value = Column(Float, nullable=False)

    # Risk Management
    target_price = Column(Float, nullable=False)
    stop_loss_price = Column(Float, nullable=False)
    trailing_stop = Column(Float, nullable=True)
    initial_risk_reward = Column(Float, nullable=False)

    # Signal Metadata
    recommendation_type = Column(String(20), nullable=False)  # STRONG BUY, BUY, WEAK BUY
    entry_confidence = Column(Float, nullable=False)
    entry_score_pct = Column(Float, nullable=False)

    # Current State
    current_price = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_pct = Column(Float, default=0.0)
    highest_price = Column(Float, nullable=True)
    is_open = Column(Boolean, default=True, index=True)
    days_held = Column(Integer, default=0)

    # Analysis Snapshot
    entry_analysis = Column(Text)  # JSON string with full analysis

    # Timestamps
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('session_id', 'symbol', name='uix_session_symbol'),
        Index('ix_paper_position_open', 'is_open'),
        Index('ix_paper_position_entry_date', 'entry_date'),
    )

    # Relationships
    session = relationship("PaperTradingSession", back_populates="positions")
    signal = relationship("DailyBuySignal", backref="paper_positions")

    @hybrid_property
    def analysis(self):
        """Get entry analysis as dict"""
        if self.entry_analysis:
            try:
                return json.loads(self.entry_analysis)
            except json.JSONDecodeError:
                return {}
        return {}

    @analysis.setter
    def analysis(self, value):
        """Set entry analysis from dict"""
        if value:
            self.entry_analysis = json.dumps(value, default=str)
        else:
            self.entry_analysis = None

    def __repr__(self):
        return f"<PaperPosition id={self.id} session_id={self.session_id} symbol={self.symbol} open={self.is_open}>"


class PaperTrade(Base):
    """Paper trade model - tracks completed trades (entry + exit)"""
    __tablename__ = 'paper_trades'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('paper_trading_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    position_id = Column(Integer, ForeignKey('paper_positions.id', ondelete='SET NULL'), nullable=True)
    symbol = Column(String(50), nullable=False, index=True)

    # Entry Details
    entry_date = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    shares = Column(Float, nullable=False)
    entry_value = Column(Float, nullable=False)

    # Exit Details
    exit_date = Column(DateTime, nullable=False)
    exit_price = Column(Float, nullable=False)
    exit_value = Column(Float, nullable=False)
    exit_reason = Column(String(50), nullable=False, index=True)  # STOP_LOSS, TARGET_HIT, TRAILING_STOP, SELL_SIGNAL

    # Performance Metrics
    pnl = Column(Float, nullable=False)
    pnl_pct = Column(Float, nullable=False)
    days_held = Column(Integer, nullable=False)
    r_multiple = Column(Float, nullable=False)  # Profit/Loss as multiple of initial risk
    is_winner = Column(Boolean, nullable=False, index=True)
    met_target = Column(Boolean, default=False)
    hit_stop_loss = Column(Boolean, default=False)

    # Signal Metadata (copied from position)
    recommendation_type = Column(String(20), nullable=False)
    entry_confidence = Column(Float, nullable=False)
    entry_score_pct = Column(Float, nullable=False)
    initial_risk_reward = Column(Float, nullable=False)

    # Risk Management (from entry)
    target_price = Column(Float, nullable=False)
    stop_loss_price = Column(Float, nullable=False)

    # Price Extremes
    highest_price = Column(Float, nullable=True)
    max_unrealized_gain = Column(Float, default=0.0)
    max_unrealized_loss = Column(Float, default=0.0)

    # Analysis Snapshots
    entry_analysis = Column(Text)  # JSON - analysis at entry
    exit_analysis = Column(Text, nullable=True)  # JSON - analysis at exit

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_paper_trade_winner', 'is_winner', 'pnl'),
        Index('ix_paper_trade_exit', 'exit_reason', 'exit_date'),
        Index('ix_paper_trade_dates', 'entry_date', 'exit_date'),
    )

    # Relationships
    session = relationship("PaperTradingSession", back_populates="trades")
    position = relationship("PaperPosition", backref="trade")

    @hybrid_property
    def entry_analysis_data(self):
        """Get entry analysis as dict"""
        if self.entry_analysis:
            try:
                return json.loads(self.entry_analysis)
            except json.JSONDecodeError:
                return {}
        return {}

    @entry_analysis_data.setter
    def entry_analysis_data(self, value):
        """Set entry analysis from dict"""
        if value:
            self.entry_analysis = json.dumps(value, default=str)
        else:
            self.entry_analysis = None

    @hybrid_property
    def exit_analysis_data(self):
        """Get exit analysis as dict"""
        if self.exit_analysis:
            try:
                return json.loads(self.exit_analysis)
            except json.JSONDecodeError:
                return {}
        return {}

    @exit_analysis_data.setter
    def exit_analysis_data(self, value):
        """Set exit analysis from dict"""
        if value:
            self.exit_analysis = json.dumps(value, default=str)
        else:
            self.exit_analysis = None

    def __repr__(self):
        return f"<PaperTrade id={self.id} symbol={self.symbol} pnl={self.pnl} winner={self.is_winner}>"


class PaperTradeAnalytics(Base):
    """Paper trade analytics model - aggregate performance metrics by period"""
    __tablename__ = 'paper_trade_analytics'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('paper_trading_sessions.id', ondelete='CASCADE'), nullable=False, index=True)

    # Period Definition
    period_type = Column(String(20), nullable=False, index=True)  # 'daily', 'weekly', 'monthly'
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)

    # Trade Statistics
    trades_count = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    losing_trades = Column(Integer, default=0, nullable=False)
    win_rate_pct = Column(Float, default=0.0, nullable=False)

    # P&L Metrics
    gross_profit = Column(Float, default=0.0, nullable=False)
    gross_loss = Column(Float, default=0.0, nullable=False)
    net_pnl = Column(Float, default=0.0, nullable=False)
    profit_factor = Column(Float, default=0.0, nullable=False)  # gross_profit / gross_loss

    # Performance Metrics
    avg_win = Column(Float, default=0.0, nullable=False)
    avg_loss = Column(Float, default=0.0, nullable=False)
    avg_r_multiple = Column(Float, default=0.0, nullable=False)
    best_trade_pnl = Column(Float, default=0.0, nullable=False)
    worst_trade_pnl = Column(Float, default=0.0, nullable=False)
    avg_hold_time_days = Column(Float, default=0.0, nullable=False)
    max_concurrent_positions = Column(Integer, default=0, nullable=False)

    # Capital Metrics
    starting_capital = Column(Float, nullable=False)
    ending_capital = Column(Float, nullable=False)
    period_return_pct = Column(Float, default=0.0, nullable=False)
    max_drawdown_pct = Column(Float, default=0.0, nullable=False)

    # Insights (JSON)
    exit_reasons_breakdown = Column(Text)  # JSON: {"STOP_LOSS": 5, "TARGET_HIT": 8, ...}
    insights = Column(Text)  # JSON: Generated recommendations and observations

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('session_id', 'period_type', 'period_start', name='uix_session_period'),
        Index('ix_analytics_period', 'period_type', 'period_start'),
    )

    # Relationships
    session = relationship("PaperTradingSession", back_populates="analytics")

    @hybrid_property
    def exit_breakdown(self):
        """Get exit reasons breakdown as dict"""
        if self.exit_reasons_breakdown:
            try:
                return json.loads(self.exit_reasons_breakdown)
            except json.JSONDecodeError:
                return {}
        return {}

    @exit_breakdown.setter
    def exit_breakdown(self, value):
        """Set exit reasons breakdown from dict"""
        if value:
            self.exit_reasons_breakdown = json.dumps(value)
        else:
            self.exit_reasons_breakdown = None

    @hybrid_property
    def insights_data(self):
        """Get insights as dict"""
        if self.insights:
            try:
                return json.loads(self.insights)
            except json.JSONDecodeError:
                return {}
        return {}

    @insights_data.setter
    def insights_data(self, value):
        """Set insights from dict"""
        if value:
            self.insights = json.dumps(value, default=str)
        else:
            self.insights = None

    def __repr__(self):
        return f"<PaperTradeAnalytics id={self.id} period={self.period_type} trades={self.trades_count} win_rate={self.win_rate_pct}%>"


class PaperTradingLog(Base):
    """Paper trading log model - detailed audit trail of all system actions"""
    __tablename__ = 'paper_trading_logs'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('paper_trading_sessions.id', ondelete='CASCADE'), nullable=False, index=True)

    # Log Entry
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    log_level = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR, TRADE
    category = Column(String(50), nullable=False, index=True)  # ENTRY, EXIT, MONITORING, ANALYSIS, ERROR
    symbol = Column(String(50), nullable=True, index=True)
    message = Column(Text, nullable=False)
    details = Column(Text)  # JSON: Flexible metadata

    # Optional References
    position_id = Column(Integer, ForeignKey('paper_positions.id', ondelete='SET NULL'), nullable=True)
    trade_id = Column(Integer, ForeignKey('paper_trades.id', ondelete='SET NULL'), nullable=True)

    # Indexes
    __table_args__ = (
        Index('ix_log_timestamp_level', 'timestamp', 'log_level'),
        Index('ix_log_category', 'category', 'timestamp'),
    )

    # Relationships
    session = relationship("PaperTradingSession", back_populates="logs")
    position = relationship("PaperPosition", backref="logs")
    trade = relationship("PaperTrade", backref="logs")

    @hybrid_property
    def details_data(self):
        """Get details as dict"""
        if self.details:
            try:
                return json.loads(self.details)
            except json.JSONDecodeError:
                return {}
        return {}

    @details_data.setter
    def details_data(self, value):
        """Set details from dict"""
        if value:
            self.details = json.dumps(value, default=str)
        else:
            self.details = None

    def __repr__(self):
        return f"<PaperTradingLog id={self.id} level={self.log_level} category={self.category} symbol={self.symbol}>"


class PendingPaperTrade(Base):
    """Pending paper trade model - queues trades to execute when market opens"""
    __tablename__ = 'pending_paper_trades'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('paper_trading_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    
    # Request Details
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    requested_by_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Signal/Analysis Data (stored as JSON)
    signal_data = Column(Text, nullable=False)  # JSON with analysis, recommendation, prices, etc.
    
    # Status
    status = Column(String(20), default='PENDING', nullable=False, index=True)  # PENDING, EXECUTED, FAILED, CANCELLED
    execution_attempts = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Execution Result
    position_id = Column(Integer, ForeignKey('paper_positions.id', ondelete='SET NULL'), nullable=True)
    executed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        Index('ix_pending_trade_status', 'status', 'requested_at'),
        Index('ix_pending_trade_session', 'session_id', 'status'),
    )
    
    # Relationships
    session = relationship("PaperTradingSession", backref="pending_trades")
    user = relationship("User", backref="pending_paper_trades")
    position = relationship("PaperPosition", backref="pending_trade")
    
    @hybrid_property
    def signal_data_dict(self):
        """Get signal data as dict"""
        if self.signal_data:
            try:
                return json.loads(self.signal_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @signal_data_dict.setter
    def signal_data_dict(self, value):
        """Set signal data from dict"""
        if value:
            self.signal_data = json.dumps(value, default=str)
        else:
            self.signal_data = None
    
    def __repr__(self):
        return f"<PendingPaperTrade id={self.id} symbol={self.symbol} status={self.status}>"


# =============================================================================
# Helper Functions
# =============================================================================

def create_tables(engine):
    """Create all tables in the database"""
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """Drop all tables from the database"""
    Base.metadata.drop_all(engine)
