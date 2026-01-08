"""
Unit tests for indicators module
"""

import unittest
import pandas as pd
import numpy as np
from indicators import (
    calculate_emas, calculate_rsi, calculate_macd, calculate_adx,
    calculate_atr, calculate_bollinger_bands, calculate_stochastic,
    calculate_volume_indicators, calculate_support_resistance,
    calculate_fibonacci_levels, calculate_momentum, calculate_all_indicators
)
from config import TIMEFRAME_CONFIGS


class TestIndicators(unittest.TestCase):
    """Test cases for technical indicator calculations"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample OHLCV data (250 rows to meet minimum requirements)
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        np.random.seed(42)
        
        # Generate realistic price data
        base_price = 100
        returns = np.random.normal(0.001, 0.02, 250)  # 0.1% mean, 2% std
        prices = base_price * np.exp(np.cumsum(returns))
        
        self.df = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.005, 250)),
            'high': prices * (1 + abs(np.random.normal(0, 0.01, 250))),
            'low': prices * (1 - abs(np.random.normal(0, 0.01, 250))),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 250)
        }, index=dates)
        
        # Ensure high >= close >= low
        self.df['high'] = self.df[['open', 'close', 'high']].max(axis=1)
        self.df['low'] = self.df[['open', 'close', 'low']].min(axis=1)
        
        self.config = TIMEFRAME_CONFIGS['medium']
    
    def test_calculate_emas(self):
        """Test EMA calculation"""
        emas = calculate_emas(self.df['close'], self.config)
        
        self.assertIn('ema_fast', emas)
        self.assertIn('ema_medium', emas)
        self.assertIn('ema_slow', emas)
        self.assertIn('ema_trend', emas)
        
        # Check that EMAs are Series
        self.assertIsInstance(emas['ema_fast'], pd.Series)
        
        # Check that latest values are numbers
        self.assertFalse(pd.isna(emas['ema_fast'].iloc[-1]))
    
    def test_calculate_rsi(self):
        """Test RSI calculation"""
        rsi_data = calculate_rsi(self.df['close'], self.config)
        
        self.assertIn('rsi', rsi_data)
        self.assertIn('rsi_zone', rsi_data)
        self.assertIn('rsi_direction', rsi_data)
        
        # RSI should be between 0 and 100
        self.assertGreaterEqual(rsi_data['rsi'], 0)
        self.assertLessEqual(rsi_data['rsi'], 100)
        
        # Zone should be valid
        valid_zones = [
            'extremely_overbought', 'overbought', 'slightly_overbought',
            'neutral', 'slightly_oversold', 'oversold', 'extremely_oversold'
        ]
        self.assertIn(rsi_data['rsi_zone'], valid_zones)
    
    def test_calculate_macd(self):
        """Test MACD calculation"""
        macd_data = calculate_macd(self.df['close'], self.config)
        
        self.assertIn('macd', macd_data)
        self.assertIn('macd_signal', macd_data)
        self.assertIn('macd_hist', macd_data)
        self.assertIn('macd_crossover', macd_data)
        self.assertIn('macd_above_zero', macd_data)
        
        # Crossover should be valid
        valid_crossovers = ['none', 'bullish', 'bearish']
        self.assertIn(macd_data['macd_crossover'], valid_crossovers)
    
    def test_calculate_adx(self):
        """Test ADX calculation"""
        adx_data = calculate_adx(
            self.df['high'], self.df['low'], self.df['close'], self.config
        )
        
        self.assertIn('adx', adx_data)
        self.assertIn('adx_strength', adx_data)
        self.assertIn('trend_exists', adx_data)
        
        # ADX should be between 0 and 100
        self.assertGreaterEqual(adx_data['adx'], 0)
        self.assertLessEqual(adx_data['adx'], 100)
        
        # Strength should be valid
        valid_strengths = [
            'no_trend', 'weak_trend', 'trend',
            'strong_trend', 'very_strong_trend'
        ]
        self.assertIn(adx_data['adx_strength'], valid_strengths)
    
    def test_calculate_atr(self):
        """Test ATR calculation"""
        atr_data = calculate_atr(
            self.df['high'], self.df['low'], self.df['close'], self.config
        )
        
        self.assertIn('atr', atr_data)
        self.assertIn('atr_percent', atr_data)
        self.assertIn('volatility_level', atr_data)
        
        # ATR should be positive
        self.assertGreater(atr_data['atr'], 0)
        
        # ATR percent should be reasonable (typically 1-5%)
        self.assertGreater(atr_data['atr_percent'], 0)
        self.assertLess(atr_data['atr_percent'], 20)  # Sanity check
    
    def test_calculate_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        bb_data = calculate_bollinger_bands(self.df['close'], self.config)
        
        self.assertIn('bb_upper', bb_data)
        self.assertIn('bb_middle', bb_data)
        self.assertIn('bb_lower', bb_data)
        self.assertIn('bb_percent', bb_data)
        
        # Upper should be > middle > lower
        self.assertGreater(bb_data['bb_upper'], bb_data['bb_middle'])
        self.assertGreater(bb_data['bb_middle'], bb_data['bb_lower'])
    
    def test_calculate_support_resistance(self):
        """Test support/resistance calculation"""
        sr_data = calculate_support_resistance(self.df, self.config)
        
        self.assertIn('resistance', sr_data)
        self.assertIn('support', sr_data)
        self.assertIn('high_52w', sr_data)
        self.assertIn('low_52w', sr_data)
        
        # Resistance should be >= support
        self.assertGreaterEqual(sr_data['resistance'], sr_data['support'])
        
        # 52-week high should be >= resistance
        self.assertGreaterEqual(sr_data['high_52w'], sr_data['resistance'])
        
        # 52-week low should be <= support
        self.assertLessEqual(sr_data['low_52w'], sr_data['support'])
    
    def test_calculate_fibonacci_levels(self):
        """Test Fibonacci level calculation"""
        high = 120
        low = 80
        current = 100
        
        fib_data = calculate_fibonacci_levels(high, low, current)
        
        self.assertIn('fib_retracements', fib_data)
        self.assertIn('fib_extensions', fib_data)
        self.assertIn('nearest_fib_level', fib_data)
        
        # Retracements should be between low and high
        for level in fib_data['fib_retracements'].values():
            self.assertGreaterEqual(level, low)
            self.assertLessEqual(level, high)
    
    def test_calculate_all_indicators(self):
        """Test complete indicator calculation"""
        indicators = calculate_all_indicators(self.df, 'medium')
        
        # Check required keys
        required_keys = [
            'current_price', 'rsi', 'macd', 'adx', 'atr',
            'ema_fast', 'ema_medium', 'ema_slow', 'ema_trend',
            'support', 'resistance', 'market_phase'
        ]
        
        for key in required_keys:
            self.assertIn(key, indicators, f"Missing key: {key}")
        
        # Current price should be positive
        self.assertGreater(indicators['current_price'], 0)
        
        # Market phase should be valid
        valid_phases = [
            'strong_uptrend', 'uptrend', 'weak_uptrend',
            'consolidation', 'weak_downtrend', 'downtrend', 'strong_downtrend'
        ]
        self.assertIn(indicators['market_phase'], valid_phases)


if __name__ == '__main__':
    unittest.main()

