# M4 LAR v1 — promoted evidence summary

**Evidence ID:** `0001-m4-lar-v1`  
**Original run:** `2026-08-21_5b8c45d` (git `5b8c45d`)  
**Protocol:** LAR v1 (no blind pair review, no adversarial challenge)  
**Why promoted:** First full tiered review; validated participant-gate behavior; exposed taxonomy coverage gaps and pre-gate eval inventory drift; motivated LAR v2 architecture.

## Tempered conclusions

**No fundamental architectural defect was observed on the curated cases evaluated.** Search/verify separation, participant enforcement on discovery acceptance, and gold_core mechanic families behaved as designed on the examined witnesses.

**Do not over-read 24/24 pair agreement.** Sixteen of twenty-four frozen rows are `invalid_candidate_data` fixture inventory. The real-card precision slice is small (eight rows). Agreement reproduced frozen labels; it is not broad independent validation of adjudication quality across Oracle space.

**Participant gate:** Five Basalt-bystander duplicate pairs are correctly labeled historically and are live-rejected post gate (`tests/eval/test_classify_store.py`).

**Eval inventory drift:** Committed `gold_pool_extras.jsonl` still reflects pre-gate discovery (~24 rows) while live extras are ~10. Certified baseline re-freeze remains on the M4 roadmap after compiler eligibility work — not because of LAR alone.

**Taxonomy coverage:** Four of eight adjudication classes had zero gold-pool exemplars at review time (`valid_generic_prerequisite`, `functional_external_requirement`, `unjustified_initial_state`, `needs_rules_research`). Class-level consistency cannot be strongly evaluated for half the taxonomy until calibration cases exist.

**Compiler gap:** `etb_damage_death` family passes on fixtures only; real Oracle compiler path remains M4 work.

## Healthy families (C1 regression signal)

| Family | Signal |
|--------|--------|
| `mana_tap_untap` | gold_core + extras aligned |
| `token_etb_untap` | gold_core + extras aligned |
| `zone_recursion_sacrifice` | strongest A+B+C alignment |
| `counters_damage` | healthy |
| `etb_damage_death` | partial — fixture-only compiler |

## Knowledge routed from this run

| Finding | Durable destination |
|---------|-------------------|
| Taxonomy boundary gaps | `docs/ADJUDICATION.md`, `eval/calibration/` backlog |
| Duplicate vs participation boundary | `eval/calibration/adjudication_cases.jsonl` CC-001/CC-003 |
| Gravecrawler generic-prerequisite example | Removed from docs (not a clean exemplar) |
| Participant gate validation | Existing regression tests |
| Stale baseline | M4 roadmap item 5 (certified re-freeze) |
| LAR storage model | LAR v2 directive + this promoted package |

## What this package is not

- Not a transcript archive (full v1 tree belongs under `data/eval/lar/runs/2026-08-21_5b8c45d/` locally).
- Not proof that human adjudication is universally trustworthy — only that frozen labels on this inventory were reproduced under v1 protocol.
- Not a composite "LAR score."

## Roadmap implication

Continue M4 order: real Oracle compiler curriculum → Spellbook eligibility ≥1 → certified baseline re-freeze → STATUS reconciliation. No verifier participant gate or join-tuning warranted by this evidence alone.
