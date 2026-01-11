# Telegram Bot Setup Guide

This guide will help you set up the Stock Analyzer Pro Telegram Bot.

## Prerequisites

- Python 3.9 or higher
- Telegram account
- Internet connection

## Step 1: Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` to BotFather
3. Follow the prompts:
   - Choose a name for your bot (e.g., "Stock Analyzer Pro")
   - Choose a username (must end in 'bot', e.g., "stock_analyzer_pro_bot")
4. BotFather will provide you with an API token
5. **Save this token** - you'll need it in Step 3

Example:
```
Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
```

## Step 2: Get Your Telegram User ID

1. Search for `@userinfobot` on Telegram
2. Send `/start` to the bot
3. The bot will reply with your user ID
4. **Save your user ID** - you'll need it in Step 3

Example response:
```
Id: 123456789
First name: John
...
```

## Step 3: Configure Environment Variables

1. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` in a text editor and update these values:
   ```env
   # Replace with your bot token from Step 1
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
   
   # Replace with your user ID from Step 2
   TELEGRAM_ADMIN_IDS=123456789
   ```

3. (Optional) Adjust other settings as needed:
   - `MAX_REQUESTS_PER_HOUR` - Rate limiting
   - `ALERT_CHECK_INTERVAL` - How often to check alerts (in seconds)
   - `LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR)
   - `DEFAULT_TIMEZONE` - Your timezone

## Step 4: Install Dependencies

Install the bot-specific dependencies:

```bash
pip install -r requirements_bot.txt
```

This will install:
- python-telegram-bot - Telegram bot framework
- SQLAlchemy - Database ORM
- python-dotenv - Environment variable management
- APScheduler - Task scheduling
- matplotlib, mplfinance - Chart generation
- And other dependencies

## Step 5: Initialize Database

The bot uses SQLite to store user data, watchlists, alerts, and portfolios.

Initialize the database:

```bash
python -c "from src.bot.database.db import init_db; init_db()"
```

You should see:
```
✅ Database initialized successfully!
```

The database file will be created at `data/bot.db`.

## Step 6: Test Configuration

Test that everything is configured correctly:

```bash
python src/bot/config.py
```

You should see your configuration summary and:
```
✅ Configuration is valid!
```

Test database connection:

```bash
python src/bot/database/db.py
```

You should see database information and statistics.

## Step 7: Run the Bot

Start the bot:

```bash
python bot_runner.py
```

You should see:
```
✅ Bot started successfully!
Bot username: @your_bot_username
Press Ctrl+C to stop
```

## Step 8: Test the Bot

1. Open Telegram
2. Search for your bot by username (e.g., @stock_analyzer_pro_bot)
3. Send `/start`
4. You should receive a welcome message
5. Try `/analyze RELIANCE.NS` to test stock analysis

## Common Issues & Troubleshooting

### Issue: "Invalid bot token"

**Solution:**
- Check that you copied the full token from BotFather
- Ensure there are no extra spaces in `.env`
- The token should be in format: `NUMBER:ALPHANUMERIC`

### Issue: "You are not authorized to use this bot"

**Solution:**
- Check that your Telegram user ID is in `TELEGRAM_ADMIN_IDS`
- Get your ID again from @userinfobot
- Make sure there are no spaces in the ID

### Issue: "Module not found"

**Solution:**
```bash
# Make sure you're in the project root directory
cd /path/to/stock-market

# Reinstall dependencies
pip install -r requirements_bot.txt
```

### Issue: "Database error"

**Solution:**
```bash
# Reset database (WARNING: This deletes all data!)
python -c "from src.bot.database.db import reset_db; reset_db()"
```

### Issue: "Rate limit exceeded"

**Solution:**
- Wait a few minutes
- Adjust `MAX_REQUESTS_PER_HOUR` in `.env`
- Restart the bot after changing `.env`

## Next Steps

Once the bot is running:

1. **Try different commands:**
   - `/help` - See all available commands
   - `/analyze [SYMBOL]` - Analyze a stock
   - `/watchlist` - Manage your watchlist
   - `/settings` - Configure your preferences

2. **Set up alerts:**
   - `/alert price RELIANCE.NS 2500` - Get notified when price crosses 2500
   - `/alert signal TCS.NS` - Get notified on signal changes

3. **Track your portfolio:**
   - `/portfolio add TCS.NS 10 3500` - Add 10 shares bought at 3500
   - `/portfolio` - View your portfolio performance

4. **Schedule reports:**
   - `/schedule daily 09:00` - Get daily reports at 9 AM
   - `/schedule weekly Monday 09:00` - Weekly reports on Mondays

## Bot Configuration Options

### Risk Modes

Set your risk tolerance:
- `/setmode conservative` - 0.5% risk per trade, minimum 3:1 R:R
- `/setmode balanced` - 1% risk per trade, minimum 2:1 R:R (default)
- `/setmode aggressive` - 2% risk per trade, minimum 1.5:1 R:R

### Timeframes

Choose analysis timeframe:
- `/settimeframe short` - 1-4 week swing trades
- `/settimeframe medium` - 1-3 month position trades (default)

### Capital

Set default capital for position sizing:
```
/setcapital 100000
```

## Advanced Features

### Multi-Stock Comparison

Compare up to 5 stocks:
```
/compare TCS.NS INFY.NS WIPRO.NS
```

### Backtesting

Test strategy on historical data:
```
/backtest TCS.NS 90
```

This tests the last 90 days.

### Stock Search

Search for ticker symbols:
```
/search reliance
```

## Bot Maintenance

### View Database Stats

```bash
python src/bot/database/db.py
```

### Clean Old Data

```python
from src.bot.database.db import get_db_context, cleanup_old_activity

with get_db_context() as db:
    deleted = cleanup_old_activity(db, days=30)
    print(f"Deleted {deleted} old activity logs")
```

### Backup Database

```bash
cp data/bot.db data/bot_backup_$(date +%Y%m%d).db
```

### Stop the Bot

Press `Ctrl+C` in the terminal where the bot is running.

## Security Best Practices

1. **Never share your bot token** - It's like a password
2. **Keep `.env` file private** - Don't commit it to git
3. **Use admin-only mode** - Set `TELEGRAM_ADMIN_IDS` to restrict access
4. **Regular backups** - Backup `data/bot.db` regularly
5. **Update dependencies** - Keep packages up-to-date for security patches

## Support

If you encounter issues:

1. Check the logs in `logs/bot.log`
2. Review this guide carefully
3. Check the project documentation in `docs/`
4. Ensure all dependencies are installed correctly

## Deployment (Optional)

For 24/7 availability, consider:

1. **Linux Server / VPS:**
   ```bash
   # Use screen or tmux
   screen -S stock_bot
   python bot_runner.py
   # Press Ctrl+A, then D to detach
   ```

2. **systemd service:**
   Create `/etc/systemd/system/stock-bot.service`

3. **Docker:**
   Create a Dockerfile (not included in this setup)

4. **Cloud services:**
   - AWS EC2
   - DigitalOcean Droplet
   - Google Cloud Compute Engine

---

**Congratulations!** 🎉 Your Stock Analyzer Pro Bot is now set up and ready to use!
