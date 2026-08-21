# ADR 0003 — Deterministic semantics and fail-closed coverage

## Status

Accepted

## Context

`VERIFIED` must mean a conservative, explainable proof under modeled rules. LLM-authored or otherwise nondeterministic semantics on that path would make proofs non-reproducible and hard to audit. Incomplete modeling of proof-relevant rules must not be papered over as success.

## Decision

- **V1 semantics are deterministic-only** (pattern library / modeled executor). Nondeterministic situations yield a **typed rejection**, not `VERIFIED`.
- **No LLM-generated semantics on any path to `VERIFIED`**, indefinitely (also listed as deferred architecture — do not scaffold).
- **Fail closed:** incomplete relevant semantics (including `PARTIAL_RELEVANT_TO_PROOF`) **may never** emit `VERIFIED`.
- Do **not** silently broaden modeled rules or pattern coverage merely to pass tests; expand deliberately with tests and docs.

## Consequences

- Compiler and verifier reject more often than a permissive engine would; that is intended.
- Coverage work (e.g. real-Oracle patterns) is explicit product work, measured via eval — not a hidden escape hatch.
- Any proposal to allow LLM semantics onto the verified path needs a superseding ADR and roadmap change; until then it is forbidden.
