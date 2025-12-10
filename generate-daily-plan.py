import os
import re
import sys
from collections import defaultdict, Counter
from datetime import datetime

BEST_TRADES_DIR = "group-best-trades"
DAILY_PLANS_DIR = "daily-plans"
LOOKBACK_DAYS_DEFAULT = 3  # default lookback if none provided


def normalize_setup(name: str) -> str:
    n = name.lower().strip()
    if "15 min" in n or "15m" in n:
        return "15m Re-Entry"
    if "emt" in n:
        return "EMT"
    if "rem" in n:
        return "REM"
    if "trend line" in n or "trendline" in n:
        return "Trend Line"
    if "reversal" in n:
        return "Reversal"
    if "continuation" in n:
        return "Continuation"
    return name.strip()


def parse_best_trades_file(path: str):
    fname = os.path.basename(path)
    m = re.match(r"(\d{4}-\d{2}-\d{2})-best-trades\.md", fname)
    if not m:
        return None, {}

    day = m.group(1)
    counts_section = False
    counts = defaultdict(int)

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not counts_section:
                if line.lower().startswith("## count by setup"):
                    counts_section = True
                continue

            if not line:
                continue

            m2 = re.match(r"[-*]\s+(.+?):\s*([\d]+)", line)
            if m2:
                raw_name = m2.group(1)
                value = int(m2.group(2))
                normalized = normalize_setup(raw_name)
                counts[normalized] += value

    return day, dict(counts)


def load_all_days():
    data = {}
    if not os.path.isdir(BEST_TRADES_DIR):
        print(f"Directory '{BEST_TRADES_DIR}' not found.")
        return data

    for fname in os.listdir(BEST_TRADES_DIR):
        if not fname.endswith("-best-trades.md"):
            continue
        path = os.path.join(BEST_TRADES_DIR, fname)
        day, counts = parse_best_trades_file(path)
        if day:
            data[day] = counts
    return data


def infer_cycle_and_setups(last_days_counts):
    agg = Counter()
    for c in last_days_counts:
        agg.update(c)

    if not agg:
        return {
            "cycle": "Unknown",
            "primary": [],
            "secondary": [],
            "avoid": [],
            "raw_counts": agg,
        }

    trend_family = agg["Continuation"] + agg["EMT"] + agg["Trend Line"]
    trap_family = agg["REM"] + agg["15m Re-Entry"] + agg["Reversal"]

    if trend_family > trap_family * 1.3 and agg["EMT"] > 0:
        cycle = "Trend / Hybrid (Trend-biased)"
    elif trap_family > trend_family * 1.3:
        cycle = "Rotational / Trap"
    else:
        cycle = "Hybrid"

    primary = []
    secondary = []
    avoid = []
    sorted_setups = [s for s, _ in agg.most_common()]

    if cycle.startswith("Trend"):
        for s in sorted_setups:
            if s in ("Continuation", "EMT", "Trend Line"):
                primary.append(s)
        if "REM" in sorted_setups:
            secondary.append("REM")
        if "15m Re-Entry" in sorted_setups:
            avoid.append("15m Re-Entry")
        if "Reversal" in sorted_setups:
            avoid.append("Reversal")

    elif cycle == "Rotational / Trap":
        for s in sorted_setups:
            if s in ("15m Re-Entry", "REM", "Reversal"):
                primary.append(s)
        if "Trend Line" in sorted_setups:
            secondary.append("Trend Line")
        if "EMT" in sorted_setups:
            avoid.append("EMT")
        if "Continuation" in sorted_setups:
            avoid.append("Continuation")

    else:  # Hybrid
        base_primary = sorted_setups[:3]
        if "REM" in sorted_setups and "REM" not in base_primary:
            base_primary.append("REM")

        seen = set()
        primary = []
        for s in base_primary:
            if s not in seen:
                primary.append(s)
                seen.add(s)

        secondary = [s for s in sorted_setups if s not in seen]
        # avoid stays empty for Hybrid – decided intraday

    return {
        "cycle": cycle,
        "primary": primary,
        "secondary": secondary,
        "avoid": avoid,
        "raw_counts": agg,
    }


def build_time_commentary(cycle: str):
    """
    Return two text blocks:
    - first_2h_comment
    - until_noon_comment
    based on inferred cycle.
    """
    cycle = cycle.lower()

    if "trend / hybrid" in cycle or cycle.startswith("trend"):
        first_2h = (
            "- Expect cleaner trend behavior in the first 2 hours if the first breakout holds.\n"
            "- EMT and Continuation can both be valid from the open if price and midband accept above/below key levels.\n"
            "- Watch for one early REM-style failed counter-move, but do not over-focus on reversals.\n"
        )
        until_noon = (
            "- Trend can continue, but the probability of traps increases as the morning progresses.\n"
            "- Look for REM after extended pushes or failed attempts to reverse the trend.\n"
            "- Trendline + Continuation remain valid if structure (HH/HL or LL/LH) is intact.\n"
        )
    elif "rotational" in cycle or "trap" in cycle:
        first_2h = (
            "- Expect fake breaks of the 15m range and key levels (PDH/PDL, ONH/ONL) in the first 2 hours.\n"
            "- 15m Re-Entry, REM, and Reversal around clear extremes have higher probability.\n"
            "- Avoid chasing the first breakout; wait for confirmation that it fails or truly holds.\n"
        )
        until_noon = (
            "- Range boundaries become more defined as the morning develops.\n"
            "- Continuation trades are lower probability unless the market clearly transitions into trend.\n"
            "- REM remains important whenever the market fakes a new direction and snaps back.\n"
        )
    else:  # Hybrid
        first_2h = (
            "- Expect a mix of trend and trap behavior in the first 2 hours.\n"
            "- Continuation and Trendline setups can work, but REM is equally important when early reversals fail.\n"
            "- Be flexible: if the first breakout holds cleanly, lean trend; if it fails, lean trap (REM / Re-Entry).\n"
        )
        until_noon = (
            "- As structure develops, Trendline + Continuation can offer cleaner entries.\n"
            "- REM remains a primary tool around failed attempts to reverse the main move.\n"
            "- Avoid over-trading: wait for confluence with midband, 80 SMA, and key levels.\n"
        )

    return first_2h, until_noon


def main():
    # lookback from CLI
    lookback_days = LOOKBACK_DAYS_DEFAULT
    if len(sys.argv) >= 2:
        try:
            arg_val = int(sys.argv[1])
            if arg_val > 0:
                lookback_days = arg_val
        except ValueError:
            pass

    all_days = load_all_days()
    if not all_days:
        print("No best-trades files found. Exiting.")
        return

    sorted_dates = sorted(all_days.keys())
    recent_dates = sorted_dates[-lookback_days:]
    recent_counts = [all_days[d] for d in recent_dates]

    result = infer_cycle_and_setups(recent_counts)
    first_2h_comment, until_noon_comment = build_time_commentary(result["cycle"])

    # Use today's date for plan filename
    today_str = datetime.today().strftime("%Y-%m-%d")
    plan_filename = f"{today_str}-plan.md"
    plan_path = os.path.join(DAILY_PLANS_DIR, plan_filename)

    os.makedirs(DAILY_PLANS_DIR, exist_ok=True)

    lines = []
    lines.append(f"# DAILY TRADING PLAN – {today_str}")
    lines.append("")
    lines.append("## 1. Market Context")
    lines.append("")
    lines.append(f"- Lookback days used: **{lookback_days}**")
    lines.append("- Days considered:")
    for d in recent_dates:
        lines.append(f"  - {d}")
    lines.append("")
    lines.append("Add any news, overnight context, HTF levels here.")
    lines.append("")
    lines.append("## 2. Expected Market Cycle")
    lines.append("")
    lines.append(f"- **Inferred cycle:** {result['cycle']}")
    lines.append("")
    lines.append("Notes:")
    lines.append("- Why this cycle makes sense given recent days.")
    lines.append("- What would *invalidate* this cycle at the open.")
    lines.append("")
    lines.append("## 3. Setup Focus")
    lines.append("")
    if result["primary"]:
        lines.append(f"- **Primary setups:** {', '.join(result['primary'])}")
    else:
        lines.append("- **Primary setups:** (none)")
    if result["secondary"]:
        lines.append(f"- **Secondary setups:** {', '.join(result['secondary'])}")
    else:
        lines.append("- **Secondary setups:** (none)")
    if result["avoid"]:
        lines.append(f"- **Setups to avoid:** {', '.join(result['avoid'])}")
    else:
        lines.append("- **Setups to avoid:** (none)")
    lines.append("")
    lines.append("## 4. Open Playbook – First 2 Hours (RTH)")
    lines.append("")
    lines.append(first_2h_comment.strip())
    lines.append("")
    lines.append("## 5. Extended Morning – Until Noon (RTH)")
    lines.append("")
    lines.append(until_noon_comment.strip())
    lines.append("")
    lines.append("## 6. Key Levels")
    lines.append("")
    lines.append("- PDH:")
    lines.append("- PDL:")
    lines.append("- ONH:")
    lines.append("- ONL:")
    lines.append("- HTF levels (daily/weekly):")
    lines.append("")
    lines.append("## 7. Risk and Rules")
    lines.append("")
    lines.append("- Max trades:")
    lines.append("- Max daily loss:")
    lines.append("- Stop trading conditions (tilt, 2R loss, plan violation, etc.):")
    lines.append("")
    lines.append("## 8. Behavioral Focus")
    lines.append("")
    lines.append("- What to do more of today (wait, size discipline, A+ only, etc.).")
    lines.append("- What to avoid (revenge, chasing, countertrend fighting, etc.).")
    lines.append("")
    lines.append("## 9. After 10:00 AM – Cycle Recheck")
    lines.append("")
    lines.append("- Does live action confirm the expected cycle?")
    lines.append("- If not, which cycle is actually playing out?")
    lines.append("- How does that change setup priority?")
    lines.append("")

    content = "\n".join(lines)

    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Daily plan skeleton written to: {plan_path}")
    print("\n---\n")
    print(content)


if __name__ == "__main__":
    main()

