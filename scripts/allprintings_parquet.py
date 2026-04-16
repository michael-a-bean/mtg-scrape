"""Daily download of MTGJSON AllPrintingsParquetFiles.tar.xz → stage to S3.

We keep this as the tar.xz archive (provenance) plus an untarred layout under
`dimension/mtgjson/allprintings/dt=YYYY-MM-DD/` so DuckDB/Athena can read the
per-table Parquet files directly.
"""
from __future__ import annotations

import logging
import os
import sys
import tarfile
import tempfile

from src import s3_util
from src.config import S3_BUCKET
from src.mtgjson_client import get_meta, stream_download

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("allprintings")

FILENAME = "AllPrintingsParquetFiles.tar.xz"


def main() -> int:
    meta = get_meta()
    tar_key = f"raw/mtgjson/dt={meta['date']}/{FILENAME}"

    if s3_util.exists(tar_key):
        log.info("already staged %s; skipping.", tar_key)
        return 0

    with tempfile.NamedTemporaryFile("wb", suffix=".tar.xz", delete=False) as tmp:
        tmp_path = tmp.name
        with stream_download(FILENAME) as stream:
            for chunk in iter(lambda: stream.read(1 << 20), b""):
                tmp.write(chunk)

    with open(tmp_path, "rb") as fp:
        s3_util.stream_to_s3(tar_key, fp)

    with tarfile.open(tmp_path, "r:xz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(".parquet"):
                continue
            leaf = os.path.basename(member.name)
            key = f"dimension/mtgjson/allprintings/dt={meta['date']}/{leaf}"
            f = tar.extractfile(member)
            if f is None:
                continue
            s3_util.put_bytes(key, f.read(), "application/octet-stream")

    os.unlink(tmp_path)
    s3_util.put_json(
        f"state/mtgjson/AllPrintingsParquet/{meta['version']}-{meta['date']}.json",
        {"meta": meta, "source": FILENAME},
    )
    log.info("AllPrintings Parquet staged for %s", meta["date"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
