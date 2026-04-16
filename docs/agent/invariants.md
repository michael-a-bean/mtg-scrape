# Invariants — never-break rules

Rules that have a reason. Each lists the rule, the reason, and how to
apply in edge cases.

## 1. Don't violate upstream TOS

**Rule.** No code in this repo scrapes or redistributes data from
sources whose TOS prohibits it — specifically **TCGplayer** and
**Cardmarket**. MTGJSON re-publishes their prices under its own
agreement; use MTGJSON.

**Why.** TCGplayer API T&Cs explicitly ban redistribution. Cardmarket
invokes EU Database Directive *sui generis* rights. Violations create
legal exposure disproportionate to the data's marginal value given
MTGJSON already aggregates it.

**Edge cases.** If a future need genuinely requires direct TCGplayer
access, the path is the partner/affiliate program — not scraping. Raise
it as a decision question rather than coding around it.

## 2. Don't silently succeed on misconfiguration

**Rule.** Operations that can no-op under missing permissions MUST raise
loudly. `delete_objects` with `Quiet=True` is banned in this repo;
always inspect `Errors` in the response.

**Why.** A previous compaction run deleted zero files because
`s3:DeleteObject` was missing from the IAM role. The API returned 200
OK with per-key errors that were suppressed — leaving 23k duplicate
files on S3 with no indication of failure. The cost of a loud crash is
always lower than silent corruption of the data layout.

**Edge cases.** If you want "best-effort" behavior, log a WARNING with
the specific failed keys; do not swallow.

## 3. Don't bypass the Meta.json idempotency check

**Rule.** `ingest.py` reads MTGJSON `Meta.json` and checks for an
existing `state/mtgjson/<file>/<version>-<date>.json` state marker
before doing work. Don't remove or shortcut this.

**Why.** Daily cron can fire twice on some edge cases (manual retry
during partial failure). Without idempotency, you get duplicate rows in
the same partition and a corrupted fact table.

**Edge cases.** An operator can pass `--force` for a legitimate re-run
(e.g., after a fix). That's the only bypass.

## 4. Don't delete from `raw/` during normal operation

**Rule.** `raw/mtgjson/...` and `raw/scryfall/...` are write-once.
Lifecycle rules transition them to cheaper storage; nothing in code
should `delete_object` against them.

**Why.** Raw bytes are the reprocessing escape hatch. If a normalization
bug is discovered months later, we need the original input to rebuild
the fact table. Storage is ~$1/month for this data — not worth losing
the safety net.

**Edge cases.** Manual operator cleanup via AWS CLI is allowed (e.g.,
removing a corrupted re-download). Never in automation.

## 5. Don't break the one-file-per-partition invariant without a plan

**Rule.** After a daily ingest or compaction run, every `dt=YYYY-MM-DD`
partition under `prices/` should contain exactly one Parquet file.

**Why.** Small-files problems compound — Athena query planning and
`ListBucket` costs scale with file count. We hit this once (23k files
from the initial backfill); the compactor was written to fix it.

**Edge cases.** Temporary multi-file state between the daily writer
running and the next compaction pass is OK. Mid-day re-runs that
produce a second file in a partition are OK — next compaction fixes
them.

## 6. Don't add frameworks or abstractions speculatively

**Rule.** No ORMs, DI containers, plugin systems, config hierarchies,
or orchestrators unless a concrete repeated pain point demands it.

**Why.** This project is small enough that every added layer costs more
than it saves. Two similar Python modules is fine; three might justify
a helper; don't pre-build for N.

**Edge cases.** If you're genuinely writing the same ~20 lines for the
third time, then extract. Not before.

## 7. Don't hardcode paths, regions, or bucket names

**Rule.** Use `src/config.py` for all configurable strings. Env vars
override file defaults.

**Why.** We've already had to flip region once (us-west-1 → us-east-1)
mid-setup. Making it a one-line env change beats grepping the codebase.

**Edge cases.** Constants that truly cannot change (e.g., MTGJSON
base URL) can stay in `config.py` as module constants. They're still
centralized.

## 8. Don't mix languages within a single analytical task

**Rule.** A Quarto `.qmd` can use both R and Python chunks, but each
analytical unit (a plot, a model, a table) should pick one and stay
there. Don't write half a plot in Python and finish it in R.

**Why.** Mental model coherence. The reader should be able to follow
one language's idioms per block. Use the escape hatch between blocks,
not within them.

**Edge cases.** DuckDB SQL is language-agnostic; using it from either
side in different chunks is fine.

## 9. Don't commit secrets

**Rule.** No AWS keys, no OAuth tokens, no API keys in the repo. All
auth flows through GitHub OIDC + repo secrets.

**Why.** Public repo. Always assume any committed string is indexed
within hours.

**Edge cases.** None.

## 10. Don't push directly to `main` without the workflows passing

**Rule.** For non-trivial changes (anything touching `src/`, `scripts/`,
or `.github/workflows/`), open a PR and let the workflows validate.

**Why.** The workflows are the integration test. A bad `src/writer.py`
change will fail the next cron run at 03:30 UTC and lose a day of
archive. Catching it in CI is cheaper.

**Edge cases.** Docs-only or R-only changes can push direct. The
engineer has latitude to decide.
