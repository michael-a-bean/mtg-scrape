# Playbooks

Recipes for common tasks. Each follows the same shape: **when**,
**steps**, **verify**.

## Add a new ingest source

**When.** A new bulk source is available (another MTGJSON file,
17Lands public datasets, EDHREC exports, Scrydex API, etc).

**Steps.**
1. Create `scripts/<source>_ingest.py` in Python. Pattern: idempotency
   check → streaming download → normalize (if needed) → write Parquet
   or stage raw → state marker.
2. If it produces a fact table (rows joinable on `card_uuid`), add the
   schema to `src/schema.py` and the writer path to `src/writer.py`.
3. If it's a dimension, stage as-is under `dimension/<source>/dt=.../`.
4. Add a job to `.github/workflows/ingest.yml` that calls the script.
5. Update `docs/agent/tour.md` with the new file.

**Verify.**
- `python3 -m py_compile scripts/<source>_ingest.py`
- Run the script locally with env vars set, or use
  `gh workflow run ingest.yml` and watch the job.
- `aws s3 ls s3://mtg-scrape-unwindgames/<new_prefix>/ --recursive | head`

## Add a new Quarto analysis

**When.** A new question about the data warrants its own document.

**Steps.**
1. Pick the next number: `analysis/NN_topic.qmd`.
2. Start from `analysis/01_explore.qmd` as a template.
3. `#| include: false` setup chunk sources `R/theme.R`.
4. Use `arrow::open_dataset` for S3 Parquet; `collect()` late.
5. Every figure gets `#| fig.cap`. Use `theme_mtg()`.
6. Document any new R dependencies in the README's package list.

**Verify.**
- `quarto render analysis/NN_topic.qmd`
- Output HTML should render without errors and include all figures.

## Run the compactor manually

**When.** After a backfill, after a bug in the writer that produced
multi-file partitions, or on a schedule if we decide to add one.

**Steps.**
1. `gh workflow run compact.yml --ref main -f dry_run=true` (dry run
   first — always).
2. Inspect the dry-run log: `gh run view <id> --log | grep "would compact"`
3. If sane: `gh workflow run compact.yml --ref main -f dry_run=false`.
4. Watch: `gh run watch <id>`.

**Verify.**
```bash
aws s3 ls s3://mtg-scrape-unwindgames/prices/ --recursive \
  | grep -c '\.parquet$'
# Should equal the number of date partitions (89 for a freshly-seeded
# 90-day window).
```

## Debug a failed GitHub Actions run

**When.** GitHub emails you about a failed workflow or a cron didn't
deliver.

**Steps.**
1. `gh run list --workflow=<name>.yml --limit 5`
2. `gh run view <id> --log-failed` — shows only failed step logs.
3. Common failure classes:
   - **AccessDenied** — IAM permission missing. Cross-reference
     `infra/aws-setup.md`; patch with `aws iam put-role-policy`.
   - **MTGJSON 404** — bulk file naming changed. Check
     https://mtgjson.com/downloads/all-files/.
   - **Lambda 15-min timeout** — doesn't apply (we use Actions, 60-min
     job timeout). If Actions hits 60-min, split into stages.
   - **pyarrow schema mismatch** — upstream added a new vendor/finish.
     Update `src/schema.py` and `src/normalize.py`.

**Verify.**
- Re-run the workflow manually: `gh workflow run <name>.yml --ref main`.
- Confirm it completes and the state marker is written.

## Change the S3 schema

**When.** Adding a column (e.g., `provider_version`), adjusting a type,
or splitting a field.

**Steps.**
1. Edit `src/schema.py` — update `PRICES_SCHEMA`.
2. Edit `src/normalize.py` — emit the new column in `iter_price_rows`.
3. Existing partitions still have the old schema. Decide:
   - **Forward-only** — new partitions have the new column; `arrow`
     readers will set old columns to null on the new fields.
   - **Rewrite all** — run a migration that reads every partition and
     writes a new one with the new schema. Implement as
     `scripts/migrate_<change>.py`.
4. Update `R/theme.R` / analysis docs if the change affects plots.

**Verify.**
- New daily run produces the new column.
- `arrow::open_dataset()` reads across both old and new partitions
  without error (it will fill nulls on the gap).

## Rotate / update AWS credentials

**When.** Moving off the root-user keys to an IAM user, or rotating.

**Steps.**
1. Create new IAM user with minimal policy (same as the workflow role).
2. Issue access key for that user.
3. Update local `~/.aws/credentials` with the new key.
4. The GitHub Actions role is OIDC-based and doesn't need rotation —
   only the local dev creds do.
5. Disable and delete the old root access key.

**Verify.**
- `aws sts get-caller-identity` shows the new user ARN (no longer root).
- Existing workflow runs still succeed (OIDC unaffected).

## Add a new AWS region (only if truly needed)

**When.** Rarely — only if data-gravity drives the choice (e.g., moving
the analysis compute to EU).

**Steps.**
1. Create bucket in new region.
2. Consider whether to replicate existing data (S3 Cross-Region
   Replication) or start fresh.
3. Update `AWS_REGION` repo variable to new region.
4. Update IAM policy ARNs if bucket name changed.
5. Update `src/config.py` default.

**Verify.** Run a daily ingest to confirm end-to-end.

## Investigate a row-count discrepancy

**When.** An analysis surfaces a partition with unexpectedly low/high
row count.

**Steps.**
1. Read raw source: `aws s3 cp
   s3://mtg-scrape-unwindgames/raw/mtgjson/dt=<date>/AllPrices*.json.xz -`
2. Count rows directly in Python: load via `ijson`, count yielded rows.
3. Compare against the state marker:
   `aws s3 cp s3://.../state/mtgjson/AllPrices/<ver>-<date>.json -`
4. Compare against the Parquet: `duckdb -c "SELECT COUNT(*) FROM
   's3://mtg-scrape-unwindgames/prices/dt=<date>/*.parquet'"`

**Verify.** Discrepancies >0.1% warrant investigation; <0.1% is likely
floating-point / counter drift (see gotchas).
