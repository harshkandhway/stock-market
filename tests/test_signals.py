"""
Unit tests for signals module
"""

import unittest
from signals import (
    check_hard_filters, calculate_trend_signals, calculate_momentum_signals,
    calculate_confirmation_signals, calculate_all_signals,
    get_confidence_level, determine_recommendation
)
from config import HARD_FILTERS, RISK_MODES


class TestSignals(unittest.TestCase):
    """Test cases for signal generation"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample indicators dictionary
        self.indicators = {
            'rsi': 50,
            'stoch_k': 50,
            'bb_percent': 0.5,
            'divergence': 'none',
            'price_vs_trend_ema': 'above',
            'price_vs_medium_ema': 'above',
            'ema_alignment': 'bullish',
            'adx': 30,
            'adx_trend_direction': 'bullish',
            'rsi_zone': 'neutral',
            'rsi_direction': 'rising',
            'macd_crossover': 'none',
            'macd_above_signal': True,
            'macd_hist': 0.5,
            'hist_direction': 'expanding',
            'macd_above_zero': True,
            'volume_ratio': 1.2,
            'momentum_direction': 'up',
            'obv_trend': 'rising',
            'bb_position': 'upper_half',
            'support_proximity': 'far',
            'resistance_proximity': 'far',
        }
    
    def test_check_hard_filters_buy_blocked(self):
        """Test hard filters blocking buy signals"""
        # Test RSI > 80 blocks buy
        indicators = self.indicators.copy()
        indicators['rsi'] = 85
        
        is_blocked, reasons = check_hard_filters(indicators, 'buy')
        self.assertTrue(is_blocked)
        self.assertGreater(len(reasons), 0)
        
        # Test Stochastic > 85 blocks buy
        indicators = self.indicators.copy()
        indicators['stoch_k'] = 90
        
        is_blocked, reasons = check_hard_filters(indicators, 'buy')
        self.assertTrue(is_blocked)
    
    def test_check_hard_filters_sell_blocked(self):
        """Test hard filters blocking sell signals"""
        # Test RSI < 20 blocks sell
        indicators = self.indicators.copy()
        indicators['rsi'] = 15
        
        is_blocked, reasons = check_hard_filters(indicators, 'sell')
        self.assertTrue(is_blocked)
        self.assertGreater(len(reasons), 0)
    
    def test_check_hard_filters_not_blocked(self):
        """Test normal conditions don't trigger filters"""
        is_blocked, reasons = check_hard_filters(self.indicators, 'buy')
        self.assertFalse(is_blocked)
        self.assertEqual(len(reasons), 0)
    
    def test_calculate_trend_signals(self):
        """Test trend signal calculation"""
        signals = calculate_trend_signals(self.indicators, 'balanced')
        
        self.assertIn('price_vs_trend_ema', signals)
        self.assertIn('price_vs_medium_ema', signals)
        self.assertIn('ema_alignment', signals)
        self.assertIn('adx_strength', signals)
        
        # Check signal format: (score, direction)
        for signal_name, signal_value in signals.items():
            self.assertIsInstance(signal_value, tuple)
            self.assertEqual(len(signal_value), 2)
            score, direction = signal_value
            self.assertIsInstance(score, (int, float))
            self.assertIn(direction, ['bullish', 'bearish', 'neutral'])
    
    def test_calculate_momentum_signals(self):
        """Test momentum signal calculation"""
        signals = calculate_momentum_signals(self.indicators, 'balanced')
        
        self.assertIn('rsi_zone', signals)
        self.assertIn('rsi_direction', signals)
        self.assertIn('macd_signal', signals)
        self.assertIn('macd_histogram', signals)
        self.assertIn('macd_zero_line', signals)
        self.assertIn('divergence', signals)
    
    def test_calculate_confirmation_signals(self):
        """Test confirmation signal calculation"""
        signals = calculate_confirmation_signals(self.indicators, 'balanced')
        
        self.assertIn('volume_confirmation', signals)
        self.assertIn('volume_trend', signals)
        self.assertIn('bollinger_position', signals)
        self.assertIn('support_resistance', signals)
    
    def test_calculate_all_signals(self):
        """Test complete signal calculation"""
        signal_data = calculate_all_signals(self.indicators, 'balanced')
        
        self.assertIn('signals', signal_data)
        self.assertIn('confidence', signal_data)
        self.assertIn('bullish_score', signal_data)
        self.assertIn('bearish_score', signal_data)
        self.assertIn('net_score', signal_data)
        
        # Confidence should be between 0 and 100
        self.assertGreaterEqual(signal_data['confidence'], 0)
        self.assertLessEqual(signal_data['confidence'], 100)
    
    def test_get_confidence_level(self):
        """Test confidence level determination"""
        self.assertEqual(get_confidence_level(95), 'VERY HIGH')
        self.assertEqual(get_confidence_level(80), 'HIGH')
        self.assertEqual(get_confidence_level(65), 'MEDIUM')
        self.assertEqual(get_confidence_level(45), 'LOW')
        self.assertEqual(get_confidence_level(20), 'VERY LOW')
    
    def test_determine_recommendation(self):
        """Test recommendation determination"""
        # High confidence, not blocked
        rec, rec_type = determine_recommendation(85, False, False, 'balanced')
        self.assertIn('BUY', rec)
        self.assertEqual(rec_type, 'BUY')
        
        # Low confidence, not blocked
        rec, rec_type = determine_recommendation(20, False, False, 'balanced')
        self.assertIn('SELL', rec)
        self.assertEqual(rec_type, 'SELL')
        
        # High confidence but buy blocked
        rec, rec_type = determine_recommendation(85, True, False, 'balanced')
        self.assertEqual(rec_type, 'BLOCKED')
        
        # Medium confidence
        rec, rec_type = determine_recommendation(50, False, False, 'balanced')
        self.assertEqual(rec_type, 'HOLD')
    
    def test_signal_weights_by_mode(self):
        """Test that different modes affect signal weights"""
        balanced_signals = calculate_all_signals(self.indicators, 'balanced')
        conservative_signals = calculate_all_signals(self.indicators, 'conservative')
        aggressive_signals = calculate_all_signals(self.indicators, 'aggressive')
        
        # All should produce valid confidence scores
        self.assertGreaterEqual(balanced_signals['confidence'], 0)
        self.assertGreaterEqual(conservative_signals['confidence'], 0)
        self.assertGreaterEqual(aggressive_signals['confidence'], 0)


if __name__ == '__main__':
    unittest.main()

