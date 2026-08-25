# audited

## Purpose

Committed audited Oracle **source records** for `ORACLE_EXACT` fixtures (ADR 0007).
CI asserts every exact fixture matches the matching file after representation-only
canonicalization.

## What belongs here

- One JSON record per `ORACLE_EXACT` oracle_id under `records/`.
- Filename: `oracle_id` with `:` → `__` (e.g. `oracle__basalt-monolith.json`).

## What does not belong here

- Full Scryfall bulk dumps (stay under gitignored `data/scryfall/`).
- Tuned or invented physics text (`SYNTHETIC` / `ORACLE_DIVERGENT`).
