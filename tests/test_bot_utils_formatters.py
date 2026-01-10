"""
Test Bot Utility Formatters
Tests for message formatting functions
"""

import pytest

from src.bot.utils.formatters import (
    format_success,
    format_error,
    format_warning,
    format_watchlist,
    format_alert,
    format_alert_list
)


class TestFormatters:
    """Test formatter functions"""
    
    # ========================================================================
    # Basic Formatters
    # ========================================================================
    
    def test_format_success(self):
        """Test success message formatting"""
        message = format_success("Alert created successfully")
        assert "Alert created successfully" in message
        assert "✓" in message or "✅" in message or "Success" in message
    
    def test_format_error(self):
        """Test error message formatting"""
        message = format_error("Invalid symbol")
        assert "Invalid symbol" in message
        assert "❌" in message or "Error" in message or "✗" in message
    
    def test_format_warning(self):
        """Test warning message formatting"""
        message = format_warning("Price seems high")
        assert "Price seems high" in message
        assert "⚠" in message or "Warning" in message
    
    # ========================================================================
    # Watchlist Formatter
    # ========================================================================
    
    def test_format_watchlist_empty(self):
        """Test formatting empty watchlist"""
        message = format_watchlist([])
        assert "watchlist" in message.lower() or "empty" in message.lower() or "no" in message.lower()
    
    def test_format_watchlist_with_symbols(self):
        """Test formatting watchlist with symbols"""
        watchlist = [
            {'symbol': 'RELIANCE.NS', 'added_at': '2026-01-09'},
            {'symbol': 'TCS.NS', 'added_at': '2026-01-09'},
        ]
        
        message = format_watchlist(watchlist)
        assert 'RELIANCE.NS' in message
        assert 'TCS.NS' in message
    
    # ========================================================================
    # Alert Formatters
    # ========================================================================
    
    def test_format_alert_price(self):
        """Test formatting price alert"""
        alert = {
            'id': 1,
            'symbol': 'RELIANCE.NS',
            'alert_type': 'price',
            'condition_type': 'above',
            'threshold_value': 100.0,
            'is_active': True
        }
        
        message = format_alert(alert)
        assert 'RELIANCE.NS' in message
        assert 'price' in message.lower() or '₹' in message or '100' in message
    
    def test_format_alert_rsi(self):
        """Test formatting RSI alert"""
        alert = {
            'id': 2,
            'symbol': 'TCS.NS',
            'alert_type': 'rsi',
            'condition_type': 'below',
            'threshold_value': 30.0,
            'is_active': True
        }
        
        message = format_alert(alert)
        assert 'TCS.NS' in message
        assert 'rsi' in message.lower() or 'RSI' in message
    
    def test_format_alert_signal_change(self):
        """Test formatting signal change alert"""
        alert = {
            'id': 3,
            'symbol': 'NIFTYBEES.NS',
            'alert_type': 'signal_change',
            'condition_type': 'change',
            'is_active': True
        }
        
        message = format_alert(alert)
        assert 'NIFTYBEES.NS' in message
        assert 'signal' in message.lower() or 'change' in message.lower()
    
    def test_format_alert_list_empty(self):
        """Test formatting empty alert list"""
        message = format_alert_list([])
        assert "alert" in message.lower() and ("no" in message.lower() or "empty" in message.lower())
    
    def test_format_alert_list_multiple(self):
        """Test formatting multiple alerts"""
        alerts = [
            {
                'id': 1,
                'symbol': 'RELIANCE.NS',
                'alert_type': 'price',
                'condition_type': 'above',
                'threshold_value': 100.0,
                'is_active': True
            },
            {
                'id': 2,
                'symbol': 'TCS.NS',
                'alert_type': 'rsi',
                'condition_type': 'below',
                'threshold_value': 30.0,
                'is_active': True
            }
        ]
        
        message = format_alert_list(alerts)
        assert 'RELIANCE.NS' in message
        assert 'TCS.NS' in message
        assert len(message) > 0
    
    # ========================================================================
    # Message Length Tests
    # ========================================================================
    
    def test_format_watchlist_message_length(self):
        """Test that watchlist messages don't exceed Telegram limits"""
        # Create large watchlist
        watchlist = [
            {'symbol': f'SYMBOL{i}.NS', 'added_at': '2026-01-09'}
            for i in range(50)
        ]
        
        message = format_watchlist(watchlist)
        # Telegram message limit is 4096 characters
        assert len(message) <= 4096, f"Message too long: {len(message)} characters"
    
    def test_format_alert_list_message_length(self):
        """Test that alert list messages can be chunked if too long"""
        alerts = [
            {
                'id': i,
                'symbol': f'SYMBOL{i}.NS',
                'alert_type': 'price',
                'condition_type': 'above',
                'threshold_value': 100.0,
                'is_active': True
            }
            for i in range(50)
        ]
        
        message = format_alert_list(alerts)
        # Message may exceed 4096, but should be chunkable
        # Test that chunk_message can handle it
        from src.bot.utils.formatters import chunk_message
        chunks = chunk_message(message)
        # Each chunk should be <= 4096
        for chunk in chunks:
            assert len(chunk) <= 4096, f"Chunk too long: {len(chunk)} characters"

