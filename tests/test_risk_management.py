"""
Unit tests for risk_management module
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.risk_management import (
    calculate_targets, calculate_stoploss, validate_risk_reward,
    calculate_trailing_stops, calculate_position_size,
    calculate_portfolio_allocation
)


class TestRiskManagement(unittest.TestCase):
    """Test cases for risk management functions"""
    
    def setUp(self):
        """Set up test data"""
        self.current_price = 100.0
        self.atr = 2.0
        self.resistance = 110.0
        self.support = 90.0
        self.fib_extensions = {
            'fib_ext_127': 115.0,
            'fib_ext_161': 120.0
        }
    
    def test_calculate_targets_long(self):
        """Test target calculation for long positions"""
        targets = calculate_targets(
            self.current_price, self.atr, self.resistance, self.support,
            self.fib_extensions, 'balanced', 'long'
        )
        
        self.assertIn('atr_target', targets)
        self.assertIn('resistance_target', targets)
        self.assertIn('recommended_target', targets)
        
        # Targets should be above current price for long
        self.assertGreater(targets['recommended_target'], self.current_price)
        
        # Target percentages should be positive
        self.assertGreater(targets['recommended_target_pct'], 0)
    
    def test_calculate_targets_short(self):
        """Test target calculation for short positions"""
        targets = calculate_targets(
            self.current_price, self.atr, self.resistance, self.support,
            self.fib_extensions, 'balanced', 'short'
        )
        
        # Targets should be below current price for short
        self.assertLess(targets['recommended_target'], self.current_price)
    
    def test_calculate_stoploss_long(self):
        """Test stop loss calculation for long positions"""
        stops = calculate_stoploss(
            self.current_price, self.atr, self.support, self.resistance,
            'balanced', 'long'
        )
        
        self.assertIn('atr_stop', stops)
        self.assertIn('support_stop', stops)
        self.assertIn('recommended_stop', stops)
        
        # Stop should be below current price for long
        self.assertLess(stops['recommended_stop'], self.current_price)
        
        # Stop percentage should be positive
        self.assertGreater(stops['recommended_stop_pct'], 0)
    
    def test_calculate_stoploss_short(self):
        """Test stop loss calculation for short positions"""
        stops = calculate_stoploss(
            self.current_price, self.atr, self.support, self.resistance,
            'balanced', 'short'
        )
        
        # Stop should be above current price for short
        self.assertGreater(stops['recommended_stop'], self.current_price)
    
    def test_validate_risk_reward_valid(self):
        """Test risk/reward validation for valid trades"""
        entry = 100.0
        target = 110.0  # 10% gain
        stop = 95.0     # 5% loss
        
        ratio, is_valid, explanation = validate_risk_reward(
            entry, target, stop, 'balanced'
        )
        
        # Should be 2:1 R:R (10% / 5%)
        self.assertAlmostEqual(ratio, 2.0, places=1)
        self.assertTrue(is_valid)
        self.assertIn('meets minimum', explanation)
    
    def test_validate_risk_reward_invalid(self):
        """Test risk/reward validation for invalid trades"""
        entry = 100.0
        target = 102.0  # 2% gain
        stop = 95.0    # 5% loss
        
        ratio, is_valid, explanation = validate_risk_reward(
            entry, target, stop, 'balanced'
        )
        
        # Should be less than 1:1 R:R
        self.assertLess(ratio, 1.0)
        self.assertFalse(is_valid)
        self.assertIn('BELOW minimum', explanation)
    
    def test_validate_risk_reward_conservative(self):
        """Test conservative mode requires higher R:R"""
        entry = 100.0
        target = 110.0  # 10% gain
        stop = 96.67   # 3.33% loss (exactly 3:1)
        
        ratio, is_valid, explanation = validate_risk_reward(
            entry, target, stop, 'conservative'
        )
        
        self.assertAlmostEqual(ratio, 3.0, places=1)
        self.assertTrue(is_valid)
    
    def test_calculate_trailing_stops(self):
        """Test trailing stop calculation"""
        trailing = calculate_trailing_stops(
            self.current_price, self.atr, 'balanced'
        )
        
        self.assertIn('entry_price', trailing)
        self.assertIn('initial_stop', trailing)
        self.assertIn('breakeven_trigger', trailing)
        self.assertIn('trail_start_trigger', trailing)
        
        # Initial stop should be below entry
        self.assertLess(trailing['initial_stop'], trailing['entry_price'])
        
        # Breakeven trigger should be above entry
        self.assertGreater(trailing['breakeven_trigger'], trailing['entry_price'])
        
        # Trail start should be above breakeven
        self.assertGreater(
            trailing['trail_start_trigger'], trailing['breakeven_trigger']
        )
    
    def test_calculate_position_size(self):
        """Test position sizing calculation"""
        capital = 100000.0
        entry = 100.0
        stop = 95.0
        
        position = calculate_position_size(capital, entry, stop, 'balanced')
        
        self.assertFalse(position['error'])
        self.assertIn('shares_to_buy', position)
        self.assertIn('position_value', position)
        self.assertIn('actual_risk', position)
        
        # Risk should be 1% of capital for balanced mode
        self.assertAlmostEqual(
            position['actual_risk_pct'], 1.0, places=1
        )
        
        # Position value should not exceed capital
        self.assertLessEqual(position['position_value'], capital)
    
    def test_calculate_position_size_conservative(self):
        """Test conservative mode position sizing"""
        capital = 100000.0
        entry = 100.0
        stop = 95.0
        
        position = calculate_position_size(capital, entry, stop, 'conservative')
        
        # Risk should be 0.5% for conservative
        self.assertAlmostEqual(
            position['actual_risk_pct'], 0.5, places=1
        )
    
    def test_calculate_position_size_invalid_stop(self):
        """Test position sizing with invalid stop loss"""
        capital = 100000.0
        entry = 100.0
        stop = 100.0  # Same as entry
        
        position = calculate_position_size(capital, entry, stop, 'balanced')
        
        self.assertTrue(position['error'])
        self.assertIn('message', position)
    
    def test_calculate_portfolio_allocation(self):
        """Test portfolio allocation calculation"""
        # Create mock analyses
        analyses = [
            {
                'symbol': 'STOCK1',
                'confidence': 80,
                'recommendation': 'BUY',
                'recommendation_type': 'BUY',
                'rr_valid': True,
                'risk_reward': 2.0,
                'current_price': 100.0,
                'stop_loss': 95.0,
                'target': 110.0
            },
            {
                'symbol': 'STOCK2',
                'confidence': 60,
                'recommendation': 'BUY',
                'recommendation_type': 'BUY',
                'rr_valid': True,
                'risk_reward': 2.0,
                'current_price': 50.0,
                'stop_loss': 47.5,
                'target': 55.0
            },
            {
                'symbol': 'STOCK3',
                'confidence': 40,
                'recommendation': 'HOLD',
                'recommendation_type': 'HOLD',
                'rr_valid': False,
                'risk_reward': 1.0,
                'current_price': 200.0,
                'stop_loss': 190.0,
                'target': 210.0
            }
        ]
        
        capital = 100000.0
        allocation = calculate_portfolio_allocation(analyses, capital, 'balanced')
        
        self.assertIn('investable', allocation)
        self.assertIn('not_recommended', allocation)
        self.assertIn('total_allocated', allocation)
        
        # Should have 2 investable stocks (STOCK1 and STOCK2)
        self.assertEqual(len(allocation['investable']), 2)
        
        # STOCK1 should have higher allocation than STOCK2 (higher confidence)
        stock1_alloc = next(
            a for a in allocation['investable'] if a['symbol'] == 'STOCK1'
        )
        stock2_alloc = next(
            a for a in allocation['investable'] if a['symbol'] == 'STOCK2'
        )
        
        self.assertGreater(
            stock1_alloc['weight_pct'], stock2_alloc['weight_pct']
        )
        
        # Total allocated should be <= capital
        self.assertLessEqual(allocation['total_allocated'], capital)
    
    def test_calculate_portfolio_allocation_no_investable(self):
        """Test allocation when no stocks are investable"""
        analyses = [
            {
                'symbol': 'STOCK1',
                'confidence': 30,
                'recommendation': 'SELL',
                'recommendation_type': 'SELL',
                'rr_valid': False,
                'risk_reward': 1.0,
                'current_price': 100.0,
                'stop_loss': 95.0,
                'target': 110.0
            }
        ]
        
        capital = 100000.0
        allocation = calculate_portfolio_allocation(analyses, capital, 'balanced')
        
        self.assertEqual(len(allocation['investable']), 0)
        self.assertEqual(allocation['total_allocated'], 0)
        self.assertEqual(allocation['cash_remaining'], capital)


if __name__ == '__main__':
    unittest.main()

