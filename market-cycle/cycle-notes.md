# Market Cycle Notes

Use this file for longer-term notes on how ES is behaving across weeks and months, and how setups should be prioritized in each cycle.

---

## Core Idea

- The **pre-market hypothesis** is just a starting point.  
- The **real cycle is decided by 10:00 AM** using:
  - Acceptance vs rejection at PDH / PDL / ONH / ONL / 15m range  
  - Midband slope (sloped vs flat)  
  - Clean vs violent pullbacks  
  - Staircase (HH/HL or LL/LH) vs choppy structure  
  - First breakout success vs failure  

Once 10:00 AM hits, the cycle tag must reflect live behavior, not the plan.

---

## Quick 10:00 AM Cycle Rules

### Trend / Momentum
- Acceptance at key levels (PDH/PDL, ONH/ONL, 15m range)  
- Sloped midband and aligned 80 SMA  
- Clean staircase structure (HH/HL or LL/LH)  
- First breakout succeeds and holds

**Setups:**  
- EMT  
- Trend Continuation  
- Trendline Touch  
- REM only if a reversal attempt fails

---

### Hybrid Trend (Trend + Traps)  ← Important for your trading
- Trend structure present, but with visible trap phases:
  - Failed reversals  
  - REM opportunities  
- Midband mostly sloped, but pullbacks can be messy.  
- Breakouts can hesitate or partially fail before continuing.

**Setups:**  
- Trend Continuation (core)  
- Trendline Touch (structure)  
- REM (high priority, not just secondary)  
- EMT when the open or a major break is unusually clean  
- Reversal / 15m Re-Entry only at very obvious extremes

---

### Rotational / Trap
- Rejection at PDH/PDL and key levels  
- Flat or choppy midband  
- First breakout fails and price returns inside 15m range  
- Repeated testing of both sides of the range

**Setups:**  
- 15m Re-Entry  
- REM  
- Reversal  
- Trendline Touch inside the range  
- Avoid EMT and raw Continuation unless the behavior clearly shifts.

---

### Trap / REM Cycle
- Multiple failed reversals  
- Double-cross sequences  
- Trend attempts that don’t stick

**Setups:**  
- REM as primary  
- 15m Re-Entry  
- Reversal at obvious extremes  
- Then Trend Continuation only after a clear REM trap resolution.

---

### End-of-Trend
- Parabolic or exhausted moves into major HTF levels  
- Big tails, volatility spikes, failed pushes  
- Trendline breaks with big rejection

**Setups:**  
- Reversal  
- REM when the final push to resume trend fails  
- 15m Re-Entry when the last breakout fails back inside range  
- Avoid new EMTs and late Continuation entries.

---

## December 2025 – Example Regime Notes

- Early December:
  - Strong presence of EMT + Continuation on some days (Dec 2, Dec 8).  
  - Other days show Hybrid Trend behavior: trend + REM + Reversal (Dec 9).  
  - Pure rotational / 15m Re-Entry days are less frequent in this slice.

- Implications:
  - Keep **REM** as an active, **primary** setup whenever the day is Hybrid Trend or Trap-biased.  
  - In clean Trend / Momentum regimes, prioritize EMT and Continuation, but still watch for one or two REM traps.  
  - Only make 15m Re-Entry the main setup when:
    - the first breakout fails  
    - midband re-enters the range  
    - structure becomes clearly rotational.

---

## Long-Term Goal

- Continue logging “best trades of the day” in `group-best-trades/`.  
- Use `cycle-predictor.py` + the 10:00 AM checklist to:
  - Detect when the environment is shifting from Trend → Hybrid → Trap → Rotation → End-of-Trend.  
  - Adjust primary setups accordingly (especially when REM starts appearing more or less often).
