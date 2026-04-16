"""Partitioned Parquet writer: one file per date, spilling to local disk.

The previous version flushed every in-memory date bucket each time total rows
crossed a threshold, which produced one small file per date per flush round —
thousands of ~20 KiB files on the 90-day backfill.

This version opens a streaming `ParquetWriter` per date, backed by a local
temp file, and appends row batches as they arrive. Row groups flush to disk
as they fill, so memory stays bounded regardless of how many dates are in
flight. At end-of-stream, each temp file becomes exactly one S3 object.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import tempfile
from collections import defaultdict
from collections.abc import Iterable

import boto3
import pyarrow as pa
import pyarrow.parquet as pq

from src.config import AWS_REGION, S3_BUCKET
from src.schema import PRICES_SCHEMA

log = logging.getLogger(__name__)

BATCH_ROWS = 50_000


def write_partitioned(rows: Iterable[dict], prefix: str = "prices") -> int:
    """Write rows as date-partitioned Parquet on S3 — one file per date."""
    s3 = boto3.client("s3", region_name=AWS_REGION)
    tmpdir = tempfile.mkdtemp(prefix="mtg_prices_")
    writers: dict[dt.date, pq.ParquetWriter] = {}
    paths: dict[dt.date, str] = {}
    counts: dict[dt.date, int] = defaultdict(int)
    buffers: dict[dt.date, list[dict]] = defaultdict(list)

    def get_writer(date: dt.date) -> pq.ParquetWriter:
        if date not in writers:
            paths[date] = os.path.join(tmpdir, f"dt-{date.isoformat()}.parquet")
            writers[date] = pq.ParquetWriter(paths[date], PRICES_SCHEMA, compression="zstd")
        return writers[date]

    def flush_date(date: dt.date) -> None:
        if not buffers[date]:
            return
        tbl = pa.Table.from_pylist(buffers[date], schema=PRICES_SCHEMA)
        get_writer(date).write_table(tbl)
        counts[date] += len(buffers[date])
        buffers[date].clear()

    try:
        for row in rows:
            date = row["date"]
            buffers[date].append(row)
            if len(buffers[date]) >= BATCH_ROWS:
                flush_date(date)

        for date in list(buffers):
            flush_date(date)
        for w in writers.values():
            w.close()

        total = 0
        ts = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
        for date, local in paths.items():
            key = f"{prefix}/dt={date.isoformat()}/part-{ts}.parquet"
            with open(local, "rb") as fp:
                s3.upload_fileobj(fp, S3_BUCKET, key)
            log.info("wrote %d rows → s3://%s/%s", counts[date], S3_BUCKET, key)
            total += counts[date]
        return total
    finally:
        for path in paths.values():
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass
