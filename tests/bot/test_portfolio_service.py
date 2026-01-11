"""
Unit tests for portfolio service
Tests portfolio calculations, P&L, and position management
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.bot.services.portfolio_service import (
    calculate_position_pnl,
    calculate_portfolio_summary
)


class TestPortfolioService(unittest.TestCase):
    """Test cases for portfolio service"""
    
    def test_calculate_position_pnl_profit(self):
        """Test P&L calculation for profitable position"""
        pnl_data = calculate_position_pnl(
            shares=100,
            avg_buy_price=100.0,
            current_price=110.0
        )
        
        self.assertEqual(pnl_data['shares'], 100)
        self.assertEqual(pnl_data['avg_buy_price'], 100.0)
        self.assertEqual(pnl_data['current_price'], 110.0)
        self.assertEqual(pnl_data['invested_value'], 10000.0)
        self.assertEqual(pnl_data['current_value'], 11000.0)
        self.assertEqual(pnl_data['pnl'], 1000.0)
        self.assertAlmostEqual(pnl_data['pnl_percent'], 10.0, places=1)
    
    def test_calculate_position_pnl_loss(self):
        """Test P&L calculation for losing position"""
        pnl_data = calculate_position_pnl(
            shares=100,
            avg_buy_price=100.0,
            current_price=90.0
        )
        
        self.assertEqual(pnl_data['pnl'], -1000.0)
        self.assertAlmostEqual(pnl_data['pnl_percent'], -10.0, places=1)
    
    def test_calculate_position_pnl_zero_price(self):
        """Test P&L calculation with zero buy price"""
        pnl_data = calculate_position_pnl(
            shares=100,
            avg_buy_price=0.0,
            current_price=100.0
        )
        
        self.assertEqual(pnl_data['pnl_percent'], 0.0)
    
    @patch('src.bot.services.portfolio_service.get_user_portfolio')
    @patch('src.bot.services.portfolio_service.get_multiple_prices')
    @patch('src.bot.services.portfolio_service.get_current_price')
    def test_calculate_portfolio_summary_empty(self, mock_get_price, mock_get_prices, mock_get_portfolio):
        """Test portfolio summary with no positions"""
        mock_get_portfolio.return_value = []
        
        mock_db = Mock()
        summary = calculate_portfolio_summary(mock_db, 123456)
        
        self.assertEqual(summary['total_positions'], 0)
        self.assertEqual(summary['total_invested'], 0.0)
        self.assertEqual(summary['total_current_value'], 0.0)
        self.assertEqual(summary['total_pnl'], 0.0)
        self.assertEqual(len(summary['positions']), 0)
    
    @patch('src.bot.services.portfolio_service.get_user_portfolio')
    @patch('src.bot.services.portfolio_service.get_multiple_prices')
    @patch('src.bot.services.portfolio_service.get_current_price')
    def test_calculate_portfolio_summary_with_positions(self, mock_get_price, mock_get_prices, mock_get_portfolio):
        """Test portfolio summary with positions"""
        # Create mock positions
        pos1 = Mock()
        pos1.symbol = 'STOCK1'
        pos1.shares = 100
        pos1.avg_buy_price = 100.0
        
        pos2 = Mock()
        pos2.symbol = 'STOCK2'
        pos2.shares = 50
        pos2.avg_buy_price = 200.0
        
        mock_get_portfolio.return_value = [pos1, pos2]
        mock_get_prices.return_value = {
            'STOCK1': 110.0,
            'STOCK2': 190.0
        }
        
        mock_db = Mock()
        summary = calculate_portfolio_summary(mock_db, 123456)
        
        self.assertEqual(summary['total_positions'], 2)
        self.assertEqual(summary['total_invested'], 20000.0)  # 100*100 + 50*200
        self.assertGreater(summary['total_current_value'], 0)
        self.assertEqual(len(summary['positions']), 2)
        
        # Check first position
        pos1_data = summary['positions'][0]
        self.assertEqual(pos1_data['symbol'], 'STOCK1')
        self.assertEqual(pos1_data['pnl'], 1000.0)  # 100 * (110 - 100)


if __name__ == '__main__':
    unittest.main()

