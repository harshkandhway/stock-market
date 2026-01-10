"""
Test Bot Keyboard Utilities
Tests for all keyboard creation functions
"""

import pytest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from src.bot.utils.keyboards import (
    create_main_menu_keyboard,
    create_analysis_action_keyboard,
    create_watchlist_menu_keyboard,
    create_watchlist_item_keyboard,
    create_alert_type_keyboard,
    create_alert_list_keyboard,
    create_alert_action_keyboard,
    create_settings_menu_keyboard,
    create_risk_mode_keyboard,
    create_timeframe_keyboard,
    create_horizon_keyboard,
    create_back_button,
    create_confirmation_keyboard,
    create_pagination_keyboard
)


class TestMainMenuKeyboard:
    """Test main menu keyboard"""
    
    def test_create_main_menu_keyboard(self):
        """Test main menu keyboard creation"""
        keyboard = create_main_menu_keyboard()
        
        assert isinstance(keyboard, ReplyKeyboardMarkup)
        assert len(keyboard.keyboard) > 0
        # Should have buttons for main actions
        all_buttons = [btn.text for row in keyboard.keyboard for btn in row]
        assert len(all_buttons) > 0


class TestAnalysisKeyboards:
    """Test analysis-related keyboards"""
    
    def test_create_analysis_action_keyboard(self):
        """Test analysis action keyboard creation"""
        symbol = "RELIANCE.NS"
        keyboard = create_analysis_action_keyboard(symbol)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
        
        # Check that symbol is in callback data
        all_callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_callbacks.append(button.callback_data)
        
        # Should have actions related to the symbol
        assert any(symbol in cb for cb in all_callbacks if cb)


class TestWatchlistKeyboards:
    """Test watchlist-related keyboards"""
    
    def test_create_watchlist_menu_keyboard_empty(self):
        """Test watchlist menu keyboard with empty list"""
        keyboard = create_watchlist_menu_keyboard(symbols=[])
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
    
    def test_create_watchlist_menu_keyboard_with_symbols(self):
        """Test watchlist menu keyboard with symbols"""
        symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
        keyboard = create_watchlist_menu_keyboard(symbols=symbols)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
        
        # Check that symbols appear in keyboard
        all_callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_callbacks.append(button.callback_data)
        
        # Should have watchlist actions
        assert any("watchlist" in cb.lower() for cb in all_callbacks if cb)
    
    def test_create_watchlist_item_keyboard(self):
        """Test watchlist item keyboard"""
        symbol = "RELIANCE.NS"
        keyboard = create_watchlist_item_keyboard(symbol)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
        
        # Check that symbol is in callback data
        all_callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_callbacks.append(button.callback_data)
        
        assert any(symbol in cb for cb in all_callbacks if cb)


class TestAlertKeyboards:
    """Test alert-related keyboards"""
    
    def test_create_alert_type_keyboard(self):
        """Test alert type keyboard creation"""
        symbol = "NIFTYBEES.NS"
        keyboard = create_alert_type_keyboard(symbol)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
        
        # Check that symbol is in callback data
        all_callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_callbacks.append(button.callback_data)
        
        assert any(symbol in cb for cb in all_callbacks if cb)
        # Should have alert type options
        assert any("alert" in cb.lower() for cb in all_callbacks if cb)
    
    def test_create_alert_list_keyboard(self):
        """Test alert list keyboard"""
        alerts = [
            {"id": 1, "symbol": "RELIANCE.NS", "alert_type": "price", "is_active": True},
            {"id": 2, "symbol": "TCS.NS", "alert_type": "rsi", "is_active": False}
        ]
        keyboard = create_alert_list_keyboard(alerts)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
    
    def test_create_alert_action_keyboard(self):
        """Test alert action keyboard"""
        alert_id = 123
        keyboard = create_alert_action_keyboard(alert_id)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
        
        # Check that alert_id is in callback data
        all_callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_callbacks.append(button.callback_data)
        
        assert any(str(alert_id) in cb for cb in all_callbacks if cb)


class TestSettingsKeyboards:
    """Test settings-related keyboards"""
    
    def test_create_settings_menu_keyboard(self):
        """Test settings menu keyboard"""
        keyboard = create_settings_menu_keyboard()
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
        
        # Should have settings options
        all_callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_callbacks.append(button.callback_data)
        
        assert any("settings" in cb.lower() for cb in all_callbacks if cb)
    
    def test_create_risk_mode_keyboard(self):
        """Test risk mode keyboard"""
        current_mode = "balanced"
        keyboard = create_risk_mode_keyboard(current_mode)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
        
        # Should have risk mode options
        all_callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_callbacks.append(button.callback_data)
        
        assert any("risk_mode" in cb.lower() or "mode" in cb.lower() for cb in all_callbacks if cb)
    
    def test_create_timeframe_keyboard(self):
        """Test timeframe keyboard"""
        current_timeframe = "medium"
        keyboard = create_timeframe_keyboard(current_timeframe)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
    
    def test_create_horizon_keyboard(self):
        """Test horizon keyboard"""
        current_horizon = "3months"
        keyboard = create_horizon_keyboard(current_horizon)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0


class TestUtilityKeyboards:
    """Test utility keyboards"""
    
    def test_create_back_button(self):
        """Test back button creation"""
        keyboard = create_back_button()
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1
        
        button = keyboard.inline_keyboard[0][0]
        assert "back" in button.callback_data.lower() or "menu" in button.callback_data.lower()
    
    def test_create_back_button_custom(self):
        """Test back button with custom callback"""
        custom_callback = "custom:action"
        keyboard = create_back_button(callback_data=custom_callback)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        button = keyboard.inline_keyboard[0][0]
        assert button.callback_data == custom_callback
    
    def test_create_confirmation_keyboard(self):
        """Test confirmation keyboard"""
        action = "delete"
        data = "alert:123"
        keyboard = create_confirmation_keyboard(action, data)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
        
        # Should have confirm and cancel buttons
        all_callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_callbacks.append(button.callback_data)
        
        assert any("confirm" in cb.lower() for cb in all_callbacks if cb)
        assert any("cancel" in cb.lower() for cb in all_callbacks if cb)
    
    def test_create_pagination_keyboard(self):
        """Test pagination keyboard"""
        current_page = 1
        total_pages = 5
        callback_prefix = "list"
        keyboard = create_pagination_keyboard(current_page, total_pages, callback_prefix)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
        
        # Should have navigation buttons
        all_callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_callbacks.append(button.callback_data)
        
        # Should have page navigation
        assert any("page" in cb.lower() or str(current_page) in cb for cb in all_callbacks if cb)


class TestKeyboardEdgeCases:
    """Test keyboard edge cases"""
    
    def test_watchlist_keyboard_large_list(self):
        """Test watchlist keyboard with many symbols"""
        symbols = [f"STOCK{i}.NS" for i in range(50)]
        keyboard = create_watchlist_menu_keyboard(symbols=symbols)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Should handle large lists gracefully
        assert len(keyboard.inline_keyboard) > 0
    
    def test_alert_list_keyboard_empty(self):
        """Test alert list keyboard with empty list"""
        keyboard = create_alert_list_keyboard([])
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Should handle empty list gracefully
    
    def test_pagination_keyboard_single_page(self):
        """Test pagination keyboard with single page"""
        keyboard = create_pagination_keyboard(1, 1, "test")
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Should handle single page gracefully
    
    def test_pagination_keyboard_first_page(self):
        """Test pagination keyboard on first page"""
        keyboard = create_pagination_keyboard(1, 5, "test")
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Should not have "previous" button on first page
    
    def test_pagination_keyboard_last_page(self):
        """Test pagination keyboard on last page"""
        keyboard = create_pagination_keyboard(5, 5, "test")
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Should not have "next" button on last page

