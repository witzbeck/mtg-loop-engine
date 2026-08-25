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

Validated from `eval/baseline/*.json`. Regenerate this section with `scripts/render_status.py` (hand edits drift from baselines).

### Gold-pool extras (`m4_gold_pool_summary.json`)

| Metric | Value |
| ------ | ----- |
| extras_total | 10 |
| extras_real_card_pairs | 3 |
| extras_fixture_pairs | 7 |
| adjudicated (precision denominator) | 3 |
| valid | 3 |
| precision | 1.0 |
| by_class.valid_strict_two_card | 3 |

Notes from baseline: Precision computed over real-card pairs only; fixture pairs (is_fixture=True) are INVALID_CANDIDATE_DATA and excluded. Joins were not tightened to chase this distribution.

### Spellbook recovery (`m4_spellbook_recovery_summary.json`)

| Metric | Value |
| ------ | ----- |
| selected | 1196 |
| eligible | 1 |
| rediscovered | 1 |
| compiler_unsupported | 1195 |
| recall_eligible | 1.0 |

Notes from baseline: Recall is defined only over eligible/supported entries. Measured via scripts/spellbook_compiler_priority.py against local Scryfall bulk (not network). Gold-fixture eval-spellbook sample still recovers 2/2 eligible rows. Most conventional pairs remain compiler_unsupported.
<!-- END:GENERATED_FROM_BASELINES -->

---

## How to read these numbers

- **10 extras** is the post-participant-gate gold-pool extra population (real cards + fixture stand-ins).
- **7 fixture pairs** are evaluation artifacts (`INVALID_CANDIDATE_DATA`); they are not in the precision denominator.
- **3 real pairs** were adjudicated: all `valid_strict_two_card` → precision **1.0**.
- Spellbook conventional recovery (50-page local sample): **1 eligible / 1 rediscovered** (Gravecrawler + Phyrexian Altar); most pairs remain `compiler_unsupported`.

See [`EVALUATION.md`](EVALUATION.md) for denominators. Active milestone is **M5** ([`runbooks/M5_NOVEL_CANDIDATES.md`](runbooks/M5_NOVEL_CANDIDATES.md)); M4 exit evidence is in [`ROADMAP.md`](../ROADMAP.md).
