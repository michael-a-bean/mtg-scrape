# Gotchas — known landmines

Things we've already stepped on, with enough detail for future-you to
recognize the same problem and fix it faster.

## 1. IAM `s3:DeleteObject` missing → silent no-op

**Symptom.** Compactor logs said `deleted N source files` for every
partition, run completed "successfully", but `aws s3 ls` showed the
source files still there.

**Root cause.** The initial IAM role policy (in `infra/aws-setup.md`)
had `PutObject`, `GetObject`, `HeadObject`, `ListBucket` — but no
`DeleteObject`. The `delete_objects` API returns HTTP 200 with per-key
`Errors` in the response body; boto3 does not raise by default. The
compactor's `Delete={"Objects": [...], "Quiet": True}` suppressed the
errors entirely, so the Python log said "done" while nothing was
deleted.

**Fix (live).** Added `s3:DeleteObject` to the role. Compactor now
raises if any key fails to delete (removed `Quiet=True`, inspects
`Errors`).

**Prevention.** Invariant #2 in `invariants.md` — never silently succeed
on misconfiguration. Any S3/IAM-adjacent operation must verify or raise.

## 2. Small-files explosion from the initial writer

**Symptom.** First backfill produced **23,131 Parquet files** across
89 date partitions — ~260 tiny (20 KiB) files per date. Data was
correct; layout was abysmal.

**Root cause.** Original `writer.py` accumulated rows in per-date
buffers in memory; when total in-memory rows crossed 250k, it flushed
**every** date bucket at once. With 90 dates filling in parallel, each
flush emitted 90 new files. Many flushes = 90 × many files.

**Fix (live).** Rewrote `writer.py` to open one
`pyarrow.parquet.ParquetWriter` per date, backed by a local temp file.
Row batches append to the per-date writer, which flushes to disk as
row groups fill. At end-of-stream, each temp file becomes exactly one
S3 object. Memory stays bounded via Parquet's own row-group flushing.

**Prevention.** Daily ingest has only one date, so it was never hit in
`ingest.py` — only in the 90-day backfill. If you add a new path that
writes multi-date batches, verify it produces one file per date.

## 3. MTGJSON 90-day rolling window

**Symptom.** (Hypothetical — the whole reason this project exists.)
You want a 2-year price panel and discover MTGJSON only has 90 days.

**Root cause.** MTGJSON's `AllPrices.json` is designed as a rolling
window for partners who archive their own history. Data older than
~90 days is dropped from the source file.

**Fix.** There is no fix. The archive must capture daily snapshots
from day one. This is why the project exists.

**Prevention.** Don't let the daily cron fail silently. Monitor
workflow success. If a day is missed, check whether re-running with
`--force` would recover it (yes if within the current window; no if
the window has advanced).

## 4. Row-count off-by-0.04% between writer and compactor

**Symptom.** Backfill's `state/mtgjson/AllPrices/...json` reported
`rows: 64,945,388`. Compactor read the same 23,131 files and counted
`64,921,597`. Delta: 23,791 rows (0.037%).

**Root cause.** Suspected — not confirmed. Leading hypothesis: the old
writer's `len(rows)` counter incremented per batch iteration in a way
that over-counted by a tiny factor at flush boundaries. Magnitude is
within noise; not load-bearing.

**Fix.** None. The Parquet files are the source of truth; the state
marker was informational. New writer uses `ParquetWriter.write_table`
exclusively, so future partitions will have exact counts.

**Prevention.** Don't trust the `state/*/rows` field for precise math.
If you need a count, query the Parquet directly (DuckDB or pyarrow).

## 5. GitHub Actions cron drift

**Symptom.** Scheduled run didn't fire at exactly 03:30 UTC.

**Root cause.** GitHub's documented behavior: scheduled workflows can
be delayed during high-load windows. Anecdotally, 03:30 UTC is a busy
window globally.

**Fix.** Not a bug. The daily archive is tolerant to 1-hour drift
because MTGJSON itself only rebuilds once per day. If strict timing
ever matters, switch to EventBridge + Lambda.

**Prevention.** Don't rely on precise cron timing for anything in this
project.

## 6. Quarto + `arrow` S3 URL format

**Symptom.** `open_dataset("s3://bucket/prefix/")` fails with a cryptic
filesystem error.

**Root cause.** `arrow` expects the region as a query parameter on the
URL for S3 paths: `s3://bucket/prefix/?region=us-east-1`.

**Fix.** Use the pattern from `analysis/01_explore.qmd`:
```r
sprintf("s3://%s/prices/?region=%s", bucket, region)
```

**Prevention.** Always use `sprintf`/`glue` with the env-provided
region. Don't hardcode.

## 7. `gh` CLI 2.4 missing `gh variable`

**Symptom.** `gh variable set AWS_REGION --body us-east-1` fails with
"unknown command".

**Root cause.** The workstation's `gh` version is 2.4.0, which predates
`gh variable` (added in ~2.20).

**Fix.** Use `gh api`:
```bash
gh api -X POST /repos/<owner>/<repo>/actions/variables \
  -f name=AWS_REGION -f value=us-east-1
```

**Prevention.** If scripting against `gh` for non-trivial commands,
pin or check version. Fall back to `gh api` for coverage.

## 8. SSH passphrase-locked key blocks `gh repo create --push`

**Symptom.** `gh repo create` created the remote repo but failed on
push with `Permission denied (publickey)` — no `ssh-askpass` available.

**Root cause.** User's SSH key requires a passphrase; there's no
interactive prompt in this environment.

**Fix.** Switch remote to HTTPS and push via the `gh` token:
```bash
gh auth setup-git
git remote set-url origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

**Prevention.** Prefer HTTPS + gh token for automated flows. SSH for
interactive use only.

## 9. Root-user AWS access key

**Symptom.** `aws sts get-caller-identity` returns
`arn:aws:iam::546464732019:root`.

**Root cause.** Local `~/.aws/credentials` has the root user's access
key.

**Fix (not yet applied).** Create an IAM user with equivalent scoped
policy; rotate local credentials; disable the root access key. This
is an operational hygiene improvement, not a bug — but it should be
done.

**Prevention.** Don't take this as license to run permissive
operations. When possible, use the GitHub Actions OIDC role for
automation even from local scripts.
