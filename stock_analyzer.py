#!/usr/bin/env python3
"""
Main entry point for Stock Analyzer Pro
This script provides easy access to the stock analyzer from the project root.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the main CLI script
from src.cli.stock_analyzer_pro import main

if __name__ == '__main__':
    main()

