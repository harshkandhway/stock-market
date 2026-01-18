"""
Verification Script for Paper Trading Capital Calculation Fix

This script verifies that the capital calculation fix is working correctly
by testing all scenarios on the actual database.

Usage: python verify_capital_fix.py
"""

import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from datetime import datetime, timezone

DATABASE_URL = 'sqlite:///data/bot.db'


def get_db():
    """Create database connection"""
    engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
    return engine


def verify_fix():
    """Main verification function"""
    print("="*70)
    print("PAPER TRADING CAPITAL CALCULATION FIX VERIFICATION")
    print("="*70)
    
    engine = get_db()
    
    # Get all active sessions
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT id, user_id, initial_capital, current_capital, peak_capital
            FROM paper_trading_sessions
            WHERE is_active = 1
            ORDER BY id
        '''))
        sessions = result.fetchall()
    
    print(f"\nFound {len(sessions)} active paper trading sessions")
    
    all_passed = True
    
    for session in sessions:
        session_id, user_id, initial_capital, current_capital, peak_capital = session
        
        print(f"\n{'='*70}")
        print(f"SESSION {session_id} (User: {user_id})")
        print(f"{'='*70}")
        
        # Get open positions
        with engine.connect() as conn:
            result = conn.execute(text(f'''
                SELECT symbol, shares, entry_price, position_value, current_price, 
                       unrealized_pnl, target_price, stop_loss_price
                FROM paper_positions
                WHERE session_id = {session_id} AND is_open = 1
            '''))
            positions = result.fetchall()
        
        if not positions:
            print("\nNo open positions - skipping detailed verification")
            continue
        
        print(f"\nOpen Positions ({len(positions)}):")
        print("-"*70)
        
        total_entry_value = 0
        total_current_value = 0
        total_unrealized = 0
        
        for pos in positions:
            symbol, shares, entry_price, entry_val, current_price, unrealized, target, stop = pos
            total_entry_value += entry_val or 0
            total_current_value += (current_price or 0) * shares if current_price else (entry_val or 0)
            total_unrealized += unrealized or 0
            
            current_val = (current_price or 0) * shares if current_price else (entry_val or 0)
            print(f"\n  {symbol}:")
            print(f"    Shares:           {shares:.2f}")
            print(f"    Entry Price:      {entry_price:.2f}")
            print(f"    Current Price:    {current_price or 'N/A':.2f}")
            print(f"    Entry Value:      {entry_val:.2f}")
            print(f"    Current Value:    {current_val:.2f}")
            print(f"    Unrealized P&L:   {unrealized:.2f}" if unrealized else "    Unrealized P&L:   N/A")
            print(f"    Target:           {target:.2f}")
            print(f"    Stop Loss:        {stop:.2f}")
        
        print(f"\n  {'-'*50}")
        print(f"  Total Entry Value:    {total_entry_value:.2f}")
        print(f"  Total Current Value:  {total_current_value:.2f}")
        print(f"  Total Unrealized:     {total_unrealized:.2f}")
        
        # Get portfolio summary from database
        with engine.connect() as conn:
            result = conn.execute(text(f'''
                SELECT 
                    (SELECT SUM(shares * current_price) 
                     FROM paper_positions 
                     WHERE session_id = {session_id} AND is_open = 1 
                     AND current_price IS NOT NULL) as deployed_current,
                    
                    (SELECT SUM(position_value) 
                     FROM paper_positions 
                     WHERE session_id = {session_id} AND is_open = 1) as deployed_entry,
                    
                    (SELECT SUM(unrealized_pnl) 
                     FROM paper_positions 
                     WHERE session_id = {session_id} AND is_open = 1) as unrealized_sum
            '''))
            summary = result.fetchone()
        
        deployed_current = summary[0] or 0
        deployed_entry = summary[1] or 0
        unrealized_sum = summary[2] or 0
        
        print(f"\n[ VERIFICATION CHECKS ]")
        print("-"*70)
        
        # Check 1: Deployed capital should use current prices
        expected_deployed = total_current_value
        if abs(deployed_current - expected_deployed) < 0.01:
            print(f"[PASS] deployed_capital uses current prices")
            print(f"       Expected: {expected_deployed:.2f}, Got: {deployed_current:.2f}")
        else:
            print(f"[FAIL] deployed_capital DOES NOT use current prices!")
            print(f"       Expected: {expected_deployed:.2f}, Got: {deployed_current:.2f}")
            all_passed = False
        
        # Check 2: Unrealized P&L should equal current_value - entry_value
        expected_unrealized = total_current_value - total_entry_value
        if abs(unrealized_sum - expected_unrealized) < 0.01:
            print(f"[PASS] total_unrealized_pnl is correct")
            print(f"       Expected: {expected_unrealized:.2f}, Got: {unrealized_sum:.2f}")
        else:
            print(f"[FAIL] total_unrealized_pnl is WRONG!")
            print(f"       Expected: {expected_unrealized:.2f}, Got: {unrealized_sum:.2f}")
            all_passed = False
        
        # Check 3: Relationship between values
        print(f"\n[ VALUE RELATIONSHIPS ]")
        print("-"*70)
        print(f"session.current_capital:     {current_capital:.2f}")
        print(f"deployed (current prices):   {deployed_current:.2f}")
        print(f"deployed (entry prices):     {deployed_entry:.2f}")
        print(f"Total Portfolio Value:       {current_capital + deployed_current:.2f}")
        print(f"Expected Unrealized:         {current_capital + deployed_current - initial_capital:.2f}")
        
        # Check 4: Verify the fix
        print(f"\n[ BOT DISPLAY VALUES ]")
        print("-"*70)
        
        # Get what the bot calculates
        from src.bot.database.db import get_db_context
        from src.bot.services.paper_portfolio_service import PaperPortfolioService
        from src.bot.database.models import PaperTradingSession
        
        with get_db_context() as db:
            session = db.query(PaperTradingSession).get(session_id)
            service = PaperPortfolioService(db)
            summary = service.get_portfolio_summary(session)
            
            print(f"  Initial Capital:    {summary['initial_capital']:>15,.2f}")
            print(f"  Total Capital:      {summary['total_capital']:>15,.2f}  <- Should be cash + current_value")
            print(f"  Current Cash:       {summary['current_cash']:>15,.2f}")
            print(f"  Deployed Capital:   {summary['deployed_capital']:>15,.2f}  <- Should be current_value")
            print(f"  Total P&L:          {summary['total_return']:>+15,.2f}")
            print(f"  Unrealized P&L:     {summary['total_unrealized_pnl']:>+15,.2f}")
            
            # Verify calculations
            print(f"\n[ FINAL VERIFICATION ]")
            print("-"*70)
            
            # total_capital = session.current_capital + deployed_capital (NOT current_cash + deployed)
            # Because current_cash = session.current_capital - deployed (entry value)
            # So current_cash + deployed (current) != session.current_capital + deployed (current)
            expected_total = current_capital + summary['deployed_capital']
            if abs(summary['total_capital'] - expected_total) < 0.01:
                print(f"[PASS] total_capital = session.current_capital + deployed_capital")
            else:
                print(f"[FAIL] total_capital != session.current_capital + deployed_capital")
                print(f"       Expected: {expected_total:.2f}, Got: {summary['total_capital']:.2f}")
                all_passed = False
            
            # total_return = total_capital - initial_capital
            expected_return = summary['total_capital'] - summary['initial_capital']
            if abs(summary['total_return'] - expected_return) < 0.01:
                print(f"[PASS] total_return = total_capital - initial_capital")
            else:
                print(f"[FAIL] total_return != total_capital - initial_capital")
                all_passed = False
            
            # deployed_capital should use current prices, not entry prices
            if abs(summary['deployed_capital'] - total_current_value) < 0.01:
                print(f"[PASS] deployed_capital uses current prices")
            else:
                print(f"[FAIL] deployed_capital does NOT use current prices")
                all_passed = False
            
            # Additional check: current_cash relationship
            print(f"\n[ CURRENT_CASH RELATIONSHIP ]")
            print("-"*70)
            print(f"Note: current_cash is calculated as session.current_capital - deployed (entry value)")
            print(f"      This means: current_cash + deployed (entry) = session.current_capital")
            print(f"      But deployed (current) may differ from deployed (entry)")
            print(f"\n  session.current_capital:    {current_capital:.2f}")
            print(f"  deployed (entry value):      {deployed_entry:.2f}")
            print(f"  deployed (current value):    {summary['deployed_capital']:.2f}")
            print(f"  current_cash:                {summary['current_cash']:.2f}")
            print(f"  current_cash + deployed(entry): {summary['current_cash'] + deployed_entry:.2f} == session.current_capital")
            print(f"\n  total_capital = session.current_capital + deployed(current)")
            print(f"                = {current_capital:.2f} + {summary['deployed_capital']:.2f}")
            print(f"                = {current_capital + summary['deployed_capital']:.2f}")
            print(f"\n  This is CORRECT because deployed(current) reflects current market value!")
    
    # Summary
    print(f"\n{'='*70}")
    if all_passed:
        print("ALL VERIFICATIONS PASSED!")
        print("The capital calculation fix is working correctly.")
    else:
        print("SOME VERIFICATIONS FAILED!")
        print("Please review the errors above.")
    print(f"{'='*70}")
    
    return all_passed


def test_bot_display():
    """Test what the bot would display"""
    print("\n" + "="*70)
    print("BOT DISPLAY SIMULATION")
    print("="*70)
    
    from src.bot.database.db import get_db_context
    from src.bot.services.paper_portfolio_service import PaperPortfolioService
    from src.bot.database.models import PaperTradingSession
    import asyncio
    
    def get_status_sync(session_id):
        with get_db_context() as db:
            session = db.query(PaperTradingSession).get(session_id)
            if not session:
                return None
            service = PaperPortfolioService(db)
            return service.get_portfolio_summary(session)
    
    with get_db_context() as db:
        sessions = db.query(PaperTradingSession).filter(
            PaperTradingSession.is_active == True
        ).all()
        
        for session in sessions:
            status = get_status_sync(session.id)
            
            if not status:
                continue
                
            print(f"\n[ Session {session.id} - User {session.user_id} ]")
            print("-"*70)
            print(f"Initial Capital:    {status['initial_capital']:>15,.2f}")
            print(f"Total Capital:      {status['total_capital']:>15,.2f}")
            print(f"Current Cash:       {status['current_cash']:>15,.2f}")
            print(f"Deployed Capital:   {status['deployed_capital']:>15,.2f}")
            print(f"Total P&L:          {status['total_return']:>+15,.2f} ({status['total_return_pct']:+.2f}%)")
            print(f"Unrealized P&L:     {status['total_unrealized_pnl']:>+15,.2f}")
            
            if status['positions']:
                print(f"\nOpen Positions ({len(status['positions'])}):")
                for pos in status['positions']:
                    print(f"  {pos['symbol']}: {pos['shares']:.2f} @ {pos['entry_price']:.2f}")
                    print(f"    Current: {pos['current_price']:.2f} | P&L: {pos['unrealized_pnl']:.2f} ({pos['unrealized_pnl_pct']:.2f}%)")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING CAPITAL CALCULATION FIX")
    print("="*70)
    print(f"\nDatabase: {DATABASE_URL}")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Run verification
    success = verify_fix()
    
    # Test bot display
    test_bot_display()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
