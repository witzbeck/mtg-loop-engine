# Bundle B2 review — participant enforcement gate

**Reviewer:** `[DDR-P1-B2]`  
**Matrix:** [`participant-enforcement-gate-review.md`](participant-enforcement-gate-review.md)  
**Milestone:** M4 follow-through items 1–2  
**Assigned bundle:** Q1=A · Q2=split · Q3=silent · Q4=none · Q5=single

## Summary

Bundle B2 implements the participant gate **in search only** (`explore_pair`), rejects witnesses where an essential oracle ID never acts by consulting the existing `analyze_prerequisites` / `strict_two_card` stamp, and **continues BFS silently** when the gate fails. It ships the gate in **one PR without bundled regression tests** for the five real Basalt bystander pairs (runbook step 2 deferred to a follow-up PR). No baseline re-freeze or STATUS prose update is required at gate time.

This matches the runbook’s stated sequence (participant enforcement → regress duplicates) and keeps the first change set small: one behavioral guard in `explorer.py`, package README / roadmap contract updates, and minimal gate-level tests. The trade-off is a deliberate window where the gate lands without the adjudicated duplicate regressions that would lock the contract end-to-end.

## Assigned options

| ID | Choice | Meaning for B2 |
|----|--------|----------------|
| Q1 | **A — search only** | Gate after `build_witness` + `Verifier.verify` inside `explore_pair`; verifier unchanged |
| Q2 | **split** | Gate PR first; five Basalt duplicate regressions in a separate PR |
| Q3 | **silent** | Failed gate → do not return hit; continue BFS (no new `VerificationStatus`) |
| Q4 | **none** | No `eval/baseline/` or `docs/STATUS.md` refresh at gate time |
| Q5 | **single** | One PR for gate + docs (not a split gate-vs-docs PR like B8) |

## Pros

- **Reuses existing detection.** `analyze_prerequisites` already computes `used_oracle_ids`, `unused_oracle_ids`, and `strict_two_card` from loop steps (`classify.py` L81–84, L94–102). `build_witness` stamps classification onto the witness (`explorer.py` L294–308). The gate is a thin acceptance filter, not new semantics.
- **ADR-aligned placement.** ADR 0001 positions the explorer as the discovery-path acceptance oracle; ADR 0002 ties strict two-card to essential-piece participation. Search-only enforcement closes the documented open defect in `search/README.md` without expanding verifier scope or risking search↔verify boundary tests.
- **Silent BFS is natural here.** With Q1=A, typed rejection UX (Q3=typed) would require verifier changes or synthetic proof objects. Continuing search after a bystander witness is already the pattern for `VERIFIED`-fail paths (`search/README.md` diagram: `reject → continueBFS`).
- **Split matches runbook ordering.** `M4_FOLLOW_THROUGH.md` lists participant enforcement (§1) before regress real duplicate cases (§2). A gate-only PR mirrors that narrative and keeps review focused.
- **Low blast radius on metrics.** Q4=none avoids touching `eval/baseline/m4_*.json` before compiler/eligibility work; gold-pool precision counts should improve only after bystander hits stop being accepted, but that refresh belongs later per roadmap freeze step.
- **No join-tuning temptation.** Rejecting at acceptance preserves the runbook’s “do not chase join-tuning to hide bystanders” constraint.

## Cons

- **Deferred regression lock.** Success criterion #1 in the matrix (`explore_pair` on five real Basalt duplicates → no hit) is **not** satisfied until the follow-up PR. The gate PR can merge with only inverted/extended classify tests, leaving a correctness gap if the guard is wrong or incomplete.
- **AGENTS.md change-discipline tension.** Project guidance prefers shipping behavior + locking tests together. Split intentionally violates that for reviewability; reviewers must track the follow-up as mandatory, not optional cleanup.
- **Temporary test contradiction.** `tests/eval/test_classify_store.py::test_basalt_altar_is_not_strict_two_card` currently asserts `explore_pair` **succeeds** while `strict_two_card is False` (L13–19). Gate PR must change this test; without bundled duplicate regressions, coverage of all five adjudicated pairs waits.
- **Silent failure observability.** Q3=silent means no typed proof for “essential never acted”; debugging discovery misses requires re-running `analyze_prerequisites` or logging. Acceptable for M4 but weaker than verifier-typed bundles (B4/B5).
- **Verifier gap remains.** Witnesses built outside `explore_pair` (manual fixtures, future entry points) could still carry bystander labels without rejection until/unless a later bundle adds verifier defense (Q1=C).

## Architecture fit

| Boundary | Fit |
|----------|-----|
| ADR 0001 | **Strong.** Search proposes; explorer + injected verifier accept. Adding a post-`VERIFIED` participant filter on the discovery path does not move search into proof obligations or add a second verify pass. |
| ADR 0002 | **Strong.** Gate enforces “both essentials act” via existing `strict_two_card` / `essential_functional_count == 2` logic already derived from participation, not raw card count. |
| `search/README.md` | **Direct fix.** Moves “Enforcement — Not implemented” to shipped behavior; diagram already shows classify → stamp before verifier. |
| `verify/README.md` | **Explicit non-change.** Verifier continues to reject functional externals and coverage gaps; participant bystanders remain a search acceptance concern until a future ADR revisits Q1. |
| Search↔verify import boundary | **Preserved.** No new `verify` → `search` or duplicate verification; `tests/unit/test_search_boundary.py` unaffected. |

Recommended gate condition (search-only, silent):

```text
proof.status == VERIFIED
AND witness.classification.strict_two_card is True
(and equivalently: no unused pair oracle IDs in analyze_prerequisites)
→ return ExploredWitness
else → continue BFS
```

Prefer reading the stamped `witness.classification.strict_two_card` (already computed in `build_witness`) rather than re-calling `analyze_prerequisites` to avoid drift.

## Code and test changes

### Gate PR (B2 scope — single PR)

| Area | Change |
|------|--------|
| `src/mtg_loop_engine/search/explorer.py` | In `explore_pair`, after L345–347 `VERIFIED` check, require `witness.classification.strict_two_card`; else continue queue |
| `src/mtg_loop_engine/search/README.md` | Close open defect; document gate as acceptance requirement |
| `ROADMAP.md` | Mark participant enforcement implemented (regressions still open) |
| `tests/eval/test_classify_store.py` | Flip `test_basalt_altar_is_not_strict_two_card` to `assert found is None` (or equivalent) |
| Optional | Add one focused unit test in `tests/unit/test_explorer.py` proving a mock verifier + bystander witness does not return early |

### Follow-up PR (explicitly out of B2 bundle — runbook §2)

| Area | Change |
|------|--------|
| `tests/eval/` or `tests/discovery/` | Parametrize five real `DUPLICATE_OR_EQUIVALENT_INTERACTION` Basalt pairs from `gold_extras.py` L54–73; assert `explore_pair` returns `None` |
| `tests/eval/test_classify_store.py` | Retain positive `test_basalt_grounds_is_strict_via_cost_reduction` |
| Docs | Note regressions complete; M4 item 2 closed |

### Explicitly excluded (Q4=none)

- No `eval/baseline/m4_gold_pool_summary.json` rewrite
- No `scripts/render_status.py` run for baseline freeze

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Gate merges without regression PR | Medium | Track follow-up as blocking for M4 item 2; link in PR description; do not start M5 |
| `strict_two_card` false negative (Training Grounds-style cost reduction) | Medium | Keep `test_basalt_grounds_is_strict_via_cost_reduction` green in gate PR; cost-reduction participation already in classify L86–92 |
| Functional-external false positives | Low | Classify leaves `functional` empty for bystanders today; gate uses participation count, consistent with adjudication notes |
| Silent search cost | Low | Bystander witnesses already paid verify cost; extra BFS depth bounded by existing limits |
| Split PR drift | Medium | Gate PR description must name exact follow-up test list (five oracle-id pairs from `GOLD_EXTRA_ADJUDICATIONS`) |

## Rubric (100 pts)

| Criterion | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Correctness / safety | 25% | **21** | Logic is sound and evidence-backed, but split defers the strongest safety net (five duplicate regressions) |
| Architecture fit | 25% | **24** | Search-only + existing classify stamp aligns with ADR 0001/0002 and package contracts |
| Rollout / blast radius | 20% | **17** | Smaller first PR; temporary incomplete M4 closure |
| Testability | 15% | **11** | Gate PR can flip one test; full contract tests delayed |
| Roadmap / runbook alignment | 15% | **14** | Matches §1→§2 sequence; matrix success criteria #1 deferred |

**Total: 87 / 100**

No zero on Correctness/safety; above 70 threshold.

## Verdict

**ACCEPT_WITH_RISKS**

Bundle B2 is a viable implementation path when the team prioritizes a **small, reviewable gate PR** and accepts **mandatory follow-up** for runbook §2 regressions. It is slightly weaker than B1 (bundled regressions) on testability and immediate success-criteria satisfaction, but stronger on rollout granularity and literal runbook sequencing. Proceed only if the follow-up regression PR is scheduled as blocking for M4 exit, not optional cleanup.
