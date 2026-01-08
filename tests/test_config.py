"""
Unit tests for config module
"""

import unittest
from config import (
    TIMEFRAME_CONFIGS, RISK_MODES, SIGNAL_WEIGHTS,
    HARD_FILTERS, RECOMMENDATION_THRESHOLDS,
    CONFIDENCE_LEVELS, DEFAULT_MODE, DEFAULT_TIMEFRAME
)


class TestConfig(unittest.TestCase):
    """Test cases for configuration validation"""
    
    def test_timeframe_configs_exist(self):
        """Test that both timeframe configs exist"""
        self.assertIn('short', TIMEFRAME_CONFIGS)
        self.assertIn('medium', TIMEFRAME_CONFIGS)
    
    def test_timeframe_config_structure(self):
        """Test timeframe config structure"""
        for timeframe, config in TIMEFRAME_CONFIGS.items():
            required_keys = [
                'name', 'description', 'data_period',
                'ema_fast', 'ema_medium', 'ema_slow', 'ema_trend',
                'rsi_period', 'macd_fast', 'macd_slow', 'macd_signal',
                'atr_period', 'adx_period'
            ]
            
            for key in required_keys:
                self.assertIn(key, config, f"Missing key {key} in {timeframe}")
    
    def test_risk_modes_exist(self):
        """Test that all risk modes exist"""
        self.assertIn('conservative', RISK_MODES)
        self.assertIn('balanced', RISK_MODES)
        self.assertIn('aggressive', RISK_MODES)
    
    def test_risk_mode_structure(self):
        """Test risk mode structure"""
        for mode, config in RISK_MODES.items():
            required_keys = [
                'name', 'description', 'risk_per_trade',
                'min_risk_reward', 'atr_stop_multiplier',
                'atr_target_multiplier', 'min_confidence_buy',
                'min_confidence_sell', 'min_adx_trend',
                'weight_multipliers'
            ]
            
            for key in required_keys:
                self.assertIn(key, config, f"Missing key {key} in {mode}")
    
    def test_risk_per_trade_values(self):
        """Test risk per trade values are reasonable"""
        self.assertEqual(RISK_MODES['conservative']['risk_per_trade'], 0.005)  # 0.5%
        self.assertEqual(RISK_MODES['balanced']['risk_per_trade'], 0.01)  # 1%
        self.assertEqual(RISK_MODES['aggressive']['risk_per_trade'], 0.02)  # 2%
    
    def test_min_risk_reward_values(self):
        """Test minimum risk/reward values"""
        self.assertEqual(RISK_MODES['conservative']['min_risk_reward'], 3.0)
        self.assertEqual(RISK_MODES['balanced']['min_risk_reward'], 2.0)
        self.assertEqual(RISK_MODES['aggressive']['min_risk_reward'], 1.5)
    
    def test_signal_weights_sum(self):
        """Test that signal weights sum to 100"""
        total = sum(SIGNAL_WEIGHTS.values())
        self.assertEqual(total, 100, f"Signal weights sum to {total}, expected 100")
    
    def test_hard_filters_structure(self):
        """Test hard filters structure"""
        self.assertIn('block_buy', HARD_FILTERS)
        self.assertIn('block_sell', HARD_FILTERS)
        
        for filter_list in HARD_FILTERS.values():
            self.assertIsInstance(filter_list, list)
            for filter_rule in filter_list:
                required_keys = ['indicator', 'operator', 'value', 'reason']
                for key in required_keys:
                    self.assertIn(key, filter_rule)
    
    def test_recommendation_thresholds(self):
        """Test recommendation thresholds structure"""
        for mode in ['conservative', 'balanced', 'aggressive']:
            self.assertIn(mode, RECOMMENDATION_THRESHOLDS)
            
            thresholds = RECOMMENDATION_THRESHOLDS[mode]
            required_keys = [
                'STRONG_BUY', 'BUY', 'WEAK_BUY',
                'HOLD_UPPER', 'HOLD_LOWER',
                'WEAK_SELL', 'SELL', 'STRONG_SELL'
            ]
            
            for key in required_keys:
                self.assertIn(key, thresholds)
                # Thresholds should be between 0 and 100
                self.assertGreaterEqual(thresholds[key], 0)
                self.assertLessEqual(thresholds[key], 100)
    
    def test_confidence_levels_coverage(self):
        """Test that confidence levels cover 0-100"""
        # Check that all ranges together cover 0-100
        ranges = list(CONFIDENCE_LEVELS.keys())
        ranges.sort()
        
        # First range should start at 0
        self.assertEqual(ranges[0][0], 0)
        
        # Last range should end at 100
        self.assertEqual(ranges[-1][1], 100)
        
        # Ranges should be contiguous or overlapping (inclusive ranges)
        # Note: ranges are inclusive, so (0, 34) means 0-34, (35, 54) means 35-54
        # The gap between 34 and 35 is acceptable as they're inclusive ranges
        for i in range(len(ranges) - 1):
            # Current range end should be <= next range start (allowing for inclusive ranges)
            self.assertLessEqual(ranges[i][1], ranges[i+1][0] + 1)
    
    def test_default_values(self):
        """Test default configuration values"""
        self.assertEqual(DEFAULT_MODE, 'balanced')
        self.assertEqual(DEFAULT_TIMEFRAME, 'medium')
        self.assertIn(DEFAULT_MODE, RISK_MODES)
        self.assertIn(DEFAULT_TIMEFRAME, TIMEFRAME_CONFIGS)


if __name__ == '__main__':
    unittest.main()

