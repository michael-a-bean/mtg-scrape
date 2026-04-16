"""Thin MTGJSON HTTP client: Meta check + streaming download."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import IO

import requests

from src.config import MTGJSON_BASE, USER_AGENT

log = logging.getLogger(__name__)


def get_meta() -> dict:
    """Return MTGJSON Meta.json — carries {version, date}."""
    r = requests.get(
        f"{MTGJSON_BASE}/Meta.json",
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["data"]


@contextmanager
def stream_download(filename: str) -> IO[bytes]:
    """Stream an MTGJSON file as raw bytes (no decompression).

    Yields a file-like bytes stream from the HTTP response so callers can pipe
    into lzma.open() without buffering the full payload.
    """
    url = f"{MTGJSON_BASE}/{filename}"
    log.info("downloading %s", url)
    with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=300) as r:
        r.raise_for_status()
        r.raw.decode_content = False  # keep xz bytes intact
        yield r.raw
