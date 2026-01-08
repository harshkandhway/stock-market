"""
Data validation tests - Verify data integrity and calculation correctness
with real-world scenarios and known reference values
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.cli.stock_analyzer_pro import fetch_data, analyze_stock
from src.core.indicators import calculate_all_indicators
from src.core.signals import calculate_all_signals
from src.core.risk_management import calculate_position_size, validate_risk_reward


class TestDataValidation(unittest.TestCase):
    """Test data accuracy and calculation validation"""
    
    def test_real_stock_data_fetch(self):
        """Test fetching real stock data and validate structure"""
        # Test with a well-known stock
        df = fetch_data('AAPL', '3mo')
        
        if not df.empty:
            # Validate data structure
            self.assertIn('close', df.columns)
            self.assertIn('high', df.columns)
            self.assertIn('low', df.columns)
            self.assertIn('open', df.columns)
            
            # Validate data quality
            self.assertFalse(df['close'].isna().all(), "Close prices should not be all NaN")
            self.assertGreater(len(df), 0, "Should have at least some data")
            
            # Validate price relationships
            self.assertTrue((df['high'] >= df['low']).all(), "High should be >= Low")
            self.assertTrue((df['high'] >= df['close']).all(), "High should be >= Close")
            self.assertTrue((df['low'] <= df['close']).all(), "Low should be <= Close")
    
    def test_calculation_consistency(self):
        """Test that calculations are consistent across multiple runs"""
        # Create test data
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        np.random.seed(42)  # Fixed seed for reproducibility
        
        prices = 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 250)))
        df = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': [1000000] * 250
        }, index=dates)
        
        # Run calculations twice
        indicators1 = calculate_all_indicators(df, 'medium')
        indicators2 = calculate_all_indicators(df, 'medium')
        
        # Results should be identical
        self.assertEqual(indicators1['current_price'], indicators2['current_price'])
        self.assertEqual(indicators1['rsi'], indicators2['rsi'])
        self.assertEqual(indicators1['adx'], indicators2['adx'])
    
    def test_position_size_formula_accuracy(self):
        """
        Test position sizing formula matches expected calculation exactly.
        
        Formula: Shares = (Capital × Risk%) / (Entry - Stop)
        This test verifies the formula is calculated correctly.
        """
        test_cases = [
            {
                'capital': 100000,
                'entry': 100,
                'stop': 95,
                'mode': 'balanced',
                'expected_risk_pct': 1.0,
                'expected_shares': 200,  # (100000 * 0.01) / 5 = 1000 / 5 = 200
                'expected_position_value': 20000,  # 200 * 100
                'description': 'Balanced mode: 1% risk, 5 point stop'
            },
            {
                'capital': 50000,
                'entry': 50,
                'stop': 48,
                'mode': 'conservative',
                'expected_risk_pct': 0.5,
                'expected_shares': 125,  # (50000 * 0.005) / 2 = 250 / 2 = 125
                'expected_position_value': 6250,  # 125 * 50
                'description': 'Conservative mode: 0.5% risk, 2 point stop'
            },
            {
                'capital': 200000,
                'entry': 200,
                'stop': 190,
                'mode': 'aggressive',
                'expected_risk_pct': 2.0,
                'expected_shares': 400,  # (200000 * 0.02) / 10 = 4000 / 10 = 400
                'expected_position_value': 80000,  # 400 * 200
                'description': 'Aggressive mode: 2% risk, 10 point stop'
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['description']):
                position = calculate_position_size(
                    case['capital'],
                    case['entry'],
                    case['stop'],
                    case['mode']
                )
                
                self.assertFalse(position['error'], 
                               f"Position sizing should not error for {case['description']}")
                
                # STRICT TEST: Shares must match exactly (no tolerance for rounding)
                self.assertEqual(
                    position['shares_to_buy'],
                    case['expected_shares'],
                    f"Shares mismatch for {case['description']}. "
                    f"Expected {case['expected_shares']}, got {position['shares_to_buy']}"
                )
                
                # STRICT TEST: Position value must match exactly
                self.assertEqual(
                    position['position_value'],
                    case['expected_position_value'],
                    f"Position value mismatch for {case['description']}. "
                    f"Expected {case['expected_position_value']}, got {position['position_value']}"
                )
                
                # STRICT TEST: Risk percentage must match exactly (within 0.01% tolerance for float precision)
                self.assertAlmostEqual(
                    position['actual_risk_pct'],
                    case['expected_risk_pct'],
                    places=2,  # 2 decimal places for percentage
                    msg=f"Risk percentage mismatch for {case['description']}. "
                        f"Expected {case['expected_risk_pct']}%, got {position['actual_risk_pct']}%"
                )
                
                # Verify position value doesn't exceed capital
                self.assertLessEqual(
                    position['position_value'],
                    case['capital'],
                    f"Position value {position['position_value']} exceeds capital {case['capital']}"
                )
                
                # Verify actual risk matches expected risk amount
                expected_risk_amount = case['capital'] * (case['expected_risk_pct'] / 100)
                self.assertAlmostEqual(
                    position['actual_risk'],
                    expected_risk_amount,
                    places=2,
                    msg=f"Risk amount mismatch. Expected {expected_risk_amount}, got {position['actual_risk']}"
                )
    
    def test_risk_reward_formula_accuracy(self):
        """Test risk/reward calculation formula"""
        test_cases = [
            {'entry': 100, 'target': 110, 'stop': 95, 'expected_rr': 2.0},
            {'entry': 100, 'target': 120, 'stop': 90, 'expected_rr': 2.0},
            {'entry': 100, 'target': 105, 'stop': 97.5, 'expected_rr': 2.0},
            {'entry': 100, 'target': 115, 'stop': 95, 'expected_rr': 3.0},
        ]
        
        for case in test_cases:
            ratio, is_valid, _ = validate_risk_reward(
                case['entry'],
                case['target'],
                case['stop'],
                'balanced'
            )
            
            self.assertAlmostEqual(ratio, case['expected_rr'], places=2)
    
    def test_indicator_bounds(self):
        """Test that all indicators stay within expected bounds"""
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        prices = 100 + np.cumsum(np.random.normal(0, 1, 250))
        
        df = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': [1000000] * 250
        }, index=dates)
        
        indicators = calculate_all_indicators(df, 'medium')
        
        # RSI bounds
        self.assertGreaterEqual(indicators['rsi'], 0)
        self.assertLessEqual(indicators['rsi'], 100)
        
        # ADX bounds
        self.assertGreaterEqual(indicators['adx'], 0)
        self.assertLessEqual(indicators['adx'], 100)
        
        # ATR should be positive
        self.assertGreater(indicators['atr'], 0)
        
        # Prices should be positive
        self.assertGreater(indicators['current_price'], 0)
        self.assertGreater(indicators['support'], 0)
        self.assertGreater(indicators['resistance'], 0)
    
    def test_signal_weights_sum(self):
        """Test that signal weights are properly normalized"""
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        prices = 100 + np.cumsum(np.random.normal(0, 1, 250))
        
        df = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': [1000000] * 250
        }, index=dates)
        
        indicators = calculate_all_indicators(df, 'medium')
        signal_data = calculate_all_signals(indicators, 'balanced')
        
        # Confidence should be between 0 and 100
        self.assertGreaterEqual(signal_data['confidence'], 0)
        self.assertLessEqual(signal_data['confidence'], 100)
        
        # Net score should be reasonable
        # Max possible score is sum of all weights (100)
        self.assertGreaterEqual(signal_data['net_score'], -100)
        self.assertLessEqual(signal_data['net_score'], 100)
    
    def test_price_relationships(self):
        """Test that calculated price relationships are logical"""
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        prices = 100 + np.cumsum(np.random.normal(0, 1, 250))
        
        df = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': [1000000] * 250
        }, index=dates)
        
        indicators = calculate_all_indicators(df, 'medium')
        
        # Support should be <= current price <= resistance (generally)
        # (Not always true, but should be logical)
        if indicators['support'] > 0 and indicators['resistance'] > 0:
            self.assertLessEqual(indicators['support'], indicators['resistance'])
        
        # 52-week high should be >= 52-week low
        self.assertGreaterEqual(indicators['high_52w'], indicators['low_52w'])
        
        # EMAs should be in logical order for trending markets
        # (Not strict, but fast EMA should be closer to price than slow EMA in trends)


if __name__ == '__main__':
    unittest.main()

