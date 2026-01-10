# Conditions Message Fix

## Issue
The formatter was showing "STRONG BUY CONDITIONS" even when the recommendation was "WEAK BUY", causing confusion.

**Example**:
- Recommendation: "WEAK BUY"
- Score: 8/10 (80%)
- Displayed: "✅ STRONG BUY CONDITIONS - Most indicators are bullish"
- **Problem**: Contradicts the actual "WEAK BUY" recommendation

## Root Cause
The formatter was using `score_pct` to determine the conditions message, not checking the actual recommendation string.

**Before**:
```python
if score_pct >= 70:
    msg_text = "STRONG BUY CONDITIONS"  # ❌ Wrong if recommendation is "WEAK BUY"
```

## Fix Applied

**File**: `src/core/formatters.py` (lines 750-785)

**New Logic**: Check the actual recommendation string first, then fall back to score-based logic:

```python
elif rec_type == 'BUY':
    # Check actual recommendation string to match conditions message
    recommendation_upper = recommendation.upper()
    
    if 'STRONG BUY' in recommendation_upper:
        msg_text = "STRONG BUY CONDITIONS"
        detail = "Most indicators are bullish"
    elif 'WEAK BUY' in recommendation_upper:
        msg_text = "WEAK BUY CONDITIONS"
        detail = "Few bullish signals, higher risk"
    elif score_pct >= 70:
        # Regular BUY with high score (fallback)
        msg_text = "STRONG BUY CONDITIONS"
        detail = "Most indicators are bullish"
    # ... rest of logic
```

## Priority Order

1. **First**: Check recommendation string for "STRONG BUY" or "WEAK BUY"
2. **Then**: Fall back to score-based logic for regular "BUY" recommendations

## Result

Now the conditions message will match the recommendation:
- "STRONG BUY" → "✅ STRONG BUY CONDITIONS"
- "WEAK BUY" → "⚠️ WEAK BUY CONDITIONS"
- "BUY" (with high score) → "✅ STRONG BUY CONDITIONS"
- "BUY" (with low score) → "⚠️ WEAK BUY CONDITIONS"

## Additional Fixes

1. **Scheduler Error**: Fixed `time_diff_seconds` undefined variable in logging
2. **Alert Formatter**: Removed unused `index` parameter

## Status
✅ **FIXED**: Conditions message now matches the actual recommendation type

---

**The conditions message will now correctly reflect the recommendation type!**

