# LAR v2 implementation report

Implementation of **Implementation Directive — LAR v2: Ephemeral Evaluation, Durable Knowledge** (2026-08-23).

---

## A. Structural changes

### Before

```text
eval/reviews/
  2026-08-21_5b8c45d/     # full v1 run committed
  _template/
  README.md

eval/
  adjudications/
  baseline/
  fixtures/
  # no calibration/

data/
  README.md               # no LAR execution path documented
```

### After

```text
data/
  README.md               # documents data/eval/lar/runs/
  eval/lar/runs/          # gitignored; v1 run copied locally

eval/
  README.md               # knowledge-plane invariant + calibration
  calibration/
    README.md
    adjudication_cases.jsonl
  reviews/
    README.md             # lifecycle + promotion contract
    _template/
      manifest.example.json
      promotion_candidates.example.json
      record.schema.json
      comparison.json
    promoted/
      README.md
      0001-m4-lar-v1/
        README.md
        summary.md
        manifest.json
        comparison.json

docs/runbooks/
  LOOP_ADJUDICATION_REVIEW.md   # v2 rewrite

.cursor/skills/
  loop-adjudication-review/
    SKILL.md                    # v2 rewrite

src/mtg_loop_engine/eval/
  lar_contracts.py              # manifest v2, calibration, promotion
  lar_calibration.py            # JSONL loader
```

---

## B. Migration — first LAR run

| Action | Detail |
|--------|--------|
| **Discarded from Git** | Entire `eval/reviews/2026-08-21_5b8c45d/` tree (phase-a/b/c, synthesis, PM report, raw records) |
| **Preserved locally** | Copy at `data/eval/lar/runs/2026-08-21_5b8c45d/` (gitignored) |
| **Promoted** | `eval/reviews/promoted/0001-m4-lar-v1/` — tempered `summary.md`, manifest v2, `comparison.json` (evidence paths updated to local run location) |
| **Routed findings** | Taxonomy/doc fixes → `docs/ADJUDICATION.md`; initial calibration → `eval/calibration/adjudication_cases.jsonl` (5 cases); participant gate → existing `tests/eval/test_classify_store.py`; stale baseline → documented M4 item 5 |

---

## C. LAR v2 protocol (demonstration)

Conceptual walkthrough using calibration case **CC-001** (Basalt + Phyrexian Altar bystander):

### B1 — Blind pair review

Reviewer receives Oracle text + witness only (no frozen `duplicate_or_equivalent_interaction` label):

```json
{
  "pair_scope_id": "oracle:basalt-monolith__oracle:phyrexian-altar",
  "proposed_class": "duplicate_or_equivalent_interaction",
  "confidence": "high",
  "rationale": "Altar never acts in loop steps; Basalt self-untaps alone.",
  "alternative_plausible_class": null,
  "needs_escalation": false
}
```

Written to `data/eval/lar/runs/<run_id>/phase-b/blind.jsonl`.

### B2 — Reveal and compare

Frozen label revealed → `agree_high_confidence` (not merely `agreement: true`).

### B3 — Adversarial challenge

Challenge reviewer argues **valid_strict_two_card** because Altar enables sacrifice outlet — rejected if witness shows unused oracle id.

Written to `challenge/oracle:basalt-monolith__oracle:phyrexian-altar.json`.

### Counterfactual path

Replace Altar with irrelevant static ability → engine should reject → candidate counterfactual negative (ephemeral until promoted to calibration/tests).

### Promotion candidate

```json
{
  "candidate_id": "PC-CC-001",
  "kind": "calibration_case",
  "target": "eval/calibration",
  "summary": "Canonical duplicate/bystander case",
  "confidence": "high",
  "requires_human_adjudication": true,
  "suspected_layer": "search_acceptance",
  "recommended_action": "Already promoted as CC-001; no action"
}
```

Emitted in `promotion_candidates.json` — **not** auto-committed during LAR.

---

## D. Calibration status

| Metric | Count |
|--------|-------|
| Classes represented | **4 / 8** |
| Classes with canonical cases | **3 / 8** (`duplicate_or_equivalent_interaction`, `valid_strict_two_card`, `invalid_candidate_data`) |
| Classes with boundary cases | **3 / 8** (`valid_strict_two_card`, `valid_generic_prerequisite`, plus duplicate via CC-003 neighbor) |

**Uncovered (intentionally):** `functional_external_requirement`, `unjustified_initial_state`, `rules_or_semantics_false_positive`, `needs_rules_research` — no responsible cases manufactured.

Initial cases: `CC-001` … `CC-005` in `eval/calibration/adjudication_cases.jsonl`.

---

## E. Provenance — manifest v2 example

See [`promoted/0001-m4-lar-v1/manifest.json`](promoted/0001-m4-lar-v1/manifest.json):

```json
{
  "schema_version": "2",
  "run_id": "2026-08-21_5b8c45d",
  "review_protocol": {
    "version": "1",
    "blinded_pair_review": false,
    "adversarial_challenge": false
  }
}
```

Future runs set `blinded_pair_review: true` and `adversarial_challenge: true` per v2 protocol.

---

## F. Tests

Added: `tests/eval/test_lar_calibration.py`

```bash
uv run pytest tests/eval/test_lar_calibration.py -q
uv run pytest  # full suite recommended before merge
```

Contracts tested:

- calibration JSONL parses via Pydantic
- unique stable `case_id`
- valid `AdjudicationClass` values
- promoted manifest v2 shape
- promotion candidate model usability

---

## G. Remaining debt

### Does not block M4

- Full 8/8 calibration coverage with canonical + boundary per class
- C2 held-out family expansion
- Large counterfactual library
- Automated CI LAR execution
- Dataset SHA256 hashing in manifest preflight helper
- Rewriting stale `comparison.json` architecture_debt keys to `suspected_layer` in future runs

### Blocks M4 (unchanged roadmap)

- Real Oracle compiler curriculum expansion
- Spellbook eligibility ≥ 1 pair
- Certified baseline re-freeze (pre-gate JSONL still stale)
- STATUS/docs reconciliation

### Deferred post-M4

- CI artifact upload for ephemeral LAR runs
- Schema migration tooling for blind/challenge record fields in JSON Schema

---

## H. Recommended next move

**Continue M4 compiler curriculum expansion** toward real Oracle coverage on gold_core families (especially `etb_damage_death`), then pursue Spellbook eligibility ≥ 1 — per `ROADMAP.md` sequencing. LAR v2 architecture is in place; the highest information-gain work now is engine capability, not another full LAR run on unchanged inventory.

---

## Acceptance criteria checklist (§26)

| Criterion | Status |
|-----------|--------|
| Routine runs under `data/eval/lar/runs/` | Done (documented + v1 copied) |
| No ordinary run under `eval/reviews/` | Done (v1 removed) |
| `eval/calibration/` contract | Done |
| Non-overlapping eval responsibilities documented | Done |
| Tier B blinding / reveal / challenge in runbook+skill | Done (protocol documented) |
| C1 vs C2 split | Done (documented) |
| Manifest v2 | Done |
| Information gain reporting | Done (runbook/skill) |
| Promotion candidates, no silent mutation | Done |
| Docs lifecycle | Done |
| M4 sequence preserved | Done |
