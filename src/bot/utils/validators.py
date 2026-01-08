"""
Input Validators for Telegram Bot
Validates user inputs and command arguments
"""

import re
from typing import Tuple, Optional


def validate_stock_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Validate stock symbol format
    
    Args:
        symbol: Stock symbol to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not symbol:
        return False, "Symbol cannot be empty"
    
    # Remove whitespace and convert to uppercase
    symbol = symbol.strip().upper()
    
    # Check length (typical symbols are 1-10 characters)
    if len(symbol) < 1 or len(symbol) > 15:
        return False, "Symbol must be between 1 and 15 characters"
    
    # Check for valid characters (alphanumeric, dots, hyphens)
    if not re.match(r'^[A-Z0-9.\-]+$', symbol):
        return False, "Symbol contains invalid characters"
    
    # Check for common suffixes
    valid_suffixes = ['.NS', '.BO', '']
    has_valid_suffix = any(symbol.endswith(suffix) for suffix in valid_suffixes)
    
    # If it has a dot but not a valid suffix, warn
    if '.' in symbol and not has_valid_suffix:
        return True, f"Warning: Unusual suffix in '{symbol}'. Common: .NS (NSE), .BO (BSE)"
    
    return True, None


def validate_price(price: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate price input
    
    Args:
        price: Price string to validate
    
    Returns:
        Tuple of (is_valid, parsed_price, error_message)
    """
    if not price:
        return False, None, "Price cannot be empty"
    
    # Remove currency symbols and commas
    price = price.replace('₹', '').replace('$', '').replace(',', '').strip()
    
    try:
        parsed_price = float(price)
        
        if parsed_price <= 0:
            return False, None, "Price must be greater than 0"
        
        if parsed_price > 1000000000:  # 1 billion
            return False, None, "Price seems unreasonably high"
        
        return True, parsed_price, None
        
    except ValueError:
        return False, None, f"Invalid price format: '{price}'"


def validate_shares(shares: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate shares/quantity input
    
    Args:
        shares: Shares string to validate
    
    Returns:
        Tuple of (is_valid, parsed_shares, error_message)
    """
    if not shares:
        return False, None, "Shares cannot be empty"
    
    # Remove commas
    shares = shares.replace(',', '').strip()
    
    try:
        parsed_shares = float(shares)
        
        if parsed_shares <= 0:
            return False, None, "Shares must be greater than 0"
        
        if parsed_shares > 1000000000:  # 1 billion shares
            return False, None, "Shares seems unreasonably high"
        
        return True, parsed_shares, None
        
    except ValueError:
        return False, None, f"Invalid shares format: '{shares}'"


def validate_capital(capital: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate capital/amount input
    
    Args:
        capital: Capital string to validate
    
    Returns:
        Tuple of (is_valid, parsed_capital, error_message)
    """
    if not capital:
        return False, None, "Capital cannot be empty"
    
    # Remove currency symbols and commas
    capital = capital.replace('₹', '').replace('$', '').replace(',', '').strip()
    
    try:
        parsed_capital = float(capital)
        
        if parsed_capital <= 0:
            return False, None, "Capital must be greater than 0"
        
        if parsed_capital < 1000:
            return True, parsed_capital, "Warning: Capital is very low (< ₹1,000)"
        
        if parsed_capital > 10000000000:  # 10 billion
            return False, None, "Capital seems unreasonably high"
        
        return True, parsed_capital, None
        
    except ValueError:
        return False, None, f"Invalid capital format: '{capital}'"


def validate_mode(mode: str) -> Tuple[bool, Optional[str]]:
    """
    Validate risk mode input
    
    Args:
        mode: Mode string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    mode = mode.strip().lower()
    
    valid_modes = ['conservative', 'balanced', 'aggressive']
    
    if mode not in valid_modes:
        return False, f"Invalid mode. Must be one of: {', '.join(valid_modes)}"
    
    return True, None


def validate_timeframe(timeframe: str) -> Tuple[bool, Optional[str]]:
    """
    Validate timeframe input
    
    Args:
        timeframe: Timeframe string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    timeframe = timeframe.strip().lower()
    
    valid_timeframes = ['short', 'medium']
    
    if timeframe not in valid_timeframes:
        return False, f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
    
    return True, None


def validate_time(time_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate time format (HH:MM)
    
    Args:
        time_str: Time string to validate
    
    Returns:
        Tuple of (is_valid, parsed_time, error_message)
    """
    if not time_str:
        return False, None, "Time cannot be empty"
    
    # Match HH:MM format
    match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    
    if not match:
        return False, None, "Time must be in HH:MM format (e.g., 09:00)"
    
    hours, minutes = int(match.group(1)), int(match.group(2))
    
    if hours < 0 or hours > 23:
        return False, None, "Hours must be between 0 and 23"
    
    if minutes < 0 or minutes > 59:
        return False, None, "Minutes must be between 0 and 59"
    
    # Format with leading zeros
    formatted_time = f"{hours:02d}:{minutes:02d}"
    
    return True, formatted_time, None


def validate_days(days_str: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate days input for backtesting
    
    Args:
        days_str: Days string to validate
    
    Returns:
        Tuple of (is_valid, parsed_days, error_message)
    """
    if not days_str:
        return False, None, "Days cannot be empty"
    
    try:
        days = int(days_str)
        
        if days <= 0:
            return False, None, "Days must be greater than 0"
        
        if days > 365:
            return False, None, "Days cannot exceed 365 (1 year)"
        
        if days < 7:
            return True, days, "Warning: Less than 7 days may not provide reliable results"
        
        return True, days, None
        
    except ValueError:
        return False, None, f"Invalid days format: '{days_str}'"


def validate_rsi_threshold(threshold_str: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate RSI threshold (0-100)
    
    Args:
        threshold_str: Threshold string to validate
    
    Returns:
        Tuple of (is_valid, parsed_threshold, error_message)
    """
    try:
        threshold = float(threshold_str)
        
        if threshold < 0 or threshold > 100:
            return False, None, "RSI threshold must be between 0 and 100"
        
        return True, threshold, None
        
    except ValueError:
        return False, None, f"Invalid RSI threshold: '{threshold_str}'"


def parse_command_args(text: str, command: str) -> list:
    """
    Parse command arguments from message text
    
    Args:
        text: Full message text
        command: Command name (without /)
    
    Returns:
        List of arguments
    """
    # Remove command from text
    text = text.replace(f'/{command}', '', 1).strip()
    
    # Split by whitespace
    args = text.split()
    
    return args


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input to prevent injection attacks
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Limit length
    text = text[:max_length]
    
    # Remove control characters except newline and tab
    text = ''.join(char for char in text if char.isprintable() or char in ['\n', '\t'])
    
    return text.strip()


def validate_telegram_id(telegram_id: int, allowed_ids: list) -> bool:
    """
    Validate that Telegram ID is in allowed list (for admin-only mode)
    
    Args:
        telegram_id: Telegram user ID
        allowed_ids: List of allowed IDs
    
    Returns:
        True if allowed, False otherwise
    """
    if not allowed_ids:
        # If no allowed IDs configured, allow everyone
        return True
    
    return telegram_id in allowed_ids
