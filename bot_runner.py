#!/usr/bin/env python3
"""
Bot Runner - Entry Point for Stock Analyzer Pro Telegram Bot
Run this script to start the bot

Author: Harsh Kandhway
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.dirname(__file__))

from src.bot.bot import run_bot

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         Stock Analyzer Pro - Telegram Bot                   ║
║                                                              ║
║  Professional Stock Technical Analysis via Telegram         ║
║                                                              ║
║              Developed by Harsh Kandhway                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

Starting bot...
""")
    
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n\n✅ Bot stopped gracefully. Goodbye!")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        print("\nPlease check:")
        print("  1. Your .env file is configured correctly")
        print("  2. All dependencies are installed (pip install -r requirements_bot.txt)")
        print("  3. Your bot token is valid")
        print("\nFor help, see docs/BOT_SETUP.md")
        sys.exit(1)
