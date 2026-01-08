#!/usr/bin/env python3
"""
Main entry point for fetching stock tickers
This script provides easy access to the ticker fetcher from the project root.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main function
from src.data.fetch_stock_tickers import main

if __name__ == '__main__':
    main()

