"""
Database Migration: Add On-Demand Signals Tables
Creates user_signal_requests and user_signal_responses tables

Run: python3 -m src.bot.database.migrations.add_on_demand_signals

Author: Harsh Kandhway
Date: January 19, 2026
"""

import logging
from sqlalchemy import create_engine, text
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.bot.config import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    """Create on-demand signals tables"""
    logger.info("Starting migration: add_on_demand_signals")
    logger.info(f"Database: {DATABASE_URL}")
    
    engine = create_engine(DATABASE_URL, echo=True)
    
    try:
        with engine.begin() as conn:
            # Create user_signal_requests table
            logger.info("Creating user_signal_requests table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_signal_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    request_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    sectors TEXT,
                    market_caps TEXT,
                    include_etf BOOLEAN DEFAULT 0,
                    min_confidence FLOAT DEFAULT 70.0,
                    min_risk_reward FLOAT DEFAULT 2.0,
                    recommendation_types TEXT DEFAULT '["STRONG BUY", "BUY"]',
                    total_stocks_analyzed INTEGER,
                    total_signals_found INTEGER,
                    signals_sent INTEGER,
                    analysis_duration_seconds FLOAT,
                    cached BOOLEAN DEFAULT 0,
                    error_message TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )
            """))
            
            # Create user_signal_responses table
            logger.info("Creating user_signal_responses table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_signal_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    recommendation_type TEXT NOT NULL,
                    confidence FLOAT NOT NULL,
                    risk_reward FLOAT NOT NULL,
                    current_price FLOAT NOT NULL,
                    target FLOAT,
                    stop_loss FLOAT,
                    sector TEXT,
                    market_cap TEXT,
                    is_etf BOOLEAN DEFAULT 0,
                    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES user_signal_requests(id),
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )
            """))
            
            # Create indices for performance
            logger.info("Creating indices...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_signal_requests_user_id 
                ON user_signal_requests(user_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_signal_requests_timestamp 
                ON user_signal_requests(request_timestamp)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_signal_responses_request_id 
                ON user_signal_responses(request_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_signal_responses_user_id 
                ON user_signal_responses(user_id)
            """))
        
        logger.info("✅ Migration complete: on-demand signals tables created")
        logger.info("Tables created:")
        logger.info("  - user_signal_requests")
        logger.info("  - user_signal_responses")
        logger.info("Indices created:")
        logger.info("  - idx_user_signal_requests_user_id")
        logger.info("  - idx_user_signal_requests_timestamp")
        logger.info("  - idx_user_signal_responses_request_id")
        logger.info("  - idx_user_signal_responses_user_id")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise


def downgrade():
    """Drop on-demand signals tables"""
    logger.info("Starting downgrade: remove on-demand signals tables")
    
    engine = create_engine(DATABASE_URL, echo=True)
    
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS user_signal_responses"))
            conn.execute(text("DROP TABLE IF NOT EXISTS user_signal_requests"))
        
        logger.info("✅ Downgrade complete: on-demand signals tables removed")
        
    except Exception as e:
        logger.error(f"❌ Downgrade failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration for on-demand signals")
    parser.add_argument('--downgrade', action='store_true', help='Downgrade (remove tables)')
    args = parser.parse_args()
    
    if args.downgrade:
        downgrade()
    else:
        upgrade()
