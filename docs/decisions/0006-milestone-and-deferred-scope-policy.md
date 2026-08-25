# ADR 0006 — Milestone and deferred-scope policy

## Status

Accepted

## Context

The roadmap sequences corpus → verifier → compiler → discovery → evaluation → novel adjudication → incremental scans → explorer. Scaffolding deferred systems early creates dead code, false progress, and pressure to violate hard boundaries (LLM-on-verified, three-card search, etc.).

## Decision

- Work follows **milestone flow** in `ROADMAP.md` (including explicit M4 follow-through before M5).
- **Review at milestone start; update at milestone exit** in the same PR that completes the milestone.
- **Explicitly deferred — do not plan or scaffold:**
  - LLM-generated semantics on any path to `VERIFIED`
  - Three-card discovery
  - Z3 / SMT solving
  - Full Comprehensive Rules implementation
  - ManaBox integration
  - Deployed / public UI
  - Performance optimization passes
- Non-trivial implementation uses **`feature/<slug>`** branches with CI green before merge to `main` (see `CONTRIBUTING.md`).
- **In-repository docs are canonical**; session notes outside the repository are ephemeral and never required.

## Consequences

- Agents must refuse deferred scaffolding even when it looks like “helpful prep.”
- Scope disputes escalate to humans via ADR / roadmap edits — not silent reinterpretation (see `AGENTS.md`).
- Feature-branch and merge workflow summaries elsewhere remain non-authoritative relative to `CONTRIBUTING.md`.
