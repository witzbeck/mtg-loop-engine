# Project status (quantitative)

## Purpose

Volatile evaluation numbers live here—not in `ROADMAP.md`. Milestone gates and frozen product decisions stay in the roadmap; this file summarizes what the frozen baselines currently report.

## Source of truth

| Kind of question | Authority |
| ---------------- | --------- |
| Milestone complete / gated | [`ROADMAP.md`](../ROADMAP.md) |
| Why a design constraint exists | [`docs/decisions/`](decisions/) + roadmap frozen decisions |
| What was measured | [`eval/baseline/`](../eval/baseline/) |
| How denominators work | [`EVALUATION.md`](EVALUATION.md) |

Regenerate or check the marked section with:

```bash
uv run python scripts/render_status.py
uv run python scripts/render_status.py --check
```

---

<!-- BEGIN:GENERATED_FROM_BASELINES -->
## Frozen M4 baselines (generated)

Validated from `eval/baseline/*.json`. Do not edit this section by hand; run `scripts/render_status.py`.

### Gold-pool extras (`m4_gold_pool_summary.json`)

| Metric | Value |
| ------ | ----- |
| extras_total | 24 |
| extras_real_card_pairs | 8 |
| extras_fixture_pairs | 16 |
| adjudicated (precision denominator) | 8 |
| valid | 3 |
| precision | 0.375 |
| by_class.duplicate_or_equivalent_interaction | 5 |
| by_class.valid_strict_two_card | 3 |

Notes from baseline: Precision computed over real-card pairs only; fixture pairs (is_fixture=True) are INVALID_CANDIDATE_DATA and excluded. Joins were not tightened to chase this distribution.

### Spellbook recovery (`m4_spellbook_recovery_summary.json`)

| Metric | Value |
| ------ | ----- |
| selected | 99 |
| eligible | 0 |
| rediscovered | 0 |
| compiler_unsupported | 99 |
| recall_eligible | null (no eligible pairs) |

Notes from baseline: Recall is defined only over eligible/supported entries. Spellbook absence is not a false positive. Gold-fixture eval-spellbook sample still recovers 2/2 eligible rows.
<!-- END:GENERATED_FROM_BASELINES -->

---

## How to read these numbers

- **24 extras** is the full gold-pool extra artifact population (real cards + fixture stand-ins).
- **16 fixture pairs** are evaluation artifacts (`INVALID_CANDIDATE_DATA`); they are not in the precision denominator.
- **8 real pairs** were adjudicated: **3** `valid_strict_two_card`, **5** `duplicate_or_equivalent_interaction` → precision **0.375**.
- Spellbook conventional recovery remains blocked by compiler coverage: **0 eligible** of **99** selected.

See [`EVALUATION.md`](EVALUATION.md) for denominators and [`runbooks/M4_FOLLOW_THROUGH.md`](runbooks/M4_FOLLOW_THROUGH.md) for the engineering sequence that must change these numbers before M5.
