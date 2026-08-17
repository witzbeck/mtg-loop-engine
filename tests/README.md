# tests

## Purpose

Pytest suites for M0–M3 gates: unit helpers, gold_core VERIFIED, hard-negative typed rejections, gold_extended UNSUPPORTED, golden proof JSON, semantic compiler, and blind discovery recall.

## Context

```mermaid
graph TB;
  unit[unit] --> lib[mtg_loop_engine];
  goldCore[gold_core] --> verifier[Verifier];
  hardNeg[hard_negatives] --> verifier;
  goldExt[gold_extended] --> verifier;
  golden[golden_proofs] --> proofs[LoopProof];
  semantic[semantic] --> compiler[compiler];
  discovery[discovery] --> search[search];
  search --> verifier;
```

## What belongs here

- `test_*.py` under the subdirs below

## What does not belong here

- Authored witness definitions (live in `src/mtg_loop_engine/corpus/`)
