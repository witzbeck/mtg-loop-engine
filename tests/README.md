# tests

## Purpose

Pytest suites for M0/M1 gates: unit helpers, gold_core VERIFIED, hard-negative typed rejections, gold_extended UNSUPPORTED, golden proof JSON.

## Context

```mermaid
graph TB;
  unit[unit] --> lib[mtg_loop_engine];
  goldCore[gold_core] --> verifier[Verifier];
  hardNeg[hard_negatives] --> verifier;
  goldExt[gold_extended] --> verifier;
  golden[golden_proofs] --> proofs[LoopProof];
```

## What belongs here

- `test_*.py` under the subdirs below

## What does not belong here

- Authored witness definitions (live in `src/mtg_loop_engine/corpus/`)
