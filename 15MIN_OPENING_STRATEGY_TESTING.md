# 15-Minute Opening Range Strategy - Testing Instructions

## Strategy File
📄 **Location:** `C:\Users\User\.openclaw\workspace\NQ_15min_Opening_Range_Strategy.pine`

## Strategy Summary
- **Trading Window:** 9:30-9:45 AM ET ONLY
- **Timeframe:** 5-minute bars
- **Max Trades:** 1 per day
- **Exit:** 9:45 bar open (15min max hold)
- **Logic:** Opening range breakout of first 5min bar (9:30-9:35)

---

## Option 1: TradingView Backtest (RECOMMENDED - Most Accurate)

### Steps:
1. Open TradingView
2. Load **CME_MINI:NQ1!** chart with **5-minute timeframe**
3. Click "Pine Editor" at bottom
4. Copy entire contents of `NQ_15min_Opening_Range_Strategy.pine`
5. Paste into Pine Editor
6. Click "Add to Chart"
7. Open "Strategy Tester" tab
8. Configure settings:
   - **Date Range:** Last 15 years (2011-01-01 to 2026-02-02)
   - **Commission:** $2.50 per side (or your broker rate)
   - **Slippage:** 0.25 points ($5)
   - **Initial Capital:** $100,000
9. Review results:
   - Net Profit
   - Total Closed Trades
   - Win Rate
   - Profit Factor
   - Max Drawdown
   - Sharpe Ratio
10. **Export Results:**
    - Click "List of Trades" tab
    - Export to CSV
    - Save as: `15min_Opening_Range_Backtest_Results.csv`

### What to Look For (Legitimate Edge):
- ✅ **Win Rate:** >40% (acceptable for breakout strategies)
- ✅ **Profit Factor:** >1.5 (1.5+ shows clear edge)
- ✅ **Avg Win/Avg Loss Ratio:** >2.0 (winners should be 2x losers)
- ✅ **Max Drawdown:** <15% of capital
- ✅ **Consistent Performance:** Positive across multiple years
- ✅ **Total Trades:** 2000-3000+ (15 years × ~250 trading days)

---

## Option 2: Python Backtest (If TradingView Unavailable)

### Requirements:
- 15 years of NQ 5-minute OHLC data (CSV format)
- Python backtesting library (backtesting.py or vectorbt)

### Data Format Needed:
```csv
Date,Time,Open,High,Low,Close,Volume
2011-01-03,09:30,5300.00,5305.25,5299.50,5303.75,1234
2011-01-03,09:35,5303.75,5308.00,5302.50,5306.25,987
...
```

### Next Steps:
1. Export 15 years of NQ 5min data from TradingView or your data provider
2. I'll create Python backtesting script to run locally
3. Results will include all performance metrics

---

## Option 3: Use Existing NQ ORB Data as Proxy

I see you have several NQ ORB backtest results in Downloads:
- `NQ_9_30_ORB_[Clean_Slate_V2]_CME_MINI_NQ1!_2026-01-30.csv` (529K)
- `NQ_9_35_Symmetric_ORB_[Robust_V4__Bulletproof]_CME_MINI_NQ1!_2026-01-30.csv` (908K)

These are similar strategies (opening range breakouts). Can analyze these to estimate performance profile.

---

## RECOMMENDATION

**Best approach:** Upload Pine Script to TradingView and run official backtest with your 15-year NQ dataset.

**Why:**
- Most accurate execution simulation
- Proper timestamp handling (ET timezone)
- Built-in commission/slippage modeling
- Visual equity curve and trade analysis
- Industry-standard results

**Time Required:** 5-10 minutes

---

## After Backtest - Next Steps

Once results are ready:
1. Review performance metrics
2. If edge is confirmed (Profit Factor >1.5), I'll:
   - Optimize parameters if needed
   - Add risk management rules
   - Prepare for paper trading
   - Create implementation plan

If edge is NOT confirmed:
- Analyze failure points
- Iterate on strategy logic
- Test alternative entry/exit rules

---

## Questions?
Let me know which testing option you prefer and I'll assist accordingly.
