#!/usr/bin/env python3
"""
Stock Analyzer Pro - Main Entry Point
======================================

This is the main entry point for Stock Analyzer Pro (Professional Technical Analysis Tool).
Runs the professional analyzer with all advanced features.

Usage:
    python stock_analyzer_pro.py RELIANCE.NS
    python stock_analyzer_pro.py TCS.NS INFY.NS --mode balanced --capital 100000

Author: Harsh Kandhway
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

