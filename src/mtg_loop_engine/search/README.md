# search

## Purpose

Bounded discovery of `LoopWitness` candidates from semantic cards.

**Search proposes witnesses. It does not decide truth.**

The explorer calls an injected `Verifier` once per productive candidate as its acceptance oracle, then applies the **participant gate** (`strict_two_card`) before accepting. `discover_loops` does not verify again.

## Role in pipeline

`InteractionIndex.candidate_pairs` + card pool → **THIS** → first verifier-accepted strict two-card `ExploredWitness` (or none) → eval / CLI.

```mermaid
graph TB;
  pool[CardPool] --> index[InteractionIndex];
  index --> pairs[candidatePairs];
  pairs --> explorer[explore_pair];
  builders[corpus.builders] --> explorer;
  explorer --> classify[analyze_prerequisites];
  classify --> stamp[classificationStamp];
  explorer --> verifier[Verifier];
  verifier -->|VERIFIED and strict_two_card| hit[ExploredWitness];
  verifier -->|reject or bystander| continueBFS[continueBFS];
```

## Inputs

- Semantic card pool (no gold pair labels)
- Candidate pairs from `interactions`
- Optional injected `Verifier`
- Bounds: `max_depth=6`, `max_states=4000` (defaults)

## Outputs

- `ExploredWitness` / `DiscoveryHit` / `DiscoveryReport`
- Witnesses stamped with `Classification.strict_two_card`, essential count, and prereq lists from `analyze_prerequisites`. `unused_oracle_ids` live on `PrerequisiteAnalysis` only — re-run classify to inspect them; they are **not** fields on `LoopWitness`.

## Responsibilities

- Bounded legal-action BFS (`explorer.explore_pair`)
- Orchestrate pool → pairs → explorer (`discover.discover_loops`)
- Reuse `corpus.builders` (`bf`, `two_card`) so witness shape matches gold
- Prune via `reusable_fingerprint` (`pruning.py`)
- Call verifier as the sole physics acceptance oracle on the discovery path
- **Participant gate:** accept only when `proof.status == VERIFIED` **and** `witness.classification.strict_two_card`; silently continue BFS otherwise

## Non-responsibilities

- Final human truth or adjudication
- Owning pair labels / gold lookup on the discovery path
- A second verification pass after acceptance
- Verifier-side participant rejection (hand-authored bystander witnesses can still verify; discovery will not accept them)

## Core invariants

### Candidate joins

Pairs come from `interactions.InteractionIndex` (capability complements + non-empty `join_reasons`). Search does not invent pairs outside that stream.

### Bounded exploration

BFS stops at depth/state limits; fingerprints avoid re-expanding reusable states. Limits are safety rails, not soundness proofs.

### Participant requirements

| Stage | Behavior |
| --- | --- |
| **Detection** | `build_witness` calls `analyze_prerequisites`, which fills `used_oracle_ids` / `unused_oracle_ids` / `strict_two_card` (including continuous cost-reduction participation). |
| **Enforcement** | `explore_pair` accepts only `VERIFIED` + `strict_two_card`. Bystander-verified sequences are skipped; BFS continues. |
| **Verifier** | Does not read `strict_two_card` / `unused_oracle_ids`. Physics/coverage/externals only. |
| **Evidence** | `tests/eval/test_classify_store.py` — five real Basalt bystander pairs → `None`; Basalt + Training Grounds still accepted. |

## Main entry points

| Module | Symbols |
| --- | --- |
| `discover.py` | `discover_loops`, `DiscoveryReport`, `DiscoveryHit` |
| `explorer.py` | `explore_pair`, `build_witness`, `legal_steps`, `default_initial_state` |
| `pruning.py` | `reusable_fingerprint` |

CLI: `mtg-loop-engine discover-gold`.

## Data contracts

Discovered witnesses carry `assumptions=["discovered_without_pair_labels", …]` and classification stamped from `analyze_prerequisites`. Accepted discoveries are always `strict_two_card=True` under current search policy. Pair keys from corpus are eval-only and must not be imported here.

## Failure behavior

Returns `None` / empty verified hits when bounds exhaust, the oracle rejects all candidates, or only bystander-verified sequences exist. Injected reject-all verifier ⇒ no hits (`tests/unit/test_explorer.py`).

## Testing

- `tests/discovery/` — blind recall 10/10; compiled seam
- `tests/unit/test_explorer.py` — oracle injection; no double-verify
- `tests/unit/test_search_boundary.py` — verify ↛ search
- `tests/eval/test_classify_store.py` — participant gate regressions

## Extension guide

1. Keep joins in `interactions/`; keep acceptance physics in `verify/`.
2. Prefer extracting `analyze_prerequisites` out of `eval` if the search↔eval import cycle becomes painful — do not invert verify→eval.
3. If hand-authored witnesses must also fail closed on bystanders, add a verifier gate (and typed status) in a deliberate follow-up — do not silently broaden this PR’s search-only contract.

## Bigger-picture relationship

Search is speculative proposal under a conservative verifier plus a participant acceptance filter. Architecture: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md).
