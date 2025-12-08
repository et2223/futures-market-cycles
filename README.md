# Futures Market Cycles

Personal trading framework for ES (S&P 500 futures) based on structured setups, market cycles, and daily planning.

## Goals

- Track the market cycle day by day  
- See which setups are working right now  
- Define one primary setup to focus on each day  
- Keep all rules and logs versioned and organized

## Structure

- `setups/` – Definitions for all setups  
- `templates/` – Reusable templates  
- `daily-plans/` – Morning plans + evening reviews  
- `group-best-trades/` – Daily group “best trades” lists and analysis  
- `trade-log/` – CSV file of every trade  
- `market-cycle/` – Notes on market regime shifts

## Daily Workflow

### Pre-Market

1. Fill the cycle-check template.  
2. Infer today’s market cycle.  
3. Choose one primary setup for the day.  
4. List setups to avoid.  
5. Mark key levels and time windows.

### During Session

- Trade only setups that are valid for today’s market cycle.  
- If live behavior clearly contradicts the expected cycle, switch to the setup family that matches the actual behavior.

### After Session

1. Fill the evening review.  
2. Log trades into `trade-log/trades.csv`.  
3. Update `group-best-trades` with the day’s best setups from the group.  
4. Update `market-cycle/cycle-notes.md` if a regime shift is visible.
