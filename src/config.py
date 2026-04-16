import os

S3_BUCKET = os.environ.get("MTG_S3_BUCKET", "mtg-scrape-unwindgames")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

MTGJSON_BASE = "https://mtgjson.com/api/v5"
SCRYFALL_BULK_URL = "https://api.scryfall.com/bulk-data"

USER_AGENT = "mtg-scrape/0.1 (+https://github.com/unwindgames/mtg-scrape)"

PAPER_PROVIDERS = ("cardkingdom", "cardmarket", "cardsphere", "tcgplayer")
MTGO_PROVIDERS = ("cardhoarder",)
