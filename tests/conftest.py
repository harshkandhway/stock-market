"""
Shared pytest fixtures for bot tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from telegram import Update, CallbackQuery, User, Message, Chat
from telegram.ext import ContextTypes


@pytest.fixture
def mock_user():
    """Create a mock Telegram user"""
    user = Mock(spec=User)
    user.id = 123456
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    return user


@pytest.fixture
def mock_chat():
    """Create a mock Telegram chat"""
    chat = Mock(spec=Chat)
    chat.id = -123456789
    chat.type = "private"
    return chat


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Create a mock Telegram message"""
    message = Mock(spec=Message)
    message.message_id = 1
    message.date = None
    message.chat = mock_chat
    message.from_user = mock_user
    message.text = "/test"
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()
    message.delete = AsyncMock()
    return message


@pytest.fixture
def mock_query(mock_user, mock_message):
    """Create a mock callback query"""
    query = Mock(spec=CallbackQuery)
    query.from_user = mock_user
    query.data = "test_action:param1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.message = mock_message
    return query


@pytest.fixture
def mock_update(mock_query):
    """Create a mock update"""
    update = Mock(spec=Update)
    update.update_id = 1
    update.callback_query = mock_query
    update.message = None
    return update


@pytest.fixture
def mock_context():
    """Create a mock context"""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.bot_data = {}
    context.chat_data = {}
    return context


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_db_context(mock_db_session):
    """Create a mock database context manager"""
    from contextlib import contextmanager
    
    @contextmanager
    def db_context():
        yield mock_db_session
    
    return db_context

