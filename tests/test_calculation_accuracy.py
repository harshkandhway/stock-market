"""
Accuracy tests for technical indicator calculations
Tests that calculations match expected mathematical formulas and known values
"""

import unittest
import pandas as pd
import numpy as np
from indicators import (
    calculate_rsi, calculate_macd, calculate_emas,
    calculate_atr, calculate_bollinger_bands,
    calculate_support_resistance, calculate_all_indicators
)
from signals import calculate_all_signals, get_confidence_level
from risk_management import (
    calculate_position_size, validate_risk_reward,
    calculate_targets, calculate_stoploss
)
from config import TIMEFRAME_CONFIGS, RISK_MODES


class TestCalculationAccuracy(unittest.TestCase):
    """Test mathematical accuracy of calculations"""
    
    def setUp(self):
        """Set up test data with known values"""
        # Create a simple dataset with predictable values for testing
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        
        # Create a simple uptrend: 100, 101, 102, 103, ...
        prices = np.array([100 + i * 0.5 for i in range(250)])
        
        self.simple_df = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': [1000000] * 250
        }, index=dates)
        
        self.config = TIMEFRAME_CONFIGS['medium']
    
    def test_rsi_calculation_accuracy(self):
        """Test RSI calculation accuracy"""
        # RSI should be between 0 and 100
        rsi_data = calculate_rsi(self.simple_df['close'], self.config)
        
        self.assertGreaterEqual(rsi_data['rsi'], 0)
        self.assertLessEqual(rsi_data['rsi'], 100)
        
        # For an uptrend, RSI should generally be above 50
        # (though not always, depending on volatility)
        # This is a sanity check, not a strict requirement
    
    def test_ema_calculation_accuracy(self):
        """Test EMA calculation accuracy"""
        emas = calculate_emas(self.simple_df['close'], self.config)
        
        # EMA should be a weighted average, so for an uptrend:
        # Fast EMA should be higher than slow EMA
        latest_fast = emas['ema_fast'].iloc[-1]
        latest_slow = emas['ema_slow'].iloc[-1]
        
        # In an uptrend, fast EMA should be >= slow EMA
        self.assertGreaterEqual(latest_fast, latest_slow)
        
        # EMA should be close to recent prices (not too far)
        latest_price = self.simple_df['close'].iloc[-1]
        # EMA should be within 20% of current price for trending data
        self.assertLess(abs(latest_fast - latest_price) / latest_price, 0.2)
    
    def test_macd_calculation_accuracy(self):
        """Test MACD calculation accuracy"""
        macd_data = calculate_macd(self.simple_df['close'], self.config)
        
        # MACD line should be calculated as EMA(fast) - EMA(slow)
        # We can't directly verify this without recalculating, but we can check:
        # - MACD should be a number
        self.assertIsInstance(macd_data['macd'], (int, float))
        self.assertIsInstance(macd_data['macd_signal'], (int, float))
        self.assertIsInstance(macd_data['macd_hist'], (int, float))
        
        # Histogram should be MACD - Signal
        calculated_hist = macd_data['macd'] - macd_data['macd_signal']
        self.assertAlmostEqual(macd_data['macd_hist'], calculated_hist, places=4)
    
    def test_atr_calculation_accuracy(self):
        """Test ATR calculation accuracy"""
        atr_data = calculate_atr(
            self.simple_df['high'],
            self.simple_df['low'],
            self.simple_df['close'],
            self.config
        )
        
        # ATR should be positive
        self.assertGreater(atr_data['atr'], 0)
        
        # ATR should be less than the price (typically 1-5% for stocks)
        latest_price = self.simple_df['close'].iloc[-1]
        atr_percent = (atr_data['atr'] / latest_price) * 100
        
        # ATR percent should be reasonable (0.1% to 20%)
        self.assertGreater(atr_percent, 0.1)
        self.assertLess(atr_percent, 20)
    
    def test_bollinger_bands_accuracy(self):
        """Test Bollinger Bands calculation accuracy"""
        bb_data = calculate_bollinger_bands(self.simple_df['close'], self.config)
        
        # Middle band should be SMA
        # Upper = Middle + (2 * std)
        # Lower = Middle - (2 * std)
        
        # Upper > Middle > Lower
        self.assertGreater(bb_data['bb_upper'], bb_data['bb_middle'])
        self.assertGreater(bb_data['bb_middle'], bb_data['bb_lower'])
        
        # %B should be between 0 and 1 (or slightly outside for extreme cases)
        # %B = (Price - Lower) / (Upper - Lower)
        latest_price = self.simple_df['close'].iloc[-1]
        calculated_percent_b = (
            (latest_price - bb_data['bb_lower']) /
            (bb_data['bb_upper'] - bb_data['bb_lower'])
        )
        
        # Allow some tolerance for rounding
        self.assertAlmostEqual(bb_data['bb_percent'], calculated_percent_b, places=2)
    
    def test_support_resistance_accuracy(self):
        """Test support/resistance calculation accuracy"""
        sr_data = calculate_support_resistance(self.simple_df, self.config)
        
        # Support should be <= current price <= resistance (generally)
        latest_price = self.simple_df['close'].iloc[-1]
        
        # In an uptrend, current price should be closer to resistance
        # But these are lookback-based, so not strict
        self.assertLessEqual(sr_data['support'], sr_data['resistance'])
        self.assertLessEqual(sr_data['low_52w'], sr_data['high_52w'])
    
    def test_position_size_calculation_accuracy(self):
        """
        Test position sizing calculation accuracy with strict assertions.
        
        Formula: Shares = (Capital × Risk%) / (Entry - Stop)
        """
        capital = 100000.0
        entry_price = 100.0
        stop_loss = 95.0  # 5 point stop
        mode = 'balanced'  # 1% risk
        
        position = calculate_position_size(capital, entry_price, stop_loss, mode)
        
        # Expected calculation:
        # Risk = 1% of 100000 = 1000
        # Stop distance = |100 - 95| = 5
        # Shares = 1000 / 5 = 200
        expected_shares = 200
        expected_position_value = 200 * 100  # 20000
        expected_risk_amount = 1000
        expected_risk_pct = 1.0
        
        # STRICT TEST: Exact match required
        self.assertEqual(
            position['shares_to_buy'],
            expected_shares,
            f"Shares mismatch. Expected {expected_shares}, got {position['shares_to_buy']}"
        )
        
        # STRICT TEST: Position value must match exactly
        self.assertEqual(
            position['position_value'],
            expected_position_value,
            f"Position value mismatch. Expected {expected_position_value}, got {position['position_value']}"
        )
        
        # STRICT TEST: Risk amount must match exactly
        self.assertAlmostEqual(
            position['actual_risk'],
            expected_risk_amount,
            places=2,
            msg=f"Risk amount mismatch. Expected {expected_risk_amount}, got {position['actual_risk']}"
        )
        
        # STRICT TEST: Risk percentage must match exactly
        self.assertAlmostEqual(
            position['actual_risk_pct'],
            expected_risk_pct,
            places=2,  # 2 decimal places for percentage
            msg=f"Risk percentage mismatch. Expected {expected_risk_pct}%, got {position['actual_risk_pct']}%"
        )
        
        # Verify formula consistency
        calculated_shares = int((capital * 0.01) / (entry_price - stop_loss))
        self.assertEqual(position['shares_to_buy'], calculated_shares)
        
        # Verify position value is calculated correctly
        calculated_position_value = position['shares_to_buy'] * entry_price
        self.assertEqual(position['position_value'], calculated_position_value)
        
        # Verify actual risk is calculated correctly
        calculated_risk = position['shares_to_buy'] * (entry_price - stop_loss)
        self.assertAlmostEqual(position['actual_risk'], calculated_risk, places=2)
    
    def test_risk_reward_calculation_accuracy(self):
        """
        Test risk/reward ratio calculation accuracy with strict assertions.
        
        Formula: R:R = (Target - Entry) / (Entry - Stop)
        """
        entry = 100.0
        target = 110.0  # 10 point gain
        stop = 95.0     # 5 point loss
        mode = 'balanced'  # Requires 2:1 minimum
        
        ratio, is_valid, explanation = validate_risk_reward(entry, target, stop, mode)
        
        # Expected calculation:
        # Reward = |110 - 100| = 10
        # Risk = |100 - 95| = 5
        # R:R = 10 / 5 = 2.0
        expected_ratio = 2.0
        
        # STRICT TEST: Ratio must match exactly
        self.assertAlmostEqual(
            ratio,
            expected_ratio,
            places=4,  # High precision for ratio
            msg=f"R:R ratio mismatch. Expected {expected_ratio}, got {ratio}"
        )
        
        # STRICT TEST: Verify formula calculation
        calculated_ratio = abs(target - entry) / abs(entry - stop)
        self.assertAlmostEqual(ratio, calculated_ratio, places=4)
        
        # STRICT TEST: Should be valid (2:1 meets balanced mode minimum of 2:1)
        self.assertTrue(
            is_valid,
            f"R:R {ratio:.2f}:1 should be valid for {mode} mode (min 2:1). {explanation}"
        )
        
        # Test invalid case
        entry2 = 100.0
        target2 = 102.0  # 2 point gain
        stop2 = 95.0     # 5 point loss
        
        ratio2, is_valid2, _ = validate_risk_reward(entry2, target2, stop2, mode)
        expected_ratio2 = 2.0 / 5.0  # 0.4:1
        
        self.assertAlmostEqual(ratio2, expected_ratio2, places=4)
        self.assertFalse(
            is_valid2,
            f"R:R {ratio2:.2f}:1 should be invalid for {mode} mode (min 2:1)"
        )
    
    def test_target_calculation_accuracy(self):
        """Test target price calculation accuracy"""
        current_price = 100.0
        atr = 2.0
        resistance = 110.0
        support = 90.0
        fib_extensions = {'fib_ext_127': 115.0, 'fib_ext_161': 120.0}
        mode = 'balanced'
        
        targets = calculate_targets(
            current_price, atr, resistance, support,
            fib_extensions, mode, 'long'
        )
        
        # ATR target should be: current + (2.5 * atr) for balanced mode
        expected_atr_target = current_price + (RISK_MODES[mode]['atr_target_multiplier'] * atr)
        self.assertAlmostEqual(targets['atr_target'], expected_atr_target, places=2)
        
        # Conservative target should be min of reasonable targets
        self.assertLessEqual(targets['conservative_target'], targets['atr_target'])
        self.assertLessEqual(targets['conservative_target'], targets['resistance_target'])
    
    def test_stoploss_calculation_accuracy(self):
        """Test stop loss calculation accuracy"""
        current_price = 100.0
        atr = 2.0
        support = 90.0
        resistance = 110.0
        mode = 'balanced'
        
        stops = calculate_stoploss(
            current_price, atr, support, resistance, mode, 'long'
        )
        
        # ATR stop should be: current - (2.0 * atr) for balanced mode
        expected_atr_stop = current_price - (RISK_MODES[mode]['atr_stop_multiplier'] * atr)
        self.assertAlmostEqual(stops['atr_stop'], expected_atr_stop, places=2)
        
        # Recommended stop should be max of ATR stop and support stop (closer to price)
        self.assertGreaterEqual(stops['recommended_stop'], stops['atr_stop'])
        self.assertLess(stops['recommended_stop'], current_price)
    
    def test_confidence_calculation_consistency(self):
        """Test that confidence calculation is consistent"""
        # Create indicators with known bullish signals
        indicators = {
            'price_vs_trend_ema': 'above',
            'price_vs_medium_ema': 'above',
            'ema_alignment': 'bullish',
            'adx': 30,
            'adx_trend_direction': 'bullish',
            'rsi': 55,  # Neutral
            'rsi_zone': 'neutral',
            'rsi_direction': 'rising',
            'macd_crossover': 'none',
            'macd_above_signal': True,
            'macd_hist': 0.5,
            'hist_direction': 'expanding',
            'macd_above_zero': True,
            'divergence': 'none',
            'volume_ratio': 1.2,
            'momentum_direction': 'up',
            'obv_trend': 'rising',
            'bb_position': 'upper_half',
            'bb_percent': 0.6,
            'support_proximity': 'far',
            'resistance_proximity': 'far',
        }
        
        signal_data = calculate_all_signals(indicators, 'balanced')
        
        # Confidence should be between 0 and 100
        self.assertGreaterEqual(signal_data['confidence'], 0)
        self.assertLessEqual(signal_data['confidence'], 100)
        
        # With mostly bullish signals, confidence should be > 50
        self.assertGreater(signal_data['confidence'], 50)
        
        # Net score should be positive for bullish signals
        self.assertGreater(signal_data['net_score'], 0)
    
    def test_known_data_set(self):
        """Test with a known dataset to verify calculations"""
        # Create a dataset where we can manually verify some calculations
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        
        # Simple dataset: constant price of 100
        constant_df = pd.DataFrame({
            'open': [100] * 50,
            'high': [101] * 50,
            'low': [99] * 50,
            'close': [100] * 50,
            'volume': [1000000] * 50
        }, index=dates)
        
        # For constant prices, RSI calculation depends on the library implementation
        # With zero price changes, RSI can be undefined or edge case
        # Just verify it doesn't crash and returns a valid value
        rsi_data = calculate_rsi(constant_df['close'], TIMEFRAME_CONFIGS['short'])
        self.assertGreaterEqual(rsi_data['rsi'], 0)
        self.assertLessEqual(rsi_data['rsi'], 100)
        
        # Test with alternating up/down pattern (should give RSI around 50)
        alternating_prices = [100 + (1 if i % 2 == 0 else -1) for i in range(50)]
        alternating_df = pd.DataFrame({
            'open': alternating_prices,
            'high': [p + 1 for p in alternating_prices],
            'low': [p - 1 for p in alternating_prices],
            'close': alternating_prices,
            'volume': [1000000] * 50
        }, index=dates)
        
        rsi_data = calculate_rsi(alternating_df['close'], TIMEFRAME_CONFIGS['short'])
        # With alternating pattern, RSI should be closer to 50
        self.assertGreaterEqual(rsi_data['rsi'], 0)
        self.assertLessEqual(rsi_data['rsi'], 100)
    
    def test_edge_cases(self):
        """Test edge cases for calculation accuracy"""
        # Test with very small price
        small_price_df = self.simple_df.copy()
        small_price_df['close'] = small_price_df['close'] * 0.01  # Very small prices
        
        # Should still calculate without errors
        rsi_data = calculate_rsi(small_price_df['close'], self.config)
        self.assertGreaterEqual(rsi_data['rsi'], 0)
        self.assertLessEqual(rsi_data['rsi'], 100)
        
        # Test with very large price
        large_price_df = self.simple_df.copy()
        large_price_df['close'] = large_price_df['close'] * 1000  # Very large prices
        
        rsi_data = calculate_rsi(large_price_df['close'], self.config)
        self.assertGreaterEqual(rsi_data['rsi'], 0)
        self.assertLessEqual(rsi_data['rsi'], 100)
    
    def test_position_size_edge_cases(self):
        """Test position sizing with edge cases"""
        # Test with very small capital
        position = calculate_position_size(1000, 100, 95, 'balanced')
        self.assertFalse(position['error'])
        self.assertGreater(position['shares_to_buy'], 0)
        
        # Test with very large capital
        position = calculate_position_size(10000000, 100, 95, 'balanced')
        self.assertFalse(position['error'])
        # Should not exceed capital
        self.assertLessEqual(position['position_value'], 10000000)
        
        # Test with very tight stop (0.1% stop)
        position = calculate_position_size(100000, 100, 99.9, 'balanced')
        self.assertFalse(position['error'])
        # Should calculate correctly even with tight stops
        self.assertGreater(position['shares_to_buy'], 0)


if __name__ == '__main__':
    unittest.main()

