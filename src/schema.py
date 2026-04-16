import pyarrow as pa

PRICES_SCHEMA = pa.schema([
    ("card_uuid", pa.string()),
    ("date", pa.date32()),
    ("game", pa.dictionary(pa.int8(), pa.string())),
    ("vendor", pa.dictionary(pa.int8(), pa.string())),
    ("finish", pa.dictionary(pa.int8(), pa.string())),
    ("kind", pa.dictionary(pa.int8(), pa.string())),
    ("currency", pa.dictionary(pa.int8(), pa.string())),
    ("price", pa.float64()),
    ("mtgjson_version", pa.string()),
])

VENDOR_CURRENCY = {
    "tcgplayer": "USD",
    "cardkingdom": "USD",
    "cardsphere": "USD",
    "cardmarket": "EUR",
    "cardhoarder": "TIX",
}
