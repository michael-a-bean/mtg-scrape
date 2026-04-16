"""Daily driver: MTGJSON AllPricesToday → partitioned Parquet → S3.

Run via GitHub Actions cron. Idempotent: reads Meta.json first and skips if
this version+date is already recorded in s3://.../state/mtgjson/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys

from src import s3_util
from src.config import S3_BUCKET
from src.mtgjson_client import get_meta, stream_download
from src.normalize import iter_price_rows, open_xz
from src.writer import write_partitioned

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("ingest")

FILENAME = "AllPricesToday.json.xz"
RAW_PREFIX = "raw/mtgjson"
STATE_PREFIX = "state/mtgjson"


def state_key(meta: dict) -> str:
    return f"{STATE_PREFIX}/AllPricesToday/{meta['version']}-{meta['date']}.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Ingest even if state key exists")
    args = parser.parse_args(argv)

    meta = get_meta()
    log.info("MTGJSON Meta: version=%s date=%s", meta["version"], meta["date"])

    key = state_key(meta)
    if not args.force and s3_util.exists(key):
        log.info("already ingested %s; skipping. bucket=%s", key, S3_BUCKET)
        return 0

    raw_key = f"{RAW_PREFIX}/dt={meta['date']}/{FILENAME}"
    with stream_download(FILENAME) as stream:
        s3_util.stream_to_s3(raw_key, stream)
    log.info("raw staged → s3://%s/%s", S3_BUCKET, raw_key)

    tmp_path = f"/tmp/{FILENAME}"
    with open(tmp_path, "wb") as out, stream_download(FILENAME) as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            out.write(chunk)

    with open_xz(tmp_path) as fp:
        rows = iter_price_rows(fp, meta["version"])
        written = write_partitioned(rows, prefix="prices")

    log.info("wrote %d price rows", written)
    s3_util.put_json(key, {
        "ingested_at": dt.datetime.now(dt.UTC).isoformat(),
        "rows": written,
        "meta": meta,
        "source": FILENAME,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
