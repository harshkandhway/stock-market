"""
Unit tests for output module
Tests report formatting and display functions
"""

import unittest
import sys
import os
from io import StringIO
from contextlib import redirect_stdout

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.output import (
    print_header, print_hard_filter_warning, print_market_regime,
    print_indicator_table, print_signal_summary, print_recommendation_box,
    print_reasoning, print_action_plan, print_price_levels,
    print_risk_reward, print_position_sizing, print_trailing_stop_strategy,
    print_full_report, print_summary_table, print_portfolio_ranking,
    print_portfolio_allocation, print_disclaimer
)
from src.core.config import CURRENCY_SYMBOL


class TestOutput(unittest.TestCase):
    """Test cases for output formatting functions"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_indicators = {
            'price_vs_trend_ema': 'above',
            'ema_trend_period': 200,
            'ema_trend': 95.0,  # Required for print_indicator_table
            'ema_medium_period': 50,  # Required for print_indicator_table
            'ema_medium': 98.0,  # Required for print_indicator_table
            'adx': 30.5,
            'adx_strength': 'trend',
            'market_phase': 'uptrend',
            'ema_alignment': 'bullish',
            'rsi': 55.5,
            'rsi_period': 14,
            'macd_hist': 0.5,
            'macd_crossover': 'none',
            'trend_exists': True,
            'volume_ratio': 1.2,
            'bb_percent': 0.6,
            'divergence': 'none',
            'current_price': 100.0,
            'high_52w': 120.0,
            'low_52w': 80.0,
            'resistance': 110.0,
            'support': 90.0,
        }
        
        self.sample_signal_data = {
            'signals': {
                'rsi_zone': (5.0, 'neutral'),
                'macd_signal': (3.0, 'bullish'),
                'price_vs_trend_ema': (10.0, 'bullish'),
                'price_vs_medium_ema': (7.0, 'bullish'),
                'adx_strength': (2.0, 'bullish'),
                'volume_confirmation': (4.0, 'bullish'),
                'bollinger_position': (3.0, 'neutral'),
                'divergence': (0.0, 'none'),
            },
            'bullish_score': 31.0,
            'bearish_score': 0.0,
            'net_score': 31.0,
            'bullish_count': 5,
            'bearish_count': 0,
            'neutral_count': 3,
            'confidence': 65.5
        }
        
        self.sample_analysis = {
            'symbol': 'TEST.NS',
            'mode': 'balanced',
            'timeframe': 'MEDIUM-TERM',
            'current_price': 100.0,
            'indicators': self.sample_indicators,
            'signal_data': self.sample_signal_data,
            'confidence': 65.5,
            'confidence_level': 'MEDIUM',
            'recommendation': 'BUY',
            'recommendation_type': 'BUY',
            'is_buy_blocked': False,
            'buy_block_reasons': [],
            'is_sell_blocked': False,
            'sell_block_reasons': [],
            'target_data': {
                'recommended_target': 110.0,
                'recommended_target_pct': 10.0,
                'conservative_target': 108.0,
                'conservative_target_pct': 8.0,
                'atr_target': 110.0,
                'atr_target_pct': 10.0,
            },
            'stop_data': {
                'recommended_stop': 95.0,
                'recommended_stop_pct': 5.0,
            },
            'target': 110.0,
            'stop_loss': 95.0,
            'risk_reward': 2.0,
            'rr_valid': True,
            'rr_explanation': 'Risk/Reward 2.00:1 meets minimum requirement of 2.0:1',
            'reasoning': [
                'Uptrend: Price above trend EMA with confirmed trend',
                'RSI at 55.5 indicates neutral conditions'
            ],
            'actions': {
                'new_investors': 'Wait for pullback to ₹50.00 for better entry',
                'existing_holders': 'Hold position. Add only on confirmed breakout above ₹110.00',
                'traders': 'Scale into position gradually. Use tight stops.'
            },
            'trailing_data': {
                'explanation': 'Trailing stop strategy explanation'
            }
        }
    
    def test_print_header(self):
        """Test header printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_header('TEST.NS', 'balanced', 'medium')
        output = f.getvalue()
        
        self.assertIn('TEST.NS', output)
        self.assertIn('BALANCED', output)
        self.assertIn('MEDIUM', output)
    
    def test_print_hard_filter_warning(self):
        """Test hard filter warning printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_hard_filter_warning(True, ['RSI > 80: Extremely overbought'], 'buy')
        output = f.getvalue()
        
        self.assertIn('BLOCKED', output)
        self.assertIn('RSI > 80', output)
        
        # Test when not blocked (should print nothing)
        f2 = StringIO()
        with redirect_stdout(f2):
            print_hard_filter_warning(False, [], 'buy')
        output2 = f2.getvalue()
        self.assertEqual(output2, '')
    
    def test_print_market_regime(self):
        """Test market regime printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_market_regime(self.sample_indicators)
        output = f.getvalue()
        
        self.assertIn('MARKET REGIME', output)
        self.assertIn('BULLISH', output)
        self.assertIn('UPTREND', output)
    
    def test_print_indicator_table(self):
        """Test indicator table printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_indicator_table(self.sample_indicators, self.sample_signal_data)
        output = f.getvalue()
        
        self.assertIn('TECHNICAL INDICATORS', output)
        self.assertIn('RSI', output)
        self.assertIn('MACD', output)
    
    def test_print_signal_summary(self):
        """Test signal summary printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_signal_summary(self.sample_signal_data)
        output = f.getvalue()
        
        self.assertIn('SIGNAL SUMMARY', output)
        self.assertIn('Bullish Signals', output)
        self.assertIn('5', output)  # bullish_count
        self.assertIn('31.0', output)  # bullish_score
    
    def test_print_recommendation_box(self):
        """Test recommendation box printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_recommendation_box('BUY', 65.5, 'MEDIUM', False)
        output = f.getvalue()
        
        self.assertIn('RECOMMENDATION', output)
        self.assertIn('BUY', output)
        self.assertIn('66', output)  # confidence rounded to 0 decimal places (65.5 -> 66)
        self.assertIn('MEDIUM', output)
        
        # Test blocked case
        f2 = StringIO()
        with redirect_stdout(f2):
            print_recommendation_box('AVOID - BUY BLOCKED', 0, 'N/A', True)
        output2 = f2.getvalue()
        self.assertIn('BLOCKED', output2)
    
    def test_print_reasoning(self):
        """Test reasoning printing"""
        reasoning = [
            'Uptrend: Price above trend EMA',
            'WARNING: RSI > 80: Extremely overbought'
        ]
        
        f = StringIO()
        with redirect_stdout(f):
            print_reasoning(reasoning)
        output = f.getvalue()
        
        self.assertIn('REASONING', output)
        self.assertIn('Uptrend', output)
        self.assertIn('WARNING', output)
    
    def test_print_action_plan(self):
        """Test action plan printing"""
        actions = {
            'new_investors': 'Wait for pullback',
            'existing_holders': 'Hold position',
            'traders': 'Scale into position'
        }
        
        f = StringIO()
        with redirect_stdout(f):
            print_action_plan(actions)
        output = f.getvalue()
        
        self.assertIn('ACTION PLAN', output)
        self.assertIn('NEW INVESTORS', output)
        self.assertIn('EXISTING HOLDERS', output)
        self.assertIn('TRADERS', output)
    
    def test_print_price_levels(self):
        """Test price levels printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_price_levels(
                self.sample_indicators,
                self.sample_analysis['target_data'],
                self.sample_analysis['stop_data']
            )
        output = f.getvalue()
        
        self.assertIn('LEVELS TO WATCH', output)
        self.assertIn('Current Price', output)
        self.assertIn('100.00', output)
        self.assertIn('RESISTANCE', output)
        self.assertIn('SUPPORT', output)
        self.assertIn('STOP LOSS', output)
    
    def test_print_risk_reward(self):
        """Test risk/reward printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_risk_reward(2.0, True, 'Risk/Reward 2.00:1 meets minimum', 'balanced')
        output = f.getvalue()
        
        self.assertIn('RISK MANAGEMENT', output)
        self.assertIn('2.00:1', output)
        self.assertIn('VALID', output)
        
        # Test invalid case
        f2 = StringIO()
        with redirect_stdout(f2):
            print_risk_reward(1.5, False, 'Risk/Reward 1.50:1 is BELOW minimum', 'balanced')
        output2 = f2.getvalue()
        self.assertIn('INVALID', output2)
    
    def test_print_position_sizing(self):
        """Test position sizing printing"""
        position_data = {
            'error': False,
            'explanation': 'Position sizing explanation'
        }
        
        f = StringIO()
        with redirect_stdout(f):
            print_position_sizing(position_data)
        output = f.getvalue()
        
        # When error is False, it just prints the explanation directly
        self.assertIn('explanation', output)
        
        # Test error case
        error_data = {
            'error': True,
            'message': 'Invalid stop loss'
        }
        
        f2 = StringIO()
        with redirect_stdout(f2):
            print_position_sizing(error_data)
        output2 = f2.getvalue()
        self.assertIn('POSITION SIZING', output2)
        self.assertIn('Error', output2)
        self.assertIn('Invalid stop loss', output2)
    
    def test_print_trailing_stop_strategy(self):
        """Test trailing stop strategy printing"""
        trailing_data = {
            'explanation': 'Trailing stop explanation text'
        }
        
        f = StringIO()
        with redirect_stdout(f):
            print_trailing_stop_strategy(trailing_data)
        output = f.getvalue()
        
        self.assertIn('explanation', output)
    
    def test_print_summary_table(self):
        """Test summary table printing"""
        analyses = [
            {
                'symbol': 'STOCK1',
                'current_price': 100.0,
                'confidence': 75.0,
                'recommendation': 'BUY',
                'risk_reward': 2.5,
                'rr_valid': True,
                'is_buy_blocked': False
            },
            {
                'symbol': 'STOCK2',
                'current_price': 50.0,
                'confidence': 45.0,
                'recommendation': 'HOLD',
                'risk_reward': 1.8,
                'rr_valid': False,
                'is_buy_blocked': False
            }
        ]
        
        f = StringIO()
        with redirect_stdout(f):
            print_summary_table(analyses)
        output = f.getvalue()
        
        self.assertIn('SUMMARY', output)
        self.assertIn('STOCK1', output)
        self.assertIn('STOCK2', output)
        self.assertIn('BUY', output)
        self.assertIn('HOLD', output)
    
    def test_print_portfolio_ranking(self):
        """Test portfolio ranking printing"""
        analyses = [
            {
                'symbol': 'STOCK1',
                'confidence': 80.0,
                'recommendation': 'BUY',
                'risk_reward': 2.5,
                'rr_valid': True,
                'is_buy_blocked': False
            },
            {
                'symbol': 'STOCK2',
                'confidence': 60.0,
                'recommendation': 'WEAK BUY',
                'risk_reward': 2.0,
                'rr_valid': True,
                'is_buy_blocked': False
            }
        ]
        
        f = StringIO()
        with redirect_stdout(f):
            print_portfolio_ranking(analyses)
        output = f.getvalue()
        
        self.assertIn('PORTFOLIO RANKING', output)
        self.assertIn('STOCK1', output)
        self.assertIn('STOCK2', output)
        # Should be ranked by confidence (STOCK1 first)
        self.assertLess(output.find('STOCK1'), output.find('STOCK2'))
    
    def test_print_portfolio_allocation(self):
        """Test portfolio allocation printing"""
        allocation_data = {
            'investable': [
                {
                    'symbol': 'STOCK1',
                    'confidence': 80.0,
                    'weight_pct': 60.0,
                    'allocated_amount': 60000.0,
                    'shares': 600
                },
                {
                    'symbol': 'STOCK2',
                    'confidence': 40.0,
                    'weight_pct': 40.0,
                    'allocated_amount': 40000.0,
                    'shares': 800
                }
            ],
            'not_recommended': [],
            'total_allocated': 100000.0,
            'cash_remaining': 0.0
        }
        
        f = StringIO()
        with redirect_stdout(f):
            print_portfolio_allocation(allocation_data, 100000.0)
        output = f.getvalue()
        
        self.assertIn('PORTFOLIO ALLOCATION', output)
        self.assertIn('STOCK1', output)
        self.assertIn('STOCK2', output)
        self.assertIn('100,000', output)  # Formatted with comma
    
    def test_print_disclaimer(self):
        """Test disclaimer printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_disclaimer()
        output = f.getvalue()
        
        self.assertIn('DISCLAIMER', output)
        self.assertIn('educational purposes', output)
    
    def test_print_full_report(self):
        """Test full report printing"""
        f = StringIO()
        with redirect_stdout(f):
            print_full_report(self.sample_analysis, None)
        output = f.getvalue()
        
        # Verify all major sections are present
        self.assertIn('TEST.NS', output)
        self.assertIn('MARKET REGIME', output)
        self.assertIn('TECHNICAL INDICATORS', output)
        self.assertIn('RECOMMENDATION', output)
        self.assertIn('REASONING', output)
        self.assertIn('ACTION PLAN', output)
        self.assertIn('LEVELS TO WATCH', output)
        self.assertIn('RISK MANAGEMENT', output)
        # Note: print_full_report doesn't call print_disclaimer, it's called separately


if __name__ == '__main__':
    unittest.main()

