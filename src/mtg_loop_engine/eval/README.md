# eval

## Purpose

M4 research instrumentation: prerequisite analysis, Spellbook **reference recovery**, human-adjudicated **precision**, persistence, and the Streamlit workbench.

This package measures the engine. Explorer UI is M7 (`ROADMAP.md`). Denominators: [`docs/EVALUATION.md`](../../../docs/EVALUATION.md).

## Role in pipeline

Discoveries / Spellbook subsets / adjudications → **THIS** → recovery & precision reports → committed artifacts under repo-root `eval/` + optional `data/eval/` DuckDB.

```mermaid
graph TB;
  discover[search.discover] --> records[candidateRecords];
  records --> store[duckdbJsonlStore];
  store --> workbench[streamlitWorkbench];
  workbench --> adj[humanAdjudications];
  adj --> precision[adjudicatedPrecision];
  spellbook[spellbookSubset] --> recovery[referenceRecovery];
  recovery --> baseline[eval/baseline];
```

## Inputs

- Discovered witnesses / proofs
- Spellbook conventional rows (snapshot or fixtures)
- Human adjudication classes

## Outputs

- `RecoveryReport`, `PrecisionReport`
- JSONL / DuckDB records
- Workbench UI narratives

## Responsibilities

| Concern | Module | Meaning |
| --- | --- | --- |
| Reference recovery | `spellbook_eval.py`, `metrics.py` | Among **eligible/supported** reference rows, how many rediscover? Stages: compile → join → search → optional prerequisite mismatch → recovered. |
| Compiler frontier (M5.1) | `compiler_frontier.py` + `scripts/spellbook_compiler_priority.py` | Rank missing fragments by COMPLETE / both-COMPLETE pair unlock (not rediscovery). Live under `data/eval/`. |
| Human-adjudicated precision | `metrics.precision_from_records` + `provenance.is_precision_eligible_ids` | Among adjudicated **ORACLE_EXACT×ORACLE_EXACT** discoveries, how many are valid classes? (ADR 0007) |
| Prerequisite analysis | `classify.py` | Participation / assumptions / `strict_two_card` **detection** |
| Persistence / UX | `store.py`, `workbench.py`, `narrate.py`, `glossary.py`, `explain.py` | Reviewer workflow; `AdjudicationClass` + optional `AdjudicationFailureReason` |

### Spellbook absence

Accepted discoveries missing from Spellbook are `ABSENT_FROM_REFERENCE` (or similar reference status). `NOVEL` requires human adjudication (M5). See [`docs/EVALUATION.md`](../../../docs/EVALUATION.md).

Workbench bridge: `candidate_records_from_discovery` + `persist_spellbook_absent_candidates` (corpus `spellbook_absent`) write DuckDB + `data/eval/spellbook_absent.jsonl`. Operator: `uv run python scripts/spellbook_absent_discovery.py --persist-workbench`, then filter corpus → `spellbook_absent` in the workbench.

### Detection vs enforcement

`analyze_prerequisites` detects unused searched cards and sets `strict_two_card`. **Search enforces** that flag in `explore_pair` (accept only `VERIFIED` + `strict_two_card`). This package owns detection and measurement; the acceptance gate lives in search.

## Boundaries

| Concern | Owner |
| --- | --- |
| FastAPI / Postgres / public explorer | M7 (`ROADMAP.md`) |
| LLM parsing | Out of scope on `VERIFIED` path |
| Join policy for unlabeled extras | Leave open unless precision bug proven |
| Verifier-side participant rejection | Optional follow-up; discovery already filters |
| Committed baseline *files* | repo-root `eval/baseline/` (this package writes/reads them) |

LAR v2 contracts (`lar_contracts.py`, `lar_calibration.py`) support ephemeral runs under `data/eval/lar/runs/` and durable calibration loading from `eval/calibration/`.

## Core invariants

- Precision denominator is `ORACLE_EXACT`×`ORACLE_EXACT` only (ADR 0007); SYNTHETIC /
  divergent pairs stay out of product precision.
- Recovery recall is undefined / null when eligible count is 0.
- Gold-extra persistence expects adjudications to cover **currently discovered** extras
  (count locked in `tests/eval/test_spellbook_eval.py`). Frozen baseline JSON matches.
- Workbench: **one** `adjudicate-workbench` process at a time — DuckDB file lock; Streamlit
  keeps a single cached connection per process. Stop via Ctrl+C in the launch terminal
  (CLI forwards signals to the Streamlit process group and closes the store); closing the
  browser tab alone leaves the lock held.
## Main entry points

| Module | Role |
| --- | --- |
| `classify.py` | `analyze_prerequisites` |
| `schema.py` | Adjudication classes / records |
| `metrics.py` | Recovery + precision reports |
| `spellbook_eval.py` | Reference subset evaluation |
| `compiler_frontier.py` | M5.1 frontier: distance / gap kind / pair unlock / P0–P2 tiers |
| `reference_absent.py` | Label verified discoveries vs reference pairs; persist absent candidates for workbench (M5) |
| `gold_extras.py` | Gold-pool extras snapshot / summary |
| `store.py` | DuckDB + JSONL |
| `workbench.py` | Streamlit UI |
| `oracle_lookup.py` | Optional real Oracle text lookup |

CLI: `eval-gold-extras`, `eval-spellbook`, `adjudicate-workbench`. Absent workbench seed: `scripts/spellbook_absent_discovery.py --persist-workbench`.

## Data contracts

Committed outputs land in repo-root `eval/` (fixtures, adjudications, baselines). Working DuckDB defaults under gitignored `data/eval/`.

## Failure behavior

`RuntimeError` when gold extras count disagrees with adjudication coverage. Recovery stages record miss reasons without claiming precision.

## Testing

`tests/eval/` — classify (including bystander detection), store roundtrip, sample recovery 2/2, extras↔adjudications, narrate helpers, compiler-frontier ranking contracts.

## Extension guide

1. Change denominators only with docs + baseline updates.
2. Keep workbench educational; surface adjudication classes clearly.
3. Participant enforcement belongs in search/verify — update classify tests when it lands.

## Bigger-picture relationship

Eval sits above the engine. Architecture: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md). Artifact layout: [`../../../eval/README.md`](../../../eval/README.md).
