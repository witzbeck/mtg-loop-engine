# proofs

## Purpose

Canonical witness and proof contracts: `LoopWitness` in, `LoopProof` out, plus light normalization.

## What belongs here

- `models.py`: classification, prerequisites, `LoopRelevantState`, version identity, proof hash fields
- `normalize.py`: VALID → NORMALIZED cleanup (not mathematical minimality)

## What does not belong here

- Rules execution (see `rules/`, `verify/`)
- Blind discovery of action sequences (M3)
