#!/usr/bin/env python3
"""Metric Driver Analysis.

Decomposes a target ratio metric into driver contributions using
linear regression with automatic correlated-feature removal.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def load_and_pivot(filepath: str, output_metric: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df = df.sort_values(["metric", "snapshot_day"])

    assert df.duplicated(subset=["metric", "snapshot_day"]).sum() == 0, "Duplicate entries found"

    df_pivot = df.pivot(index="snapshot_day", columns="metric", values="value")

    if output_metric not in df_pivot.columns:
        print(f"Available metrics: {list(df_pivot.columns)}", file=sys.stderr)
        raise ValueError(f"Output metric '{output_metric}' not found")

    return df_pivot


def remove_correlated(df: pd.DataFrame, output_metric: str, threshold: float = 0.8) -> list[str]:
    input_cols = [c for c in df.columns if c != output_metric]

    # Remove high-missing columns
    input_cols = [c for c in input_cols if df[c].isna().mean() < 0.5]

    remaining = input_cols.copy()
    while True:
        corr = df[remaining].corr().abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        max_corr = upper.max().max()

        if pd.isna(max_corr) or max_corr <= threshold:
            break

        idx = np.where(upper == max_corr)
        f1, f2 = remaining[idx[0][0]], remaining[idx[1][0]]

        # Keep the one more correlated with output
        c1 = abs(df[f1].corr(df[output_metric]))
        c2 = abs(df[f2].corr(df[output_metric]))
        drop = f2 if c1 >= c2 else f1
        remaining.remove(drop)

    return remaining


def analyze(df: pd.DataFrame, output_metric: str, target_week: str, features: list[str]):
    df_clean = df[[output_metric] + features].dropna()
    X = df_clean[features]
    y = df_clean[output_metric]

    model = LinearRegression()
    model.fit(X, y)

    print(f"\nR² = {model.score(X, y):.4f}")
    print(f"Intercept = {model.intercept_:.6f}\n")

    # Contributions for target week
    if target_week in df_clean.index:
        means = X.mean()
        print(f"{'Feature':<40} {'Coef':>12} {'Deviation':>12} {'Contribution':>14}")
        print("-" * 80)

        contributions = []
        for i, feat in enumerate(features):
            val = df_clean.loc[target_week, feat]
            dev = val - means[feat]
            contrib = model.coef_[i] * dev
            contributions.append((feat, model.coef_[i], dev, contrib))

        contributions.sort(key=lambda x: abs(x[3]), reverse=True)
        total = 0
        for feat, coef, dev, contrib in contributions:
            print(f"{feat:<40} {coef:>12.6f} {dev:>+12.6f} {contrib:>+14.6f}")
            total += contrib

        print("-" * 80)
        print(f"{'Total':<40} {'':>12} {'':>12} {total:>+14.6f}")
        print(f"{'Predicted':<40} {'':>12} {'':>12} {model.intercept_ + total:>+14.6f}")
        print(f"{'Actual':<40} {'':>12} {'':>12} {df_clean.loc[target_week, output_metric]:>+14.6f}")
    else:
        print(f"Target week '{target_week}' not found in data.")
        print(f"Available: {list(df_clean.index[-10:])}")


def main():
    parser = argparse.ArgumentParser(description="Metric driver decomposition")
    parser.add_argument("filepath", help="CSV with columns: metric, snapshot_day, value")
    parser.add_argument("output_metric", help="Target metric to decompose")
    parser.add_argument("week", help="Target week (as it appears in snapshot_day)")
    parser.add_argument("--threshold", type=float, default=0.8, help="Correlation removal threshold")
    parser.add_argument("--features", nargs="+", help="Specific features to use")
    args = parser.parse_args()

    df = load_and_pivot(args.filepath, args.output_metric)

    if args.features:
        features = [f for f in args.features if f in df.columns]
    else:
        features = remove_correlated(df, args.output_metric, args.threshold)

    print(f"Target: {args.output_metric}")
    print(f"Features ({len(features)}): {', '.join(features)}")

    analyze(df, args.output_metric, args.week, features)


if __name__ == "__main__":
    main()
