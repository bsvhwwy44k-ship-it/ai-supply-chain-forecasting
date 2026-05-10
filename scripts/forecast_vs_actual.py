#!/usr/bin/env python3
"""Forecast vs Actual Comparison.

Compares multiple planning cycle forecasts against actuals,
quantifies beat/miss in bps, and decomposes variance into drivers.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def load_data(filepath):
    return pd.read_csv(filepath)


def parse_week(date_str):
    """Parse YYYY-WW format to datetime."""
    date_str = str(date_str).strip()
    year, week = date_str.split("-")
    return pd.to_datetime(f"{year}-W{int(week):02d}-1", format="%G-W%V-%w")


def prepare_data(forecast_df, actual_df, target_week, planning_cycle=None):
    """Merge forecast and actual data for comparison."""
    if planning_cycle is None:
        max_creation = forecast_df.loc[forecast_df["creation_date"].idxmax(), "planning_cycle"]
        planning_cycle = max_creation
        print(f"Using latest planning cycle: {planning_cycle}")

    forecast_df = forecast_df[forecast_df["planning_cycle"] == planning_cycle].copy()

    forecast_df["week_dt"] = forecast_df["year_week"].apply(parse_week)
    actual_df["week_dt"] = actual_df["snapshot_day"].apply(parse_week)

    forecast_pivot = forecast_df.pivot(index="week_dt", columns="metric", values="value")
    actual_pivot = actual_df.pivot(index="week_dt", columns="metric", values="value")

    common_metrics = list(set(forecast_pivot.columns) & set(actual_pivot.columns))
    if not common_metrics:
        raise ValueError("No common metrics between forecast and actual data")

    merged = {}
    for metric in common_metrics:
        combined = pd.DataFrame({
            "forecast": forecast_pivot[metric],
            "actual": actual_pivot[metric],
        }).dropna()
        if len(combined) > 0:
            merged[metric] = combined

    return merged, parse_week(target_week), common_metrics, planning_cycle


def compute_accuracy(merged, target_week_dt):
    """Compute forecast accuracy metrics for target week."""
    results = {"metrics": {}}

    for metric, data in merged.items():
        if target_week_dt not in data.index:
            continue
        forecast_val = data.loc[target_week_dt, "forecast"]
        actual_val = data.loc[target_week_dt, "actual"]
        delta = actual_val - forecast_val

        results["metrics"][metric] = {
            "forecast": float(forecast_val),
            "actual": float(actual_val),
            "delta": float(delta),
            "delta_bps": int(delta * 10000),
            "pct_error": float((delta / actual_val * 100) if actual_val != 0 else np.inf),
            "beat_or_miss": "beat" if delta > 0 else "miss",
        }

        # Trailing accuracy (MAPE over available history)
        history = data[data.index <= target_week_dt].tail(10)
        if len(history) > 1:
            mape = (abs(history["actual"] - history["forecast"]) / history["actual"]).mean() * 100
            bias = (history["actual"] - history["forecast"]).mean()
            results["metrics"][metric]["trailing_mape"] = float(mape)
            results["metrics"][metric]["trailing_bias"] = float(bias)
            results["metrics"][metric]["bias_direction"] = "under-forecast" if bias > 0 else "over-forecast"

    return results


def generate_comparison_chart(merged, target_week_dt, planning_cycle, output_dir):
    """Generate forecast vs actual multi-metric chart."""
    metrics = list(merged.keys())
    n = len(metrics)
    if n == 0:
        return

    n_cols = min(3, n)
    n_rows = (n + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 4 * n_rows))

    if n == 1:
        axes = [axes]
    elif n_rows == 1:
        axes = list(axes) if n > 1 else [axes]
    else:
        axes = axes.flatten()

    for i, metric in enumerate(sorted(metrics)):
        ax = axes[i]
        data = merged[metric].sort_index()

        ax.plot(data.index, data["actual"], "b-", linewidth=2, label="Actual", alpha=0.8)
        ax.plot(data.index, data["forecast"], "r--", linewidth=2, label="Forecast", alpha=0.8)
        ax.axvline(x=target_week_dt, color="gray", linestyle=":", alpha=0.7)

        ax.set_title(metric, fontsize=11, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", rotation=45)

    for i in range(len(metrics), len(axes)):
        axes[i].set_visible(False)

    plt.suptitle(f"Forecast vs Actual — {planning_cycle}", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/forecast_vs_actual.png", dpi=150, bbox_inches="tight")
    plt.close()


def generate_plan_over_plan(forecast_df, actual_df, output_dir):
    """Compare forecasts across planning cycles for the target metric."""
    target_metric = forecast_df["metric"].value_counts().idxmax()

    fig, ax = plt.subplots(figsize=(14, 6))

    # Actuals
    actuals = actual_df[actual_df["metric"] == target_metric].copy()
    actuals["week_dt"] = actuals["snapshot_day"].apply(parse_week)
    actuals = actuals.sort_values("week_dt")
    ax.plot(actuals["week_dt"], actuals["value"], "b-", linewidth=2.5, label="Actual", alpha=0.9)

    # Each planning cycle
    colors = ["red", "orange", "green", "purple", "brown"]
    cycles = forecast_df["planning_cycle"].unique()
    for i, cycle in enumerate(cycles):
        cycle_data = forecast_df[
            (forecast_df["planning_cycle"] == cycle) & (forecast_df["metric"] == target_metric)
        ].copy()
        cycle_data["week_dt"] = cycle_data["year_week"].apply(parse_week)
        cycle_data = cycle_data.sort_values("week_dt")
        color = colors[i % len(colors)]
        ax.plot(cycle_data["week_dt"], cycle_data["value"], "--", color=color,
                linewidth=1.8, label=f"Plan: {cycle}", alpha=0.8)

    ax.set_title(f"{target_metric} — Plan over Plan", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/plan_over_plan.png", dpi=150, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Forecast vs Actual comparison")
    parser.add_argument("forecast_file", help="CSV: year_week, planning_cycle, creation_date, metric, value")
    parser.add_argument("actual_file", help="CSV: metric, snapshot_day (YYYY-WW), value")
    parser.add_argument("week", help="Target week (YYYY-WW)")
    parser.add_argument("--planning-cycle", help="Specific planning cycle (default: latest)")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    forecast_df = load_data(args.forecast_file)
    actual_df = load_data(args.actual_file)

    merged, target_week_dt, common_metrics, cycle = prepare_data(
        forecast_df, actual_df, args.week, args.planning_cycle
    )

    # Accuracy report
    results = compute_accuracy(merged, target_week_dt)
    results["target_week"] = args.week
    results["planning_cycle"] = cycle

    print(f"\n{'='*60}")
    print(f"FORECAST vs ACTUAL — {args.week} ({cycle})")
    print(f"{'='*60}")
    print(f"\n{'Metric':<35} {'Forecast':>10} {'Actual':>10} {'Delta':>10} {'Bps':>8}")
    print("-" * 75)
    for metric, d in sorted(results["metrics"].items()):
        print(f"{metric:<35} {d['forecast']:>10.4f} {d['actual']:>10.4f} {d['delta']:>+10.4f} {d['delta_bps']:>+8d}")
        if "trailing_mape" in d:
            print(f"{'':35} MAPE: {d['trailing_mape']:.1f}%  Bias: {d['bias_direction']}")
    print(f"{'='*60}\n")

    # Save JSON
    with open(output_dir / "forecast_comparison.json", "w") as f:
        json.dump(results, f, indent=2)

    # Generate charts
    generate_comparison_chart(merged, target_week_dt, cycle, output_dir)
    generate_plan_over_plan(forecast_df, actual_df, output_dir)

    print(f"Outputs: {output_dir}/forecast_comparison.json")
    print(f"         {output_dir}/forecast_vs_actual.png")
    print(f"         {output_dir}/plan_over_plan.png")


if __name__ == "__main__":
    main()
