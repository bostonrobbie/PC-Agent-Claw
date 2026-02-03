# 15-Minute Opening Range Strategy - Variants Report

## Base Strategy Performance (15 Years)

**Top 5 Metrics:**
- Total Return: **348.33%**
- Max Drawdown: **20.91%**
- Sharpe Ratio: **0.93**
- Profit Factor: **1.22**
- Win Rate: **53.6%**

**Trade Statistics:**
- Total Trades: 3,515
- Winning Trades: 1,884
- Losing Trades: 1,631
- Avg Win: $1,038
- Avg Loss: -$985

**Assessment:** ✅ Shows legitimate edge - profitable, positive Sharpe, good profit factor

---

## Variant #1: Extended Window (Low Overfit Risk)

**Changes:**
- Extend trading window from 15min to 30min (9:30-10:00)
- Still capture opening range from first 5min (9:30-9:35)
- Allow entries until 9:55
- Exit at 10:00 instead of 9:45

**Hypothesis:**
More time for breakout to develop. Catches momentum that materializes slightly later in the session.

**Expected Impact:**
- May increase win rate
- Larger average wins (more time to run)
- Could increase average loss if late entries catch false breakouts

**Overfit Risk:** LOW

**Implementation Status:** Not yet implemented

---

## Variant #2: Volatility Filter (Low Overfit Risk) ✅ IMPLEMENTED

**Changes:**
- Add ATR(14) volatility filter
- Only trade when ATR > SMA(ATR, 20)
- Filter applied at 9:30 bar (consistent daily check)

**Hypothesis:**
Opening range breakouts perform better in volatile markets. Low volatility days produce choppy, range-bound price action with more false breakouts.

**Expected Impact:**
- ~40% fewer trades
- Higher win rate (better quality setups)
- Improved profit factor
- Lower drawdown

**Overfit Risk:** LOW

**Files:**
- Pine Script: `NQ_15min_Opening_Range_VARIANT_Volatility_Filter.pine`

**Implementation Status:** ✅ COMPLETE - Ready for TradingView backtest

---

## Variant #3: Wider Range Threshold (Low Overfit Risk)

**Changes:**
- Only trade if opening range width > 0.3% of price
- Skip days with tight ranges
- Calculation: `(OR_High - OR_Low) / OR_Low > 0.003`

**Hypothesis:**
Tight opening ranges often lead to false breakouts. Wider ranges indicate genuine volatility and clearer directional intent.

**Expected Impact:**
- Fewer trades
- Higher quality setups
- Improved profit factor
- Better win rate

**Overfit Risk:** LOW

**Implementation Status:** Not yet implemented

---

## Variant #4: Directional Bias (Medium Overfit Risk)

**Changes:**
- Add pre-market bias filter
- Only LONG if previous day closed higher than opened
- Only SHORT if previous day closed lower
- Filters: 50% of potential trades

**Hypothesis:**
Align with prevailing market sentiment. Following momentum from previous session improves probability.

**Expected Impact:**
- 50% fewer trades
- Potentially higher win rate
- May miss counter-trend reversals

**Overfit Risk:** MEDIUM (using previous day data could be look-ahead bias)

**Implementation Status:** Not yet implemented

---

## Variant #5: Trailing Stop (Medium Overfit Risk)

**Changes:**
- Replace fixed 9:45 exit with trailing stop at 0.2% from entry
- Exit at 9:45 OR when trailing stop hit (whichever first)
- Dynamic exit based on price action

**Hypothesis:**
Lock in profits on strong moves while limiting holding time. Prevents giving back gains on quick reversals.

**Expected Impact:**
- Better average win
- Reduced "favorable excursion give-back"
- May exit winning trades too early

**Overfit Risk:** MEDIUM (optimizing exit percentage can overfit)

**Implementation Status:** Not yet implemented

---

## Recommended Testing Order

### Phase 1: Low Risk Variants (Test First)
1. ✅ **Variant #2: Volatility Filter** (READY TO TEST)
   - Lowest overfit risk
   - Strong theoretical foundation
   - Easy to backtest

2. **Variant #3: Wider Range Threshold**
   - Also low overfit risk
   - Simple filter logic
   - Good complement to volatility filter

3. **Variant #1: Extended Window**
   - Low risk
   - Easy to implement
   - Tests timing hypothesis

### Phase 2: Medium Risk Variants (Test if Phase 1 successful)
4. **Variant #4: Directional Bias**
   - More complex logic
   - Need to verify no look-ahead bias

5. **Variant #5: Trailing Stop**
   - Requires parameter optimization
   - Higher overfit risk

---

## Combination Variants (Future)

If individual variants perform well, consider combining:

### Combo A: Volatility + Range Threshold
- Filters for both high volatility AND wider ranges
- Double quality filter
- Expect fewer but higher quality trades

### Combo B: Extended Window + Volatility Filter
- More time + better market conditions
- May capture best of both

### Combo C: All Low-Risk Filters
- Volatility Filter + Range Threshold + Extended Window
- Maximum quality filtering
- Likely very few trades but high win rate

---

## Backtesting Protocol

For each variant:

1. **Run 15-year backtest on TradingView**
   - CME_MINI:NQ1!
   - 5-minute timeframe
   - Date range: 2011-2026

2. **Generate Results:**
   - Equity curve (PNG)
   - Top 5 metrics
   - Trade list (CSV)

3. **Compare to Base:**
   - Is Total Return better?
   - Is Max Drawdown lower?
   - Is Sharpe Ratio higher?
   - Is Profit Factor improved?
   - Is Win Rate higher?

4. **Check for Overfitting:**
   - Performance similar across different market periods?
   - No suspicious perfect optimization?
   - Logic makes theoretical sense?

5. **Rob Approval:**
   - Present results with equity curve
   - Show comparison table
   - Get approval before moving to next variant

---

## Success Criteria

A variant is considered successful if:

✅ **At least 3 of 5 metrics improve:**
- Higher Total Return
- Lower Max Drawdown
- Higher Sharpe Ratio
- Higher Profit Factor
- Higher Win Rate

✅ **No signs of overfitting:**
- Consistent performance across years
- Makes theoretical sense
- Not overly optimized

✅ **Practical for live trading:**
- Clear entry/exit rules
- No ambiguity
- Can be executed in real-time

---

## Current Status

**Completed:**
- ✅ Base strategy backtested (348% return, 0.93 Sharpe)
- ✅ 5 variants designed
- ✅ Variant #2 (Volatility Filter) implemented in Pine Script

**Next Steps:**
1. Rob to run Variant #2 backtest on TradingView
2. Compare results with base strategy
3. If successful, implement Variant #3
4. Continue testing variants in order

**Files Ready for Testing:**
- Base: `NQ_15min_Opening_Range_Strategy.pine`
- Variant #2: `NQ_15min_Opening_Range_VARIANT_Volatility_Filter.pine`

---

## Notes

- Local LLM (Ollama) encountered CUDA error - couldn't generate variants automatically
- Pivoted to manual variant creation using trading expertise
- All variants follow Rob's rules: 5min OHLC data, NQ-Main-Algo alignment, no overfitting
- Volatility Filter variant has strongest theoretical foundation
- Focus on Low overfit risk variants first to build confidence

**Cost:** $0 (used manual analysis after LLM failure)
