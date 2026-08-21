# Agent contract (human / AI)

Authoritative operating rules for contributors and coding agents. In-repository docs are canonical. Home-directory plan files under `~/.cursor/plans/` are ephemeral session notes — never treat them as required reading or as a substitute for `ROADMAP.md`, ADRs, or package READMEs.

Cursor adapters under `.cursor/rules/` summarize workflow preferences; **this file and `CONTRIBUTING.md` win** on conflict.

## Mandatory preflight

Before changing behavior, tests, eval, or architecture-facing docs:

1. Read the root [`README.md`](README.md) (purpose, contracts, quick start).
2. Read [`ROADMAP.md`](ROADMAP.md): current milestone, next work, deferred items, frozen product decisions.
3. Read package READMEs for every package you will touch under `src/mtg_loop_engine/` (and related `tests/` / `eval/` folders). The package README is the **local operating contract**.
4. Read relevant ADRs under [`docs/decisions/`](docs/decisions/).
5. Skim existing tests that cover the area you are changing.
6. **Identify the active milestone** and confirm the change belongs there (or is an explicit M4 follow-through / bugfix called out in the roadmap).

Do not start implementation until this preflight is done.

## Hard boundaries

| Rule | Meaning |
|------|---------|
| Discovery may speculate; verifier may not | Search/joins may over-propose. The verifier never searches and never softens proof requirements to “find” a loop. |
| No Spellbook pairing leakage into discovery | Blind discovery must not use Spellbook pair labels (or equivalent pairing hints) as search guidance. |
| No LLM semantics on the `VERIFIED` path | Deterministic compiler / modeled semantics only. LLM-authored card semantics must not feed anything that can emit `VERIFIED`. |
| Incomplete relevant semantics fail closed | If proof-relevant coverage is incomplete (`PARTIAL_RELEVANT_TO_PROOF` or equivalent), never emit `VERIFIED`. |
| Spellbook absence ≠ falsehood | Missing from Spellbook is `ABSENT_FROM_REFERENCE`, not an automatic false positive. |
| `NOVEL` requires human review | Only human adjudication upgrades a candidate to `NOVEL`. Do not auto-promote. |
| No hidden functional third piece as strict two-card | Strict two-card means exactly two **essential** functional pieces. Generic fodder is OK; a functional external piece is not strict. |
| Do not silently broaden modeled rules to pass tests | Expand patterns or executor coverage deliberately, with tests and docs — not as a quiet patch to green a failing case. |

Align with frozen decisions in `ROADMAP.md` and ADRs `0001`–`0006`.

## Change discipline

Ship related updates **together** in the same change (or tightly linked commits on one feature branch):

- **Code** that changes behavior
- **Tests** that lock the intended contract
- **Package / folder README** updates when the local operating contract changes
- **`ROADMAP.md` and/or ADR** updates when milestone status, frozen decisions, or deferred scope is affected

Do not leave the next reader to reverse-engineer a contract change from diffs alone.

## Escalation

- Do **not** silently reinterpret frozen product decisions or Accepted ADRs.
- If a task conflicts with a frozen decision, **stop and escalate** to a human: open an ADR revision proposal or ask for an explicit override in the PR — do not “fix forward” by redefining terms.
- Deferred items in `ROADMAP.md` are off-limits for scaffolding (see Scope).

## Metrics

- Never copy old prose numbers from chat, plans, or stale markdown into new docs or PRs.
- Read live baselines under [`eval/baseline/`](eval/baseline/) (and regenerate STATUS/eval docs only when your change actually affects metrics — follow eval package docs).
- When reporting recovery, precision, or gold-pool rates, cite the baseline files (or freshly produced summaries), not memorized percentages.

## Tests

Treat tests as epistemic contracts. Map critical behavior to the owning suite under `tests/`; do not add vacuous or coverage-padding tests. See [`tests/README.md`](tests/README.md) and [`.cursor/rules/test-quality.mdc`](.cursor/rules/test-quality.mdc).

## Scope

- No deferred architecture scaffolding (LLM-on-`VERIFIED`, three-card discovery, Z3/SMT, full Comprehensive Rules, ManaBox, deployed UI, premature perf passes — see `ROADMAP.md`).
- Stay inside the active milestone / explicit follow-through unless a human widens scope.

## Local context

For any package under `src/mtg_loop_engine/`, the package `README.md` is the operating contract for that boundary: purpose, what belongs, what does not, and how it talks to neighbors. Prefer updating that README over inventing parallel “agent notes.”

## Land and return

When feature work is complete and the user has asked to open a PR or finish the branch: land once CI is green **and** the CI merge gate is satisfied, then switch back to up-to-date `main` and delete the local feature branch. Do not remain parked on a merged branch. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`.cursor/rules/land-and-return.mdc`](.cursor/rules/land-and-return.mdc), and [`.cursor/rules/ci-merge-gate.mdc`](.cursor/rules/ci-merge-gate.mdc).

## Related

- Contributor workflow: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Frozen decisions: [`docs/decisions/`](docs/decisions/)
- Gate document: [`ROADMAP.md`](ROADMAP.md)
