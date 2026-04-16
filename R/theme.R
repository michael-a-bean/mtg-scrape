# Tufte-inspired ggplot2 theme for the MTG price project.
#
# Source this at the top of every analysis:
#     source(here::here("R", "theme.R"))
#
# Design principles (after Tufte): maximize data-ink ratio, prefer direct
# labels over legends where practical, use small multiples for comparisons,
# and keep gridlines to the minimum that still aids reading.

suppressPackageStartupMessages(library(ggplot2))

theme_mtg <- function(base_size = 11, base_family = "") {
  theme_minimal(base_size = base_size, base_family = base_family) +
    theme(
      plot.title         = element_text(face = "bold", size = rel(1.15),
                                        margin = margin(b = 6)),
      plot.subtitle      = element_text(color = "grey35", size = rel(0.95),
                                        margin = margin(b = 12)),
      plot.caption       = element_text(color = "grey50", size = rel(0.75),
                                        hjust = 0, margin = margin(t = 10)),
      plot.title.position   = "plot",
      plot.caption.position = "plot",

      axis.title         = element_text(size = rel(0.9), color = "grey25"),
      axis.text          = element_text(color = "grey35"),
      axis.line          = element_line(color = "grey80", linewidth = 0.3),
      axis.ticks         = element_line(color = "grey80", linewidth = 0.3),
      axis.ticks.length  = unit(3, "pt"),

      panel.grid.major.y = element_line(color = "grey92", linewidth = 0.25),
      panel.grid.major.x = element_blank(),
      panel.grid.minor   = element_blank(),

      strip.text         = element_text(face = "bold", hjust = 0,
                                        margin = margin(b = 4)),
      strip.background   = element_blank(),

      legend.position    = "bottom",
      legend.title       = element_text(size = rel(0.85), color = "grey25"),
      legend.key.width   = unit(1.2, "lines"),
      legend.margin      = margin(t = 4),

      plot.background    = element_rect(fill = "transparent", color = NA),
      panel.background   = element_rect(fill = "transparent", color = NA),

      plot.margin        = margin(t = 12, r = 14, b = 12, l = 12)
    )
}

# MTG mana-color palette. Ordered WUBRG + colorless + gold.
mtg_palette <- c(
  white      = "#F4EFD4",
  blue       = "#1E6DC4",
  black      = "#1C1A19",
  red        = "#D23C2D",
  green      = "#2E8A4E",
  colorless  = "#B8B1A7",
  gold       = "#C9A227"
)

scale_color_mtg <- function(...) {
  ggplot2::scale_color_manual(values = unname(mtg_palette), ...)
}

scale_fill_mtg <- function(...) {
  ggplot2::scale_fill_manual(values = unname(mtg_palette), ...)
}

# Convenience: a faint annotation helper that matches the theme's muted grey.
mtg_annotate <- function(...) {
  ggplot2::annotate("text", color = "grey35", size = 3.2, ...)
}
