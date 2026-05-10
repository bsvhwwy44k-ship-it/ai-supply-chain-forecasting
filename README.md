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
Merges forecast data (by planning cycle) with actuals:
- Identifies latest planning cycle automatically
- Computes delta in absolute, percentage, and basis points
- Generates multi-metric comparison charts
- Supports multiple forecast overlays on single chart

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
