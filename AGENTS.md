# AGENTS.md

Canonical brief for any agent working on this repo. Read this first. Deep
details live in `docs/agent/` so you can load only the section you need.

## Project

**mtg-scrape** — daily Magic: The Gathering card-price archive for a
long-horizon data-science project. Ingests MTGJSON + Scryfall bulk data,
normalizes prices to date-partitioned Parquet on S3, runs on GitHub Actions,
and is analyzed with Quarto + R.

**Status.** Live. 64.9M rows seeded across 89 date partitions on
`s3://mtg-scrape-unwindgames/`. Daily cron at 03:30 UTC pulls new data.

## Orient in 30 seconds

```
src/           Python data-engineering library (ingest, normalize, write)
scripts/       Python one-shots (backfill, scryfall bulk, compact)
.github/       workflows: ingest.yml (cron), backfill.yml, compact.yml
analysis/      Quarto .qmd analyses
R/             Reusable R code (theme_mtg, palettes)
infra/         AWS setup runbook
docs/agent/    Agent-oriented deep docs (this directory)
```

Full file-by-file map: **`docs/agent/tour.md`**.

## Working on this repo — quick rules

- **Python for engineering; R/tidyverse+tidymodels for analysis.**
- **Quarto wraps every analysis.** Don't scaffold plain `.R` files.
- **ggplot only.** Use `theme_mtg()` from `R/theme.R` (Tufte-inspired).
- **Pick the best tool per job** regardless of language. DuckDB works from
  either side and is often the right answer.
- **No silent failures.** If a tool call might no-op under misconfiguration
  (see the IAM `DeleteObject` postmortem in `docs/agent/gotchas.md`), have
  it raise — silent success is worse than a crash.
- **No bonus refactors.** Surgical changes only. See `docs/agent/invariants.md`.

Full conventions: **`docs/agent/conventions.md`**.

## Before changing anything — check

1. **Conventions** — `docs/agent/conventions.md` — language choice, style,
   the Quarto/ggplot/Tufte triad.
2. **Invariants** — `docs/agent/invariants.md` — never-break rules (TOS,
   idempotency, surgical-fix, etc.).
3. **Gotchas** — `docs/agent/gotchas.md` — landmines we've already stepped
   on. Read if you're touching S3, the compactor, or MTGJSON.

## Common tasks (recipes)

Playbooks live in **`docs/agent/playbooks.md`**. Index:

- Add a new ingest source
- Add a new Quarto analysis
- Run the compactor manually
- Debug a failed GitHub Actions run
- Change the S3 schema
- Rotate / update AWS credentials

## Stack

- **Runtime.** GitHub Actions (Python 3.12, `ubuntu-latest`)
- **Auth.** AWS via GitHub OIDC (no long-lived keys)
- **Storage.** S3 `mtg-scrape-unwindgames` in `us-east-1`
- **Format.** Parquet (zstd), partitioned by `dt=YYYY-MM-DD`
- **Python.** pyarrow, boto3, ijson, requests
- **R.** arrow, dplyr, ggplot2, scales, lubridate, tidymodels (planned)
- **Docs.** Quarto 1.8+

## External facts that matter

- **MTGJSON AllPrices has a 90-day rolling window.** Older data is not
  recoverable from the source — this archive is irreplaceable once the
  window advances. Daily ingest is load-bearing.
- **TCGplayer & Cardmarket APIs are closed to new applicants.** Do not
  scaffold code that assumes we can obtain them.
- **Scryfall metadata is CC0; prices are upstream (TCGplayer/Cardmarket)
  and inherit those TOS.** Keep that in mind before publishing derivatives.

## Verifying work

After any change touching ingest/writer/compactor, verify:

```bash
python3 -m py_compile src/*.py scripts/*.py  # smoke
```

After any S3-affecting workflow run:

```bash
aws s3 ls s3://mtg-scrape-unwindgames/prices/ --recursive --summarize | tail -3
```

After any Quarto/R change:

```bash
quarto render analysis/<file>.qmd
```

## Where to put new things

| New thing                              | Location                 |
|----------------------------------------|--------------------------|
| Python ingest source                   | `scripts/<source>.py` + workflow job |
| Python normalization / writer change   | `src/<module>.py`        |
| R analysis                             | `analysis/NN_topic.qmd`  |
| R reusable helper                      | `R/<helper>.R`           |
| AWS config / runbook step              | `infra/aws-setup.md`     |
| Agent guidance (rules, playbooks)      | `docs/agent/<topic>.md`  |
| Human doc / prose                      | extend `README.md`       |

## How human and agent docs relate

**Agent docs are the source of truth.** `README.md` is a human-readable
skin that points into these docs for depth. When information diverges,
trust the agent doc and update the README.
