"""Compact partitioned Parquet: collapse many small files into one per date.

For each date partition under s3://$BUCKET/prices/dt=YYYY-MM-DD/, reads every
existing part-*.parquet, concatenates in memory via pyarrow, writes one
part-compacted-<ts>.parquet, then deletes the source files. Runs idempotently
— a partition already down to a single file is left alone.

Usage:
    python -m scripts.compact                 # all partitions
    python -m scripts.compact --dt 2026-04-01 # one partition
    python -m scripts.compact --dry-run       # report only
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
import tempfile

import boto3
import pyarrow as pa
import pyarrow.fs as pafs
import pyarrow.parquet as pq

from src.config import AWS_REGION, S3_BUCKET

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("compact")

PREFIX = "prices/"


def list_partition_dates(s3) -> list[str]:
    dates: set[str] = set()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            parts = obj["Key"].split("/")
            if len(parts) >= 3 and parts[1].startswith("dt="):
                dates.add(parts[1][3:])
    return sorted(dates)


def list_partition_keys(s3, date: str) -> list[str]:
    prefix = f"{PREFIX}dt={date}/"
    keys: list[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".parquet"):
                keys.append(obj["Key"])
    return keys


def delete_keys(s3, keys: list[str]) -> None:
    """Delete keys in batches. Raises if any key fails — silent partial
    failure was the bug that caused duplicate files to persist."""
    for i in range(0, len(keys), 1000):
        batch = keys[i : i + 1000]
        resp = s3.delete_objects(
            Bucket=S3_BUCKET,
            Delete={"Objects": [{"Key": k} for k in batch]},
        )
        errors = resp.get("Errors", [])
        if errors:
            raise RuntimeError(
                f"delete_objects returned {len(errors)} errors; "
                f"first: {errors[0]}"
            )


def compact_partition(s3, s3fs: pafs.S3FileSystem, date: str, dry_run: bool) -> tuple[int, int]:
    """Merge every .parquet in this partition into one compacted file.

    Reads source files AND any pre-existing compacted file (the latter is a
    merge of earlier sources, so we only read it if no sources remain;
    otherwise reading both would double-count). After writing the new
    compacted file, deletes every prior key.
    """
    all_keys = list_partition_keys(s3, date)
    sources = [k for k in all_keys if "compacted" not in k]
    compacted = [k for k in all_keys if "compacted" in k]

    # Nothing to do: already a single compacted file, no sources arrived since.
    if not sources and len(compacted) <= 1:
        return 0, 0

    # Read the right set. If sources exist, they are authoritative and a stale
    # compacted file (if any) is a subset — don't read it.
    read_keys = sources if sources else compacted

    uris = [f"{S3_BUCKET}/{k}" for k in read_keys]
    table = pq.read_table(uris, filesystem=s3fs)
    rows = table.num_rows

    obsolete = all_keys  # everything gets replaced by the new compacted file

    if dry_run:
        log.info(
            "dt=%s — would compact %d files (%d rows); would delete %d old keys",
            date, len(read_keys), rows, len(obsolete),
        )
        return rows, len(read_keys)

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        pq.write_table(table, tmp_path, compression="zstd")
        ts = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
        new_key = f"{PREFIX}dt={date}/part-compacted-{ts}.parquet"
        with open(tmp_path, "rb") as fp:
            s3.upload_fileobj(fp, S3_BUCKET, new_key)
        log.info("dt=%s — wrote %s (%d rows)", date, new_key, rows)

        delete_keys(s3, obsolete)
        log.info("dt=%s — deleted %d old files", date, len(obsolete))
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass

    return rows, len(read_keys)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", help="Compact only this date (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3fs = pafs.S3FileSystem(region=AWS_REGION)

    dates = [args.dt] if args.dt else list_partition_dates(s3)
    log.info("compacting %d date partitions (dry_run=%s)", len(dates), args.dry_run)

    total_rows = 0
    total_sources = 0
    for date in dates:
        rows, sources = compact_partition(s3, s3fs, date, args.dry_run)
        total_rows += rows
        total_sources += sources

    log.info(
        "done: %d rows across %d source files → %d dates",
        total_rows,
        total_sources,
        len(dates),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
