# Root Cause Analysis (RCA) - Test Failures and Calculation Issues

## Issue #1: Position Sizing Test Failure

### Problem
Test `test_position_size_formula_accuracy` fails for aggressive mode case:
- Expected: 200 shares
- Actual: 400 shares

### Root Cause Analysis

**Step 1: Understand the Formula**
```
Position Size = (Capital × Risk%) / (Entry - Stop)
```

**Step 2: Calculate Expected**
- Capital: 200,000
- Entry: 200
- Stop: 190
- Mode: aggressive (2% risk)
- Risk Amount: 200,000 × 0.02 = 4,000
- Stop Distance: 200 - 190 = 10
- Expected Shares: 4,000 / 10 = 400 shares
- Position Value: 400 × 200 = 80,000

**Step 3: Check Actual Implementation**
Looking at `risk_management.py` lines 331-342:
1. First calculates: `shares = int(risk_amount / stop_distance)` = 400
2. Calculates: `position_value = shares * entry_price` = 80,000
3. Checks: `if position_value > capital` → 80,000 > 200,000? NO
4. So it keeps 400 shares

**Step 4: Why Test Expects 200?**
The test comment says: `# (200000 * 0.02) / 10 = 200`
But the actual calculation is: (200000 * 0.02) / 10 = 4000 / 10 = 400

**Root Cause**: Test has incorrect expected value. The formula is correct, but the test expectation is wrong.

### Fix Required
1. Fix the test to have correct expected values
2. Verify the formula implementation is mathematically correct
3. Ensure capital constraint logic is correct

---

## Issue #2: Capital Constraint Logic

### Problem
When position value exceeds capital, the code recalculates shares but doesn't maintain risk percentage.

### Root Cause Analysis

**Current Logic (lines 337-342):**
```python
if position_value > capital:
    shares = int(capital / entry_price)
    position_value = shares * entry_price
    actual_risk = shares * stop_distance
```

**Issue**: When capital is constrained, the actual risk percentage will be LESS than the target risk percentage. This is correct behavior (can't risk more than you have), but we need to verify:
1. The calculation is correct
2. The actual risk is properly reported
3. Tests verify this behavior

### Fix Required
1. Verify capital constraint logic is correct
2. Add tests for capital-constrained scenarios
3. Ensure actual_risk_pct is correctly calculated in constrained cases

---

## Issue #3: Test Strictness

### Problem
Some tests use loose assertions (e.g., `assertGreaterEqual` with ±1 tolerance) instead of exact matches.

### Root Cause Analysis

**Current Test (test_data_validation.py:108-109):**
```python
self.assertGreaterEqual(position['shares_to_buy'], expected_shares - 1)
self.assertLessEqual(position['shares_to_buy'], expected_shares + 1)
```

**Issue**: This allows incorrect calculations to pass. If the formula is correct, we should get exact matches (except for capital-constrained cases).

### Fix Required
1. Use exact assertions where formula should be exact
2. Only use tolerance for floating-point rounding errors
3. Separate tests for capital-constrained scenarios

---

## Issue #4: Calculation Accuracy Verification

### Problem
We haven't verified that technical indicators (RSI, MACD, etc.) use correct formulas.

### Root Cause Analysis

**Current State**: We use the `ta` library for indicators, but we don't verify:
1. The library is using correct formulas
2. Our wrapper functions preserve accuracy
3. Edge cases are handled correctly

### Fix Required
1. Create reference calculations for known datasets
2. Compare against industry-standard implementations
3. Test edge cases (constant prices, extreme values, etc.)

---

## Issue #5: Signal Weight Calculations

### Problem
Need to verify signal scoring and confidence calculation formulas are correct.

### Root Cause Analysis

**Current Implementation**: 
- Signal weights sum to 100
- Confidence = 50 + (net_score / max_score) * 50
- Need to verify this formula is correct

### Fix Required
1. Verify signal weight normalization
2. Verify confidence calculation formula
3. Test with known signal combinations

---

## Summary of Required Fixes

1. **Fix test expectations** - Correct expected values in position sizing tests
2. **Strengthen test assertions** - Use exact matches where appropriate
3. **Add capital constraint tests** - Test scenarios where capital limits position size
4. **Verify indicator formulas** - Compare against reference implementations
5. **Verify signal calculations** - Test confidence and scoring formulas
6. **Add edge case tests** - Test boundary conditions and extreme values

