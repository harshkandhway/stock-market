"""
Comprehensive Tests for Market Hours Service
Tests market hours detection, holidays, weekends, and edge cases

Author: Harsh Kandhway
"""

import pytest
from datetime import datetime, time, date
import pytz

from src.bot.services.market_hours_service import MarketHoursService, get_market_hours_service


class TestMarketHoursService:
    """Test market hours service"""

    @pytest.fixture
    def market_hours(self):
        """Create market hours service instance"""
        return MarketHoursService()

    def test_is_market_open_weekday_during_hours(self, market_hours):
        """Test market is open on weekday during trading hours"""
        # Monday 10:00 AM IST
        test_time = datetime(2026, 1, 13, 10, 0, 0)  # Monday
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        assert market_hours.is_market_open(test_time) is True

    def test_is_market_open_weekday_before_open(self, market_hours):
        """Test market is closed before 9:15 AM"""
        # Monday 8:00 AM IST
        test_time = datetime(2026, 1, 13, 8, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        assert market_hours.is_market_open(test_time) is False

    def test_is_market_open_weekday_after_close(self, market_hours):
        """Test market is closed after 3:30 PM"""
        # Monday 4:00 PM IST
        test_time = datetime(2026, 1, 13, 16, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        assert market_hours.is_market_open(test_time) is False

    def test_is_market_open_saturday(self, market_hours):
        """Test market is closed on Saturday"""
        # Saturday 10:00 AM IST
        test_time = datetime(2026, 1, 11, 10, 0, 0)  # Saturday
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        assert market_hours.is_market_open(test_time) is False

    def test_is_market_open_sunday(self, market_hours):
        """Test market is closed on Sunday"""
        # Sunday 10:00 AM IST - Jan 12, 2026 is actually a Monday, use Jan 11, 2026 (Sunday)
        test_time = datetime(2026, 1, 11, 10, 0, 0)  # Sunday
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        assert market_hours.is_market_open(test_time) is False

    def test_is_market_open_republic_day(self, market_hours):
        """Test market is closed on Republic Day"""
        # January 26, 2026 - Republic Day
        test_time = datetime(2026, 1, 26, 10, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        assert market_hours.is_market_open(test_time) is False

    def test_is_market_open_diwali(self, market_hours):
        """Test market is closed on Diwali"""
        # October 20, 2026 - Diwali
        test_time = datetime(2026, 10, 20, 10, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        assert market_hours.is_market_open(test_time) is False

    def test_is_market_open_exact_open_time(self, market_hours):
        """Test market is open exactly at 9:15 AM"""
        test_time = datetime(2026, 1, 13, 9, 15, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        assert market_hours.is_market_open(test_time) is True

    def test_is_market_open_exact_close_time(self, market_hours):
        """Test market is open exactly at 3:30 PM"""
        test_time = datetime(2026, 1, 13, 15, 30, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        assert market_hours.is_market_open(test_time) is True

    def test_get_next_market_open_weekday_during_hours(self, market_hours):
        """Test getting next market open when market is currently open"""
        # Monday 10:00 AM IST (market is open)
        test_time = datetime(2026, 1, 13, 10, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        next_open = market_hours.get_next_market_open(test_time)
        
        # Should be next day at 9:15 AM
        assert next_open.date() == date(2026, 1, 14)
        assert next_open.time() == time(9, 15)

    def test_get_next_market_open_weekday_after_hours(self, market_hours):
        """Test getting next market open after market hours"""
        # Monday 5:00 PM IST (market closed)
        test_time = datetime(2026, 1, 13, 17, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        next_open = market_hours.get_next_market_open(test_time)
        
        # Should be next day at 9:15 AM
        assert next_open.date() == date(2026, 1, 14)
        assert next_open.time() == time(9, 15)

    def test_get_next_market_open_friday_after_hours(self, market_hours):
        """Test getting next market open after Friday close"""
        # Friday 4:00 PM IST
        test_time = datetime(2026, 1, 17, 16, 0, 0)  # Friday
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        next_open = market_hours.get_next_market_open(test_time)
        
        # Should be Monday at 9:15 AM (skip weekend)
        assert next_open.weekday() == 0  # Monday
        assert next_open.time() == time(9, 15)

    def test_get_next_market_open_saturday(self, market_hours):
        """Test getting next market open on Saturday"""
        # Saturday 10:00 AM IST
        test_time = datetime(2026, 1, 11, 10, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        next_open = market_hours.get_next_market_open(test_time)
        
        # Should be Monday at 9:15 AM
        assert next_open.weekday() == 0  # Monday
        assert next_open.time() == time(9, 15)

    def test_get_next_market_open_sunday(self, market_hours):
        """Test getting next market open on Sunday"""
        # Sunday 10:00 AM IST - Jan 11, 2026 is actually a Sunday
        test_time = datetime(2026, 1, 11, 10, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        next_open = market_hours.get_next_market_open(test_time)
        
        # Should be Monday at 9:15 AM
        assert next_open.weekday() == 0  # Monday
        assert next_open.time() == time(9, 15)

    def test_get_next_market_open_holiday(self, market_hours):
        """Test getting next market open on a holiday"""
        # Republic Day (Monday) - market closed
        test_time = datetime(2026, 1, 26, 10, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        next_open = market_hours.get_next_market_open(test_time)
        
        # Should be next trading day (Tuesday) at 9:15 AM
        assert next_open.date() == date(2026, 1, 27)
        assert next_open.time() == time(9, 15)

    def test_get_next_market_close_weekday_during_hours(self, market_hours):
        """Test getting next market close when market is open"""
        # Monday 10:00 AM IST
        test_time = datetime(2026, 1, 13, 10, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        next_close = market_hours.get_next_market_close(test_time)
        
        # Should be same day at 3:30 PM
        assert next_close.date() == date(2026, 1, 13)
        assert next_close.time() == time(15, 30)

    def test_seconds_until_market_open(self, market_hours):
        """Test calculating seconds until market opens"""
        # Monday 8:00 AM IST (1 hour 15 min before open)
        test_time = datetime(2026, 1, 13, 8, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        seconds = market_hours.seconds_until_market_open(test_time)
        
        # Should be approximately 1 hour 15 minutes = 4500 seconds
        assert 4400 <= seconds <= 4600

    def test_seconds_until_market_close(self, market_hours):
        """Test calculating seconds until market closes"""
        # Monday 10:00 AM IST (5 hours 30 min before close)
        test_time = datetime(2026, 1, 13, 10, 0, 0)
        test_time = market_hours.TIMEZONE.localize(test_time)
        
        seconds = market_hours.seconds_until_market_close(test_time)
        
        # Should be approximately 5 hours 30 minutes = 19800 seconds
        assert 19700 <= seconds <= 19900

    def test_is_market_day_weekday(self, market_hours):
        """Test weekday is a market day"""
        # Monday
        test_date = date(2026, 1, 13)
        
        assert market_hours.is_market_day(test_date) is True

    def test_is_market_day_weekend(self, market_hours):
        """Test weekend is not a market day"""
        # Saturday
        test_date = date(2026, 1, 11)
        
        assert market_hours.is_market_day(test_date) is False

    def test_is_market_day_holiday(self, market_hours):
        """Test holiday is not a market day"""
        # Republic Day
        test_date = date(2026, 1, 26)
        
        assert market_hours.is_market_day(test_date) is False

    def test_all_holidays_recognized(self, market_hours):
        """Test all defined holidays are recognized"""
        holidays_2026 = [
            (1, 26),   # Republic Day
            (3, 14),   # Holi
            (4, 6),    # Mahavir Jayanti
            (4, 10),   # Good Friday
            (8, 15),   # Independence Day
            (10, 2),   # Gandhi Jayanti / Dussehra
            (10, 20),  # Diwali
            (12, 25),  # Christmas
        ]
        
        for month, day in holidays_2026:
            test_date = date(2026, month, day)
            assert market_hours.is_market_day(test_date) is False, f"Holiday {month}/{day} not recognized"

    def test_get_market_hours_service_singleton(self):
        """Test get_market_hours_service returns singleton"""
        service1 = get_market_hours_service()
        service2 = get_market_hours_service()
        
        assert service1 is service2

    def test_timezone_handling_utc(self, market_hours):
        """Test handling UTC datetime"""
        # UTC time equivalent to 10:00 AM IST
        utc_time = datetime(2026, 1, 13, 4, 30, 0, tzinfo=pytz.UTC)  # IST is UTC+5:30
        
        # Should convert to IST and check market hours
        result = market_hours.is_market_open(utc_time)
        
        # 4:30 UTC = 10:00 IST, so market should be open
        assert result is True

    def test_timezone_handling_naive(self, market_hours):
        """Test handling naive datetime (assumes IST)"""
        # Naive datetime (no timezone)
        naive_time = datetime(2026, 1, 13, 10, 0, 0)
        
        # Should localize to IST
        result = market_hours.is_market_open(naive_time)
        
        assert result is True

