# MTG price archive — starter exploration
#
# Reads partitioned Parquet directly from S3 using the arrow package.
# Requires: install.packages(c("arrow","dplyr","ggplot2","aws.s3"))

library(arrow)
library(dplyr)
library(ggplot2)

bucket  <- Sys.getenv("MTG_S3_BUCKET",  "mtg-scrape-unwindgames")
region  <- Sys.getenv("AWS_REGION",     "us-east-1")
profile <- Sys.getenv("AWS_PROFILE",    "default")

# Lazy dataset over all date partitions.
prices <- open_dataset(
  sources = sprintf("s3://%s/prices/?region=%s", bucket, region),
  format  = "parquet"
)

# One month of Reserved-List-ish high-value cards on TCGplayer retail.
sample <- prices |>
  filter(
    vendor == "tcgplayer",
    kind   == "retail",
    finish == "normal",
    date   >= as.Date("2026-01-01")
  ) |>
  select(card_uuid, date, price) |>
  collect()

# Quick median-price trajectory for the top 20 most-expensive cards today.
latest_day <- max(sample$date)
top20 <- sample |>
  filter(date == latest_day) |>
  slice_max(price, n = 20) |>
  pull(card_uuid)

sample |>
  filter(card_uuid %in% top20) |>
  ggplot(aes(date, price, group = card_uuid)) +
  geom_line(alpha = 0.4) +
  scale_y_log10() +
  labs(
    title    = "Top-20 TCGplayer retail — log price over time",
    subtitle = "Non-foil, this month",
    x        = NULL,
    y        = "USD (log)"
  ) +
  theme_minimal()
