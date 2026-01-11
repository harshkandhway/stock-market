"""
Unit tests for backtest service
Tests strategy backtesting on historical data
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.bot.services.backtest_service import backtest_strategy


class TestBacktestService(unittest.TestCase):
    """Test cases for backtest service"""
    
    def setUp(self):
        """Set up test data"""
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        np.random.seed(42)
        
        base_price = 100
        returns = np.random.normal(0.001, 0.02, 250)
        prices = base_price * np.exp(np.cumsum(returns))
        
        self.sample_df = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.005, 250)),
            'high': prices * (1 + abs(np.random.normal(0, 0.01, 250))),
            'low': prices * (1 - abs(np.random.normal(0, 0.01, 250))),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 250)
        }, index=dates)
        
        self.sample_df['high'] = self.sample_df[['open', 'close', 'high']].max(axis=1)
        self.sample_df['low'] = self.sample_df[['open', 'close', 'low']].min(axis=1)
    
    @patch('src.bot.services.backtest_service.fetch_stock_data')
    @patch('src.bot.services.backtest_service.calculate_all_indicators')
    @patch('src.bot.services.backtest_service.check_hard_filters')
    @patch('src.bot.services.backtest_service.calculate_all_signals')
    @patch('src.bot.services.backtest_service.determine_recommendation')
    @patch('src.bot.services.backtest_service.calculate_stoploss')
    @patch('src.bot.services.backtest_service.calculate_targets')
    def test_backtest_strategy_basic(self, mock_targets, mock_stop, mock_rec,
                                     mock_signals, mock_filters, mock_indicators,
                                     mock_fetch):
        """Test basic backtest execution"""
        # Setup mocks
        mock_fetch.return_value = self.sample_df
        
        # Mock indicators to return consistent values
        mock_indicators.return_value = {
            'current_price': 100.0,
            'atr': 2.0,
            'support': 95.0,
            'resistance': 105.0,
            'fib_extensions': {}
        }
        
        mock_filters.return_value = (False, [])
        mock_signals.return_value = {'confidence': 75}
        
        # Return BUY signal for first half, HOLD for second half
        def recommendation_side_effect(*args):
            # This is a simplified mock - in real test would need more control
            return ('BUY', 'BUY')
        
        mock_rec.side_effect = recommendation_side_effect
        mock_stop.return_value = {'recommended_stop': 95.0}
        mock_targets.return_value = {'recommended_target': 105.0}
        
        result = backtest_strategy('TEST.NS', 100, 'balanced', 'medium', 100000.0)
        
        self.assertEqual(result['symbol'], 'TEST.NS')
        self.assertEqual(result['days'], 100)
        self.assertEqual(result['mode'], 'balanced')
        self.assertEqual(result['initial_capital'], 100000.0)
        self.assertIn('final_capital', result)
        self.assertIn('total_return', result)
        self.assertIn('total_trades', result)
        self.assertIn('win_rate', result)
        self.assertIn('trades', result)
        self.assertIn('equity_curve', result)
    
    @patch('src.bot.services.backtest_service.fetch_stock_data')
    def test_backtest_strategy_insufficient_data(self, mock_fetch):
        """Test backtest with insufficient data"""
        mock_fetch.return_value = pd.DataFrame({'close': [100, 200]})
        
        with self.assertRaises(ValueError):
            backtest_strategy('TEST.NS', 100, 'balanced', 'medium', 100000.0)
    
    @patch('src.bot.services.backtest_service.fetch_stock_data')
    def test_backtest_strategy_fetch_error(self, mock_fetch):
        """Test backtest when data fetch fails"""
        mock_fetch.side_effect = ValueError("Fetch error")
        
        with self.assertRaises(ValueError):
            backtest_strategy('TEST.NS', 100, 'balanced', 'medium', 100000.0)


if __name__ == '__main__':
    unittest.main()

