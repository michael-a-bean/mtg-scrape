"""Batched Parquet writer that partitions rows by date and uploads to S3."""
from __future__ import annotations

import datetime as dt
import io
import logging
from collections import defaultdict
from collections.abc import Iterable

import boto3
import pyarrow as pa
import pyarrow.parquet as pq

from src.config import AWS_REGION, S3_BUCKET
from src.schema import PRICES_SCHEMA

log = logging.getLogger(__name__)

BATCH_ROWS = 250_000


def _flush_batch(
    rows_by_date: dict[dt.date, list[dict]],
    s3,
    prefix: str,
) -> int:
    total = 0
    for date, rows in rows_by_date.items():
        if not rows:
            continue
        table = pa.Table.from_pylist(rows, schema=PRICES_SCHEMA)
        buf = io.BytesIO()
        pq.write_table(table, buf, compression="zstd")
        key = f"{prefix}/dt={date.isoformat()}/part-{dt.datetime.utcnow().strftime('%H%M%S')}.parquet"
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=buf.getvalue())
        log.info("wrote %d rows → s3://%s/%s", len(rows), S3_BUCKET, key)
        total += len(rows)
    rows_by_date.clear()
    return total


def write_partitioned(
    rows: Iterable[dict],
    prefix: str = "prices",
) -> int:
    """Write rows as date-partitioned Parquet to S3.

    Groups rows in memory by date; flushes a partition whenever the in-memory
    batch exceeds BATCH_ROWS total. Writes many small files per date if called
    repeatedly — that's fine; consumers should glob dt=.../*.parquet.
    """
    s3 = boto3.client("s3", region_name=AWS_REGION)
    buckets: dict[dt.date, list[dict]] = defaultdict(list)
    in_memory = 0
    written = 0

    for row in rows:
        buckets[row["date"]].append(row)
        in_memory += 1
        if in_memory >= BATCH_ROWS:
            written += _flush_batch(buckets, s3, prefix)
            in_memory = 0

    written += _flush_batch(buckets, s3, prefix)
    return written
