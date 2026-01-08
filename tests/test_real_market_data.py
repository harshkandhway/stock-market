"""
Real Market Data Tests - Test the system with actual stock and ETF data
Tests at least 10 different stocks/ETFs to verify calculations work with real data
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.cli.stock_analyzer_pro import fetch_data, analyze_stock
from src.core.indicators import calculate_all_indicators
from src.core.signals import calculate_all_signals
from src.core.risk_management import calculate_position_size, validate_risk_reward
from src.core.config import RISK_MODES, TIMEFRAME_CONFIGS


class TestRealMarketData(unittest.TestCase):
    """Test with real stock and ETF data from Yahoo Finance"""
    
    # Test symbols: Mix of stocks and ETFs from different markets
    TEST_SYMBOLS = [
        # Indian ETFs
        'SILVERBEES.NS',  # Silver ETF
        'GOLDBEES.NS',    # Gold ETF
        'NIFTYBEES.NS',   # Nifty ETF
        
        # Indian Stocks
        'RELIANCE.NS',    # Reliance Industries
        'TCS.NS',         # Tata Consultancy Services
        'INFY.NS',        # Infosys
        'HDFCBANK.NS',    # HDFC Bank
        
        # US Stocks
        'AAPL',           # Apple
        'MSFT',           # Microsoft
        'GOOGL',          # Google
    ]
    
    def setUp(self):
        """Set up test data by fetching real market data"""
        self.analyses = {}
        self.failed_symbols = []
        
        print("\n" + "=" * 80)
        print("FETCHING REAL MARKET DATA FOR TESTING")
        print("=" * 80)
        
        for symbol in self.TEST_SYMBOLS:
            print(f"\nFetching data for {symbol}...")
            df = fetch_data(symbol, '1y')
            
            if df.empty:
                print(f"  [WARNING] No data available for {symbol}")
                self.failed_symbols.append(symbol)
                continue
            
            if len(df) < 200:
                print(f"  [WARNING] Insufficient data for {symbol} ({len(df)} rows)")
                self.failed_symbols.append(symbol)
                continue
            
            print(f"  [OK] Data fetched: {len(df)} rows")
            self.analyses[symbol] = df
    
    def test_data_fetching_success_rate(self):
        """Test that we can fetch data for most symbols"""
        success_rate = len(self.analyses) / len(self.TEST_SYMBOLS)
        
        print(f"\n{'='*80}")
        print(f"DATA FETCHING RESULTS")
        print(f"{'='*80}")
        print(f"Total symbols tested: {len(self.TEST_SYMBOLS)}")
        print(f"Successfully fetched: {len(self.analyses)}")
        print(f"Failed: {len(self.failed_symbols)}")
        print(f"Success rate: {success_rate*100:.1f}%")
        
        if self.failed_symbols:
            print(f"\nFailed symbols: {', '.join(self.failed_symbols)}")
        
        # We should be able to fetch at least 7 out of 10 symbols
        self.assertGreaterEqual(
            len(self.analyses),
            7,
            f"Should fetch data for at least 7 symbols. Got {len(self.analyses)}"
        )
    
    def test_indicator_calculation_with_real_data(self):
        """Test that indicators can be calculated for all fetched symbols"""
        print(f"\n{'='*80}")
        print(f"INDICATOR CALCULATION TEST")
        print(f"{'='*80}")
        
        for symbol, df in self.analyses.items():
            with self.subTest(symbol=symbol):
                try:
                    indicators = calculate_all_indicators(df, 'medium')
                    
                    # Verify all required indicators are present
                    required_indicators = [
                        'current_price', 'rsi', 'macd', 'adx', 'atr',
                        'ema_fast', 'ema_medium', 'ema_slow', 'ema_trend',
                        'support', 'resistance', 'market_phase'
                    ]
                    
                    for indicator in required_indicators:
                        self.assertIn(
                            indicator,
                            indicators,
                            f"Missing indicator '{indicator}' for {symbol}"
                        )
                    
                    # Verify indicator values are reasonable
                    self.assertGreater(indicators['current_price'], 0, 
                                     f"Price should be positive for {symbol}")
                    self.assertGreaterEqual(indicators['rsi'], 0,
                                          f"RSI should be >= 0 for {symbol}")
                    self.assertLessEqual(indicators['rsi'], 100,
                                       f"RSI should be <= 100 for {symbol}")
                    self.assertGreater(indicators['atr'], 0,
                                     f"ATR should be positive for {symbol}")
                    
                    print(f"  [OK] {symbol}: All indicators calculated successfully")
                    print(f"    Price: {indicators['current_price']:.2f}, "
                          f"RSI: {indicators['rsi']:.1f}, "
                          f"ADX: {indicators['adx']:.1f}")
                    
                except Exception as e:
                    self.fail(f"Failed to calculate indicators for {symbol}: {e}")
    
    def test_signal_generation_with_real_data(self):
        """Test that signals can be generated for all symbols"""
        print(f"\n{'='*80}")
        print(f"SIGNAL GENERATION TEST")
        print(f"{'='*80}")
        
        for symbol, df in self.analyses.items():
            with self.subTest(symbol=symbol):
                try:
                    indicators = calculate_all_indicators(df, 'medium')
                    signal_data = calculate_all_signals(indicators, 'balanced')
                    
                    # Verify signal data structure
                    self.assertIn('confidence', signal_data)
                    self.assertIn('bullish_score', signal_data)
                    self.assertIn('bearish_score', signal_data)
                    self.assertIn('net_score', signal_data)
                    
                    # Verify confidence is in valid range
                    self.assertGreaterEqual(signal_data['confidence'], 0,
                                          f"Confidence should be >= 0 for {symbol}")
                    self.assertLessEqual(signal_data['confidence'], 100,
                                       f"Confidence should be <= 100 for {symbol}")
                    
                    print(f"  [OK] {symbol}: Signals generated successfully")
                    print(f"    Confidence: {signal_data['confidence']:.1f}%, "
                          f"Net Score: {signal_data['net_score']:+.1f}")
                    
                except Exception as e:
                    self.fail(f"Failed to generate signals for {symbol}: {e}")
    
    def test_complete_analysis_with_real_data(self):
        """Test complete analysis pipeline with real data"""
        print(f"\n{'='*80}")
        print(f"COMPLETE ANALYSIS TEST")
        print(f"{'='*80}")
        
        results = []
        
        for symbol, df in self.analyses.items():
            with self.subTest(symbol=symbol):
                try:
                    analysis = analyze_stock(symbol, df, 'balanced', 'medium')
                    
                    # Verify analysis structure
                    required_keys = [
                        'symbol', 'confidence', 'recommendation',
                        'current_price', 'target', 'stop_loss',
                        'risk_reward', 'rr_valid'
                    ]
                    
                    for key in required_keys:
                        self.assertIn(key, analysis,
                                    f"Missing key '{key}' in analysis for {symbol}")
                    
                    # Verify values are reasonable
                    self.assertGreater(analysis['current_price'], 0)
                    self.assertGreater(analysis['target'], 0)
                    self.assertGreater(analysis['stop_loss'], 0)
                    self.assertGreater(analysis['risk_reward'], 0)
                    
                    # Verify recommendation is valid
                    valid_recommendations = [
                        'STRONG BUY', 'BUY', 'WEAK BUY', 'HOLD',
                        'WEAK SELL', 'SELL', 'STRONG SELL',
                        'AVOID - BUY BLOCKED', 'AVOID - SELL BLOCKED'
                    ]
                    self.assertIn(
                        analysis['recommendation'],
                        valid_recommendations,
                        f"Invalid recommendation '{analysis['recommendation']}' for {symbol}"
                    )
                    
                    results.append({
                        'symbol': symbol,
                        'price': analysis['current_price'],
                        'confidence': analysis['confidence'],
                        'recommendation': analysis['recommendation'],
                        'rr': analysis['risk_reward']
                    })
                    
                    print(f"  [OK] {symbol}: Analysis complete")
                    print(f"    {analysis['recommendation']} "
                          f"({analysis['confidence']:.0f}% confidence, "
                          f"R:R {analysis['risk_reward']:.2f}:1)")
                    
                except Exception as e:
                    self.fail(f"Failed to analyze {symbol}: {e}")
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"ANALYSIS SUMMARY")
        print(f"{'='*80}")
        print(f"{'Symbol':<20} {'Price':>12} {'Confidence':>12} {'Recommendation':<20} {'R:R':>8}")
        print(f"{'-'*80}")
        for r in results:
            print(f"{r['symbol']:<20} {r['price']:>12.2f} {r['confidence']:>11.0f}% "
                  f"{r['recommendation']:<20} {r['rr']:>7.2f}:1")
    
    def test_position_sizing_with_real_data(self):
        """Test position sizing with real stock prices"""
        print(f"\n{'='*80}")
        print(f"POSITION SIZING WITH REAL DATA TEST")
        print(f"{'='*80}")
        
        capital = 100000  # Test with 100k capital
        
        for symbol, df in list(self.analyses.items())[:5]:  # Test first 5
            with self.subTest(symbol=symbol):
                try:
                    analysis = analyze_stock(symbol, df, 'balanced', 'medium')
                    
                    if analysis['recommendation_type'] == 'BUY' and analysis['rr_valid']:
                        position = calculate_position_size(
                            capital,
                            analysis['current_price'],
                            analysis['stop_loss'],
                            'balanced'
                        )
                        
                        self.assertFalse(position['error'])
                        self.assertGreater(position['shares_to_buy'], 0)
                        self.assertLessEqual(position['position_value'], capital)
                        
                        # Verify risk percentage
                        self.assertAlmostEqual(
                            position['actual_risk_pct'],
                            1.0,  # Balanced mode = 1%
                            places=1
                        )
                        
                        print(f"  [OK] {symbol}: Position sizing valid")
                        print(f"    {position['shares_to_buy']} shares @ "
                              f"{analysis['current_price']:.2f} = "
                              f"{position['position_value']:,.2f}")
                        print(f"    Risk: {position['actual_risk_pct']:.2f}% "
                              f"({position['actual_risk']:,.2f})")
                    else:
                        print(f"  - {symbol}: Not a valid BUY (skipping position sizing)")
                        
                except Exception as e:
                    self.fail(f"Failed position sizing for {symbol}: {e}")
    
    def test_different_risk_modes_with_real_data(self):
        """Test that different risk modes work with real data"""
        print(f"\n{'='*80}")
        print(f"RISK MODE TESTING")
        print(f"{'='*80}")
        
        test_symbol = list(self.analyses.keys())[0] if self.analyses else None
        if not test_symbol:
            self.skipTest("No data available for testing")
        
        df = self.analyses[test_symbol]
        
        for mode in ['conservative', 'balanced', 'aggressive']:
            with self.subTest(mode=mode, symbol=test_symbol):
                try:
                    analysis = analyze_stock(test_symbol, df, mode, 'medium')
                    
                    # Verify mode-specific thresholds
                    min_rr = RISK_MODES[mode]['min_risk_reward']
                    
                    if analysis['rr_valid']:
                        self.assertGreaterEqual(
                            analysis['risk_reward'],
                            min_rr,
                            f"R:R {analysis['risk_reward']:.2f}:1 should be >= {min_rr}:1 for {mode} mode"
                        )
                    
                    print(f"  [OK] {test_symbol} ({mode}): "
                          f"R:R {analysis['risk_reward']:.2f}:1, "
                          f"Valid: {analysis['rr_valid']}")
                    
                except Exception as e:
                    self.fail(f"Failed {mode} mode analysis for {test_symbol}: {e}")
    
    def test_different_timeframes_with_real_data(self):
        """Test that different timeframes work with real data"""
        print(f"\n{'='*80}")
        print(f"TIMEFRAME TESTING")
        print(f"{'='*80}")
        
        test_symbol = list(self.analyses.keys())[0] if self.analyses else None
        if not test_symbol:
            self.skipTest("No data available for testing")
        
        df = self.analyses[test_symbol]
        
        for timeframe in ['short', 'medium']:
            with self.subTest(timeframe=timeframe, symbol=test_symbol):
                try:
                    analysis = analyze_stock(test_symbol, df, 'balanced', timeframe)
                    
                    # Verify timeframe-specific indicators
                    config = TIMEFRAME_CONFIGS[timeframe]
                    self.assertEqual(analysis['timeframe'], config['name'])
                    
                    # Verify indicators use correct periods
                    indicators = analysis['indicators']
                    self.assertEqual(indicators['rsi_period'], config['rsi_period'])
                    self.assertEqual(indicators['ema_fast_period'], config['ema_fast'])
                    
                    print(f"  [OK] {test_symbol} ({timeframe}): "
                          f"RSI period {config['rsi_period']}, "
                          f"Confidence: {analysis['confidence']:.1f}%")
                    
                except Exception as e:
                    self.fail(f"Failed {timeframe} timeframe analysis for {test_symbol}: {e}")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)

