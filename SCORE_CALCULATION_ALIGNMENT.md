# Score Calculation Alignment Fix

## Problem Identified

The formatter (`src/core/formatters.py`) was recalculating the score independently from the analysis service (`src/bot/services/analysis_service.py`), causing discrepancies:

- **User sees**: 9/10 score (90%) in the output
- **Analysis service calculates**: 5/10 score (50%)
- **Result**: Contradiction - high score but showing AVOID

## Root Cause

### Formatter Logic (WRONG - Independent Calculation)
```python
# Formatter recalculates score:
trend_score = 0-3 (from direct indicator checks)
momentum_score = 0-3 (from direct indicator checks)
volume_score = 0-1 (vol_ratio >= 1.5)
pattern_score = 0-3 (2 for bullish pattern + 1 for bullish bias)
risk_score = 0-2 (1 for R:R valid + 1 for volume >= 1.0)  # ❌ DIFFERENT!
total = trend + momentum + volume + pattern + risk (max 12, but treated as 10)
```

### Analysis Service Logic (CORRECT - Used for Recommendations)
```python
# Analysis service calculates score:
trend_score = 0-3 (from trend_signals count)
momentum_score = 0-3 (from momentum_signals count)
volume_score = 0-1 (vol_ratio >= 1.5)
pattern_score = 0-3 (from pattern_signals + bias)
risk_score = 0-1 (only R:R valid, NOT volume)  # ✅ CORRECT
total = trend + momentum + volume + pattern + risk (max 10)
overall_score_pct = (total / 10) * 100
```

## Key Differences

1. **Risk Score**:
   - Formatter: 2 points (R:R + volume) ❌
   - Analysis Service: 1 point (R:R only) ✅

2. **Trend Score**:
   - Formatter: Checks `market_phase` string directly
   - Analysis Service: Counts from `trend_signals` dictionary

3. **Pattern Score**:
   - Formatter: Adds 2 for bullish pattern + 1 for bias = 3 max
   - Analysis Service: Counts from `pattern_signals` + bias = 3 max
   - (This one is actually similar, but calculation method differs)

## Fix Applied

### Solution: Use `overall_score_pct` from Analysis Service

**File**: `src/core/formatters.py`

**Change**:
```python
# BEFORE (WRONG - Independent calculation):
total_bullish = trend_score + momentum_score + volume_score + pattern_score + risk_score
score_pct = (total_bullish / max_score) * 100

# AFTER (CORRECT - Use analysis service score):
if 'overall_score_pct' in analysis:
    # Use the score calculated by analysis_service (matches recommendation logic)
    score_pct = analysis['overall_score_pct']
    # Calculate total_bullish from score_pct for display
    total_bullish = int(round((score_pct / 100) * 10))
else:
    # Fallback: Calculate total score (for backward compatibility)
    total_bullish = trend_score + momentum_score + volume_score + pattern_score + risk_score
    score_pct = (total_bullish / 10) * 100
```

### Additional Fixes

1. **Risk Score**: Changed from max 2 to max 1 (matches analysis service)
   - Removed: `if vol_ratio >= 1.0: risk_score += 1`
   - Now: Only R:R validity counts (1 point)

2. **Consistency**: Formatter now uses the same score that drives recommendations

## Impact

### Before Fix
- Formatter shows: 9/10 (90%)
- Analysis service: 5/10 (50%)
- Recommendation: AVOID (based on 50%)
- **User sees contradiction**: High score but AVOID

### After Fix
- Formatter shows: 5/10 (50%) ✅
- Analysis service: 5/10 (50%) ✅
- Recommendation: AVOID (based on 50%) ✅
- **Consistent**: Score matches recommendation

## Professional Standard Alignment

This fix ensures:
1. ✅ **Single Source of Truth**: Score is calculated once in analysis service
2. ✅ **Consistency**: Display matches recommendation logic
3. ✅ **Transparency**: User sees the same score used for decision-making
4. ✅ **Professional Standard**: Matches how professional tools work (single calculation, consistent display)

## Testing

After this fix:
- Formatter score will match analysis service score
- No more contradictions between displayed score and recommendation
- Override logic will use the correct score (from analysis service)
- Test framework will validate correctly

---

**This fix ensures the displayed score is the same score used for recommendations, eliminating contradictions.**

