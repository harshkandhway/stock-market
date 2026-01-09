"""
Unit tests for analysis service
Tests stock data fetching, analysis, caching, and symbol search
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.bot.services.analysis_service import (
    fetch_stock_data,
    analyze_stock,
    get_current_price,
    get_multiple_prices,
    search_symbol,
    validate_symbol,
    get_cached_analysis,
    save_analysis_cache,
    analyze_multiple_stocks
)


class TestAnalysisService(unittest.TestCase):
    """Test cases for analysis service"""
    
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
    
    @patch('yahooquery.Ticker')
    def test_fetch_stock_data_success(self, mock_ticker):
        """Test successful data fetch"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = self.sample_df
        mock_ticker.return_value = mock_ticker_instance
        
        df = fetch_stock_data('TEST.NS', '1y')
        
        self.assertFalse(df.empty)
        self.assertIn('close', df.columns)
        self.assertIn('high', df.columns)
        self.assertIn('low', df.columns)
        self.assertIn('open', df.columns)
    
    @patch('yahooquery.Ticker')
    def test_fetch_stock_data_error_string(self, mock_ticker):
        """Test error handling when API returns error string"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = "Error: Invalid symbol"
        mock_ticker.return_value = mock_ticker_instance
        
        with self.assertRaises(ValueError):
            fetch_stock_data('INVALID', '1y')
    
    @patch('yahooquery.Ticker')
    def test_fetch_stock_data_empty(self, mock_ticker):
        """Test error handling when data is empty"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_ticker_instance
        
        with self.assertRaises(ValueError):
            fetch_stock_data('INVALID', '1y')
    
    @patch('src.bot.services.analysis_service.fetch_stock_data')
    @patch('src.bot.services.analysis_service.calculate_all_indicators')
    @patch('src.bot.services.analysis_service.check_hard_filters')
    @patch('src.bot.services.analysis_service.calculate_all_signals')
    @patch('src.bot.services.analysis_service.determine_recommendation')
    @patch('src.bot.services.analysis_service.calculate_targets')
    @patch('src.bot.services.analysis_service.calculate_stoploss')
    @patch('src.bot.services.analysis_service.validate_risk_reward')
    @patch('src.bot.services.analysis_service.generate_reasoning')
    @patch('src.bot.services.analysis_service.generate_action_plan')
    @patch('src.bot.services.analysis_service.calculate_trailing_stops')
    @patch('src.bot.services.analysis_service.estimate_time_to_target')
    @patch('src.bot.services.analysis_service.calculate_safety_score')
    def test_analyze_stock_success(self, mock_safety, mock_time, mock_trailing,
                                   mock_actions, mock_reasoning, mock_rr,
                                   mock_stop, mock_targets, mock_rec,
                                   mock_signals, mock_filters, mock_indicators,
                                   mock_fetch):
        """Test successful stock analysis"""
        # Setup mocks
        mock_fetch.return_value = self.sample_df
        
        mock_indicators.return_value = {
            'current_price': 100.0,
            'atr': 2.0,
            'support': 90.0,
            'resistance': 110.0,
            'fib_extensions': {},
            'atr_percent': 2.0,
            'momentum': 0.5,
            'adx': 30.0,
            'rsi': 50.0
        }
        
        mock_filters.return_value = (False, [])
        mock_signals.return_value = {
            'confidence': 75,
            'signals': {}
        }
        mock_rec.return_value = ('BUY', 'BUY')
        mock_targets.return_value = {
            'recommended_target': 110.0,
            'recommended_target_pct': 10.0
        }
        mock_stop.return_value = {
            'recommended_stop': 95.0,
            'recommended_stop_pct': 5.0
        }
        mock_rr.return_value = (2.0, True, 'Valid')
        mock_reasoning.return_value = ['Reason 1', 'Reason 2']
        mock_actions.return_value = ['Action 1']
        mock_trailing.return_value = {'initial_stop': 95.0}
        mock_time.return_value = {'estimated_days': 30}
        mock_safety.return_value = 4.0
        
        analysis = analyze_stock('TEST.NS', 'balanced', 'medium', '3months')
        
        self.assertEqual(analysis['symbol'], 'TEST.NS')
        self.assertEqual(analysis['mode'], 'balanced')
        self.assertIn('confidence', analysis)
        self.assertIn('recommendation', analysis)
        self.assertIn('current_price', analysis)
    
    def test_analyze_stock_invalid_symbol(self):
        """Test analysis with invalid symbol"""
        with self.assertRaises(ValueError):
            analyze_stock('', 'balanced', 'medium')
    
    def test_analyze_stock_invalid_mode(self):
        """Test analysis with invalid mode"""
        with self.assertRaises(ValueError):
            analyze_stock('TEST.NS', 'invalid_mode', 'medium')
    
    def test_analyze_stock_invalid_timeframe(self):
        """Test analysis with invalid timeframe"""
        with self.assertRaises(ValueError):
            analyze_stock('TEST.NS', 'balanced', 'invalid')
    
    @patch('src.bot.services.analysis_service.fetch_stock_data')
    def test_get_current_price_success(self, mock_fetch):
        """Test getting current price"""
        mock_fetch.return_value = self.sample_df
        
        price = get_current_price('TEST.NS')
        
        self.assertIsNotNone(price)
        self.assertIsInstance(price, float)
        self.assertGreater(price, 0)
    
    @patch('src.bot.services.analysis_service.fetch_stock_data')
    def test_get_current_price_failure(self, mock_fetch):
        """Test getting current price when fetch fails"""
        mock_fetch.side_effect = ValueError("Error")
        
        price = get_current_price('INVALID')
        
        self.assertIsNone(price)
    
    @patch('src.bot.services.analysis_service.get_current_price')
    def test_get_multiple_prices(self, mock_get_price):
        """Test getting multiple prices"""
        mock_get_price.side_effect = [100.0, 200.0, None]
        
        prices = get_multiple_prices(['STOCK1', 'STOCK2', 'STOCK3'])
        
        self.assertEqual(len(prices), 2)
        self.assertEqual(prices['STOCK1'], 100.0)
        self.assertEqual(prices['STOCK2'], 200.0)
        self.assertNotIn('STOCK3', prices)
    
    @patch('src.bot.services.analysis_service.fetch_stock_data')
    def test_validate_symbol_valid(self, mock_fetch):
        """Test symbol validation for valid symbol"""
        mock_fetch.return_value = self.sample_df
        
        is_valid = validate_symbol('TEST.NS')
        
        self.assertTrue(is_valid)
    
    @patch('src.bot.services.analysis_service.fetch_stock_data')
    def test_validate_symbol_invalid(self, mock_fetch):
        """Test symbol validation for invalid symbol"""
        mock_fetch.side_effect = ValueError("Error")
        
        is_valid = validate_symbol('INVALID')
        
        self.assertFalse(is_valid)
    
    @patch('src.bot.services.analysis_service.get_db_context')
    def test_get_cached_analysis_hit(self, mock_db):
        """Test getting cached analysis"""
        mock_cache = Mock()
        mock_cache.data = {'symbol': 'TEST.NS', 'confidence': 75}
        mock_cache.is_expired.return_value = False
        
        mock_session = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_cache
        mock_session.query.return_value = mock_query
        mock_db.return_value.__enter__.return_value = mock_session
        
        with patch('src.bot.services.analysis_service.ENABLE_ANALYSIS_CACHE', True):
            cached = get_cached_analysis('TEST.NS', 'balanced', 'medium')
            
            self.assertIsNotNone(cached)
            self.assertEqual(cached['symbol'], 'TEST.NS')
    
    @patch('src.bot.services.analysis_service.get_db_context')
    def test_get_cached_analysis_miss(self, mock_db):
        """Test getting cached analysis when cache miss"""
        mock_session = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        mock_db.return_value.__enter__.return_value = mock_session
        
        with patch('src.bot.services.analysis_service.ENABLE_ANALYSIS_CACHE', True):
            cached = get_cached_analysis('TEST.NS', 'balanced', 'medium')
            
            self.assertIsNone(cached)
    
    @patch('src.bot.services.analysis_service.analyze_stock')
    def test_analyze_multiple_stocks(self, mock_analyze):
        """Test analyzing multiple stocks"""
        mock_analyze.side_effect = [
            {'symbol': 'STOCK1', 'confidence': 75},
            {'symbol': 'STOCK2', 'confidence': 80},
            ValueError("Error")
        ]
        
        results = analyze_multiple_stocks(['STOCK1', 'STOCK2', 'STOCK3'], 'balanced', 'medium')
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['symbol'], 'STOCK1')
        self.assertEqual(results[1]['symbol'], 'STOCK2')
        self.assertTrue(results[2]['error'])


if __name__ == '__main__':
    unittest.main()

