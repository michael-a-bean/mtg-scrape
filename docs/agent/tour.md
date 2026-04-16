# Tour — file-by-file map

## `src/` — Python data-engineering library

| File                | Purpose                                                  |
|---------------------|----------------------------------------------------------|
| `config.py`         | Env-driven settings (`MTG_S3_BUCKET`, `AWS_REGION`, provider constants). |
| `schema.py`         | pyarrow `PRICES_SCHEMA` + `VENDOR_CURRENCY` map.         |
| `mtgjson_client.py` | Thin HTTP client: `get_meta()` + `stream_download()` for `.xz` bulk files. |
| `s3_util.py`        | boto3 helpers — `exists`, `put_bytes`, `put_json`, `stream_to_s3`. |
| `normalize.py`      | `iter_price_rows()` — ijson streaming parse of AllPrices JSON → flat dicts. `open_xz()` helper. |
| `writer.py`         | `write_partitioned()` — one `ParquetWriter` per date, spilled to local temp, uploaded at end. **Produces exactly one file per date.** |
| `ingest.py`         | Daily driver: Meta-check idempotency → download `AllPricesToday.json.xz` → normalize → write → state marker. |

## `scripts/` — Python one-shots

| File                         | Purpose                                            |
|------------------------------|----------------------------------------------------|
| `backfill.py`                | One-shot 90-day seed: pulls `AllPrices.json.xz`, explodes 90 dates into partitioned Parquet. Run manually via backfill workflow. |
| `scryfall_bulk.py`           | Stages Scryfall `default_cards` JSON to S3 as-is.  |
| `allprintings_parquet.py`    | Downloads MTGJSON `AllPrintingsParquetFiles.tar.xz`, stages raw, then extracts per-table `.parquet` files under `dimension/mtgjson/allprintings/`. |
| `compact.py`                 | Merges multi-file date partitions into one compacted Parquet per date. Idempotent. Raises on delete errors (load-bearing — see gotchas). |

## `.github/workflows/`

| File           | Trigger                        | What it does                  |
|----------------|--------------------------------|-------------------------------|
| `ingest.yml`   | `cron: 30 3 * * *` + manual    | Three parallel jobs: MTGJSON prices, MTGJSON printings Parquet, Scryfall bulk. |
| `backfill.yml` | `workflow_dispatch` only       | Runs `scripts/backfill.py`.   |
| `compact.yml`  | `workflow_dispatch` + inputs   | Runs `scripts/compact.py` with optional `--dt` and `--dry-run`. |

All workflows authenticate to AWS via OIDC against the
`mtg-scrape-ingest` IAM role.

## `analysis/` — Quarto analyses

| File               | Purpose                                            |
|--------------------|----------------------------------------------------|
| `01_explore.qmd`   | First exploration — reads Parquet via `arrow::open_dataset`, shows vendor distribution, daily volume, top-20 trajectories. |

Planned (not yet written):
- `02_card_dimension.qmd` — join AllPrintings dimension (rarity, set, color, Reserved List).
- `03_volatility.qmd` — 7/30/90-day returns and cross-vendor dispersion.
- `04_reprint_shocks.qmd` — event study around reprint announcements.

## `R/` — reusable R code

| File       | Purpose                                                  |
|------------|----------------------------------------------------------|
| `theme.R`  | `theme_mtg()` Tufte-inspired ggplot theme; `mtg_palette` (WUBRG + colorless + gold); `scale_color_mtg`, `scale_fill_mtg`, `mtg_annotate`. |

Source via `source(here::here("R", "theme.R"))`.

## `infra/`

| File              | Purpose                                                |
|-------------------|--------------------------------------------------------|
| `aws-setup.md`    | Runbook for provisioning bucket + lifecycle + OIDC provider + IAM role. The live resources already exist — this is the reproduction recipe. |

## Project-level

| File                | Purpose                                             |
|---------------------|-----------------------------------------------------|
| `_quarto.yml`       | Quarto project config: cosmo theme, freeze cache, fig defaults. |
| `pyproject.toml`    | Python project metadata (not currently installed, informational). |
| `requirements.txt`  | Runtime Python deps for GitHub Actions runners.    |
| `README.md`         | Human entry point.                                  |
| `AGENTS.md`         | Canonical agent brief.                              |
| `CLAUDE.md`         | Claude Code shortcut.                               |
| `docs/agent/*.md`   | Agent deep docs (you are here).                    |

## S3 layout (live)

```
s3://mtg-scrape-unwindgames/
├── prices/dt=YYYY-MM-DD/part-compacted-YYYYMMDD-HHMMSS.parquet
│                         (or part-YYYYMMDD-HHMMSS.parquet pre-compaction)
├── raw/mtgjson/dt=YYYY-MM-DD/AllPricesToday.json.xz
├── raw/mtgjson/dt=YYYY-MM-DD/AllPrintingsParquetFiles.tar.xz
├── raw/scryfall/default_cards/dt=YYYY-MM-DD/default_cards.json
├── dimension/mtgjson/allprintings/dt=YYYY-MM-DD/*.parquet
└── state/mtgjson/{AllPrices,AllPricesToday,AllPrintingsParquet}/VERSION-DATE.json
```
