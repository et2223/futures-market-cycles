import os
import re
from collections import defaultdict, Counter
from datetime import datetime
import streamlit as st

BEST_TRADES_DIR = "group-best-trades"
DAILY_PLANS_DIR = "daily-plans"


# ---------- Core parsing & logic (same brain as your scripts) ----------

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

    elif "rotational" in cycle or "trap" in cycle:
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

    return {
        "cycle": cycle,
        "primary": primary,
        "secondary": secondary,
        "avoid": avoid,
        "raw_counts": agg,
    }


def build_time_commentary(cycle: str):
    c = cycle.lower()

    if "trend / hybrid" in c or c.startswith("trend"):
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
    elif "rotational" in c or "trap" in c:
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


def build_daily_plan_md(lookback_days, recent_dates, result):
    today_str = datetime.today().strftime("%Y-%m-%d")
    first_2h_comment, until_noon_comment = build_time_commentary(result["cycle"])

    lines = []
    lines.append(f"# DAILY TRADING PLAN – {today_str}")
    lines.append("")
    lines.append("## 1. Cycle & Bias")
    lines.append("")
    lines.append(f"- Lookback days used: **{lookback_days}**")
    lines.append("- Days considered:")
    for d in recent_dates:
        lines.append(f"  - {d}")
    lines.append("")
    lines.append(f"- **Inferred cycle:** {result['cycle']}")
    lines.append("- **Directional bias:** __________________________")
    lines.append("  (e.g. 'Short unless 15m range reclaims PDH' or 'Neutral until 15m range breaks cleanly.')")
    lines.append("")
    lines.append("## 2. Setup Focus")
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
    lines.append("## 3. First 2 Hours – RTH 09:30–11:30 ET (15:30–17:30 CET)")
    lines.append("")
    lines.append(first_2h_comment.strip())
    lines.append("")
    lines.append("Notes:")
    lines.append("- What would CONFIRM this view in the first 2 hours?")
    lines.append("- What would INVALIDATE it?")
    lines.append("")
    lines.append("## 4. Until Noon – RTH 09:30–13:30 ET (15:30–19:30 CET)")
    lines.append("")
    lines.append(until_noon_comment.strip())
    lines.append("")
    lines.append("Notes:")
    lines.append("- When will you stop trading even if the market keeps moving?")
    lines.append("- What kind of conditions make you walk away (too choppy, too parabolic, etc.)?")
    lines.append("")
    lines.append("## 5. Behavior / Reminders")
    lines.append("")
    lines.append("- Today, do MORE of: ______________________________")
    lines.append("- Today, avoid: ___________________________________")
    lines.append("- Non-negotiable rules (e.g. no countertrend without REM / no trades after 2R loss).")
    lines.append("")

    return "\n".join(lines)



# ---------- Streamlit UI ----------

def main():
    st.title("Futures Market Cycles – Web Interface")
    st.write("ES best-trades → cycle prediction → daily plan")

        st.caption(
        "Time reference: US RTH 09:30–16:00 ET (15:30–22:00 CET). "
        "First 2h ≈ 09:30–11:30 ET (15:30–17:30 CET). "
        "Until noon ≈ 09:30–13:30 ET (15:30–19:30 CET)."
    )


    all_days = load_all_days()
    if not all_days:
        st.error(f"No files found in `{BEST_TRADES_DIR}`. Add your best-trades markdown files first.")
        return

    sorted_dates = sorted(all_days.keys())
    st.sidebar.header("Settings")
    max_lookback = len(sorted_dates)

    lookback_days = st.sidebar.slider(
        "Lookback days", min_value=1, max_value=max_lookback, value=min(3, max_lookback)
    )

    recent_dates = sorted_dates[-lookback_days:]
    recent_counts = [all_days[d] for d in recent_dates]

    result = infer_cycle_and_setups(recent_counts)

    st.subheader("Today’s Market Cycle Prediction")
    st.markdown(f"**Lookback days used:** {lookback_days}")
    st.markdown("**Days considered:**")
    for d in recent_dates:
        st.markdown(f"- {d}")
    st.markdown(f"**Inferred cycle:** `{result['cycle']}`")

    st.markdown("### Recommended Setups")
    st.markdown(f"- **Primary:** {', '.join(result['primary']) if result['primary'] else '(none)'}")
    st.markdown(f"- **Secondary:** {', '.join(result['secondary']) if result['secondary'] else '(none)'}")
    st.markdown(f"- **Avoid:** {', '.join(result['avoid']) if result['avoid'] else '(none)'}")

    st.markdown("### Raw Setup Frequency (lookback window)")
    for setup, count in result["raw_counts"].most_common():
        st.markdown(f"- {setup}: {count}")

    st.markdown("---")

    st.subheader("Generate Daily Plan (Markdown)")
    if st.button("Generate plan for today"):
        today_str = datetime.today().strftime("%Y-%m-%d")
        md = build_daily_plan_md(lookback_days, recent_dates, result)

        # Show in app
        st.code(md, language="markdown")

        # Save to file
        os.makedirs(DAILY_PLANS_DIR, exist_ok=True)
        plan_path = os.path.join(DAILY_PLANS_DIR, f"{today_str}-plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(md)
        st.success(f"Saved to {plan_path}")

        st.download_button(
            label="Download plan as .md",
            data=md,
            file_name=f"{today_str}-plan.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
