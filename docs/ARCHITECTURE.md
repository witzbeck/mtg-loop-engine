# Architecture

Package boundaries, data flow, and dependency direction for MTG Loop Engine.

Cross-cutting narrative: [`PHILOSOPHY.md`](PHILOSOPHY.md), [`TERMINOLOGY.md`](TERMINOLOGY.md), [`EVALUATION.md`](EVALUATION.md). Package-local operating contracts live next to code under `src/mtg_loop_engine/*/README.md`.

## Pipeline (high level)

```mermaid
graph TB;
  scryfall[ScryfallOracle] --> cards[cards];
  cards --> semantics[semantics];
  fixtures[oracleFixtures] --> semantics;
  semantics --> interactions[interactions];
  semantics --> rules[rules];
  semantics --> state[state];
  semantics --> proofs[proofs];
  interactions --> search[search];
  corpus[corpus] --> search;
  corpus --> verify[verify];
  rules --> verify;
  state --> verify;
  proofs --> verify;
  search --> verify;
  verify --> proofsOut[LoopProof];
  search --> evalPkg[eval];
  verify --> evalPkg;
  benchmark[benchmark] --> evalPkg;
  evalPkg --> evalArt[repoRootEval];
```

**North star:** Oracle text → semantics → blind discovery → rules proof. Discovery may speculate; verification may not. Optimize verified precision over recall.

## Dependency direction (normative)

| Edge | Status | Why |
| --- | --- | --- |
| `search → verify` | **Required** | Search proposes; verifier accepts or rejects. Explorer injects `Verifier` as the acceptance oracle. |
| `verify → search` | **Prohibited** | Verifier is witness-in / proof-out only. Enforced by `tests/unit/test_search_boundary.py`. |
| `interactions → search` | Allowed | Joins propose pairs; search explores sequences. |
| `search → interactions` | Avoid | Search consumes `CandidatePair`; it does not own join logic. |
| `semantics → {interactions, rules, state, proofs, verify}` | Allowed | IR is the shared language. |
| `{verify, search} → semantics` | Read-only | Consume compiled IR; do not compile inside verify. |
| `corpus → {verify, search, eval}` | Allowed | Fixtures and shared builders. |
| `search → corpus.builders` | Allowed | Shared witness shape (`bf`, `two_card`); **not** gold pair keys. |
| `eval → {search, verify, corpus, benchmark}` | Allowed | Research / measurement layer sits above the engine. |
| `search → eval.classify` | **Acknowledged cycle** | Explorer stamps classification via `analyze_prerequisites`. Prefer extracting classify into a neutral module later; do not invert so verify depends on eval. |
| `benchmark → corpus` | **Prohibited / unused** | Spellbook extract does not feed gold authorship. |

```mermaid
graph LR;
  cards --> semantics;
  semantics --> interactions;
  semantics --> rules;
  semantics --> state;
  semantics --> proofs;
  interactions --> search;
  corpus --> search;
  corpus --> verify;
  rules --> verify;
  state --> verify;
  proofs --> verify;
  search --> verify;
  search -.->|classify stamp| eval;
  eval --> search;
  eval --> verify;
  benchmark --> eval;
```

Solid arrows are intended production dependencies. The dashed `search → eval` edge is the classification stamp used when building discovered witnesses; it must never become a path for eval to influence verifier acceptance logic.

## Layer responsibilities (one line each)

| Package | Contract |
| --- | --- |
| `cards` | Ingest Scryfall Oracle snapshots; no semantics. |
| `semantics` | Oracle language → deterministic IR + coverage. |
| `semantics/patterns` | Ordered deterministic clause matchers. |
| `interactions` | Capability joins → candidate pairs (propose only). |
| `search` | Bounded exploration → witness candidates. **Does not decide truth.** |
| `verify` | **Acceptance boundary.** Witness → proof. No discovery. |
| `rules` | Modeled executor for costs/effects/triggers. |
| `state` | Minimal `GameState` for recurrence paths. |
| `proofs` | Shared pydantic contracts (`LoopWitness`, `LoopProof`, …). |
| `corpus` | Curated epistemic fixtures + shared builders. |
| `benchmark` | Spellbook reference extract/filter. |
| `eval` (package) | Recovery metrics + human-adjudicated precision. |
| `eval/` (repo root) | Committed fixtures, adjudications, frozen baselines. |

## Participant gate (search acceptance)

**Both searched essentials must participate before discovery accepts a hit.**

- **Detection:** `mtg_loop_engine.eval.classify.analyze_prerequisites` computes `used_oracle_ids` / `unused_oracle_ids` / `strict_two_card` from which searched cards act in loop steps (including continuous cost-reduction participation). Explorer stamps `Classification.strict_two_card` onto the witness. `unused_oracle_ids` remain on `PrerequisiteAnalysis` only.
- **Enforcement (search-only):** `explore_pair` accepts only when `Verifier.verify` returns `VERIFIED` **and** `strict_two_card`. Bystander-verified sequences are skipped; BFS continues. The verifier does not read participation flags (hand-authored bystander witnesses can still verify).
- **Evidence:** `tests/eval/test_classify_store.py` — five real Basalt bystander pairs → no hit; Basalt + Training Grounds still accepted.
- **Baselines:** committed `eval/baseline/` numbers remain the pre-gate M4 freeze until roadmap item 5 (post-eligibility re-freeze).

## Fail-closed coverage

`SemanticCoverage` (`semantics.enums`):

| Value | Meaning | Verifier |
| --- | --- | --- |
| `COMPLETE` | All fragments matched | May `VERIFIED` |
| `PARTIAL_IRRELEVANT_TO_PROOF` | Gaps marked irrelevant | May `VERIFIED` if otherwise sound |
| `PARTIAL_RELEVANT_TO_PROOF` | Proof-relevant gaps (default for unmatched) | **Never** `VERIFIED` → `UNSUPPORTED_SEMANTICS` |

Fail-closed also fires when any card’s `relevant_unsupported()` is true. Discovery often leaves witness-level `semantic_coverage` at its default; per-card IR coverage remains the load-bearing gate.

## Evaluation split

| Instrument | Question | Spellbook absence |
| --- | --- | --- |
| Reference recovery | Among eligible/supported reference rows, how many rediscover? | N/A (denominator is eligible only) |
| Human-adjudicated precision | Of accepted real-card discoveries, how many are valid? | `ABSENT_FROM_REFERENCE`, **not** a false positive |

Frozen numbers: `eval/baseline/*.json` (prefer over prose). See [`EVALUATION.md`](EVALUATION.md).

## Testing as epistemic contracts

| Suite | Contract |
| --- | --- |
| `tests/gold_core` | **Positives** → `VERIFIED` |
| `tests/hard_negatives` | **Hard negatives** → exact typed rejection |
| `tests/gold_extended` | Unsupported stubs stay non-`VERIFIED` (curriculum) |
| `tests/golden_proofs` | Proof JSON / hash / `normalize_proof` as executable artifacts |
| `tests/semantic` | Compiler coverage + compile→verify seam |
| `tests/discovery` | Blind recall + compiled Oracle→discovery→verify seam |
| `tests/eval` | Classify detection, recovery sample, precision exclusions |
| `tests/unit/test_search_boundary` | `verify` must not import `search` |
