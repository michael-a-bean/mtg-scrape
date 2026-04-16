"""Daily Scryfall bulk download → staged raw on S3.

Scryfall publishes a directory of bulk files; we pull `default_cards` (one
record per unique printing in English-preferred) and stage it as-is. Keeping
the raw bytes is enough for now — we'll add normalization later if we end up
needing a card dimension table in query-native form.
"""
from __future__ import annotations

import logging
import sys

import requests

from src import s3_util
from src.config import SCRYFALL_BULK_URL, USER_AGENT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("scryfall")

BULK_TYPE = "default_cards"


def find_bulk_entry(bulk_type: str) -> dict:
    r = requests.get(SCRYFALL_BULK_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    for entry in r.json()["data"]:
        if entry["type"] == bulk_type:
            return entry
    raise RuntimeError(f"bulk type {bulk_type!r} not found")


def main() -> int:
    entry = find_bulk_entry(BULK_TYPE)
    updated_at = entry["updated_at"][:10]
    uri = entry["download_uri"]
    log.info("Scryfall %s updated_at=%s uri=%s", BULK_TYPE, updated_at, uri)

    key = f"raw/scryfall/{BULK_TYPE}/dt={updated_at}/{BULK_TYPE}.json"
    if s3_util.exists(key):
        log.info("already staged %s; skipping.", key)
        return 0

    with requests.get(uri, headers={"User-Agent": USER_AGENT}, stream=True, timeout=600) as r:
        r.raise_for_status()
        r.raw.decode_content = False
        s3_util.stream_to_s3(key, r.raw, content_type="application/json")
    log.info("staged s3://.../%s", key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
