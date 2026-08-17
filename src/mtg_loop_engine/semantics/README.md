# semantics

## Purpose

Domain enums and intermediate representation (IR) for card abilities, costs, effects, and coverage tracking. Search and verification reason over these concepts, not Oracle strings.

## Context

```mermaid
graph TB;
  oracleText[OracleText] --> compiler[compiler];
  patterns[patterns] --> compiler;
  compiler --> ir[CardSemantics];
  ir --> verify[verify];
  ir --> proofs[proofs models];
  ir --> rules[rules executor];
```

## What belongs here

- `enums.py`, `ir.py`, `compiler.py`, `coverage.py`, `oracle_fixtures.py`
- Deterministic `patterns/` for gold_core ability families

## What does not belong here

- Full Oracle text parser completeness (grow patterns incrementally)
- LLM proposal paths (blocked through M3)
