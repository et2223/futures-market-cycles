import os
import re
from collections import defaultdict, Counter
from datetime import datetime

# CONFIG
BEST_TRADES_DIR = "group-best-trades"
OUTPUT_FILE = os.path.join("market-cycle", "today-prediction.md")
LOOKBACK_DAYS = 3  # how many most recent days to use for the prediction

# Mapping raw setup names to normalized categories
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
    return name.strip()  # fallback, should rarely be used


def parse_best_trades_file(path: str):
    """
    Parse a best-trades markdown file and return:
    - date (YYYY-MM-DD)
    - dict: setup -> count
    """
    fname = os.path.basename(path)
    # Expect format like 2025-12-08-best-trades.md
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
                # detect start of "Count by Setup" section
                if line.lower().startswith("## count by setup"):
                    counts_section = True
                continue
            # inside Count by Setup section
            if not line or line.startswith("#"):
                # end if we hit another header or blank
                # but allow blank lines between bullet points
                continue
            # lines expected like "- EMT: 3"
            m2 = re.match(r"[-*]\s+(.+?):\s*([\d]+)", line)
            if m2:
                raw_name = m2.group(1)
                value = int(m2.group(2))
                normalized = normalize_setup(raw_name)
                counts[normalized] += value

    return day, dict(counts)


def load_all_days():
    """Load all best-trades files and return dict: date -> counts dict."""
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
    """
    Given list of counts dicts for last N days,
    infer market cycle and recommend setups.
    """

    # Aggregate counts across lookback window
    agg = Counter()
    for c in last_days_counts:
        agg.update(c)

    # If no data, return neutral
    if not agg:
        return {
            "cycle": "Unknown",
            "primary": [],
            "secondary": [],
            "avoid": [],
            "raw_counts": agg,
        }

    # Sum families
    trend_family = agg["Continuation"] + agg["EMT"] + agg["Trend Line"]
    trap_family = agg["REM"] + agg["15m Re-Entry"] + agg["Reversal"]

    # Simple logic for cycle
    if trend_family > trap_family * 1.3 and agg["EMT"] > 0:
        cycle = "Trend / Hybrid (Trend-biased)"
    elif trap_family > trend_family * 1.3:
        cycle = "Rotational / Trap"
    else:
        cycle = "Hybrid"

    # Decide primary & secondary setups based on cycle & frequency
    primary = []
    secondary = []
    avoid = []

    # Sort setups by frequency (desc)
    sorted_setups = [s for s, _ in agg.most_common()]

    if cycle.startswith("Trend"):
        # Trend-biased: focus on Continuation, EMT, Trend Line
        for s in sorted_setups:
            if s in ("Continuation", "EMT", "Trend Line"):
                primary.append(s)
        # Secondary = REM as filter on traps
        if "REM" in sorted_setups:
            secondary.append("REM")
        # Avoid = 15m Re-Entry and naked Reversal
        if "15m Re-Entry" in sorted_setups:
            avoid.append("15m Re-Entry")
        if "Reversal" in sorted_setups:
            avoid.append("Reversal")

    elif cycle == "Rotational / Trap":
        # Trap/rotational: focus on 15m Re-Entry, REM, Reversal
        for s in sorted_setups:
            if s in ("15m Re-Entry", "REM", "Reversal"):
                primary.append(s)
        # Secondary = Trend Line as structure trade in chop
        if "Trend Line" in sorted_setups:
            secondary.append("Trend Line")
        # Avoid EMT / raw Continuation unless insanely clean
        if "EMT" in sorted_setups:
            avoid.append("EMT")
        if "Continuation" in sorted_setups:
            avoid.append("Continuation")

    else:  # Hybrid
        # Hybrid: mix of trend + traps. Choose top 2–3 overall as primary
        primary = sorted_setups[:3]
        # Secondary = the rest that are not clearly opposite
        for s in sorted_setups[3:]:
            secondary.append(s)
        # Avoid list left empty here – up to intraday read

    return {
        "cycle": cycle,
        "primary": primary,
        "secondary": secondary,
        "avoid": avoid,
        "raw_counts": agg,
    }


def main():
    all_days = load_all_days()
    if not all_days:
        print("No best-trades files found. Exiting.")
        return

    # Sort days ascending, then take the last N for prediction
    sorted_dates = sorted(all_days.keys())
    recent_dates = sorted_dates[-LOOKBACK_DAYS:]
    recent_counts = [all_days[d] for d in recent_dates]

    result = infer_cycle_and_setups(recent_counts)

    # Build markdown output
    lines = []
    lines.append(f"# Today’s Market Cycle Prediction")
    lines.append("")
    lines.append(f"**Lookback days used:** {LOOKBACK_DAYS}")
    lines.append("")
    lines.append("**Days considered:**")
    for d in recent_dates:
        lines.append(f"- {d}")
    lines.append("")
    lines.append(f"## Inferred Cycle")
    lines.append("")
    lines.append(f"- **Cycle:** {result['cycle']}")
    lines.append("")
    lines.append(f"## Recommended Setups for Today")
    lines.append("")
    if result["primary"]:
        lines.append(f"- **Primary setups:** " + ", ".join(result["primary"]))
    else:
        lines.append(f"- **Primary setups:** (none)")
    if result["secondary"]:
        lines.append(f"- **Secondary setups:** " + ", ".join(result["secondary"]))
    else:
        lines.append(f"- **Secondary setups:** (none)")
    if result["avoid"]:
        lines.append(f"- **Setups to avoid:** " + ", ".join(result["avoid"]))
    else:
        lines.append(f"- **Setups to avoid:** (none)")
    lines.append("")
    lines.append("## Raw Setup Frequency (last lookback window)")
    lines.append("")
    for setup, count in result["raw_counts"].most_common():
        lines.append(f"- {setup}: {count}")
    lines.append("")

    output = "\n".join(lines)

    # Print to terminal
    print(output)

    # Save to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\nPrediction written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
