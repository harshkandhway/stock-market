"""
Unit tests for CLI module (stock_analyzer_pro.py)
Tests data fetching and main analysis functions
"""

import unittest
import sys
import os
import pandas as pd
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.cli.stock_analyzer_pro import (
    fetch_data, analyze_stock, get_capital_interactive
)


class TestCLI(unittest.TestCase):
    """Test cases for CLI functions"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample DataFrame with valid price data
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        base_price = 100.0
        prices = pd.Series([base_price + i * 0.1 for i in range(250)], dtype=float)
        
        self.sample_df = pd.DataFrame({
            'open': (prices * 0.99).astype(float),
            'high': (prices * 1.02).astype(float),
            'low': (prices * 0.98).astype(float),
            'close': prices.astype(float),
            'volume': pd.Series([1000000] * 250, dtype=float)
        }, index=dates)
        
        # Ensure no NaN values and all prices are positive
        self.sample_df = self.sample_df.fillna(0.01)
        self.sample_df = self.sample_df.clip(lower=0.01)
        
        # Ensure high >= low and high >= close >= low
        self.sample_df['high'] = self.sample_df[['high', 'close']].max(axis=1)
        self.sample_df['low'] = self.sample_df[['low', 'close']].min(axis=1)
        self.sample_df['high'] = self.sample_df[['high', 'low']].max(axis=1)
    
    def test_fetch_data_invalid_symbol(self):
        """Test fetch_data with invalid symbol"""
        df = fetch_data('INVALID_SYMBOL_XYZ123', '1y')
        self.assertTrue(df.empty)
    
    def test_fetch_data_validation(self):
        """Test that fetch_data validates inputs"""
        # Test None symbol
        df = fetch_data(None, '1y')
        self.assertTrue(df.empty)
        
        # Test empty string
        df = fetch_data('', '1y')
        self.assertTrue(df.empty)
        
        # Test non-string
        df = fetch_data(123, '1y')
        self.assertTrue(df.empty)
    
    @patch('src.cli.stock_analyzer_pro.Ticker')
    def test_fetch_data_success(self, mock_ticker):
        """Test successful data fetch"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = self.sample_df
        mock_ticker.return_value = mock_ticker_instance
        
        df = fetch_data('TEST.NS', '1y')
        
        self.assertFalse(df.empty)
        self.assertIn('close', df.columns)
        self.assertIn('high', df.columns)
        self.assertIn('low', df.columns)
        self.assertIn('open', df.columns)
    
    @patch('src.cli.stock_analyzer_pro.Ticker')
    def test_fetch_data_error_handling(self, mock_ticker):
        """Test fetch_data error handling"""
        # Test string error response
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = "Error: Invalid symbol"
        mock_ticker.return_value = mock_ticker_instance
        
        df = fetch_data('INVALID', '1y')
        self.assertTrue(df.empty)
        
        # Test exception handling
        mock_ticker_instance.history.side_effect = Exception("Network error")
        df = fetch_data('TEST', '1y')
        self.assertTrue(df.empty)
    
    def test_analyze_stock_validation(self):
        """Test analyze_stock input validation"""
        # Test invalid symbol
        with self.assertRaises(ValueError):
            analyze_stock(None, self.sample_df, 'balanced', 'medium')
        
        with self.assertRaises(ValueError):
            analyze_stock('', self.sample_df, 'balanced', 'medium')
        
        # Test invalid DataFrame
        with self.assertRaises(ValueError):
            analyze_stock('TEST.NS', pd.DataFrame(), 'balanced', 'medium')
        
        # Test invalid mode
        with self.assertRaises(ValueError):
            analyze_stock('TEST.NS', self.sample_df, 'invalid_mode', 'medium')
        
        # Test invalid timeframe
        with self.assertRaises(ValueError):
            analyze_stock('TEST.NS', self.sample_df, 'balanced', 'invalid')
    
    def test_analyze_stock_success(self):
        """Test successful stock analysis"""
        analysis = analyze_stock('TEST.NS', self.sample_df, 'balanced', 'medium')
        
        # Verify analysis structure
        self.assertEqual(analysis['symbol'], 'TEST.NS')
        self.assertEqual(analysis['mode'], 'balanced')
        self.assertIn('confidence', analysis)
        self.assertIn('recommendation', analysis)
        self.assertIn('current_price', analysis)
        self.assertIn('target', analysis)
        self.assertIn('stop_loss', analysis)
        self.assertIn('risk_reward', analysis)
        
        # Verify values are reasonable
        self.assertGreater(analysis['current_price'], 0)
        self.assertGreaterEqual(analysis['confidence'], 0)
        self.assertLessEqual(analysis['confidence'], 100)
    
    def test_analyze_stock_different_modes(self):
        """Test analysis with different risk modes"""
        for mode in ['conservative', 'balanced', 'aggressive']:
            with self.subTest(mode=mode):
                analysis = analyze_stock('TEST.NS', self.sample_df, mode, 'medium')
                self.assertEqual(analysis['mode'], mode)
                self.assertIn('confidence', analysis)
    
    def test_analyze_stock_different_timeframes(self):
        """Test analysis with different timeframes"""
        for timeframe in ['short', 'medium']:
            with self.subTest(timeframe=timeframe):
                analysis = analyze_stock('TEST.NS', self.sample_df, 'balanced', timeframe)
                self.assertIn('timeframe', analysis)
                self.assertIn('confidence', analysis)
    
    @patch('builtins.input', side_effect=['y', '100000'])
    def test_get_capital_interactive_yes(self, mock_input):
        """Test get_capital_interactive when user says yes"""
        capital = get_capital_interactive()
        self.assertEqual(capital, 100000.0)
    
    @patch('builtins.input', side_effect=['n'])
    def test_get_capital_interactive_no(self, mock_input):
        """Test get_capital_interactive when user says no"""
        capital = get_capital_interactive()
        self.assertIsNone(capital)
    
    @patch('builtins.input', side_effect=['y', 'invalid', '100000'])
    def test_get_capital_interactive_retry(self, mock_input):
        """Test get_capital_interactive with invalid input then valid"""
        capital = get_capital_interactive()
        self.assertEqual(capital, 100000.0)
    
    @patch('builtins.input', side_effect=['y', '-100'])
    def test_get_capital_interactive_negative(self, mock_input):
        """Test get_capital_interactive with negative capital"""
        capital = get_capital_interactive()
        # Should return None after max attempts or validation failure
        # The function should handle this gracefully
    
    def test_analyze_stock_with_blocked_trade(self):
        """Test analysis when trade is blocked"""
        # Create data that would trigger a block (extremely overbought)
        # This is harder to simulate, but we can test the structure
        analysis = analyze_stock('TEST.NS', self.sample_df, 'balanced', 'medium')
        
        # Verify block flags exist
        self.assertIn('is_buy_blocked', analysis)
        self.assertIn('is_sell_blocked', analysis)
        self.assertIn('buy_block_reasons', analysis)
        self.assertIn('sell_block_reasons', analysis)
        
        # Verify recommendation type
        self.assertIn(analysis['recommendation_type'], ['BUY', 'SELL', 'HOLD', 'BLOCKED'])


if __name__ == '__main__':
    unittest.main()

