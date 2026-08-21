# Bundle B3 review — participant enforcement gate

**Reviewer:** `[DDR-P1-B3]`  
**Matrix:** [`participant-enforcement-gate-review.md`](participant-enforcement-gate-review.md)  
**Milestone:** M4 follow-through items 1–2  
**Assigned bundle:** Q1=B · Q2=bundle · Q3=silent · Q4=none · Q5=single

## Summary

Bundle B3 implements the participant gate **in the verifier only** (`Verifier.verify`), rejecting witnesses where an essential oracle ID never acts in loop steps, and relies on **silent BFS continuation** in `explore_pair` (no explorer change: any non-`VERIFIED` proof already continues search). It **bundles** the five real Basalt bystander duplicate regressions in the **same PR** as the gate. No baseline re-freeze or STATUS prose update is required at ship time.

This closes the open defect on every path that can emit `VERIFIED` (discovery, compile→verify, gold fixtures), not only `explore_pair`. The trade-off is an architecture tension: `docs/ARCHITECTURE.md` forbids `verify → eval` and warns that eval-stamped classification must not become load-bearing for verifier acceptance — so the gate must **recompute participation from witness-native fields** (or extract shared logic to a neutral module), not import `analyze_prerequisites` or trust `witness.classification.strict_two_card` alone.

## Assigned options

| ID | Choice | Meaning for B3 |
|----|--------|----------------|
| Q1 | **B — verifier only** | Gate inside `Verifier.verify`; `explore_pair` unchanged |
| Q2 | **bundle** | Gate + five real Basalt duplicate regressions in one PR |
| Q3 | **silent** | Verifier returns typed rejection; explorer continues BFS (no new explore-side UX) |
| Q4 | **none** | No `eval/baseline/` or `docs/STATUS.md` refresh at ship time |
| Q5 | **single** | One PR for gate, regressions, and contract docs |

## Pros

- **Universal acceptance boundary.** ADR 0001 places truth at verification; `verify/README.md` invites gates for truth conditions. A verifier gate rejects bystander witnesses from discovery, hand-built fixtures, and compile→verify seams — search-only bundles (B1/B2) leave those paths open.
- **Silent explore is free.** `explore_pair` already returns only when `proof.status == VerificationStatus.VERIFIED` (`explorer.py` L345–347). A verifier rejection automatically continues BFS; no new search branching or synthetic proof objects required for Q3=silent.
- **Bundled regressions satisfy matrix success criteria.** Q2=bundle locks all five real `DUPLICATE_OR_EQUIVALENT_INTERACTION` Basalt pairs from `gold_extras.py` L54–73 in the same PR as the gate — stronger immediate safety than split bundles (B2).
- **ADR 0002 alignment.** Participation is an essential-piece truth condition: both named essentials must act. The gate enforces the same contract `analyze_prerequisites` already detects (`classify.py` L81–102).
- **Positive control preserved.** `test_basalt_grounds_is_strict_via_cost_reduction` (`test_classify_store.py` L22–30) must stay green; cost-reduction participation (`classify.py` L86–92) must be mirrored in the verifier-side check.
- **Observability without explore UX.** Q3=silent applies to search only; the verifier can still emit a **typed** `VerificationStatus` and `rejection_reason` on the proof (unlike search-only silent bundles that skip proof emission entirely on gate failure).

## Cons

- **Architecture layering constraint.** `docs/ARCHITECTURE.md` normative table: `verify → eval` is prohibited; dashed `search → eval` stamp “must never become a path for eval to influence verifier acceptance logic.” Verifier gate **cannot** `import analyze_prerequisites` or gate solely on eval-stamped `witness.classification.strict_two_card`. Participation logic must be reimplemented or extracted to a neutral module (`proofs/` or `semantics/`) within the single PR — duplication risk vs. B1/B2 reuse of classify in search.
- **Runbook wording mismatch.** `M4_FOLLOW_THROUGH.md` §1 says “after a witness is built” in the participant step; the parent matrix notes “gate after witness build in search path.” Verifier-only satisfies the **intent** (no bystander acceptance) but not the literal “search path” placement. Docs must be updated to say enforcement lives in verify, not explore.
- **New rejection status decision.** Existing `EXTERNAL_FUNCTIONAL_PIECE_REQUIRED` covers functional externals and essential-count overflow (`verifier.py` L167–182), not in-pair bystanders (`functional_external_requirements` is empty for Basalt+Altar). Overloading that enum conflates ADR 0002 concepts. A dedicated status (e.g. `ESSENTIAL_NON_PARTICIPANT`) is cleaner for hard negatives and proof contracts even when explore is silent.
- **ROADMAP / open-defect prose drift.** `ROADMAP.md` L79 says “not yet enforced in search”; B3 enforces in verify. Multiple READMEs (`search/`, `verify/`, `ARCHITECTURE.md`, `tests/eval/README.md`) must be updated together so the defect is not half-closed.
- **No defense in depth.** Unlike B5/B6 (Q1=C), a bug or bypass that constructs `VERIFIED` without calling `Verifier.verify` would not be caught. Today the only production acceptance path is verifier-injected explore; risk is low but nonzero for future entry points.

## Architecture fit

| Boundary | Fit |
|----------|-----|
| ADR 0001 | **Strong.** Verification may not speculate; participant check is deterministic witness-in / proof-out. Search continues to propose; verifier decides. |
| ADR 0002 | **Strong** if participation mirrors classify rules (actors in loop steps + continuous cost-reduction). **Weak** if gate reads only stamped labels without recomputation. |
| `docs/ARCHITECTURE.md` | **Conditional.** `verify → eval` import is **disallowed**. Recompute from `witness.essential_cards`, `witness.loop_actions`, `witness.initial_state`, `witness.card_semantics` inside `verify/` (or neutral shared module). Do **not** trust eval stamp alone. |
| `verify/README.md` | **Direct fix.** Moves “participant enforcement — open defect” to shipped; matches “add acceptance gates when they are truth conditions.” |
| `search/README.md` | **Indirect fix.** Enforcement moves off explore; diagram `verifier → VERIFIED \| reject → continueBFS` already matches B3 behavior without code change. |
| Search↔verify import boundary | **Preserved.** No `verify → search`; `tests/unit/test_search_boundary.py` unaffected. |

Recommended gate placement (verifier-only, silent explore):

```text
After existing coverage / functional-external gates, before executor run:
  participation_ok, detail = check_essential_participation(witness)
  if not participation_ok:
    return reject(<typed status>, detail)

explore_pair (unchanged):
  proof = verifier.verify(witness)
  if proof.status == VERIFIED:
    return ExploredWitness(...)
  else:
    continue BFS   # silent for bystander and all other rejects
```

Participation check must include cost-reduction participation (`classify.py` L86–92) so Training Grounds-style pairs remain `VERIFIED`.

## New rejection status?

| Option | Recommendation |
|--------|----------------|
| Reuse `EXTERNAL_FUNCTIONAL_PIECE_REQUIRED` | **Reject.** Bystander ≠ external functional piece; adjudication and hard negatives lose precision. |
| Reuse `NOT_A_LOOP` | **Reject.** Physics succeeded; failure is eligibility / essential-piece contract. |
| Add `ESSENTIAL_NON_PARTICIPANT` (or similar) | **Preferred.** Typed proof for tests (`tests/hard_negatives/`), eval exports, and future workbench filters. Compatible with Q3=silent (explore ignores status detail). |

Q3=silent does **not** argue against a new enum — it only means `explore_pair` does not branch on rejection subtype.

## Code and test changes

### Single PR scope (B3 — gate + regressions + docs)

| Area | Change |
|------|--------|
| `src/mtg_loop_engine/verify/verifier.py` | Add participation gate before executor run; return typed rejection |
| `src/mtg_loop_engine/verify/` (helper) | `check_essential_participation(witness)` — mirror `analyze_prerequisites` actor/cost-reduction rules without importing `eval` |
| `src/mtg_loop_engine/semantics/enums.py` | Add `ESSENTIAL_NON_PARTICIPANT` (or chosen name) to `VerificationStatus` |
| `src/mtg_loop_engine/verify/README.md` | Close open defect; document gate and status |
| `src/mtg_loop_engine/search/README.md` | Enforcement lives in verifier; explore continues on reject |
| `docs/ARCHITECTURE.md` | Update open-defect section; note verify-side enforcement |
| `ROADMAP.md` | Mark M4 items 1–2 implemented |
| `tests/eval/test_classify_store.py` | Flip `test_basalt_altar_is_not_strict_two_card` → `assert found is None`; keep `test_basalt_grounds_is_strict_via_cost_reduction` green |
| `tests/eval/` or `tests/discovery/` | Parametrize five real Basalt duplicate pairs from `GOLD_EXTRA_ADJUDICATIONS` L54–73; assert `explore_pair` returns `None` |
| `tests/hard_negatives/` or `tests/unit/` | Verifier rejects hand-built bystander witness with new status + reason |
| `tests/discovery/test_blind_discovery.py` | Gold 10/10 rediscoveries still `VERIFIED` (regression guard) |

### Explicitly excluded (Q4=none)

- No `eval/baseline/m4_*.json` rewrite
- No `scripts/render_status.py` baseline freeze

### Explicitly unchanged

- `explorer.py` loop body (silent continue is existing behavior)
- Join / interaction logic (runbook: no join-tuning to hide bystanders)

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `verify → eval` import or stamp-only gate | **High** | Code review against `ARCHITECTURE.md`; recompute participation in verify; add unit test that mutates stamped `strict_two_card=True` on bystander witness — verifier must still reject |
| Participation logic drift vs `classify.py` | Medium | Share test vectors between classify and verify tests; parametrize Basalt+Grounds (positive) and Basalt+Altar (negative) |
| Training Grounds false negative | Medium | Port cost-reduction branch (`classify.py` L86–92) into verify helper |
| Enum / proof-schema churn | Low | Single new status; update golden proof tests if status appears in fixtures |
| Runbook “search path” ambiguity | Low | Update `M4_FOLLOW_THROUGH.md` §1 to say “verifier rejects before `VERIFIED`” |
| Metrics not refreshed (Q4=none) | Low | Expected; precision improves only after later baseline freeze per roadmap |

## Rubric (100 pts)

| Criterion | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Correctness / safety | 25% | **23** | Bundled five duplicate regressions + universal verify path; participation reimplementation must match classify including cost reduction |
| Architecture fit | 25% | **19** | Strong ADR 0001/0002 fit at verifier boundary; minus for eval-import prohibition requiring duplicated/extracted logic and runbook literal “search path” mismatch |
| Rollout / blast radius | 20% | **18** | Single PR, no baseline; all discovery hits re-verified; gold_core / compile_verify must stay green |
| Testability | 15% | **14** | Clear oracles: explore `None`, verifier typed status, blind 10/10 guard; silent explore does not block proof-level asserts |
| Roadmap / runbook alignment | 15% | **13** | Satisfies M4 items 1+2 in one PR; runbook wording and ROADMAP “in search” prose need coordinated edits |

**Total: 87 / 100**

No zero on Correctness/safety; above 70 threshold.

## Verdict

**ACCEPT_WITH_RISKS**

Bundle B3 is a viable path when the team wants **verifier-centric enforcement**, **full duplicate regression lock in one PR**, and **silent explore without touching `explorer.py`**. Proceed only if implementation **recomputes participation inside verify** (or a neutral shared module) — never imports `eval.classify` and never gates on eval-stamped `strict_two_card` alone — and adds a **dedicated rejection status** rather than overloading `EXTERNAL_FUNCTIONAL_PIECE_REQUIRED`. Update runbook and architecture prose so “participant enforcement” is documented at the verifier boundary, not as a search-only filter.

Compared to B1 (search-only + bundle): B3 trades simpler explore code for layering discipline and duplicated participation logic, but wins **all-path** protection. Compared to B2 (search-only + split): B3 is **stronger on testability and immediate success criteria** (Q2=bundle) at the cost of verifier scope and architecture care.
