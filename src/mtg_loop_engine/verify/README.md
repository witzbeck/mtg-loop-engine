# verify

## Purpose

**The verifier is the acceptance boundary.**

Witness-in / proof-out. No discovery logic here. Search may call this package; this package must never import or embed search.

## Role in pipeline

`LoopWitness` → **THIS (`Verifier.verify`)** → `LoopProof` (`VERIFIED` or typed rejection).

```mermaid
graph TB;
  witness[LoopWitness] --> verifier[Verifier];
  executor[rules.Executor] --> verifier;
  state[GameState] --> verifier;
  verifier --> proof[LoopProof];
```

## Inputs

- Fully formed `LoopWitness` (cards, IR, setup, loop actions, relevant state, expected outputs, classification, coverage)

## Outputs

- `LoopProof` with status, rejection reason (if any), recurrence details, proof hash, version identity

## Responsibilities

- Fail-closed semantic coverage gates
- Functional-external and essential-count gates
- Execute setup + loop via `rules.Executor`
- Check proof-specific recurrence (`LoopRelevantState`) and expected outputs
- Hash proofs for stability tracking

## Non-responsibilities

- Candidate pair enumeration or action-space BFS (`search/`)
- Gold pair labels
- Human adjudication
- **Participant / `strict_two_card` enforcement** — discovery applies that gate in `search.explore_pair`; this package judges physics/coverage/externals only (see `search/README.md`)

## Core invariants

- Module contract: `"Witness-in / proof-out verifier (no search)."`
- `PARTIAL_RELEVANT_TO_PROOF` or `card.relevant_unsupported()` → `UNSUPPORTED_SEMANTICS` (never `VERIFIED`)
- `PARTIAL_IRRELEVANT_TO_PROOF` may still `VERIFIED` if abilities are otherwise supported
- Non-empty `functional_external_requirements` → `EXTERNAL_FUNCTIONAL_PIECE_REQUIRED`
- Nondeterministic witnesses rejected
- `verify` package must not import `search` (`tests/unit/test_search_boundary.py`)
- Does **not** enforce `strict_two_card` / unused participant IDs (intentional; search-only gate). Hand-authored bystander witnesses may still `VERIFIED`.

## Main entry points

- `verifier.py`: `Verifier`, `Verifier.verify`, `check_recurrence`, `check_outputs`, `proof_hash`

## Data contracts

Consumes `proofs.models.LoopWitness`; emits `LoopProof` with `VerificationStatus` / `ProofKind`. Proof hash covers witness identity + status + loop + outputs.

## Failure behavior

Always returns a `LoopProof` for ordinary verification attempts — typed rejection statuses rather than exceptions for loop/physics failures.

## Testing

- `tests/gold_core/` — positives `VERIFIED`
- `tests/hard_negatives/` — expected typed rejection
- `tests/semantic/test_compile_verify.py` — compile → verify
- `tests/unit/test_search_boundary.py` — layering
- `tests/golden_proofs/` — proof artifact contracts

## Extension guide

Add acceptance gates here when they are truth conditions (physics, coverage, externals). Do not pull exploration into this package. Participant enforcement for discovery lives in `search.explore_pair`; adding a verifier-side participant gate is an optional follow-up if hand-authored bystanders must also fail closed.

## Bigger-picture relationship

Verification may not speculate. Architecture: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md).
