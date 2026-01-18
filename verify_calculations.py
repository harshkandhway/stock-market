"""
Script to verify position sizing calculations and other formulas.
Useful for debugging and validating calculation accuracy.
"""

from risk_management import calculate_position_size, validate_risk_reward
from config import RISK_MODES

def verify_position_sizing():
    """Verify position sizing calculations"""
    print("=" * 60)
    print("POSITION SIZING CALCULATION VERIFICATION")
    print("=" * 60)
    
    test_cases = [
        {
            'capital': 200000,
            'entry': 200,
            'stop': 190,
            'mode': 'aggressive',
            'description': 'Aggressive mode: 2% risk, 10 point stop'
        },
        {
            'capital': 100000,
            'entry': 100,
            'stop': 95,
            'mode': 'balanced',
            'description': 'Balanced mode: 1% risk, 5 point stop'
        },
        {
            'capital': 50000,
            'entry': 50,
            'stop': 48,
            'mode': 'conservative',
            'description': 'Conservative mode: 0.5% risk, 2 point stop'
        }
    ]
    
    for case in test_cases:
        print(f"\n{case['description']}")
        print("-" * 60)
        
        risk_pct = RISK_MODES[case['mode']]['risk_per_trade']
        risk_amount = case['capital'] * risk_pct
        stop_dist = abs(case['entry'] - case['stop'])
        expected_shares = int(risk_amount / stop_dist)
        expected_pos_val = expected_shares * case['entry']
        
        print(f"Capital: {case['capital']:,}")
        print(f"Entry: {case['entry']}")
        print(f"Stop: {case['stop']}")
        print(f"Mode: {case['mode']} ({risk_pct*100}% risk)")
        print()
        print("Expected Calculation:")
        print(f"  Risk Amount: {case['capital']:,} × {risk_pct} = {risk_amount:,.2f}")
        print(f"  Stop Distance: |{case['entry']} - {case['stop']}| = {stop_dist}")
        print(f"  Shares: {risk_amount:,.2f} ÷ {stop_dist} = {expected_shares}")
        print(f"  Position Value: {expected_shares} × {case['entry']} = {expected_pos_val:,}")
        print(f"  Exceeds Capital: {expected_pos_val > case['capital']}")
        print()
        
        result = calculate_position_size(
            case['capital'],
            case['entry'],
            case['stop'],
            case['mode']
        )
        
        print("Actual Result:")
        print(f"  Shares: {result['shares_to_buy']}")
        print(f"  Position Value: {result['position_value']:,}")
        print(f"  Actual Risk: {result['actual_risk']:,.2f} ({result['actual_risk_pct']:.2f}%)")
        print()
        
        match = result['shares_to_buy'] == expected_shares
        status = "PASS" if match else "FAIL"
        print(f"Verification: {status}")
        if not match:
            print(f"  Expected {expected_shares} shares, got {result['shares_to_buy']}")
        print()


def verify_risk_reward():
    """Verify risk/reward ratio calculations"""
    print("=" * 60)
    print("RISK/REWARD CALCULATION VERIFICATION")
    print("=" * 60)
    
    test_cases = [
        {
            'entry': 100.0,
            'target': 110.0,
            'stop': 95.0,
            'mode': 'balanced',
            'expected_rr': 2.0,
            'description': 'Balanced: 10 point gain, 5 point loss = 2:1'
        },
        {
            'entry': 100.0,
            'target': 115.0,
            'stop': 95.0,
            'mode': 'balanced',
            'expected_rr': 3.0,
            'description': 'Balanced: 15 point gain, 5 point loss = 3:1'
        },
        {
            'entry': 100.0,
            'target': 102.0,
            'stop': 95.0,
            'mode': 'balanced',
            'expected_rr': 0.4,
            'description': 'Invalid: 2 point gain, 5 point loss = 0.4:1'
        }
    ]
    
    for case in test_cases:
        print(f"\n{case['description']}")
        print("-" * 60)
        
        reward = abs(case['target'] - case['entry'])
        risk = abs(case['entry'] - case['stop'])
        expected_ratio = reward / risk
        
        print(f"Entry: {case['entry']}")
        print(f"Target: {case['target']}")
        print(f"Stop: {case['stop']}")
        print()
        print("Expected Calculation:")
        print(f"  Reward: |{case['target']} - {case['entry']}| = {reward}")
        print(f"  Risk: |{case['entry']} - {case['stop']}| = {risk}")
        print(f"  R:R = {reward} / {risk} = {expected_ratio:.2f}:1")
        print()
        
        ratio, is_valid, explanation = validate_risk_reward(
            case['entry'],
            case['target'],
            case['stop'],
            case['mode']
        )
        
        print("Actual Result:")
        print(f"  R:R Ratio: {ratio:.2f}:1")
        print(f"  Valid: {is_valid}")
        print(f"  Explanation: {explanation}")
        print()
        
        match = abs(ratio - expected_ratio) < 0.01
        status = "PASS" if match else "FAIL"
        print(f"Verification: {status}")
        if not match:
            print(f"  Expected {expected_ratio:.2f}:1, got {ratio:.2f}:1")
        print()


if __name__ == '__main__':
    verify_position_sizing()
    print("\n" + "=" * 60 + "\n")
    verify_risk_reward()
    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)



