# Context — why this repo exists

## The problem

Magic: The Gathering card prices are a rich economic time series, but no
public multi-year per-printing daily panel exists. The de-facto canonical
feeds cap out at 90 days (MTGJSON `AllPrices`) or 24 hours (Scryfall
bulk). Commercial APIs that would fill the gap (TCGplayer, Cardmarket)
are closed to new applicants as of 2026.

**Every day the archive isn't running is a day of history that cannot
be recovered.** This is the single most important fact about the project.

## The goal

Operate a reliable daily archive that accumulates a long-horizon
per-printing Parquet panel of MTG card prices, suitable for:

- reprint-shock event studies
- cross-vendor spread modeling (TCGplayer vs Cardmarket vs Card Kingdom)
- reserved-list / scarcity feature engineering
- format-rotation and banlist effects

## Downstream use

A data-science project on price trends. Tooling split:

- **Engineering** — Python, running on GitHub Actions, staging to S3.
- **Analysis** — R tidyverse + tidymodels, wrapped in Quarto (`.qmd`).
- **Graphics** — ggplot2 with a Tufte-inspired `theme_mtg()`.

See `conventions.md` for the full stack.

## Out of scope (explicitly)

- A public website / API on top of the data (TOS concerns).
- Real-time / intra-day pricing (MTGJSON rebuilds once/day).
- Redistributing scraped TCGplayer or Cardmarket data publicly.
- Collection-tracking features (not the use case).

## Origin research

The full landscape review that informed this design is in
`MEMORY/WORK/20260416-000000_mtg-price-trends-research/PRD.md`. Key
findings summarized in `AGENTS.md`.
