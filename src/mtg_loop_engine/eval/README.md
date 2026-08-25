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
| Human-adjudicated precision | `metrics.precision_from_records` | Among adjudicated **real-card** accepted discoveries, how many are valid classes? |
| Prerequisite analysis | `classify.py` | Participation / assumptions / `strict_two_card` **detection** |
| Persistence / UX | `store.py`, `workbench.py`, `narrate.py`, `glossary.py`, `explain.py` | Reviewer workflow |

### Spellbook absence

Accepted discoveries missing from Spellbook are `ABSENT_FROM_REFERENCE` (or similar reference status). `NOVEL` requires human adjudication (M5). See [`docs/EVALUATION.md`](../../../docs/EVALUATION.md).

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

- Precision denominator excludes skipped and `INVALID_CANDIDATE_DATA` (fixture pairs).
- Recovery recall is undefined / null when eligible count is 0.
- Gold-extra persistence expects adjudications to cover **currently discovered** extras (10-row post-gate contract in tests). Frozen baseline JSON may still show the pre-gate 24-row snapshot until ROADMAP item 5.

## Main entry points

| Module | Role |
| --- | --- |
| `classify.py` | `analyze_prerequisites` |
| `schema.py` | Adjudication classes / records |
| `metrics.py` | Recovery + precision reports |
| `spellbook_eval.py` | Reference subset evaluation |
| `gold_extras.py` | Gold-pool extras snapshot / summary |
| `store.py` | DuckDB + JSONL |
| `workbench.py` | Streamlit UI |
| `oracle_lookup.py` | Optional real Oracle text lookup |

CLI: `eval-gold-extras`, `eval-spellbook`, `adjudicate-workbench`.

## Data contracts

Committed outputs land in repo-root `eval/` (fixtures, adjudications, baselines). Working DuckDB defaults under gitignored `data/eval/`.

## Failure behavior

`RuntimeError` when gold extras count disagrees with adjudication coverage. Recovery stages record miss reasons without claiming precision.

## Testing

`tests/eval/` — classify (including bystander detection), store roundtrip, sample recovery 2/2, extras↔adjudications, narrate helpers.

## Extension guide

1. Change denominators only with docs + baseline updates.
2. Keep workbench educational; surface adjudication classes clearly.
3. Participant enforcement belongs in search/verify — update classify tests when it lands.

## Bigger-picture relationship

Eval sits above the engine. Architecture: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md). Artifact layout: [`../../../eval/README.md`](../../../eval/README.md).
