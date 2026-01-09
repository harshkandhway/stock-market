"""
Unit tests for Telegram bot callback handlers
Tests all inline keyboard buttons to ensure they work correctly

Author: Harsh Kandhway
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, CallbackQuery, User, Message, Chat
from telegram.ext import ContextTypes

from src.bot.handlers.callbacks import (
    handle_callback_query,
    handle_analyze_refresh,
    handle_analyze_quick,
    handle_analyze_full,
    handle_watchlist_add,
    handle_watchlist_remove,
    handle_watchlist_menu,
    handle_watchlist_add_prompt,
    handle_watchlist_remove_prompt,
    handle_watchlist_analyze,
    handle_watchlist_clear_confirm,
    handle_alert_menu,
    handle_alert_price_setup,
    handle_alert_rsi_setup,
    handle_alert_signal_setup,
    handle_alert_delete,
    handle_alert_view,
    handle_alert_disable,
    handle_alert_enable,
    handle_alert_breakout,
    handle_alert_divergence,
    handle_alert_add_prompt,
    handle_alert_clear_all_confirm,
    handle_chart,
    handle_portfolio_add,
    handle_back,
    handle_close,
    handle_main_menu,
    handle_confirm,
    handle_cancel,
    handle_schedule,
)


class TestCallbackHandlers:
    """Test suite for callback handlers"""
    
    @pytest.fixture
    def mock_query(self):
        """Create a mock callback query"""
        query = Mock(spec=CallbackQuery)
        query.from_user = Mock(spec=User)
        query.from_user.id = 123456
        query.from_user.username = "testuser"
        query.data = "test_action:param1"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message = Mock(spec=Message)
        query.message.chat = Mock(spec=Chat)
        query.message.message_id = 1
        query.message.date = None
        return query
    
    @pytest.fixture
    def mock_update(self, mock_query):
        """Create a mock update"""
        update = Mock(spec=Update)
        update.callback_query = mock_query
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_analyze_refresh_handler(self, mock_query, mock_context):
        """Test refresh analysis button"""
        mock_query.data = "analyze:RELIANCE.NS"
        
        with patch('src.bot.handlers.callbacks.analyze_stock_with_settings') as mock_analyze, \
             patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.get_or_create_user'), \
             patch('src.bot.handlers.callbacks.get_user_settings') as mock_settings, \
             patch('src.bot.handlers.callbacks.format_analysis_beginner') as mock_format:
            
            # Mock database context
            mock_db.return_value.__enter__.return_value = Mock()
            
            # Mock settings
            mock_settings_obj = Mock()
            mock_settings_obj.beginner_mode = True
            mock_settings_obj.investment_horizon = '3months'
            mock_settings.return_value = mock_settings_obj
            
            # Mock analysis result
            mock_analyze.return_value = {
                'symbol': 'RELIANCE.NS',
                'current_price': 2500.0,
                'recommendation': 'BUY',
                'confidence': 75
            }
            
            # Mock formatter
            mock_format.return_value = "Analysis result"
            
            # Create update
            update = Mock()
            update.callback_query = mock_query
            
            # Test handler
            await handle_analyze_refresh(mock_query, mock_context, ['RELIANCE.NS'])
            
            # Verify
            assert mock_query.answer.called
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_watchlist_add_handler(self, mock_query, mock_context):
        """Test add to watchlist button"""
        mock_query.data = "watchlist_add:TCS.NS"
        
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.get_or_create_user'), \
             patch('src.bot.handlers.callbacks.get_user_watchlist') as mock_watchlist, \
             patch('src.bot.handlers.callbacks.add_to_watchlist') as mock_add:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_watchlist.return_value = []
            mock_add.return_value = True
            
            await handle_watchlist_add(mock_query, mock_context, ['TCS.NS'])
            
            assert mock_query.answer.called
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_chart_handler(self, mock_query, mock_context):
        """Test chart view button"""
        await handle_chart(mock_query, mock_context, ['RELIANCE.NS'])
        
        assert mock_query.answer.called
        assert mock_query.edit_message_text.called
        # Verify message contains chart info
        call_args = mock_query.edit_message_text.call_args
        assert 'RELIANCE.NS' in call_args[0][0] or 'chart' in call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_portfolio_add_handler(self, mock_query, mock_context):
        """Test add to portfolio button"""
        await handle_portfolio_add(mock_query, mock_context, ['TCS.NS'])
        
        assert mock_query.answer.called
        assert mock_query.edit_message_text.called
        # Verify message contains portfolio info
        call_args = mock_query.edit_message_text.call_args
        assert 'portfolio' in call_args[0][0].lower() or 'TCS.NS' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_settings_callbacks(self, mock_update, mock_context):
        """Test settings-related callbacks"""
        mock_update.callback_query.data = "settings_menu"
        
        with patch('src.bot.handlers.settings.handle_settings_callback') as mock_handler:
            mock_handler.return_value = AsyncMock()
            
            await handle_callback_query(mock_update, mock_context)
            
            # Settings callbacks are routed to settings handler
            assert mock_handler.called
    
    @pytest.mark.asyncio
    async def test_main_menu_callback(self, mock_query, mock_context):
        """Test main menu button"""
        mock_query.data = "main_menu"
        
        with patch('src.bot.handlers.callbacks.handle_main_menu') as mock_handler:
            mock_handler.return_value = AsyncMock()
            
            update = Mock()
            update.callback_query = mock_query
            
            await handle_callback_query(update, mock_context)
            
            assert mock_handler.called
    
    @pytest.mark.asyncio
    async def test_unknown_action(self, mock_query, mock_context):
        """Test unknown callback action"""
        mock_query.data = "unknown_action:param"
        
        update = Mock()
        update.callback_query = mock_query
        
        await handle_callback_query(update, mock_context)
        
        # Should show error message
        assert mock_query.edit_message_text.called
        call_args = mock_query.edit_message_text.call_args
        assert 'Unknown' in call_args[0][0] or 'error' in call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_watchlist_remove_handler(self, mock_query, mock_context):
        """Test remove from watchlist button"""
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.remove_from_watchlist') as mock_remove:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_remove.return_value = True
            
            await handle_watchlist_remove(mock_query, mock_context, ['TCS.NS'])
            
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_watchlist_menu_handler(self, mock_query, mock_context):
        """Test watchlist menu handler"""
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.get_user_watchlist') as mock_watchlist:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_watchlist.return_value = []
            
            await handle_watchlist_menu(mock_query, mock_context, [])
            
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_analyze_quick_handler(self, mock_query, mock_context):
        """Test quick analyze handler"""
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.get_or_create_user'), \
             patch('src.bot.handlers.callbacks.get_user_settings') as mock_settings, \
             patch('src.bot.handlers.callbacks.analyze_stock') as mock_analyze, \
             patch('src.bot.handlers.callbacks.format_analysis_summary') as mock_format:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_settings_obj = Mock()
            mock_settings_obj.risk_mode = 'balanced'
            mock_settings_obj.timeframe = 'medium'
            mock_settings.return_value = mock_settings_obj
            
            mock_analyze.return_value = {'status': 'success', 'data': {}}
            mock_format.return_value = "Analysis summary"
            
            await handle_analyze_quick(mock_query, mock_context, ['RELIANCE.NS'])
            
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_analyze_full_handler(self, mock_query, mock_context):
        """Test full analyze handler"""
        await handle_analyze_full(mock_query, mock_context, ['RELIANCE.NS'])
        
        assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_alert_menu_handler(self, mock_query, mock_context):
        """Test alert menu handler"""
        await handle_alert_menu(mock_query, mock_context, ['RELIANCE.NS'])
        
        assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_alert_price_setup_handler(self, mock_query, mock_context):
        """Test alert price setup handler"""
        with patch('src.bot.handlers.callbacks.get_current_price') as mock_price:
            mock_price.return_value = 2500.0
            
            await handle_alert_price_setup(mock_query, mock_context, ['RELIANCE.NS'])
            
            assert mock_query.edit_message_text.called
            assert 'awaiting_price_alert' in mock_context.user_data
    
    @pytest.mark.asyncio
    async def test_alert_rsi_setup_handler(self, mock_query, mock_context):
        """Test alert RSI setup handler"""
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.get_or_create_user'), \
             patch('src.bot.handlers.callbacks.create_alert') as mock_create:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_create.return_value = Mock()
            
            await handle_alert_rsi_setup(mock_query, mock_context, ['RELIANCE.NS'])
            
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_alert_signal_setup_handler(self, mock_query, mock_context):
        """Test alert signal setup handler"""
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.get_or_create_user'), \
             patch('src.bot.handlers.callbacks.create_alert') as mock_create:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_create.return_value = Mock()
            
            await handle_alert_signal_setup(mock_query, mock_context, ['RELIANCE.NS'])
            
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_alert_delete_handler(self, mock_query, mock_context):
        """Test alert delete handler"""
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.delete_alert') as mock_delete:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_delete.return_value = True
            
            await handle_alert_delete(mock_query, mock_context, ['1'])
            
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_back_handler(self, mock_query, mock_context):
        """Test back button handler"""
        with patch('src.bot.handlers.callbacks.handle_watchlist_menu') as mock_watchlist:
            await handle_back(mock_query, mock_context, ['watchlist'])
            
            assert mock_watchlist.called
    
    @pytest.mark.asyncio
    async def test_close_handler(self, mock_query, mock_context):
        """Test close button handler"""
        await handle_close(mock_query, mock_context)
        
        assert mock_query.message.delete.called
    
    @pytest.mark.asyncio
    async def test_main_menu_handler(self, mock_query, mock_context):
        """Test main menu handler"""
        await handle_main_menu(mock_query, mock_context)
        
        assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_confirm_handler(self, mock_query, mock_context):
        """Test confirm handler"""
        with patch('src.bot.handlers.callbacks.confirm_settings_reset') as mock_reset:
            await handle_confirm(mock_query, mock_context, ['confirm_settings_reset'])
            
            # Should call confirm function or show success
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_cancel_handler(self, mock_query, mock_context):
        """Test cancel handler"""
        await handle_cancel(mock_query, mock_context, [])
        
        assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_watchlist_add_prompt_handler(self, mock_query, mock_context):
        """Test watchlist add prompt handler"""
        await handle_watchlist_add_prompt(mock_query, mock_context)
        
        assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_watchlist_remove_prompt_handler(self, mock_query, mock_context):
        """Test watchlist remove prompt handler"""
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.get_user_watchlist') as mock_watchlist:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_watchlist.return_value = []
            
            await handle_watchlist_remove_prompt(mock_query, mock_context)
            
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_alert_breakout_handler(self, mock_query, mock_context):
        """Test alert breakout handler"""
        await handle_alert_breakout(mock_query, mock_context, ['RELIANCE.NS'])
        
        assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_alert_divergence_handler(self, mock_query, mock_context):
        """Test alert divergence handler"""
        await handle_alert_divergence(mock_query, mock_context, ['RELIANCE.NS'])
        
        assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_alert_view_handler(self, mock_query, mock_context):
        """Test alert view handler"""
        mock_alert = Mock()
        mock_alert.user_id = 123456
        mock_alert.symbol = 'RELIANCE.NS'
        mock_alert.alert_type = 'price'
        mock_alert.condition = {}
        mock_alert.is_active = True
        
        with patch('src.bot.handlers.callbacks.get_db_context') as mock_db, \
             patch('src.bot.handlers.callbacks.get_alert_by_id') as mock_get_alert:
            
            mock_db.return_value.__enter__.return_value = Mock()
            mock_get_alert.return_value = mock_alert
            
            await handle_alert_view(mock_query, mock_context, ['1'])
            
            assert mock_query.edit_message_text.called
    
    @pytest.mark.asyncio
    async def test_schedule_handler(self, mock_query, mock_context):
        """Test schedule handler"""
        await handle_schedule(mock_query, mock_context, 'schedule_daily', [])
        
        assert mock_query.edit_message_text.called


class TestButtonCallbacks:
    """Test all button callback data formats"""
    
    def test_analyze_button_format(self):
        """Verify analyze button callback format"""
        from src.bot.utils.keyboards import create_analysis_action_keyboard
        
        keyboard = create_analysis_action_keyboard("RELIANCE.NS")
        
        # Check that refresh button exists
        buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                buttons.append(button.callback_data)
        
        assert any("analyze:RELIANCE.NS" in cb for cb in buttons), "Refresh Analysis button missing"
    
    def test_watchlist_button_formats(self):
        """Verify watchlist button formats"""
        from src.bot.utils.keyboards import create_watchlist_menu_keyboard
        
        keyboard = create_watchlist_menu_keyboard()
        
        buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                buttons.append(button.callback_data)
        
        # Check key buttons exist
        assert any("watchlist_add" in cb for cb in buttons), "Add button missing"
        assert any("watchlist_show" in cb for cb in buttons), "View button missing"
        assert any("main_menu" in cb for cb in buttons), "Back button missing"
    
    def test_settings_button_formats(self):
        """Verify settings button formats"""
        from src.bot.utils.keyboards import create_settings_menu_keyboard
        
        keyboard = create_settings_menu_keyboard()
        
        buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                buttons.append(button.callback_data)
        
        # Check key buttons exist
        assert any("settings_horizon" in cb for cb in buttons), "Horizon button missing"
        assert any("settings_risk_mode" in cb for cb in buttons), "Risk mode button missing"
        assert any("settings_capital" in cb for cb in buttons), "Capital button missing"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

