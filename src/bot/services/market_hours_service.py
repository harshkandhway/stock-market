"""
Market Hours Service
Determines if NSE/BSE is open for trading
Handles market hours, weekends, and holidays

Author: Harsh Kandhway
"""

import logging
from datetime import datetime, time, timedelta
from typing import Optional
import pytz

logger = logging.getLogger(__name__)


class MarketHoursService:
    """Service to check NSE/BSE market hours and holidays"""

    # Market timing (IST)
    MARKET_OPEN = time(9, 15)   # 9:15 AM IST
    MARKET_CLOSE = time(15, 30)  # 3:30 PM IST
    TIMEZONE = pytz.timezone('Asia/Kolkata')

    # NSE/BSE Holidays for 2026 (major holidays)
    # Format: (month, day) tuples
    HOLIDAYS_2026 = [
        (1, 26),   # Republic Day
        (3, 14),   # Holi
        (4, 6),    # Mahavir Jayanti
        (4, 10),   # Good Friday
        (4, 14),   # Dr. Ambedkar Jayanti
        (5, 1),    # Maharashtra Day
        (8, 15),   # Independence Day
        (10, 2),   # Gandhi Jayanti / Dussehra
        (10, 20),  # Diwali - Lakshmi Pujan
        (10, 21),  # Diwali - Balipratipada
        (11, 5),   # Guru Nanak Jayanti
        (12, 25),  # Christmas
    ]

    # Islamic holidays (approximate dates for 2026 - vary by moon sighting)
    ISLAMIC_HOLIDAYS_2026 = [
        (4, 4),    # Eid al-Fitr (Ramadan)
        (6, 16),   # Eid ul-Adha (Bakri Eid)
        (8, 22),   # Ganesh Chaturthi
    ]

    def __init__(self):
        """Initialize market hours service"""
        self.all_holidays_2026 = set(self.HOLIDAYS_2026 + self.ISLAMIC_HOLIDAYS_2026)
        logger.info("MarketHoursService initialized with %d holidays", len(self.all_holidays_2026))

    def is_market_open(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if market is currently open

        Args:
            check_time: Time to check (defaults to now)

        Returns:
            True if market is open, False otherwise
        """
        if check_time is None:
            check_time = datetime.now(self.TIMEZONE)
        elif check_time.tzinfo is None:
            # Convert naive datetime to IST
            check_time = self.TIMEZONE.localize(check_time)
        else:
            # Convert to IST if different timezone
            check_time = check_time.astimezone(self.TIMEZONE)

        logger.info(f"Market hours check: input_time={check_time}, weekday={check_time.weekday()}, time={check_time.strftime('%H:%M:%S IST')}")

        # Check if weekend (Saturday=5, Sunday=6)
        if check_time.weekday() >= 5:
            logger.info("Market closed: Weekend (%s)", check_time.strftime('%A'))
            return False

        # Check if holiday
        if self._is_holiday(check_time.date()):
            logger.info("Market closed: Holiday (%s)", check_time.date())
            return False

        # Check market hours
        current_time = check_time.time()
        is_open = self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE

        if is_open:
            logger.info("Market is OPEN at %s (between %s and %s)", check_time.strftime('%H:%M:%S'), self.MARKET_OPEN.strftime('%H:%M'), self.MARKET_CLOSE.strftime('%H:%M'))
        else:
            logger.info("Market closed: Outside trading hours (%s, market hours: %s-%s)", check_time.strftime('%H:%M:%S'), self.MARKET_OPEN.strftime('%H:%M'), self.MARKET_CLOSE.strftime('%H:%M'))

        return is_open

    def _is_holiday(self, check_date: datetime.date) -> bool:
        """
        Check if given date is a market holiday

        Args:
            check_date: Date to check

        Returns:
            True if holiday, False otherwise
        """
        # Only check holidays for 2026 (extend this for future years)
        if check_date.year == 2026:
            return (check_date.month, check_date.day) in self.all_holidays_2026

        # For other years, return False (extend holiday calendar as needed)
        logger.warning("Holiday calendar not available for year %d", check_date.year)
        return False

    def get_next_market_open(self, from_time: Optional[datetime] = None) -> datetime:
        """
        Calculate next market open time

        Args:
            from_time: Starting time (defaults to now)

        Returns:
            Datetime of next market open
        """
        if from_time is None:
            from_time = datetime.now(self.TIMEZONE)
        elif from_time.tzinfo is None:
            from_time = self.TIMEZONE.localize(from_time)
        else:
            from_time = from_time.astimezone(self.TIMEZONE)

        # Start checking from current time
        check_time = from_time

        # If currently during market hours, return next day's open
        if self.is_market_open(check_time):
            check_time = check_time.replace(
                hour=self.MARKET_CLOSE.hour,
                minute=self.MARKET_CLOSE.minute,
                second=0,
                microsecond=0
            ) + timedelta(minutes=1)  # Move past market close

        # Find next valid trading day
        max_iterations = 30  # Prevent infinite loop (check up to 30 days)
        for _ in range(max_iterations):
            # Set to market open time
            next_open = check_time.replace(
                hour=self.MARKET_OPEN.hour,
                minute=self.MARKET_OPEN.minute,
                second=0,
                microsecond=0
            )

            # If we've passed market open time today, try tomorrow
            if check_time.time() > self.MARKET_OPEN:
                next_open += timedelta(days=1)

            # Check if this is a valid trading day
            if next_open.weekday() < 5 and not self._is_holiday(next_open.date()):
                logger.info("Next market open: %s", next_open.strftime('%Y-%m-%d %H:%M %Z'))
                return next_open

            # Move to next day
            check_time = next_open + timedelta(days=1)

        # Fallback (should never reach here)
        logger.error("Could not find next market open within 30 days")
        return check_time

    def get_next_market_close(self, from_time: Optional[datetime] = None) -> datetime:
        """
        Calculate next market close time

        Args:
            from_time: Starting time (defaults to now)

        Returns:
            Datetime of next market close
        """
        if from_time is None:
            from_time = datetime.now(self.TIMEZONE)
        elif from_time.tzinfo is None:
            from_time = self.TIMEZONE.localize(from_time)
        else:
            from_time = from_time.astimezone(self.TIMEZONE)

        # If market is currently open, return today's close
        if self.is_market_open(from_time):
            next_close = from_time.replace(
                hour=self.MARKET_CLOSE.hour,
                minute=self.MARKET_CLOSE.minute,
                second=0,
                microsecond=0
            )
            logger.info("Next market close: %s", next_close.strftime('%Y-%m-%d %H:%M %Z'))
            return next_close

        # Otherwise, get next market open and return its close
        next_open = self.get_next_market_open(from_time)
        next_close = next_open.replace(
            hour=self.MARKET_CLOSE.hour,
            minute=self.MARKET_CLOSE.minute
        )
        logger.info("Next market close: %s", next_close.strftime('%Y-%m-%d %H:%M %Z'))
        return next_close

    def seconds_until_market_open(self, from_time: Optional[datetime] = None) -> int:
        """
        Calculate seconds until next market open

        Args:
            from_time: Starting time (defaults to now)

        Returns:
            Number of seconds until next market open
        """
        if from_time is None:
            from_time = datetime.now(self.TIMEZONE)
        elif from_time.tzinfo is None:
            from_time = self.TIMEZONE.localize(from_time)
        else:
            from_time = from_time.astimezone(self.TIMEZONE)

        next_open = self.get_next_market_open(from_time)
        seconds = int((next_open - from_time).total_seconds())

        logger.debug("Seconds until market open: %d (%.1f hours)", seconds, seconds / 3600)
        return max(0, seconds)

    def seconds_until_market_close(self, from_time: Optional[datetime] = None) -> int:
        """
        Calculate seconds until next market close

        Args:
            from_time: Starting time (defaults to now)

        Returns:
            Number of seconds until next market close
        """
        if from_time is None:
            from_time = datetime.now(self.TIMEZONE)
        elif from_time.tzinfo is None:
            from_time = self.TIMEZONE.localize(from_time)
        else:
            from_time = from_time.astimezone(self.TIMEZONE)

        next_close = self.get_next_market_close(from_time)
        seconds = int((next_close - from_time).total_seconds())

        logger.debug("Seconds until market close: %d (%.1f hours)", seconds, seconds / 3600)
        return max(0, seconds)

    def is_market_day(self, check_date: Optional[datetime.date] = None) -> bool:
        """
        Check if given date is a trading day (not weekend or holiday)

        Args:
            check_date: Date to check (defaults to today)

        Returns:
            True if trading day, False otherwise
        """
        if check_date is None:
            check_date = datetime.now(self.TIMEZONE).date()

        # Check weekend
        if check_date.weekday() >= 5:
            return False

        # Check holiday
        return not self._is_holiday(check_date)

    def get_market_status_summary(self) -> dict:
        """
        Get comprehensive market status information

        Returns:
            Dictionary with market status details
        """
        now = datetime.now(self.TIMEZONE)
        is_open = self.is_market_open(now)

        status = {
            'is_open': is_open,
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'market_open_time': f"{self.MARKET_OPEN.strftime('%H:%M')} IST",
            'market_close_time': f"{self.MARKET_CLOSE.strftime('%H:%M')} IST",
        }

        if is_open:
            status['next_close'] = self.get_next_market_close(now).strftime('%Y-%m-%d %H:%M %Z')
            status['seconds_until_close'] = self.seconds_until_market_close(now)
        else:
            status['next_open'] = self.get_next_market_open(now).strftime('%Y-%m-%d %H:%M %Z')
            status['seconds_until_open'] = self.seconds_until_market_open(now)

        status['is_trading_day'] = self.is_market_day(now.date())
        status['day_of_week'] = now.strftime('%A')

        return status


# Singleton instance
_market_hours_service = None


def get_market_hours_service() -> MarketHoursService:
    """
    Get singleton instance of MarketHoursService

    Returns:
        MarketHoursService instance
    """
    global _market_hours_service
    if _market_hours_service is None:
        _market_hours_service = MarketHoursService()
    return _market_hours_service
