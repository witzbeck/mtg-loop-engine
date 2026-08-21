# Review: M4 participant enforcement gate

**Milestone:** M4 follow-through item 1 (and bundled item 2 regressions)  
**Status:** Resolved (2026-08-21) — winner **B7**  
**Skill:** `.cursor/skills/design-decision-review/SKILL.md`

## Problem

Search accepts witnesses where one essential oracle ID never acts (`strict_two_card is False`). Detection exists in `analyze_prerequisites`; `explore_pair` returns on first `VERIFIED` without checking participation. Five real Basalt-monolith pairs are adjudicated `duplicate_or_equivalent_interaction`.

## Evidence (verified)

| Layer | Location | Today |
|-------|----------|-------|
| Detection | `eval/classify.py` → `unused_oracle_ids`, `strict_two_card` | Works |
| Stamp | `search/explorer.py` `build_witness` | Copies classification |
| Accept | `explore_pair` L346–347 | `VERIFIED` only; ignores `strict_two_card` |
| Living defect | `tests/eval/test_classify_store.py` `test_basalt_altar_is_not_strict_two_card` | Asserts explore **succeeds** with bystander |
| Runbook | `docs/runbooks/M4_FOLLOW_THROUGH.md` §1 | Gate after witness build in search path |
| ADR 0001 | Discovery may speculate; verification may not | Search filter fits acceptance oracle role |
| ADR 0002 | Strict two-card = both essentials act | Participant gate enforces labeling contract |

## Decision dimensions

| ID | Question | Options | Notes |
|----|----------|---------|-------|
| Q1 | Gate placement | **A** search only · **B** verifier only · **C** both | **Blocks coding** |
| Q2 | Regression bundling | **bundle** same PR · **split** gate then regressions | Roadmap items 1+2 |
| Q3 | Rejection UX | **silent** continue BFS · **typed** proof status | Typed only if Q1 ∈ {B,C} |
| Q4 | Baseline refresh | **none** · **note** STATUS prose · **freeze** full re-freeze | Roadmap puts freeze after eligibility |
| Q5 | PR shape | **single** · **split** gate vs docs | Change discipline favors single |

## Bundles under review

| Bundle | Q1 | Q2 | Q3 | Q4 | Q5 | Hypothesis |
|--------|----|----|----|----|-----|------------|
| B1 | A | bundle | silent | none | single | Recommended default |
| B2 | A | split | silent | none | single | Gate without bundled regressions |
| B3 | B | bundle | silent | none | single | Verifier-only, silent explore |
| B4 | B | bundle | typed | none | single | Verifier-only + observability |
| B5 | C | bundle | typed | none | single | Defense in depth + typed |
| B6 | C | bundle | silent | none | single | Both layers, silent search |
| B7 | A | bundle | silent | note | single | Gate + soft STATUS note only |
| B8 | A | bundle | silent | none | split | Separate docs PR |

## Rubric (100 pts)

| Criterion | Weight |
|-----------|--------|
| Correctness / safety | 25% |
| Architecture fit (ADR 0001, 0002) | 25% |
| Rollout / blast radius | 20% |
| Testability | 15% |
| Roadmap / runbook alignment | 15% |

**Blockers:** Any bundle scoring &lt;70 total or 0 on Correctness/safety cannot win without human override.

## Success criteria (winner must satisfy)

1. `explore_pair(BASALT, PHYREXIAN_ALTAR)` and four other real Basalt duplicate pairs → no accepted hit (if Q2=bundle).
2. `explore_pair(BASALT, TRAINING_GROUNDS)` and gold_core 10/10 rediscoveries still succeed.
3. Docs stop describing enforcement as open defect.
4. No join-tuning to hide bystanders; no baseline re-freeze unless Q4=freeze (not recommended).

---

## Bundle reviews

Full per-bundle write-ups: `participant-enforcement-gate-review-B1.md` … `B8.md`.

| Bundle | Q1 | Q2 | Q3 | Q4 | Q5 | Score | Verdict |
|--------|----|----|----|----|-----|-------|---------|
| **B7** | A | bundle | silent | **note** | single | **94** | **ACCEPT** |
| B1 | A | bundle | silent | none | single | 92 | ACCEPT_WITH_RISKS |
| B4 | B | bundle | typed | none | single | 89 | ACCEPT_WITH_RISKS |
| B2 | A | split | silent | none | single | 87 | ACCEPT_WITH_RISKS |
| B3 | B | bundle | silent | none | single | 87 | ACCEPT_WITH_RISKS |
| B6 | C | bundle | silent | none | single | 85 | ACCEPT_WITH_RISKS |
| B8 | A | bundle | silent | none | split | 84 | ACCEPT_WITH_RISKS |
| B5 | C | bundle | typed | none | single | 82 | ACCEPT_WITH_RISKS |

### Merge notes (`[DDR-P2-COALESCE]`)

All eight `[DDR-P1-*]` bundle reviewers completed ([B1](648531b8-ca86-46e6-9bdb-a1ecef2fbc40), [B2](c2696a3c-1459-461e-8071-084aa9e39af3), [B3](b12165ef-8314-45c7-a26b-06983c234ff8), [B4](ec42d824-3273-4bd2-b492-838c974e2400), [B5](6cfb62f6-97b1-409d-9d36-036f72a72477), [B6](db8d9a2b-fc82-4b5f-9070-18056b29f55e), [B7](a4def5f7-1701-4856-a6c9-3f27ba61563d), [B8](69403031-7634-4ead-8bd6-972f3098c1e2)). All scored ≥70 with no zero on Correctness/safety. Reviewers **unanimously rejected** premature baseline re-freeze (no bundle used Q4=freeze). **Unanimous:** bundled regressions (Q2=bundle) beat split (B2) for immediate contract lock. **Unanimous:** split PR (B8) conflicts with `AGENTS.md` change discipline unless docs PR is blocking same-day follow-up.

**Q1 fork:** Search-only (A) won on architecture fit and runbook literal placement (`M4_FOLLOW_THROUGH.md` §1). Verifier-only (B3/B4) is viable when all-path `verify()` hardening matters, but requires participation logic in `verify/` without `verify → eval` import (`docs/ARCHITECTURE.md`). Dual-layer (B5/B6) adds defense-in-depth at duplication cost; reviewers prefer B1/B7 unless direct-verify bypass is a live CI concern.

**Q3 fork:** Typed rejection (B4/B5) improves observability but expands enum surface; not required for M4 exit when search silently continues (B1/B7).

**Q4 fork:** B7’s soft STATUS note (outside generated block) improves discoverability for step-5 re-freeze without contradicting runbook ordering; B1 and B7 differ only on that prose.

---

## Verdict

**Status:** Resolved and implemented (2026-08-21)  
**Review coalescer preferred:** **B7** (soft STATUS note)  
**Human lock for this PR:** **B1** — same as B7 except **Q4 = none** (no STATUS soft note; baselines stay historical until runbook step 5)

| Dimension | Resolved choice |
|-----------|-----------------|
| Q1 | **A** — search-only gate in `explore_pair` after `build_witness`, before return on `VERIFIED` |
| Q2 | **bundle** — gate + five real Basalt duplicate regressions in same PR |
| Q3 | **silent** — continue BFS when participation fails; no new `VerificationStatus` in this slice |
| Q4 | **none** — no baseline re-freeze; no STATUS soft note (human override of B7’s “note”) |
| Q5 | **single** — code + tests + README contract updates in one PR |

### Q4 note (not applied)

B7 recommended a soft STATUS caveat outside the generated block. The human chose **Q4 = none** for this PR; `eval/baseline/README.md` still documents that the frozen gold-pool summary is pre-gate.

### Implementation guardrails

1. Gate on **`unused_oracle_ids` empty** (runbook-aligned), not `strict_two_card` alone — preserves Training Grounds cost-reduction participation (`tests/eval/test_classify_store.py::test_basalt_grounds_is_strict_via_cost_reduction`).
2. Invert `test_basalt_altar_is_not_strict_two_card` → `explore_pair` returns `None`.
3. Parametrize five real Basalt duplicate pairs from `GOLD_EXTRA_ADJUDICATIONS` (`gold_extras.py` L54–72).
4. Realign `persist_gold_pool_extras` expected discovery count in same PR (contract fix, not baseline JSON).
5. **Do not** join-tune to hide bystanders.
6. Document verifier bypass on non-search paths in `verify/README.md`; defer verifier gate to a follow-up unless needed.

### Alternatives (if human override)

| If you need… | Use instead |
|--------------|-------------|
| Leanest doc surface | **B1** (drop Q4 note only) |
| Typed rejection + all-path enforcement | **B4** |
| Defense in depth + typed status | **B5** (explicit follow-up PR) |

### Next action

Implement on `feature/participant-enforcement` with RED tests first (matrix success criteria §1–3). Promote to ADR 0007 only if verifier gate ships later.
