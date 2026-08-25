# Agent contract (human / AI)

Authoritative operating rules for contributors and coding agents. In-repository docs are canonical. Required reading is `ROADMAP.md`, ADRs, and package READMEs.

**This file and `CONTRIBUTING.md` win** on conflict with other workflow summaries.

## Prose

Say what is true. Explain what changes. Question what matters. Cut the rest.

## Mandatory preflight

Before changing behavior, tests, eval, or architecture-facing docs:

1. Read the root [`README.md`](README.md) (purpose, contracts, quick start).
2. Read [`ROADMAP.md`](ROADMAP.md): current milestone, next work, deferred items, frozen product decisions.
3. Read package READMEs for every package you will touch under `src/mtg_loop_engine/` (and related `tests/` / `eval/` folders). The package README is the **local operating contract**.
4. Read relevant ADRs under [`docs/decisions/`](docs/decisions/).
5. Skim existing tests that cover the area you are changing.
6. **Identify the active milestone** and confirm the change belongs there (or is an explicit M4 follow-through / bugfix called out in the roadmap).

Finish this preflight before implementation.

## Hard boundaries

| Rule | Meaning |
|------|---------|
| Search proposes; verify decides | Search/joins may over-propose. The verifier never searches and never softens proof requirements to find a loop. |
| Memory proposes; sources decide | Agent/human recall may hypothesize rules behavior. Oracle text, Comprehensive Rules, and official rulings decide modeled physics. Spellbook stays discovery/recovery only. See [`docs/RULES_EVIDENCE.md`](docs/RULES_EVIDENCE.md). |
| Blind discovery | Discovery uses compiled capabilities and joins only. Spellbook pair labels stay on the eval / recovery path (ADR 0001). |
| Deterministic `VERIFIED` path | `VERIFIED` requires deterministic compiler + modeled executor semantics (ADR 0003). |
| Fail closed on incomplete coverage | Incomplete proof-relevant coverage (`PARTIAL_RELEVANT_TO_PROOF` or equivalent) yields a typed rejection. |
| Spellbook absence is a label | Missing from Spellbook → `ABSENT_FROM_REFERENCE` (ADR 0004). |
| Humans own `NOVEL` | Only human adjudication upgrades absence to `NOVEL` (ADR 0005). |
| Strict two-card | Exactly two **essential** functional pieces. Generic fodder may appear; a functional external piece is a different claim (ADR 0002). |
| Deliberate coverage growth | Expand patterns or executor coverage with tests and docs when the model grows — not as a quiet patch to green a failing case. |

Align with frozen decisions in `ROADMAP.md` and ADRs `0001`–`0010`.

## Change discipline

Ship related updates **together** in the same change (or tightly linked commits on one feature branch):

- **Code** that changes behavior
- **Tests** that lock the intended contract
- **Package / folder README** updates when the local operating contract changes
- **`ROADMAP.md` and/or ADR** updates when milestone status, frozen decisions, or deferred scope is affected

Contract changes should be readable from the PR, not only from reverse-engineering diffs.

## Escalation

- Frozen product decisions and Accepted ADRs stay as written until a human revises them.
- If a task conflicts with a frozen decision, **stop and escalate**: ADR revision proposal or explicit PR override.
- Deferred items in `ROADMAP.md` stay deferred until a human widens scope (see Scope).

## Metrics

- Never copy old prose numbers from chat, plans, or stale markdown into new docs or PRs.
- Cite live baselines under [`eval/baseline/`](eval/baseline/) (and regenerate STATUS/eval docs only when the change affects metrics — follow eval package docs).
- When reporting recovery, precision, or gold-pool rates, cite baseline files or freshly produced summaries, not memorized percentages.

## Tests

Treat tests as epistemic contracts. Map critical behavior to the owning suite under `tests/`. See [`tests/README.md`](tests/README.md).

## Scope

- No deferred architecture scaffolding (LLM-on-`VERIFIED`, three-card discovery, Z3/SMT, full Comprehensive Rules, ManaBox, deployed UI, premature perf passes — see `ROADMAP.md`).
- Stay inside the active milestone in `ROADMAP.md` (or an explicit M4 follow-through / bugfix) unless a human widens scope.

## Local context

For any package under `src/mtg_loop_engine/`, the package `README.md` is the operating contract for that boundary: purpose, boundaries, and neighbors. Update that README when the contract changes.

## Land and return

When feature work is complete and the user has asked to open a PR or finish the branch: land once CI is green **and** the CI merge gate is satisfied, then switch back to up-to-date `main` and delete the local feature branch. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Related

- Contributor workflow: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Frozen decisions: [`docs/decisions/`](docs/decisions/)
- Gate document: [`ROADMAP.md`](ROADMAP.md)
- Rules evidence: [`docs/RULES_EVIDENCE.md`](docs/RULES_EVIDENCE.md)
