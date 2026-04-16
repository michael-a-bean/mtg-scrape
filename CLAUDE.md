# CLAUDE.md

**Read `AGENTS.md` first.** It is the canonical agent brief for this repo.

## Claude-specific notes

- Session-scoped project memory lives at
  `~/.claude/projects/-home-michael-mtg-scrape/memory/` — includes the
  Python-for-eng / R-for-analysis / Quarto / ggplot+Tufte workflow
  preference. Respect it without re-confirming each session.
- The operator's preferred mode selection is in global `CLAUDE.md`. Short
  version: NATIVE for single-step, ALGORITHM for multi-step or complex.
- Agents must not narrate internal deliberation; state results directly.

## When asked about this repo

- Code convention → `docs/agent/conventions.md`
- Can I do X? / never do Y? → `docs/agent/invariants.md`
- How do I X? → `docs/agent/playbooks.md`
- Why isn't Y working? → `docs/agent/gotchas.md`
- What does file Z do? → `docs/agent/tour.md`
- Why does this project exist? → `docs/agent/context.md`

Load the narrowest relevant file; do not load the whole directory.
