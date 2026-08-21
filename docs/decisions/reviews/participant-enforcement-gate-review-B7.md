# Bundle B7 review — participant enforcement gate

**Reviewer:** `[DDR-P1-B7]`  
**Matrix:** [`participant-enforcement-gate-review.md`](participant-enforcement-gate-review.md)  
**Milestone:** M4 follow-through items 1–2  
**Assigned bundle:** Q1=A · Q2=bundle · Q3=silent · Q4=note · Q5=single

## Summary

Bundle B7 implements the participant gate **in search only** (`explore_pair`), **bundles** the five real Basalt bystander regression tests in the same PR, continues BFS **silently** on gate failure, and adds a **manual prose note** to `docs/STATUS.md` (outside the `render_status.py` generated block) explaining that frozen baselines are unchanged and full re-freeze remains deferred until post-eligibility runbook step 5. It does **not** rewrite `eval/baseline/m4_*.json` or run a baseline refresh at gate time.

Compared to B1 (recommended default), B7 is identical on Q1–Q3 and Q5; the only delta is Q4=**note** instead of Q4=**none**. The central question for this bundle is whether that soft note is **helpful reader guidance** or **misleading implied metric refresh**.

## Assigned options

| ID | Choice | Meaning for B7 |
|----|--------|----------------|
| Q1 | **A — search only** | Gate after `build_witness` + `Verifier.verify` inside `explore_pair`; verifier unchanged |
| Q2 | **bundle** | Gate + five adjudicated duplicate regressions in one PR (runbook §1 + §2) |
| Q3 | **silent** | Failed gate → do not return hit; continue BFS (no new `VerificationStatus`) |
| Q4 | **note** | Add manual STATUS prose only; **no** `eval/baseline/` rewrite, **no** `render_status.py` metric change |
| Q5 | **single** | One PR for gate + regressions + docs (not split gate vs docs like B8) |

## Soft note without re-freeze: helpful or misleading?

### Runbook and baseline authority (verified)

The M4 follow-through sequence is explicit:

```text
participant → regression → patterns → eligible → baseline (re-freeze) → m4exit
```

(`docs/runbooks/M4_FOLLOW_THROUGH.md` L11–27; mirrored in `ROADMAP.md` L90–105.)

Baseline re-freeze is **step 5**, after compiler curriculum and Spellbook eligibility — not at participant-enforcement time. The matrix itself marks Q4=**freeze** as “not recommended” at gate time (`participant-enforcement-gate-review.md` L63).

Frozen metrics live in `eval/baseline/m4_*.json`; `scripts/render_status.py` copies them into the delimited `<!-- BEGIN:GENERATED_FROM_BASELINES -->` section only. Manual prose in `docs/STATUS.md` § “How to read these numbers” is outside that block and survives `render_status.py --check`.

Current frozen gold-pool summary reports precision **0.375** with **5** `duplicate_or_equivalent_interaction` rows (`eval/baseline/m4_gold_pool_summary.json`). Those counts reflect **historical adjudication** of 24 accepted extras from a pre-enforcement discovery run, not live search acceptance today.

### Why re-freeze at gate time is infeasible anyway

`persist_gold_pool_extras` hard-requires exactly 24 extras matching `GOLD_EXTRA_ADJUDICATIONS` (`gold_extras.py` L179–182). After participant enforcement, `collect_gold_pool_extras` will stop accepting the five Basalt bystander pairs; a naive re-run would **raise** rather than produce an updated summary. A truthful re-freeze requires reconciling adjudication corpus, `GOLD_EXTRA_ADJUDICATIONS`, and baseline JSON together — scope that belongs to runbook step 5, not gate PR.

Therefore Q4=**freeze** at gate time would be wrong; the real choice is Q4=**none** (B1) vs Q4=**note** (B7).

### Verdict on the note

| If the note… | Effect |
|--------------|--------|
| Lives in manual STATUS prose (below generated block) | **Helpful** — preserves CI `--check` integrity |
| States frozen JSON is **unchanged** and precision **0.375** is historical adjudication | **Helpful** — prevents conflating adjudicated denominator with live search |
| Names deferred re-freeze to runbook step 5 (post-eligibility) | **Helpful** — aligns with roadmap sequence |
| Explains engine now rejects bystanders (tests + gate) while metrics lag | **Helpful** — closes the “open defect” narrative without fake numbers |
| Implies metrics were refreshed, precision improved, or baseline updated | **Misleading** |
| Sits inside or paraphrases the generated baseline table | **Misleading** — overwritten or drifts from JSON |
| Suggests M4 precision/coverage gates are closed | **Misleading** — eligibility and re-freeze remain |

**Conclusion:** A **constrained soft note is helpful, not misleading**, provided it is an explicit staleness disclaimer in manual prose. Without any note (B1), readers who skim STATUS tables may assume **0.375** still describes what `eval-gold-extras` would emit today — which it would not (and cannot without corpus work). B7’s Q4=note closes that gap at low cost; the risk is **wording discipline**, not the concept.

## Pros

- **Same correctness envelope as B1.** Bundled regressions satisfy matrix success criteria #1–#2 in one PR; five real `DUPLICATE_OR_EQUIVALENT_INTERACTION` pairs from `gold_extras.py` L54–73 locked via parametrized `explore_pair` tests.
- **Reuses existing detection.** `analyze_prerequisites` / `strict_two_card` already computed in `build_witness` (`explorer.py` L294–308; `classify.py` L81–102). Gate is a thin post-`VERIFIED` filter.
- **ADR-aligned search-only placement.** ADR 0001: explorer remains acceptance oracle on the discovery path. ADR 0002: gate enforces essential-piece participation via existing stamp.
- **Runbook-aligned deferral of metrics.** Skipping re-freeze matches step ordering; note documents the intentional gap instead of silent staleness.
- **Low blast radius on CI.** No JSON edits → `render_status.py --check` unchanged; no spurious precision drift in PR review.
- **Change discipline.** Behavior + regressions + contract docs in one PR (Q2=bundle, Q5=single), unlike B2 split.

## Cons

- **Dual truth window.** Until step 5, STATUS tables show 5 duplicates / 0.375 while engine rejects those pairs. Note mitigates but requires maintenance if prose drifts.
- **No live metric improvement yet.** Adjudicated precision denominator unchanged; M4 exit still blocked on eligibility + re-freeze. Note must not overclaim progress.
- **Silent observability (Q3).** Same as B1/B2: no typed rejection for bystander witnesses on search path.
- **Verifier gap (Q1=A).** Manual/fixture entry points outside `explore_pair` still unguarded until a future Q1∈{B,C} bundle.
- **Extra doc obligation.** Q4=note adds reviewer checklist: verify note placement, tone, and that ROADMAP item 1–2 closure is not confused with item 5–6.

## Architecture fit

| Boundary | Fit |
|----------|-----|
| ADR 0001 | **Strong.** Post-`VERIFIED` participant filter on discovery path; no search inside verifier; no second verify pass. |
| ADR 0002 | **Strong.** Gate uses stamped `strict_two_card` derived from participation, consistent with adjudication classes. |
| `search/README.md` | **Direct fix.** Closes “Enforcement — Not implemented” open defect (L65–75). |
| `verify/README.md` | **Explicit non-change.** Verifier scope unchanged; bystanders remain search acceptance concern. |
| `eval/baseline/README.md` | **Respected.** “Do not regenerate casually” (L56); note explains why JSON is stale, not wrong. |
| Search↔verify import boundary | **Preserved.** `tests/unit/test_search_boundary.py` unaffected. |

Recommended gate condition (identical to B1/B2):

```text
proof.status == VERIFIED
AND witness.classification.strict_two_card is True
→ return ExploredWitness
else → continue BFS
```

## Code and test changes (single PR)

| Area | Change |
|------|--------|
| `src/mtg_loop_engine/search/explorer.py` | After L345–347, require `witness.classification.strict_two_card` before return |
| `src/mtg_loop_engine/search/README.md` | Mark enforcement shipped; remove open-defect row |
| `ROADMAP.md` | Close M4 items 1–2 (participant + duplicate regressions); leave 3–6 open |
| `tests/eval/test_classify_store.py` | Flip `test_basalt_altar_is_not_strict_two_card` → `found is None`; keep `test_basalt_grounds_is_strict_via_cost_reduction` |
| `tests/eval/` or `tests/discovery/` | Parametrize five real Basalt duplicate pairs; assert `explore_pair` returns `None` |
| `docs/STATUS.md` | **Manual section only:** staleness note (see template below) |
| Package READMEs | `tests/eval/README.md`, `tests/README.md` — stop describing bystander acceptance as expected |

### Explicitly excluded (Q4=note, not freeze)

- No edit to `eval/baseline/m4_gold_pool_summary.json` or `m4_spellbook_recovery_summary.json`
- No change inside `<!-- BEGIN:GENERATED_FROM_BASELINES -->` … `<!-- END -->`
- No claim that `eval-gold-extras` was re-run successfully post-gate

### Suggested note template (manual prose)

> **Participant gate (shipped):** Search now rejects witnesses where an essential card in the searched pair never acts. Frozen baselines above are **unchanged** — they record pre-gate adjudication of 24 gold-pool extras (including five bystander duplicates). Re-running `eval-gold-extras` will not match this snapshot until adjudication corpus and baseline JSON are reconciled at runbook step 5 (after real-Oracle eligibility). Do not treat precision **0.375** as live post-gate search recall.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Note reads like metric refresh | Medium | Use template; PR review checklist; never edit generated block |
| Reader ignores note, trusts table | Low–Medium | Bold “unchanged” + link to runbook step 5 |
| `strict_two_card` false negative (Training Grounds) | Medium | Keep `test_basalt_grounds_is_strict_via_cost_reduction` green |
| Stale note after step 5 re-freeze | Low | Delete or rewrite note in the baseline PR that lands step 5 |
| Join-tuning to hide bystanders | Low | Reject at acceptance; runbook forbids |

## Rubric (100 pts)

| Criterion | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Correctness / safety | 25% | **24** | Bundled regressions lock five duplicates + positive gold path; same as B1 |
| Architecture fit | 25% | **24** | Search-only + classify stamp; ADR 0001/0002 aligned |
| Rollout / blast radius | 20% | **18** | No JSON churn; small dual-truth window mitigated by note if well-written |
| Testability | 15% | **14** | Full contract in one PR; matrix criteria #1–#2 satisfied |
| Roadmap / runbook alignment | 15% | **14** | Defers re-freeze correctly; note improves step-5 discoverability vs B1 |

**Total: 94 / 100**

No zero on Correctness/safety; above 70 threshold.

## Comparison to adjacent bundles

| Bundle | Q4 | Trade-off |
|--------|-----|-----------|
| **B1** | none | Leanest; relies on ROADMAP/tests alone for staleness |
| **B7** | note | +4 roadmap-alignment clarity; requires prose discipline |
| **B2** | none | Split regressions; weaker immediate test lock |
| freeze @ gate | — | **Rejected** — contradicts runbook ordering and breaks `persist_gold_pool_extras` expectations |

B7 ≈ B1 + constrained STATUS disclaimer. Prefer B7 when reviewers want STATUS readers explicitly warned; prefer B1 if minimizing doc surface is paramount.

## Verdict

**ACCEPT**

Bundle B7 is a strong implementation path: same engineering substance as the recommended B1 default, with Q4=note adding **helpful** (not misleading) context **when** the note is manual prose that states baselines are frozen, metrics are historical, and re-freeze awaits runbook step 5. Reject Q4=note if the PR would touch generated baseline tables or imply refreshed precision without JSON evidence.
