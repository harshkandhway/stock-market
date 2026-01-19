#!/bin/bash
# Comprehensive Bot Killer Script
# Finds and kills ALL bot instances everywhere

echo "🔍 Searching for ALL bot instances..."
echo ""

# 1. Find Python processes
echo "1️⃣ Python processes running bot code:"
ps aux | grep -E "python.*bot|bot_runner" | grep -v grep || echo "   None found"
echo ""

# 2. Find processes using the bot token (in environment)
echo "2️⃣ Processes with Telegram bot environment:"
lsof -i :8443 2>/dev/null || echo "   None on port 8443"
echo ""

# 3. Check for any Python processes
echo "3️⃣ All Python3 processes:"
ps aux | grep python3 | grep -v grep | awk '{print $2" "$11" "$12" "$13" "$14}' || echo "   None found"
echo ""

# 4. Find processes in current directory
echo "4️⃣ Processes in $(pwd):"
lsof +D "$(pwd)" 2>/dev/null | grep python || echo "   None found"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔪 KILLING ALL FOUND PROCESSES..."
echo ""

# Kill by pattern
pkill -9 -f "bot_runner" 2>/dev/null && echo "✅ Killed bot_runner processes" || echo "ℹ️  No bot_runner processes"
pkill -9 -f "src.bot.bot" 2>/dev/null && echo "✅ Killed src.bot.bot processes" || echo "ℹ️  No src.bot.bot processes"

# Kill all python3 (nuclear option - use with caution!)
# Uncomment if needed:
# killall -9 python3 2>/dev/null && echo "✅ Killed all python3" || echo "ℹ️  No python3 processes"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ VERIFICATION - Remaining processes:"
ps aux | grep -E "python.*bot|bot_runner" | grep -v grep || echo "🎉 No bot processes running!"
echo ""
echo "📝 NEXT STEPS:"
echo "   1. Close any IDE terminal tabs showing bot output"
echo "   2. Wait 10 seconds for Telegram API to reset"
echo "   3. Start fresh: python3 bot_runner.py"
