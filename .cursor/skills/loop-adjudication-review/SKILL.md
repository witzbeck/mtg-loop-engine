---
name: loop-adjudication-review
description: >-
  Multi-phase LAR v2: ephemeral execution under data/eval/lar/runs/, durable
  knowledge via promotion. Tiered review of adjudication classes, blind pair
  adjudication, adversarial challenge, known vs held-out mechanic families.
  Use when evaluating loop claims — not engineering design forks.
---

# Loop adjudication review (LAR) v2

Human-style review of **what loops the project claims to find**, with explicit **promotion discipline**. Distinct from [`design-decision-review`](../design-decision-review/SKILL.md).

**Runbook:** [`docs/runbooks/LOOP_ADJUDICATION_REVIEW.md`](../../../docs/runbooks/LOOP_ADJUDICATION_REVIEW.md)  
**Execution:** `data/eval/lar/runs/<run_id>/` (gitignored)  
**Exceptional evidence:** [`eval/reviews/promoted/`](../../../eval/reviews/promoted/)

## Core invariant

> Evaluation execution is ephemeral. Accepted knowledge is durable.

Generate freely. Challenge aggressively. Promote sparingly. **Do not commit routine runs.**

## When to use

- Measure taxonomy calibration coverage and blind-label agreement
- Find counterexamples and boundary cases worth promoting
- Re-run after participant gate, compiler curriculum, or baseline re-freeze
- Propose routing to `eval/adjudications/`, `eval/calibration/`, `tests/`, `docs/`

## Tier overview

| Tier | Phase | Units | Parallelism |
|------|-------|-------|-------------|
| 0 | Preflight + manifest v2 | 1 | sequential |
| A | Taxonomy calibration coverage | 8 classes | 8 `[LAR-P1-A-*]` |
| B1 | Blind pair adjudication | batches | 4 `[LAR-P1-B1-*]` |
| B2 | Reveal + compare | merge | sequential after B1 |
| B3 | Adversarial challenge | sampled + disagreements | `[LAR-P1-B3-*]` |
| C1 | Known-family regression | 5 families | 5 `[LAR-P1-C1-*]` |
| C2 | Held-out generalization | small set | optional `[LAR-P1-C2-*]` |
| D | Cross-tier synthesis | 1 | `[LAR-P2-SYNTH]` |

Run B2 after B1 freezes blind outputs. Run D after A, B3, C legs terminal.

## Tier 0 — Preflight

1. Read `README.md`, `ROADMAP.md`, `docs/ADJUDICATION.md`, `docs/EVALUATION.md`.
2. `uv sync && uv run pytest` — record in manifest.
3. Create **`data/eval/lar/runs/<run_id>/`** from `eval/reviews/_template/`.
4. Fill manifest v2 (`mtg_loop_engine.eval.lar_contracts.LarManifestV2` fields).

**Never** create `eval/reviews/<run_id>/` for ordinary runs.

## Tier A — Calibration coverage

For each `AdjudicationClass`:

1. Count rows in `eval/calibration/adjudication_cases.jsonl` with that `expected_class`.
2. Note canonical vs boundary presence.
3. Sample observed adjudications for context only.
4. Write `phase-a/<class_slug>.json`.

Zero calibration rows → report **coverage unknown**.

## Tier B1 — Blind pairs (critical)

**Do not inspect frozen labels before blind classification.**

Each reviewer receives Oracle text, witness, taxonomy — not committed adjudication rows.

Write `phase-b/blind.jsonl` with:

- `proposed_class`, `confidence`, `rationale`, `assumptions`, `rules_evidence`
- `alternative_plausible_class`, `needs_escalation`

## Tier B2 — Reveal + compare

After blind freeze, load frozen labels and emit compare outcomes:

`agree_high_confidence` | `agree_low_confidence` | `disagree` | `taxonomy_ambiguous` | `insufficient_evidence`

Merge to `phase-b/pairs.jsonl`.

## Tier B3 — Adversarial challenge

For disagreements, low-confidence agreements, boundary cases, and a small agreement sample:

> Strongest argument the classification is wrong.

Write `challenge/*.json`. One distinct challenge task — not redundant same-context reviewers.

**Independence language:** parallel same-model agents are throughput, not statistical replication.

## Tier C1 — Known families

Families: `mana_tap_untap`, `token_etb_untap`, `zone_recursion_sacrifice`, `counters_damage`, `etb_damage_death`.

Regression on gold_core — do not claim broad generalization from C1 alone.

## Tier C2 — Held-out cases

Small real Oracle cases excluded from implementation curriculum. Document holdout rationale.

## Counterfactuals

Generate nearby negatives for positive witnesses when practical. Ephemeral until promoted.

## Tier D — Synthesis

Coalescer writes:

- `synthesis.md` — evidence scope first; knowledge changes + coverage sections required
- `comparison.json`
- `promotion_candidates.json` (`PromotionCandidate` shapes)

Use **`suspected_layer`** in cross-tier signals — not definitive `architecture_debt.layer` from disagreement alone.

Report **information gain**, not a composite LAR score.

## Promotion discipline

Emit `promotion_candidates[]`; **never** edit during LAR:

- `eval/adjudications/*`
- `eval/calibration/*`
- `eval/baseline/*`
- engine code
- committed tests

Humans land promotions via PR.

## Evidence discipline

Label findings: `observed` | `inferred` | `suspected` | `confirmed`.

Temper confidence by: real-card sample size, fixture proportion, taxonomy coverage, known vs held-out families.

## Schemas

- `mtg_loop_engine.eval.lar_contracts` — manifest v2, calibration, promotion candidates
- Examples: `eval/reviews/_template/`

## Partial failure

Missing P1 leg: synth marks `unverified_legs` and proceeds with partial merge.

## Task stubs

**Blind pair batch:**

```
[LAR-P1-B1-batch2] LAR v2 run data/eval/lar/runs/<run_id>/.
Blind adjudicate 6 pairs — NO frozen labels before proposed_class.
Write phase-b/blind.jsonl entries only. No durable artifact edits.
```

**Synthesis:**

```
[LAR-P2-SYNTH] Merge LAR v2 tiers for data/eval/lar/runs/<run_id>/.
Output synthesis.md, comparison.json, promotion_candidates.json.
Include knowledge_changes and coverage sections.
```
