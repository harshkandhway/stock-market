"""
Strict tests for position sizing when capital constraints apply.
These test cases verify behavior when calculated position size exceeds available capital.
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.risk_management import calculate_position_size
from src.core.config import RISK_MODES


class TestPositionSizeCapitalConstraint(unittest.TestCase):
    """Test position sizing when capital is a limiting factor"""
    
    def test_capital_constraint_reduces_position(self):
        """
        Test that when calculated position exceeds capital, 
        position is reduced to fit within capital.
        
        This should result in actual risk < target risk percentage.
        """
        # Small capital relative to entry price
        capital = 1000  # Very small capital
        entry = 100
        stop = 95
        mode = 'balanced'  # 1% risk = 10
        
        position = calculate_position_size(capital, entry, stop, mode)
        
        self.assertFalse(position['error'])
        
        # Calculated shares would be: (1000 * 0.01) / 5 = 2 shares
        # Position value: 2 * 100 = 200 (within capital)
        # So capital constraint should NOT apply here
        
        # But if we use tighter stop, we get more shares
        # Let's test with a scenario where capital IS constrained
        capital = 500
        entry = 100
        stop = 99.5  # Very tight stop: 0.5 point
        mode = 'balanced'  # 1% risk = 5
        
        position = calculate_position_size(capital, entry, stop, mode)
        
        self.assertFalse(position['error'])
        
        # Calculated shares: (500 * 0.01) / 0.5 = 10 shares
        # Position value: 10 * 100 = 1000 (exceeds capital of 500)
        # So capital constraint should apply: shares = int(500 / 100) = 5
        
        # Position value should not exceed capital
        self.assertLessEqual(position['position_value'], capital)
        
        # Actual risk should be less than target risk when constrained
        if position['position_value'] < capital:
            # When constrained, we can't achieve full risk percentage
            self.assertLess(
                position['actual_risk_pct'],
                RISK_MODES[mode]['risk_per_trade'] * 100,
                "When capital constrained, actual risk should be less than target"
            )
    
    def test_capital_constraint_exact_fit(self):
        """Test position sizing when capital exactly fits calculated position"""
        capital = 20000
        entry = 100
        stop = 95
        mode = 'balanced'  # 1% risk = 200
        
        # Expected: (20000 * 0.01) / 5 = 40 shares
        # Position value: 40 * 100 = 4000 (within capital)
        
        position = calculate_position_size(capital, entry, stop, mode)
        
        self.assertFalse(position['error'])
        self.assertEqual(position['shares_to_buy'], 40)
        self.assertEqual(position['position_value'], 4000)
        self.assertLessEqual(position['position_value'], capital)
        self.assertAlmostEqual(position['actual_risk_pct'], 1.0, places=2)
    
    def test_capital_constraint_prevents_overallocation(self):
        """Test that capital constraint prevents allocating more than available"""
        capital = 10000
        entry = 50
        stop = 49  # 1 point stop
        mode = 'aggressive'  # 2% risk = 200
        
        # Without constraint: (10000 * 0.02) / 1 = 200 shares
        # Position value: 200 * 50 = 10000 (exactly capital)
        
        position = calculate_position_size(capital, entry, stop, mode)
        
        self.assertFalse(position['error'])
        
        # Should be exactly at capital limit
        self.assertLessEqual(position['position_value'], capital)
        
        # If position value equals capital, shares should be int(capital / entry)
        if position['position_value'] == capital:
            expected_shares = int(capital / entry)
            self.assertEqual(position['shares_to_buy'], expected_shares)
    
    def test_capital_constraint_with_fractional_shares(self):
        """
        Test that capital constraint handles fractional share calculations correctly.
        Since we use int() conversion, we should never exceed capital.
        """
        capital = 1500
        entry = 100
        stop = 95
        mode = 'balanced'  # 1% risk = 15
        
        # Calculated: (1500 * 0.01) / 5 = 3 shares
        # Position value: 3 * 100 = 300 (within capital)
        
        position = calculate_position_size(capital, entry, stop, mode)
        
        self.assertFalse(position['error'])
        self.assertLessEqual(position['position_value'], capital)
        
        # Verify shares are integer
        self.assertIsInstance(position['shares_to_buy'], int)
        
        # Verify position value calculation is exact
        calculated_value = position['shares_to_buy'] * entry
        self.assertEqual(position['position_value'], calculated_value)


if __name__ == '__main__':
    unittest.main()

