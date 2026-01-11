"""
Test Bot Command Handlers
Critical tests for command handlers focusing on:
- Command parsing and routing
- Database operations in commands
- Message formatting
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

from src.bot.handlers.start import (
    start_command,
    help_command
)
from src.bot.handlers.watchlist import watchlist_command
from src.bot.handlers.alerts import alerts_command, alert_command
from src.bot.handlers.settings import settings_command
from src.bot.database.db import get_or_create_user, get_user_settings


class TestStartCommand:
    """Test /start command handler"""
    
    @pytest.fixture
    def mock_update(self):
        """Create mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        update.message.chat = Mock(spec=Chat)
        update.message.chat.id = 123456
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        context.bot_data = {}
        return context
    
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
    
    @pytest.mark.asyncio
    async def test_start_command_new_user(self, mock_update, mock_context, test_db):
        """Test /start command for new user"""
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.start.get_db_context', test_db_context):
            await start_command(mock_update, mock_context)
        
        # Verify user created
        user = get_or_create_user(test_db, telegram_id=123456)
        assert user.telegram_id == 123456
        assert user.username == "testuser"
        
        # Verify settings created
        settings = get_user_settings(test_db, telegram_id=123456)
        assert settings is not None
        
        # Verify welcome message sent
        mock_update.message.reply_text.assert_called_once()
        message = mock_update.message.reply_text.call_args[0][0]
        assert "Welcome" in message or "welcome" in message.lower()
    
    @pytest.mark.asyncio
    async def test_start_command_existing_user(self, mock_update, mock_context, test_db):
        """Test /start command for existing user"""
        # Create user first
        get_or_create_user(test_db, telegram_id=123456, username="existing")
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.start.get_db_context', test_db_context):
            await start_command(mock_update, mock_context)
        
        # Verify welcome message sent
        mock_update.message.reply_text.assert_called_once()


class TestHelpCommand:
    """Test /help command handler"""
    
    @pytest.fixture
    def mock_update(self):
        """Create mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_update, mock_context):
        """Test /help command displays help message"""
        await help_command(mock_update, mock_context)
        
        # Verify help message sent
        mock_update.message.reply_text.assert_called_once()
        message = mock_update.message.reply_text.call_args[0][0]
        assert len(message) > 0  # Help message should not be empty


class TestWatchlistCommand:
    """Test /watchlist command handler"""
    
    @pytest.fixture
    def mock_update(self):
        """Create mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
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
    
    @pytest.mark.asyncio
    async def test_watchlist_command_empty(self, mock_update, mock_context, test_db):
        """Test /watchlist command with empty watchlist"""
        # Create user first
        get_or_create_user(test_db, telegram_id=123456, username="testuser")
        test_db.commit()
        
        from contextlib import contextmanager
        @contextmanager
        def test_db_context():
            yield test_db
        
        with patch('src.bot.handlers.watchlist.get_db_context', test_db_context):
            await watchlist_command(mock_update, mock_context)
        
        # Verify message sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args.kwargs.get('text', '')
        assert len(message) > 0  # Message should not be empty

