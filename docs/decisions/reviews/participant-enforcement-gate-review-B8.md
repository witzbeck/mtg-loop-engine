# Bundle B8 review — participant enforcement gate

**Reviewer:** `[DDR-P1-B8]`  
**Matrix:** [`participant-enforcement-gate-review.md`](participant-enforcement-gate-review.md)  
**Milestone:** M4 follow-through items 1–2  
**Assigned bundle:** Q1=A · Q2=bundle · Q3=silent · Q4=none · Q5=split (gate code vs docs)

## Summary

Bundle B8 matches the recommended **technical** shape for participant enforcement: a **search-only** gate in `explore_pair` after `Verifier.verify` returns `VERIFIED`, using the existing `strict_two_card` stamp from `build_witness` / `analyze_prerequisites`, with **silent BFS continuation** on rejection and **bundled regression tests** for the five real Basalt bystander pairs (`gold_extras.py` L54–73). No baseline re-freeze or STATUS refresh at gate time (Q4=none).

The distinguishing choice is **Q5=split PR**: behavioral code + locking tests land in one PR; package READMEs, architecture prose, and roadmap status updates land in a **separate docs PR**. That split conflicts with [`AGENTS.md`](../../../AGENTS.md) change discipline and delays matrix success criterion #3 until the second PR merges. It is implementable only with strict merge ordering and linked PR descriptions; it is **inferior to B1** (identical except Q5=single) as the default winner.

## Assigned options

| ID | Choice | Meaning for B8 |
|----|--------|----------------|
| Q1 | **A — search only** | Gate after `build_witness` + `Verifier.verify` inside `explore_pair`; verifier unchanged |
| Q2 | **bundle** | Gate + five Basalt duplicate regressions + flipped classify test in the **code PR** |
| Q3 | **silent** | Failed gate → do not return hit; continue BFS (no new `VerificationStatus`) |
| Q4 | **none** | No `eval/baseline/` or full STATUS re-freeze at gate time |
| Q5 | **split** | **Code PR** (explorer + tests); **docs PR** (READMEs, `ROADMAP.md`, `ARCHITECTURE.md`, test README notes) |

## Split vs single PR — contract + docs coupling

### What repo policy says

[`AGENTS.md`](../../../AGENTS.md) **Change discipline** (authoritative):

> Ship related updates **together** in the same change (or tightly linked commits on one feature branch):
>
> - **Code** that changes behavior  
> - **Tests** that lock the intended contract  
> - **Package / folder README** updates when the local operating contract changes  
> - **`ROADMAP.md` and/or ADR** updates when milestone status, frozen decisions, or deferred scope is affected  
>
> Do not leave the next reader to reverse-engineer a contract change from diffs alone.

[`CONTRIBUTING.md`](../../../CONTRIBUTING.md) adds:

- Milestone checklist item **5 — Docs**: update package READMEs / ADR / `ROADMAP.md` when contracts or milestones change.
- PR expectations: prefer **small, reviewable PRs** scoped to one milestone concern — but does **not** carve out an exception for deferring contract docs.

[`.cursor/rules/feature-branches.mdc`](../../../.cursor/rules/feature-branches.mdc) is a Cursor adapter only; it defers to `CONTRIBUTING.md` and does not authorize doc lag.

### What changes when the gate ships

The gate is not a private implementation detail. It **changes the local operating contract** documented in at least:

| Doc | Current state | Required update |
|-----|---------------|-----------------|
| `src/mtg_loop_engine/search/README.md` | “Enforcement — **Not implemented**” (L70) | Gate is acceptance requirement |
| `src/mtg_loop_engine/verify/README.md` | Explicit non-enforcement today | Clarify search owns participant acceptance |
| `src/mtg_loop_engine/eval/README.md` | Detect vs enforce split | Note search now enforces |
| `src/mtg_loop_engine/README.md` | Open defect callout | Close defect |
| `docs/ARCHITECTURE.md` | Non-enforcement paragraph (L95) | Enforcement on discovery path |
| `tests/README.md`, `tests/eval/README.md` | Bystander success documents open defect | Regressions lock new contract |
| `ROADMAP.md` | M4 item 1 open | Mark participant enforcement done (item 2 if bundled) |

`scripts/check_docs.py` validates README presence and link integrity; it does **not** assert that “open defect” prose is removed. Green CI on the **code PR alone** therefore does **not** prove contract docs are synchronized.

### Split PR — arguments for

| Argument | Weight |
|----------|--------|
| Code reviewers focus on behavior + tests without multi-file prose churn | Moderate |
| Docs PR can batch cross-package README + architecture edits coherently | Weak — same batch fits one PR |
| Aligns with “small PR” spirit for the behavioral diff | Moderate |

### Split PR — arguments against

| Argument | Weight |
|----------|--------|
| Direct violation of AGENTS change discipline | **High** |
| Window on `main` where code rejects bystanders but docs still say “open defect” | **High** — misleads agents and humans doing preflight |
| Matrix success criterion **#3** (“Docs stop describing enforcement as open defect”) unmet until docs PR lands | **High** |
| Two merge events, two review cycles, ordering dependency (docs PR must follow immediately) | Moderate |
| Risk docs PR is treated as optional follow-up (same class of failure as B2’s deferred regressions, but for **authoritative contracts**) | **High** |
| `ROADMAP.md` item 1 closure split from code that implements item 1 | Moderate |

### Comparison to B1 (recommended default)

| Dimension | B1 (Q5=single) | B8 (Q5=split) |
|-----------|----------------|---------------|
| Q1–Q4 | Identical | Identical |
| Behavior + tests + docs | One atomic merge | Two merges |
| AGENTS change discipline | Satisfied | Violated unless “tightly linked” is interpreted as back-to-back PRs (stretch) |
| Success criteria #1–#2 (if Q2=bundle) | Met at merge | Met at **code** PR merge |
| Success criterion #3 | Met at merge | Met only after **docs** PR |
| CI as contract oracle | Code + doc checks on one diff | Code PR can green while docs lie |

**Conclusion:** Splitting gate code from contract docs trades a small review-size win for a **documented epistemic failure mode** on `main`. Repository policy clearly favors **single PR (B1)** for this change. B8 is only defensible when a human explicitly wants decoupled review lanes **and** commits to landing the docs PR before any further M4 work.

## Pros

- **Strong technical core (Q1–Q4).** Same strengths as B1: reuses `analyze_prerequisites` / `strict_two_card`; ADR 0001/0002 aligned; silent BFS avoids new proof statuses; bundled regressions satisfy matrix criteria #1–#2 at code merge.
- **Evidence-backed gate placement.** `explore_pair` today returns on first `VERIFIED` without reading `strict_two_card` (`explorer.py` L345–347). Post-verify participant filter closes the defect without verifier scope creep.
- **Bundled safety net (Q2=bundle).** Five adjudicated `DUPLICATE_OR_EQUIVALENT_INTERACTION` Basalt pairs in `gold_extras.py` plus flipped `test_basalt_altar_is_not_strict_two_card` — stronger than split bundles (B2) on immediate correctness lock.
- **No premature metrics churn (Q4=none).** Baseline re-freeze remains at runbook step 5 after eligibility work.
- **Optional doc-review parallelism.** If team process demands prose review by a different reviewer, split PRs can run in parallel **before** merge — but both must land before the milestone item is considered closed.

## Cons

- **Change-discipline violation (Q5).** Primary weakness; see section above.
- **Temporary authoritative falsehood.** Between merges, `search/README.md`, `ARCHITECTURE.md`, and agent preflight still describe enforcement as open while behavior enforces — violates “do not leave the next reader to reverse-engineer.”
- **No CI guard on prose sync.** Unlike test failures, stale “open defect” text will not block the code PR.
- **Merge-order fragility.** If code PR merges and docs PR stalls, M4 item 1 is “done” in behavior but not in roadmap/docs — complicates exit review.
- **Verifier-only entry points unchanged.** Same residual gap as B1/B2: witnesses outside `explore_pair` are not gated (acceptable under Q1=A until a future ADR revisits placement).

## Architecture fit

| Boundary | Fit |
|----------|-----|
| ADR 0001 | **Strong.** Explorer remains discovery-path acceptance oracle; post-`VERIFIED` filter does not move search into proof obligations. |
| ADR 0002 | **Strong.** Enforces essential-piece participation via existing `strict_two_card` derivation. |
| `search/README.md` | **Requires update** — split defers the contract flip that architecture fit assumes. |
| `verify/README.md` | **No code change**; docs must still record search-owned enforcement. |
| Search↔verify import boundary | **Preserved** — no new cross-layer imports. |

Recommended gate condition (identical to B1/B2):

```text
proof.status == VERIFIED
AND witness.classification.strict_two_card is True
→ return ExploredWitness
else → continue BFS
```

## Code and test changes

### Code PR (B8 — behavioral scope)

| Area | Change |
|------|--------|
| `src/mtg_loop_engine/search/explorer.py` | After L345–347, require `witness.classification.strict_two_card` |
| `tests/eval/test_classify_store.py` | Flip `test_basalt_altar_is_not_strict_two_card` to `assert found is None` |
| `tests/eval/` or `tests/discovery/` | Parametrize five Basalt duplicate pairs from `gold_extras.py` L54–73 → `explore_pair` returns `None` |
| `tests/eval/test_classify_store.py` | Keep `test_basalt_grounds_is_strict_via_cost_reduction` green |

**Must not** merge code PR without bundled regressions (Q2=bundle).

### Docs PR (B8 — contract scope; separate PR)

| Area | Change |
|------|--------|
| `src/mtg_loop_engine/search/README.md` | Close open defect; document gate |
| `src/mtg_loop_engine/verify/README.md`, `eval/README.md`, package root README | Sync detect vs enforce narrative |
| `docs/ARCHITECTURE.md` | Update non-enforcement paragraph |
| `tests/README.md`, `tests/eval/README.md` | Remove “documents open defect until ships” framing |
| `ROADMAP.md` | Close M4 items 1–2 when regressions bundled |

**Must** link both PRs; docs PR should merge **immediately** after code PR (same day / same sprint), treated as blocking for M4 narrative closure.

### Explicitly excluded (Q4=none)

- No `eval/baseline/m4_*.json` rewrite  
- No full STATUS re-freeze via `scripts/render_status.py`

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Docs PR never lands or drifts | **High** | Block M4 item closure; link PRs; assign same owner |
| Agents read stale READMEs post-code-merge | **High** | Prefer B1; if B8, land docs PR before further M4 coding |
| `strict_two_card` false negative (Training Grounds) | Medium | Keep `test_basalt_grounds_is_strict_via_cost_reduction` in code PR |
| Reviewers approve code PR without doc follow-up plan | Medium | PR template: explicit docs PR link + checklist item |
| Split interpreted as permission to skip ROADMAP update | Medium | Milestone checklist in CONTRIBUTING applies to **both** PRs as one logical change |

## Success criteria (matrix)

| # | Criterion | B8 satisfaction |
|---|-----------|-----------------|
| 1 | Five Basalt duplicates → no accepted hit | **Yes** at code PR merge (Q2=bundle) |
| 2 | Basalt + Training Grounds + gold_core rediscoveries | **Yes** at code PR merge |
| 3 | Docs stop describing open defect | **No** until docs PR merges — **gap vs B1** |
| 4 | No join-tuning; no baseline re-freeze unless Q4=freeze | **Yes** |

## Rubric (100 pts)

| Criterion | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Correctness / safety | 25% | **24** | Bundled regressions + sound gate logic; split docs does not weaken runtime safety |
| Architecture fit | 25% | **24** | Q1=A aligns with ADR 0001/0002; deferred README updates do not change code architecture |
| Rollout / blast radius | 20% | **12** | Split creates doc/code drift on `main`; no CI prose guard |
| Testability | 15% | **14** | Code PR fully testable; docs PR relies on manual review |
| Roadmap / runbook alignment | 15% | **10** | Q2=bundle matches runbook §1+§2 in code; Q5=split conflicts with AGENTS + delays criterion #3 |

**Total: 84 / 100**

No zero on Correctness/safety; above 70 threshold. **Below B1** on rollout and roadmap alignment solely due to Q5=split.

## Verdict

**ACCEPT_WITH_RISKS**

Bundle B8 is **technically sound** (Q1–Q4 match the matrix’s recommended default) but **not recommended as the default winner** because Q5=split PR materially conflicts with [`AGENTS.md`](../../../AGENTS.md) change discipline and [`CONTRIBUTING.md`](../../../CONTRIBUTING.md) milestone doc expectations without compensating safety benefit. Prefer **B1** unless the team explicitly wants separated review lanes and will treat the docs PR as **blocking**, same-day follow-up — not optional cleanup.

If B8 is chosen: merge code PR first with bundled regressions; merge docs PR immediately after with cross-linked descriptions; do not mark M4 participant enforcement closed in narrative until both are on `main`.
