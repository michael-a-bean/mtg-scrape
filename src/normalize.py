"""Stream MTGJSON AllPrices JSON into long-form rows.

MTGJSON AllPrices shape:
    {"data": {UUID: {GAME: {VENDOR: {KIND: {FINISH: {YYYY-MM-DD: price}}}}}}}

where:
    GAME    ∈ {"paper", "mtgo"}
    VENDOR  ∈ {"cardkingdom","cardmarket","cardsphere","tcgplayer","cardhoarder"}
    KIND    ∈ {"retail", "buylist"}
    FINISH  ∈ {"normal", "foil", "etched"}  (varies per provider)

We flatten to one row per (uuid, date, game, vendor, kind, finish).
Streaming via ijson keeps memory flat; AllPrices.json uncompressed is 1-3 GB.
"""
from __future__ import annotations

import datetime as dt
import io
import lzma
from collections.abc import Iterator
from typing import IO

import ijson

from src.schema import VENDOR_CURRENCY


def iter_price_rows(
    fp: IO[bytes],
    mtgjson_version: str,
) -> Iterator[dict]:
    """Yield one flat dict per price point from an AllPrices JSON stream.

    `fp` must be a binary stream positioned at the start of the JSON document.
    """
    for uuid, game_map in ijson.kvitems(fp, "data"):
        for game, vendor_map in game_map.items():
            for vendor, kind_map in vendor_map.items():
                currency = VENDOR_CURRENCY.get(vendor, "USD")
                for kind, finish_map in kind_map.items():
                    if kind not in ("retail", "buylist"):
                        continue
                    for finish, date_map in finish_map.items():
                        for date_str, price in date_map.items():
                            if price is None:
                                continue
                            yield {
                                "card_uuid": uuid,
                                "date": dt.date.fromisoformat(date_str),
                                "game": game,
                                "vendor": vendor,
                                "finish": finish,
                                "kind": kind,
                                "currency": currency,
                                "price": float(price),
                                "mtgjson_version": mtgjson_version,
                            }


def open_xz(path_or_fp) -> IO[bytes]:
    """Open an .xz file (path or file-like) as a binary stream."""
    if isinstance(path_or_fp, (str, bytes)):
        return lzma.open(path_or_fp, "rb")
    return lzma.open(path_or_fp, "rb")


def stream_xz_bytes(body: bytes) -> IO[bytes]:
    return lzma.open(io.BytesIO(body), "rb")
