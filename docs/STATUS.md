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
| extras_total | 1 |
| extras_real_card_pairs | 1 |
| extras_fixture_pairs | 0 |
| adjudicated (precision denominator) | 1 |
| valid | 1 |
| precision | 1.0 |
| by_class.valid_strict_two_card | 1 |

Notes from baseline: ADR 0007 Waves 1–2 + Heliod re-promotion: Oracle gold_core has eight EXACT positives (paid Heliod grant + 0/0 Ballista; seed_grant_lifelink still quarantined from product VERIFIED). Gold-pool extra = Alarm+Gond (valid). Wave 3 SBA closed Basalt/Gond+Druid finite false positives. Precision uses eligible VALID denominator only.

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

- **1 Oracle gold-pool extra** (Alarm+Gond) after Wave 1; precision **1.0** on the eligible denominator.
- Historical **11 physics extras** remain under `PHYSICS_EXTRA_ADJUDICATIONS` / `collect_physics_pool_extras` — not product precision.
- Pre-migration gold-pool precision **1.0** on divergent “real” pairs is **historical and not comparable** (ADR 0007).
- Spellbook conventional recovery (50-page local sample): **1 eligible / 1 rediscovered** (Gravecrawler + Phyrexian Altar); most pairs remain `compiler_unsupported`.

See [`EVALUATION.md`](EVALUATION.md) for denominators. Active milestone is **M5** ([`runbooks/M5_NOVEL_CANDIDATES.md`](runbooks/M5_NOVEL_CANDIDATES.md)); M4 exit evidence is in [`ROADMAP.md`](../ROADMAP.md).
