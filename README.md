# mtg-scrape

Daily MTG price archive. Pulls MTGJSON + Scryfall bulk data, normalizes
prices to long-form Parquet, stages everything to S3. Runs on GitHub
Actions; costs about a dollar a month.

## Layout

```
src/
  config.py          — env-driven settings
  schema.py          — pyarrow schema for the prices fact table
  mtgjson_client.py  — HTTP client (Meta + streaming downloads)
  s3_util.py         — put/head/stream helpers
  normalize.py       — streaming JSON → long-form rows (ijson)
  writer.py          — batched Parquet writer, date-partitioned
  ingest.py          — daily driver: AllPricesToday → S3

scripts/
  backfill.py            — one-shot: 90-day AllPrices seed
  scryfall_bulk.py       — daily Scryfall default_cards → S3 raw
  allprintings_parquet.py— daily MTGJSON card dimension (native Parquet)

.github/workflows/
  ingest.yml    — daily cron @ 03:30 UTC (prices + printings + scryfall)
  backfill.yml  — manual workflow_dispatch to seed 90 days

infra/aws-setup.md — one-time AWS setup (bucket, IAM, OIDC)
notebooks/explore.R — starter R analysis over S3 Parquet
```

## S3 layout

```
s3://mtg-scrape-unwindgames/
├── prices/dt=YYYY-MM-DD/part-HHMMSS.parquet    ← normalized fact table
├── raw/mtgjson/dt=YYYY-MM-DD/AllPricesToday.json.xz
├── raw/mtgjson/dt=YYYY-MM-DD/AllPrintingsParquetFiles.tar.xz
├── raw/scryfall/default_cards/dt=YYYY-MM-DD/default_cards.json
├── dimension/mtgjson/allprintings/dt=YYYY-MM-DD/*.parquet
└── state/mtgjson/{AllPricesToday,AllPrices,AllPrintingsParquet}/VERSION-DATE.json
```

## Fact schema (`prices/`)

| column           | type   | notes                                   |
|------------------|--------|-----------------------------------------|
| card_uuid        | string | MTGJSON UUID (primary join key)         |
| date             | date32 | price observation date                  |
| game             | dict   | paper / mtgo                            |
| vendor           | dict   | tcgplayer, cardmarket, cardkingdom, cardsphere, cardhoarder |
| finish           | dict   | normal / foil / etched                  |
| kind             | dict   | retail / buylist                        |
| currency         | dict   | USD / EUR / TIX (derived from vendor)   |
| price            | float64 |                                        |
| mtgjson_version  | string | provenance, e.g. "5.2.3"                |

## Quickstart

1. Do [infra/aws-setup.md](infra/aws-setup.md) once.
2. Push this repo to GitHub. Add repo secret `AWS_ROLE_ARN` and repo
   variables `MTG_S3_BUCKET`, `AWS_REGION`.
3. Actions tab → **backfill** → Run workflow. Seeds 90 days.
4. Daily cron takes over tomorrow at 03:30 UTC.

## Local dev

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MTG_S3_BUCKET=mtg-scrape-unwindgames
export AWS_REGION=us-east-1
python -m scripts.backfill   # or -m src.ingest
```

## Querying

- **Python:** `pyarrow.dataset.dataset("s3://.../prices/")` then `.to_table()`.
- **R:** see `notebooks/explore.R`.
- **DuckDB:** `SELECT * FROM 's3://.../prices/*/*.parquet' LIMIT 10;`
- **Athena:** point a Glue crawler at `s3://.../prices/` (partition keys: `dt`).
