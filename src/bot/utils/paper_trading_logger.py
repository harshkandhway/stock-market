"""
Paper Trading Logger
Setup comprehensive logging for paper trading system

Author: Harsh Kandhway
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from datetime import datetime
from pathlib import Path


def setup_paper_trading_logger():
    """
    Setup comprehensive logging for paper trading system

    Log Files:
    1. logs/paper_trading/trades.log - Trade executions (rotating daily, 30 days retention)
    2. logs/paper_trading/performance.log - Performance metrics (rotating daily, 90 days retention)
    3. logs/paper_trading/errors.log - Errors only (rotating weekly, 12 weeks retention)
    4. logs/paper_trading/audit.log - Complete audit trail (never rotates, append only)

    Returns:
        Configured logger instance
    """
    # Create log directory
    log_dir = Path(__file__).parent.parent.parent / 'logs' / 'paper_trading'
    log_dir.mkdir(parents=True, exist_ok=True)

    # Main paper trading logger
    pt_logger = logging.getLogger('paper_trading')
    pt_logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if pt_logger.handlers:
        return pt_logger

    # Formatters
    standard_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    detailed_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    audit_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)06d | AUDIT | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Trade execution log (daily rotation, keep 30 days)
    trade_handler = TimedRotatingFileHandler(
        filename=str(log_dir / 'trades.log'),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    trade_handler.setLevel(logging.INFO)
    trade_handler.setFormatter(standard_formatter)
    trade_handler.addFilter(TradeFilter())  # Only trade-related logs

    # 2. Performance log (daily rotation, keep 90 days)
    perf_handler = TimedRotatingFileHandler(
        filename=str(log_dir / 'performance.log'),
        when='midnight',
        interval=1,
        backupCount=90,
        encoding='utf-8'
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(standard_formatter)
    perf_handler.addFilter(PerformanceFilter())  # Only performance-related logs

    # 3. Error log (weekly rotation, keep 12 weeks)
    error_handler = TimedRotatingFileHandler(
        filename=str(log_dir / 'errors.log'),
        when='W0',  # Monday
        interval=1,
        backupCount=12,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # 4. Audit trail (append only, never rotates)
    audit_handler = RotatingFileHandler(
        filename=str(log_dir / 'audit.log'),
        mode='a',
        maxBytes=100 * 1024 * 1024,  # 100 MB
        backupCount=10,  # Keep 10 backup files (1 GB total)
        encoding='utf-8'
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(audit_formatter)
    audit_handler.addFilter(AuditFilter())  # Only audit-related logs

    # Console handler for development (optional)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(standard_formatter)

    # Add handlers
    pt_logger.addHandler(trade_handler)
    pt_logger.addHandler(perf_handler)
    pt_logger.addHandler(error_handler)
    pt_logger.addHandler(audit_handler)
    pt_logger.addHandler(console_handler)

    # Prevent propagation to root logger
    pt_logger.propagate = False

    return pt_logger


class TradeFilter(logging.Filter):
    """Filter for trade execution logs"""
    def filter(self, record):
        # Log entries with 'ENTRY', 'EXIT', 'TRADE' in message or category
        message = record.getMessage()
        return any(keyword in message.upper() for keyword in ['ENTRY', 'EXIT', 'TRADE', 'POSITION'])


class PerformanceFilter(logging.Filter):
    """Filter for performance-related logs"""
    def filter(self, record):
        # Log entries with performance keywords
        message = record.getMessage()
        keywords = ['PERFORMANCE', 'ANALYTICS', 'SUMMARY', 'METRICS', 'WIN RATE', 'PROFIT FACTOR', 'P&L']
        return any(keyword in message.upper() for keyword in keywords)


class AuditFilter(logging.Filter):
    """Filter for audit trail logs"""
    def filter(self, record):
        # Log all INFO and above for audit trail
        return record.levelno >= logging.INFO


# Global logger instance
_paper_trading_logger = None


def get_paper_trading_logger():
    """
    Get or create paper trading logger instance

    Returns:
        Configured logger instance
    """
    global _paper_trading_logger
    if _paper_trading_logger is None:
        _paper_trading_logger = setup_paper_trading_logger()
    return _paper_trading_logger


# Convenience functions for common log operations
def log_trade_entry(symbol: str, entry_price: float, shares: int, **kwargs):
    """Log trade entry"""
    logger = get_paper_trading_logger()
    details = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(
        f"ENTRY | {symbol} | Entry: ₹{entry_price:.2f} | Shares: {shares} | {details}"
    )


def log_trade_exit(symbol: str, exit_price: float, pnl: float, pnl_pct: float, exit_reason: str, **kwargs):
    """Log trade exit"""
    logger = get_paper_trading_logger()
    details = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(
        f"EXIT | {symbol} | Exit: ₹{exit_price:.2f} | P&L: ₹{pnl:+,.2f} ({pnl_pct:+.2f}%) | "
        f"Reason: {exit_reason} | {details}"
    )


def log_performance(metric: str, value: float, **kwargs):
    """Log performance metric"""
    logger = get_paper_trading_logger()
    details = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"PERFORMANCE | {metric}: {value} | {details}")


def log_audit(action: str, session_id: int, **kwargs):
    """Log audit trail entry"""
    logger = get_paper_trading_logger()
    details = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"AUDIT | SESSION:{session_id} | ACTION:{action} | {details}")


