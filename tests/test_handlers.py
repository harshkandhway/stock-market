"""
Unit tests for bot handlers
Tests search, compare, schedule, and backtest handlers
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, Message, User, Chat

from src.bot.handlers.search import search_command
from src.bot.handlers.compare import compare_command
from src.bot.handlers.schedule import schedule_command, show_scheduled_reports
from src.bot.handlers.backtest import backtest_command


class TestSearchHandler:
    """Test cases for search handler"""
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.message = Mock(spec=Message)
        update.message.text = "/search reliance"
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context"""
        context = Mock()
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_search_command_no_args(self, mock_update, mock_context):
        """Test search command with no arguments"""
        mock_update.message.text = "/search"
        
        await search_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_search_command_with_keyword(self, mock_update, mock_context):
        """Test search command with keyword"""
        with patch('src.bot.handlers.search.search_symbol') as mock_search:
            mock_search.return_value = [
                {'symbol': 'RELIANCE.NS', 'name': 'Reliance Industries', 'exchange': 'NSE'}
            ]
            
            # Mock edit_text for the searching message
            mock_msg = Mock()
            mock_msg.edit_text = AsyncMock()
            mock_update.message.reply_text.return_value = mock_msg
            
            await search_command(mock_update, mock_context)
            
            assert mock_update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_search_command_no_results(self, mock_update, mock_context):
        """Test search command with no results"""
        with patch('src.bot.handlers.search.search_symbol') as mock_search:
            mock_search.return_value = []
            
            mock_msg = Mock()
            mock_msg.edit_text = AsyncMock()
            mock_update.message.reply_text.return_value = mock_msg
            
            await search_command(mock_update, mock_context)
            
            assert mock_update.message.reply_text.called


class TestCompareHandler:
    """Test cases for compare handler"""
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.effective_user.username = "testuser"
        update.message = Mock(spec=Message)
        update.message.text = "/compare RELIANCE.NS TCS.NS"
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context"""
        context = Mock()
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_compare_command_no_args(self, mock_update, mock_context):
        """Test compare command with no arguments"""
        mock_update.message.text = "/compare"
        
        await compare_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_compare_command_one_symbol(self, mock_update, mock_context):
        """Test compare command with only one symbol"""
        mock_update.message.text = "/compare RELIANCE.NS"
        
        await compare_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_compare_command_too_many_symbols(self, mock_update, mock_context):
        """Test compare command with too many symbols"""
        mock_update.message.text = "/compare STOCK1 STOCK2 STOCK3 STOCK4 STOCK5 STOCK6"
        
        await compare_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_compare_command_valid(self, mock_update, mock_context):
        """Test compare command with valid symbols"""
        with patch('src.bot.handlers.compare.get_db_context') as mock_db, \
             patch('src.bot.handlers.compare.get_or_create_user'), \
             patch('src.bot.handlers.compare.get_user_settings') as mock_settings, \
             patch('src.bot.handlers.compare.analyze_multiple_stocks') as mock_analyze, \
             patch('src.bot.handlers.compare.validate_stock_symbol') as mock_validate:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_settings.return_value = Mock()
            mock_settings.return_value.risk_mode = 'balanced'
            mock_settings.return_value.timeframe = 'medium'
            mock_validate.return_value = (True, None)
            
            mock_analyze.return_value = [
                {'symbol': 'RELIANCE.NS', 'confidence': 75},
                {'symbol': 'TCS.NS', 'confidence': 80}
            ]
            
            mock_msg = Mock()
            mock_msg.edit_text = AsyncMock()
            mock_update.message.reply_text.return_value = mock_msg
            
            await compare_command(mock_update, mock_context)
            
            assert mock_update.message.reply_text.called


class TestScheduleHandler:
    """Test cases for schedule handler"""
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.message = Mock(spec=Message)
        update.message.text = "/schedule"
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context"""
        context = Mock()
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_schedule_command_no_args(self, mock_update, mock_context):
        """Test schedule command with no arguments"""
        with patch('src.bot.handlers.schedule.show_scheduled_reports') as mock_show:
            await schedule_command(mock_update, mock_context)
            
            assert mock_show.called
    
    @pytest.mark.asyncio
    async def test_show_scheduled_reports_empty(self, mock_update, mock_context):
        """Test showing scheduled reports when empty"""
        with patch('src.bot.handlers.schedule.get_db_context') as mock_db, \
             patch('src.bot.handlers.schedule.get_or_create_user'), \
             patch('src.bot.handlers.schedule.get_user_scheduled_reports') as mock_get:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_get.return_value = []
            
            await show_scheduled_reports(mock_update, mock_context)
            
            assert mock_update.message.reply_text.called


class TestBacktestHandler:
    """Test cases for backtest handler"""
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock update"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.message = Mock(spec=Message)
        update.message.text = "/backtest RELIANCE.NS 30"
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context"""
        context = Mock()
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_backtest_command_no_args(self, mock_update, mock_context):
        """Test backtest command with no arguments"""
        mock_update.message.text = "/backtest"
        
        await backtest_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
    
    @pytest.mark.asyncio
    async def test_backtest_command_invalid_days(self, mock_update, mock_context):
        """Test backtest command with invalid days"""
        mock_update.message.text = "/backtest RELIANCE.NS invalid"
        
        await backtest_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called

