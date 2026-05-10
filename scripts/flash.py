#!/usr/bin/env python3
"""Weekly Flash Analyzer.

Reads actuals and regional CSVs from data/, computes WoW and YoY
bridging for ratio metrics, and outputs a Markdown report.
"""

import argparse
import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
REPORTS_DIR = SCRIPT_DIR.parent / "reports"


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def compute_ratio(num: float, denom: float) -> float | None:
    if denom == 0:
        return None
    return num / denom


def format_val(val: float | None, is_pct: bool = False) -> str:
    if val is None:
        return "-"
    if is_pct:
        return f"{val * 100:.2f}%"
    return f"{val:.4f}"


def format_delta(current: float | None, prior: float | None, is_pct: bool = False) -> str:
    if current is None or prior is None:
        return "-"
    delta = current - prior
    if is_pct:
        return f"{'+' if delta >= 0 else ''}{delta * 100:.2f}pp"
    return f"{'+' if delta >= 0 else ''}{delta:.4f}"


def format_delta_pct(current: float | None, prior: float | None) -> str:
    if current is None or prior is None or prior == 0:
        return "-"
    pct = (current - prior) / abs(prior) * 100
    return f"{'+' if pct >= 0 else ''}{pct:.1f}%"


def aggregate_by_week(rows: list[dict]) -> dict:
    """Aggregate by (year, week, metric) -> (numerator, denominator)."""
    agg = defaultdict(lambda: [0.0, 0.0])
    for row in rows:
        year = (row.get("year") or row.get("YEAR") or "").strip()
        week = (row.get("week") or row.get("WEEK") or "").strip().zfill(2)
        metric = (row.get("metric") or row.get("METRIC") or "").strip()
        if not year or not week or not metric:
            continue
        num = float(row.get("numerator") or row.get("NUMERATOR") or 0)
        denom = float(row.get("denominator") or row.get("DENOMINATOR") or 0)
        agg[(year, week, metric)][0] += num
        agg[(year, week, metric)][1] += denom
    return agg


def bridging_table(agg: dict, target_year: str, target_week: str, metrics: list[str]) -> list[dict]:
    tw = int(target_week)
    ty = int(target_year)
    prior_week = str(tw - 1).zfill(2) if tw > 1 else "52"
    prior_week_year = target_year if tw > 1 else str(ty - 1)
    yoy_year = str(ty - 1)

    results = []
    for metric in metrics:
        is_pct = metric.startswith("%")
        curr = agg.get((target_year, target_week, metric))
        wow_prior = agg.get((prior_week_year, prior_week, metric))
        yoy_prior = agg.get((yoy_year, target_week, metric))

        curr_val = compute_ratio(curr[0], curr[1]) if curr else None
        wow_val = compute_ratio(wow_prior[0], wow_prior[1]) if wow_prior else None
        yoy_val = compute_ratio(yoy_prior[0], yoy_prior[1]) if yoy_prior else None

        results.append({
            "metric": metric,
            "current": format_val(curr_val, is_pct),
            "wow_prior": format_val(wow_val, is_pct),
            "wow_delta": format_delta(curr_val, wow_val, is_pct),
            "wow_pct": format_delta_pct(curr_val, wow_val),
            "yoy_prior": format_val(yoy_val, is_pct),
            "yoy_delta": format_delta(curr_val, yoy_val, is_pct),
            "yoy_pct": format_delta_pct(curr_val, yoy_val),
        })
    return results


def md_table(headers: list[str], rows: list[dict], keys: list[str]) -> str:
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(k, "-")) for k in keys) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate Weekly Flash bridging report")
    parser.add_argument("--week", type=int, required=True, help="ISO week number")
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--metrics", nargs="+", default=["Units/Box", "Units/Purchase", "Shipped Units"])
    parser.add_argument("--input", type=Path, required=True, help="Path to actuals CSV")
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()

    target_year = str(args.year)
    target_week = str(args.week).zfill(2)

    rows = load_csv(args.input)
    agg = aggregate_by_week(rows)
    results = bridging_table(agg, target_year, target_week, args.metrics)

    headers = ["Metric", f"WK{target_week}", f"WK{int(target_week)-1}", "WoW Δ", "WoW %", f"WK{target_week} LY", "YoY Δ", "YoY %"]
    keys = ["metric", "current", "wow_prior", "wow_delta", "wow_pct", "yoy_prior", "yoy_delta", "yoy_pct"]

    report = f"# Weekly Flash - WK{target_week} {target_year}\n\n"
    report += f"Generated: {date.today().isoformat()}\n\n"
    report += md_table(headers, results, keys) + "\n"

    if args.stdout:
        print(report)
    else:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        out = REPORTS_DIR / f"flash_wk{target_week}_{target_year}.md"
        out.write_text(report)
        print(f"Report: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
