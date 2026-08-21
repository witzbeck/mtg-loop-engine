# ADR 0001 — Discovery / verification boundary

## Status

Accepted

## Context

The engine both *searches* for candidate loops and *proves* them. Mixing speculation into proof would inflate recall while destroying trust in `VERIFIED`. Spellbook (and similar corpora) contain known pairs; feeding those pairings into blind discovery would invalidate “rediscovery” claims.

## Decision

- **Discovery may speculate** (joins, bounded search, over-proposal).
- **Verification may not**: witness-in / proof-out; no search inside the verifier; no softening of proof obligations to accept a candidate.
- **No Spellbook pairing leakage into discovery**: pair labels and equivalent pairing hints must not guide blind search.
- Explorer (or the designated acceptance path) remains the single acceptance oracle where the architecture already separates “propose” from “accept”; discovery must not re-verify in a way that bypasses the verifier contract.

## Consequences

- False or weak proposals are expected at the discovery layer; they must die at verification or adjudication, not be patched into proofs.
- Benchmarks that claim blind rediscovery must keep reference pairing out of the search path.
- Changes that blur this boundary require a new ADR and an explicit `ROADMAP.md` frozen-table update — not a quiet refactor.
