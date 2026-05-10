# Supply Chain Metrics Automation Framework

An AI-powered analytics workspace that automates weekly business review (WBR) generation for supply chain metrics. Built with Python, Claude Code, and Obsidian.

## What It Does

Transforms raw data exports into actionable weekly reports with:
- **Week-over-Week (WoW) bridging** across multiple regions and marketplaces
- **Year-over-Year (YoY) comparison** with proper ISO week alignment
- **Forecast vs Actuals analysis** with beat/miss quantification in basis points
- **Metric driver decomposition** using linear regression to attribute changes
- **Regional breakdown** with geographic visualization
- **Anomaly detection** on daily/weekly time series

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Data Sources                        │
│  S3 Data Lake  │  Data Warehouse  │  CSV Exports     │
└────────┬────────────────┬──────────────────┬─────────┘
         │                │                  │
         ▼                ▼                  ▼
┌─────────────────────────────────────────────────────┐
│              Python Analysis Layer                    │
│  • Query Preparation (parameterized SQL)             │
│  • Data Ingestion & Normalization                    │
│  • WoW/YoY Bridging Engine                          │
│  • Regression-based Driver Analysis                  │
│  • Forecast Comparison (multi-plan overlay)          │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              Output Layer                             │
│  • Markdown Reports (Obsidian-compatible)            │
│  • PDF Summaries with Charts                         │
│  • Regional Maps (matplotlib + shapefiles)           │
│  • Slide-ready Data Tables                           │
└─────────────────────────────────────────────────────┘
```

## Key Components

### 1. Bridging Engine (`scripts/flash.py`)
Computes WoW and YoY deltas for any ratio metric (numerator/denominator pattern). Handles:
- Multiple marketplace aggregation
- Regional decomposition
- Automatic date alignment (ISO weeks)
- Missing data graceful degradation

### 2. Forecast vs Actuals (`scripts/forecast_vs_actual.py`)
End-to-end forecast accuracy framework for supply chain metrics:
- **Multi-plan comparison** — overlay forecasts from different planning cycles (e.g., annual plan vs quarterly guidance vs latest estimate) on the same timeline
- **Beat/miss quantification** — delta in absolute, percentage, and basis points for each metric per week
- **Forecast accuracy tracking** — trailing N-week MAPE, bias detection (persistent over/under-forecast), accuracy trend
- **Planning cycle management** — auto-identifies latest forecast by creation date when multiple exist for the same target period
- **Driver-level forecast decomposition** — when a composite metric misses forecast, attributes the miss to specific input drivers (e.g., "inventory placement -160bps + consolidation -112bps = net UPB miss of -480bps")
- **Forward projection** — extracts future forecast horizon and flags weeks where forecast diverges from recent actuals trend

### 3. Metric Driver Analysis (`scripts/metric_driver_analysis.py`)
Linear regression decomposition of a target metric against its drivers:
- Automatic correlated feature removal (configurable threshold)
- Demeaned contribution calculation per time period
- Identifies which input metrics drove the change
- Generates 5 diagnostic plots (correlation heatmap, contributions over time, last 8 weeks, year-over-year by week, feature values)

### 4. Data Pipeline (`scripts/ingest.py`, `scripts/sync_s3.py`)
- Parameterized SQL query preparation with clipboard copy
- CSV ingestion with automatic naming and deduplication
- S3 bucket sync with date-based filtering
- Credential management via IAM temporary credentials

### 5. Knowledge Vault (Obsidian)
Structured markdown workspace:
- `Reflections/` — weekly learnings
- `Meetings/` — action items and decisions
- `Reports/` — generated flash reports
- `Data/` — ingested datasets
- `Hubs/` — project and stakeholder context

## Example Output

```markdown
# Weekly Flash - WK12 2025

## Network Bridging

| Metric | WK12 | WK11 | WoW Δ | WoW % | WK12 LY | YoY Δ | YoY % |
|--------|------|------|-------|-------|----------|-------|-------|
| Units/Box | 2.3412 | 2.3301 | +0.0111 | +0.5% | 2.2876 | +0.0536 | +2.3% |
| Units/Purchase | 3.0145 | 3.0098 | +0.0047 | +0.2% | 2.9512 | +0.0633 | +2.1% |

## Regional Performance

| Region | WK12 | WK11 | WoW Δ | WoW % |
|--------|------|------|-------|-------|
| Region A | 2.4510 | 2.4320 | +0.0190 | +0.8% |
| Region B | 2.2890 | 2.2740 | +0.0150 | +0.7% |
| Region C | 2.3100 | 2.3095 | +0.0005 | +0.0% |
| ... | ... | ... | ... | ... |
```

## Tech Stack

- **Python 3.11+** — pandas, numpy, matplotlib, scikit-learn, boto3
- **Claude Code** — AI orchestration layer (natural language → analysis)
- **Obsidian** — Knowledge management with WikiLinks
- **AWS** — S3 (data lake), Redshift (warehouse), IAM (auth)
- **Git** — Version control for queries and scripts

## Forecasting Capabilities

This framework was built by a Product Manager who owns the full forecasting lifecycle across multiple horizons — from weekly operational tracking through 3-year strategic planning.

### Forecast Horizons

| Horizon | Cadence | Purpose |
|---------|---------|---------|
| **Short-term** (1-8 weeks) | Weekly | Operational execution, WBR reporting, anomaly detection |
| **Mid-term** (1-4 quarters) | Quarterly | Guidance updates, resource planning, target-setting |
| **Long-term** (1-3 years) | Annual/Biannual | Strategic planning, capacity investment, goal-setting |

### Planning Cycle Management
Supply chain forecasts are produced at overlapping cadences: annual operating plans, quarterly guidance updates, transition plans, and weekly re-forecasts. This system:
- Tracks multiple concurrent forecasts for the same target period across all horizons
- Resolves "which forecast is current?" via creation date ordering
- Enables plan-over-plan comparison (how did our 3-year view change between annual plans?)
- Supports rolling forecast windows that shift each planning cycle

### Forecast Accuracy Framework
```
┌─────────────────────────────────────────────────┐
│          Forecast Accuracy Pipeline              │
│                                                  │
│  1. Ingest forecasts (by planning cycle)         │
│  2. Align with actuals (ISO week matching)       │
│  3. Compute miss: absolute, %, bps              │
│  4. Decompose miss into driver contributions     │
│  5. Identify bias (persistent direction)         │
│  6. Generate accuracy report + charts            │
└─────────────────────────────────────────────────┘
```

### Variance Decomposition
When a composite metric misses forecast, the system answers **"why did we miss?"** by:
1. Running regression of the composite metric against its N input drivers
2. Computing each driver's demeaned contribution for the miss week
3. Ranking drivers by contribution magnitude
4. Identifying whether the miss is structural (persistent) or episodic

Example output:
```
Driver Attribution for Metric Miss (-480 bps):
  Inventory Placement    -163 bps  (structural — missed 5 consecutive weeks)
  Consolidation Rate     -112 bps  (worsening trend)
  Purchase Composition   +517 bps  (tailwind, beating forecast)
  Order Splitting        +117 bps  (worse than plan, but helping metric)
  Net explained:         -479 bps
```

### Plan-over-Plan Tracking
Compares how forecasts evolve across planning cycles:
- Did the latest plan raise or lower the bar vs. prior plan?
- Which drivers changed between plans?
- Are we converging toward actuals or diverging?

### Forecast Horizon Monitoring
For the forward-looking portion of the active forecast:
- Flags weeks where forecast assumes improvement not supported by recent trend
- Identifies seasonal ramps that may need re-baselining
- Tracks forecast confidence band (distance from trailing actuals)

### Long-Range Forecast (3-Year)
For strategic planning horizons:
- Builds 3-year projections incorporating secular trends, seasonality, and program launches
- Decomposes long-range targets into quarterly glide paths
- Tracks annual plan vs quarterly guidance vs latest estimate convergence
- Supports "what-if" scenario modeling (e.g., new program impact, network expansion effects)
- Validates long-range assumptions against trailing actuals trend

---

## Design Principles

1. **Separate SQL from Python** — Queries live in `.sql` files, Python is the runner
2. **Date-stamped outputs** — Every run produces a new file; history accumulates
3. **No pandas for simple I/O** — `csv.writer` for lightweight CSV; pandas only for analysis
4. **Clipboard-first UX** — Query prep copies to clipboard for paste-into-query-tool workflow
5. **Graceful degradation** — Missing data shows "-" not errors; partial weeks still report
6. **Obsidian-native** — WikiLinks, full content preservation, markdown tables

## Getting Started

```bash
# Clone and install
git clone <this-repo>
cd supply-chain-metrics-automation
pip install -r scripts/requirements.txt

# List available queries
python scripts/run_query.py

# Prepare a query for week 18
python scripts/run_query.py actuals.sql --week 18 --copy

# Ingest results after running in your query tool
python scripts/ingest.py ~/Downloads/result.csv --tag wk18

# Generate flash report
python scripts/flash.py --week 18

# Run forecast comparison
python scripts/forecast_vs_actual.py data/forecast.csv data/actuals.csv 2026-18

# Run driver analysis
python scripts/metric_driver_analysis.py data/actuals.csv "Units/Box" 2026-18
```

## Author

Rakesh Sukumar — Supply Chain Analytics & AI/ML Automation

## License

MIT
