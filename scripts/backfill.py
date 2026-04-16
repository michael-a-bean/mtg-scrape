"""One-shot: pull AllPrices.json.xz (90-day rolling window) and explode every
date into its own partitioned Parquet file. Run once to seed the archive.
"""
from __future__ import annotations

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
log = logging.getLogger("backfill")

FILENAME = "AllPrices.json.xz"
RAW_PREFIX = "raw/mtgjson"


def main() -> int:
    meta = get_meta()
    log.info("MTGJSON Meta: version=%s date=%s", meta["version"], meta["date"])

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

    log.info("backfill wrote %d price rows across 90 daily partitions", written)
    s3_util.put_json(
        f"state/mtgjson/AllPrices/{meta['version']}-{meta['date']}.json",
        {"rows": written, "meta": meta, "source": FILENAME},
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
