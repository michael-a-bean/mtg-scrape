# mtg-scrape

Daily Magic: The Gathering price archive. Pulls MTGJSON + Scryfall bulk
data, normalizes to partitioned Parquet on S3, runs on GitHub Actions.
Analysis in Quarto + R.

> **Working on the codebase?** Read [`AGENTS.md`](AGENTS.md) — it is the
> canonical brief for both human and agent contributors. This README is
> a skim-friendly entry point.

## Why

MTGJSON's `AllPrices` feed only retains 90 days; Scryfall prices go
stale after 24 hours; commercial APIs (TCGplayer, Cardmarket) are
closed to new applicants. **The only way to get a multi-year MTG price
panel is to start archiving daily — today.** That's the whole project.

## How it works

```
MTGJSON AllPricesToday.json.xz ──┐
MTGJSON AllPrintings (Parquet) ──┼─▶ GitHub Actions daily @03:30 UTC ─▶ S3
Scryfall default_cards.json ─────┘                                       │
                                                                         ▼
                                                              DuckDB / Athena / R arrow
                                                                         │
                                                                         ▼
                                                              Quarto analysis (analysis/*.qmd)
```

## Current state

- **S3 bucket:** `s3://mtg-scrape-unwindgames` (us-east-1)
- **Archive:** 64.9M price rows seeded across 89 date partitions
- **Cron:** daily at 03:30 UTC (active)
- **Analysis:** one starter Quarto doc (`analysis/01_explore.qmd`)

## Quickstart

### Query the archive

From R, with the `arrow` package:

```r
library(arrow); library(dplyr)
prices <- open_dataset(
  "s3://mtg-scrape-unwindgames/prices/?region=us-east-1",
  format = "parquet"
)
prices |> count(vendor, kind, finish) |> collect()
```

From the CLI, with DuckDB:

```bash
duckdb -c "SELECT COUNT(*) FROM 's3://mtg-scrape-unwindgames/prices/*/*.parquet';"
```

### Render the analysis

```bash
Rscript -e 'install.packages(c("arrow","dplyr","ggplot2","scales","lubridate","here"))'
quarto preview analysis/01_explore.qmd
```

### Run local Python ingest (optional)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MTG_S3_BUCKET=mtg-scrape-unwindgames AWS_REGION=us-east-1
python -m src.ingest             # daily: pulls AllPricesToday
python -m scripts.backfill       # one-shot: 90-day seed
```

## Repo layout

```
src/           Python data-engineering library
scripts/       Python one-shots (backfill, compact, scryfall, allprintings)
.github/       GitHub Actions workflows (ingest, backfill, compact)
analysis/      Quarto analyses (.qmd)
R/             Reusable R code (theme_mtg, palettes)
infra/         AWS setup runbook
docs/agent/    Deep agent docs (context, tour, conventions, invariants,
               playbooks, gotchas)
AGENTS.md      Canonical agent brief (start here if contributing)
CLAUDE.md      Claude Code shortcut (points to AGENTS.md)
```

## Philosophy

- **Python** for engineering; **R tidyverse/tidymodels** for analysis;
  **Quarto** wraps both. Pick the best tool per job — DuckDB is often
  the right answer from either side.
- **ggplot2 + Tufte-inspired** graphics via `theme_mtg()` in
  `R/theme.R`.
- **Agent-first docs.** `docs/agent/` is the source of truth; this
  README is a human-friendly skin over those docs.

## Deeper reading

- [`AGENTS.md`](AGENTS.md) — canonical brief for contributors
- [`docs/agent/context.md`](docs/agent/context.md) — why this project exists
- [`docs/agent/tour.md`](docs/agent/tour.md) — file-by-file map
- [`docs/agent/conventions.md`](docs/agent/conventions.md) — language, style, graphics preferences
- [`docs/agent/invariants.md`](docs/agent/invariants.md) — never-break rules with reasons
- [`docs/agent/playbooks.md`](docs/agent/playbooks.md) — common-task recipes
- [`docs/agent/gotchas.md`](docs/agent/gotchas.md) — landmines (with postmortems)
- [`infra/aws-setup.md`](infra/aws-setup.md) — AWS provisioning runbook
