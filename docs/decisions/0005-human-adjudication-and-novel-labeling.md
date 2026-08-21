# ADR 0005 — Human adjudication and `NOVEL` labeling

## Status

Accepted

## Context

Blind discovery will surface pairs absent from Spellbook. Automatically calling those “novel true combos” or “false positives” both mislead: absence is not falsehood, and novelty is a human claim about the world and the model’s trustworthiness.

## Decision

- Spellbook (reference) **absence** is labeled **`ABSENT_FROM_REFERENCE`**, not an automatic false positive.
- **`NOVEL` requires human review** — only adjudication upgrades a candidate to `NOVEL`.
- Report `NOVEL` **separately** from the precision denominator.
- Do **not** tighten joins (or otherwise suppress) merely to hide `ABSENT_FROM_REFERENCE` results — **label them**.
- Adjudication schemas and the local workbench are the system of record for these upgrades.

## Consequences

- M5 (novel candidate adjudication) is meaningless until M4 correctness follow-through keeps precision trustworthy.
- Agents and CI must not auto-promote `NOVEL` from heuristics or LLM judgment.
- Eval reporting must keep absence, duplicate, valid, and novel buckets distinct.
