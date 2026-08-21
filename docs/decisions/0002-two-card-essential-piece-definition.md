# ADR 0002 — Two-card essential-piece definition

## Status

Accepted

## Context

Raw card count on a board is a poor definition of “two-card combo.” Generic fodder (tokens, free mana rocks used as fuel, etc.) often appears without being an essential functional piece. Conversely, a hidden third *functional* piece can make a loop look two-card while depending on external machinery.

## Decision

- A **strict two-card** loop has **exactly two essential functional pieces**.
- **Generic fodder is allowed** and does not, by itself, disqualify strict two-card status.
- A **functional external** piece (essential to the loop’s function but outside the two named essentials) means the loop is **not** strict two-card.
- Prerequisite / eligibility analysis derives `strict_two_card` from **essential-piece participation**, not from raw card count alone.
- Do **not** present a loop that depends on a hidden functional third piece as strict two-card.

## Consequences

- Gold labeling, adjudication enums (e.g. `VALID_STRICT_TWO_CARD`), and participant filters must reason about essential vs generic vs functional-external roles.
- Search may still see extra permanents; acceptance as strict two-card requires essential-piece discipline.
- Broadening or narrowing “essential” requires ADR + roadmap alignment, not silent test edits.
