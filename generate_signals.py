#!/usr/bin/env python3
"""
Generate Daily BUY Signals for Paper Trading
Analyzes 30 top Indian stocks and saves BUY signals to database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.bot.services.analysis_service import analyze_stock
from src.bot.database.db import get_db_context
from src.bot.database.models import DailyBuySignal
from datetime import datetime
import json

# Top 30 Indian blue-chip stocks (high liquidity, reliable data)
TOP_30_STOCKS = [
    # Banking & Financial Services
    'HDFCBANK.NS', 'ICICIBANK.NS', 'AXISBANK.NS', 'KOTAKBANK.NS', 'SBIN.NS',

    # IT Services
    'TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS',

    # Energy & Oil
    'RELIANCE.NS', 'ONGC.NS', 'BPCL.NS', 'IOC.NS',

    # Automobiles
    'MARUTI.NS', 'TATAMOTORS.NS', 'M&M.NS', 'BAJAJ-AUTO.NS',

    # FMCG & Consumer
    'HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'BRITANNIA.NS',

    # Pharma
    'SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS',

    # Metals & Mining
    'TATASTEEL.NS', 'HINDALCO.NS', 'COALINDIA.NS',

    # Telecom & Infrastructure
    'BHARTIARTL.NS', 'LT.NS'
]

def main():
    print('='*70)
    print('GENERATING DAILY BUY SIGNALS FOR PAPER TRADING')
    print('='*70)
    print(f'\n📊 Analyzing {len(TOP_30_STOCKS)} stocks...\n')

    buy_signals = []
    errors = []
    blocked_signals = []

    with get_db_context() as db:
        # Clear today's old signals first
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        old_signals = db.query(DailyBuySignal).filter(
            DailyBuySignal.analysis_date >= today
        ).delete()
        db.commit()

        if old_signals > 0:
            print(f'🗑️  Cleared {old_signals} old signals from today\n')

        for i, symbol in enumerate(TOP_30_STOCKS, 1):
            try:
                print(f'[{i:2d}/{len(TOP_30_STOCKS)}] Analyzing {symbol:15s}... ', end='', flush=True)

                # Analyze with balanced mode and medium timeframe
                result = analyze_stock(symbol, mode='balanced', timeframe='medium', use_cache=False)

                rec_type = result['recommendation_type']
                rec = result['recommendation']
                confidence = result['confidence']

                # Check if it's a BUY signal (STRONG BUY, BUY, or WEAK BUY)
                if rec_type in ['STRONG BUY', 'BUY', 'WEAK BUY']:
                    # Check if BLOCKED
                    if 'BLOCKED' in rec or 'AVOID' in rec.upper():
                        print(f'⛔ {rec_type} but BLOCKED - {rec[:40]}...')
                        blocked_signals.append({
                            'symbol': symbol,
                            'type': rec_type,
                            'reason': rec
                        })
                    else:
                        # Save BUY signal
                        # Get target and stop loss
                        target_data = result.get('target_data', {})
                        stop_data = result.get('stop_data', {})
                        
                        signal = DailyBuySignal(
                            symbol=symbol,
                            analysis_date=datetime.utcnow(),
                            recommendation=rec,
                            recommendation_type=rec_type,
                            current_price=result.get('current_price', 0.0),
                            target=target_data.get('recommended_target') if target_data else None,
                            stop_loss=stop_data.get('recommended_stop') if stop_data else None,
                            risk_reward=result.get('risk_reward', 0.0),
                            confidence=confidence,
                            overall_score_pct=result.get('overall_score_pct', 50.0),
                            analysis_data=json.dumps({
                                'mode': result.get('mode', 'balanced'),
                                'timeframe': result.get('timeframe', 'medium'),
                                'indicators': result.get('indicators', {}),
                                'safety_score': result.get('safety_score', {})
                            }, default=str)
                        )
                        db.add(signal)
                        db.flush()  # Flush to get the ID
                        db.refresh(signal)  # Refresh to load all attributes
                        
                        # Store signal data for sorting
                        buy_signals.append({
                            'signal': signal,
                            'confidence': confidence,
                            'symbol': symbol,
                            'type': rec_type,
                            'price': result.get('current_price', 0.0),
                            'target': target_data.get('recommended_target') if target_data else None,
                            'stop': stop_data.get('recommended_stop') if stop_data else None,
                            'rr': result.get('risk_reward', 0.0)
                        })

                        print(f'✅ {rec_type} - ₹{result.get("current_price", 0):.2f} - Conf: {confidence:.0f}%')
                else:
                    print(f'⚪ {rec_type} - Skipped')

            except Exception as e:
                print(f'❌ ERROR: {str(e)[:50]}')
                errors.append({'symbol': symbol, 'error': str(e)})

        # Commit all signals
        db.commit()

    # Summary
    print('\n' + '='*70)
    print('SIGNAL GENERATION SUMMARY')
    print('='*70)
    print(f'\n✅ BUY Signals Generated: {len(buy_signals)}')
    print(f'⛔ BLOCKED Signals: {len(blocked_signals)}')
    print(f'❌ Errors: {len(errors)}')

    if buy_signals:
        print(f'\n{"="*70}')
        print('BUY SIGNALS DETAILS:')
        print('='*70)
        print(f'{"#":<4} {"Symbol":<15} {"Type":<12} {"Price":<10} {"Target":<10} {"Stop":<10} {"R:R":<6} {"Conf%"}')
        print('-'*70)

        # Sort by confidence descending (using stored data, not SQLAlchemy objects)
        buy_signals.sort(key=lambda x: x['confidence'], reverse=True)

        for i, signal_data in enumerate(buy_signals, 1):
            signal = signal_data['signal']
            print(f'{i:<4} {signal_data["symbol"]:<15} {signal_data["type"]:<12} '
                  f'₹{signal_data["price"]:<9.2f} ₹{signal_data["target"] or 0:<9.2f} '
                  f'₹{signal_data["stop"] or 0:<9.2f} {signal_data["rr"]:<6.2f} {signal_data["confidence"]:.0f}%')

    if blocked_signals:
        print(f'\n{"="*70}')
        print('BLOCKED SIGNALS (Not saved to DB):')
        print('='*70)
        for blocked in blocked_signals:
            print(f'⛔ {blocked["symbol"]:15s} - {blocked["type"]:12s} - {blocked["reason"][:50]}...')

    if errors:
        print(f'\n{"="*70}')
        print('ERRORS:')
        print('='*70)
        for err in errors:
            print(f'❌ {err["symbol"]:15s} - {err["error"][:50]}')

    print('\n' + '='*70)
    print(f'✅ Process complete! {len(buy_signals)} signals ready for paper trading.')
    print('='*70)

    # Return count of actual signal objects
    return len([s['signal'] for s in buy_signals])

if __name__ == '__main__':
    try:
        count = main()
        sys.exit(0 if count > 0 else 1)
    except KeyboardInterrupt:
        print('\n\n⚠️  Process interrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'\n\n❌ Fatal error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
