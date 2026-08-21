# Contributing

How humans and agents contribute to this repository. **`CONTRIBUTING.md` and [`AGENTS.md`](AGENTS.md) are authoritative.** Files under `.cursor/rules/` are Cursor adapters (shortcuts for the IDE); they must not contradict these docs. On conflict, follow this file and `AGENTS.md`.

In-repository docs are canonical. Do not require `~/.cursor/plans/...` (or any home-directory plan) as part of setup or review.

## Environment setup

Requires Python **≥ 3.13** and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
```

Optional evaluation / adjudication UI:

```bash
uv sync --group eval
uv run --group eval mtg-loop-engine adjudicate-workbench
```

See the root [`README.md`](README.md) for the full CLI quick-start list. Keep Oracle bulk JSON and local snapshots under `data/` (gitignored); never commit them.

## Feature-branch policy

- All non-trivial work lands on a `feature/<slug>` branch (never commit non-trivial changes directly to `main`).
- Keep `main` mergeable: CI green before merge.
- Default merge strategy is squash (see `.cursor/rules/merge-strategy.mdc`); say why in the PR if you need otherwise.
- Cursor adapter only: [`.cursor/rules/feature-branches.mdc`](.cursor/rules/feature-branches.mdc) — this file remains authoritative.

## Land and return

When a feature branch is finished, close the loop so the next change starts from current `main`:

1. Open a PR against `main` (when asked to finish or open a PR).
2. **Standing merge permission:** once required CI is green **and** the change’s critical behavior is covered by the CI suite (see below), land the PR (squash by default) without waiting for a second “merge it,” unless the user said to wait or hold.
3. After merge: check out `main`, fast-forward/pull from `origin`, delete the local feature branch, and leave a clean tree ready for the next `feature/<slug>`.

Cursor adapters: [`.cursor/rules/land-and-return.mdc`](.cursor/rules/land-and-return.mdc), [`.cursor/rules/ci-merge-gate.mdc`](.cursor/rules/ci-merge-gate.mdc).

## CI merge gate

Green CI authorizes merge only when critical path behavior is exercised by what CI runs today (`pytest`, `scripts/check_docs.py`, `scripts/render_status.py --check`). If a behavior change is not covered, add tests (or a CI step) in the same PR, or get an explicit “merge anyway.” Do not weaken tests to green the badge.

## Testing

- Run `uv run pytest` locally before opening or updating a PR.
- Behavior changes need tests in the same change (regression tests preferred when fixing adjudicated or gold failures).
- Do not weaken assertions or broaden modeled rules solely to pass existing tests — see [`AGENTS.md`](AGENTS.md).
- Critical path for a PR must be covered by the CI suite before treating green CI as merge OK (see **CI merge gate** above).
- Prefer epistemic contract tests (status, typed rejection, rediscovery, coverage, hashes) over coverage-padding or mock-only tests. Details: [`tests/README.md`](tests/README.md), [`.cursor/rules/test-quality.mdc`](.cursor/rules/test-quality.mdc).
- Pytest mechanical preferences (`strict-markers`, `xfail_strict`, warnings as errors) live in `pyproject.toml`; do not treat a global line-coverage percentage as the merge bar.

## Documentation expectations

- Update package / folder `README.md` files when the local operating contract changes.
- Update [`ROADMAP.md`](ROADMAP.md) at milestone exit (and when next-milestone goals shift).
- Record durable product decisions as ADRs under [`docs/decisions/`](docs/decisions/); do not bury them only in chat or ephemeral plans.
- Agents: complete the preflight in [`AGENTS.md`](AGENTS.md) before coding.

## Baseline-update expectations

- Frozen summaries live under [`eval/baseline/`](eval/baseline/).
- If your change affects gold-pool adjudication distribution, Spellbook recovery eligibility, or other recorded metrics:
  - Regenerate summaries via the project’s eval CLIs / scripts (see `eval/` package docs).
  - Update committed baseline JSON when the new numbers are intentionally frozen.
  - Refresh any STATUS / evaluation prose that cites those numbers — **never** paste stale percentages from memory.
- If metrics are unchanged, do not churn baseline files.

## Pull request expectations

- Use the GitHub PR template checkboxes; do not check items you did not verify.
- Prefer small, reviewable PRs scoped to one milestone concern (or one explicit M4 follow-through item).
- Call out architecture-contract impact and any ADR touches in the PR body.
- No Spellbook pairing leakage into discovery; no LLM semantics on the `VERIFIED` path.

## Milestone-impact checklist

Before merge, confirm:

1. **Milestone fit** — Work belongs to the active roadmap item (or an explicit follow-through listed in `ROADMAP.md`).
2. **Frozen decisions** — No silent reinterpretation of the frozen product table or Accepted ADRs.
3. **Deferred scope** — No scaffolding for explicitly deferred architecture.
4. **Tests** — Relevant unit / discovery / eval / gold tests updated or added.
5. **Docs** — Package READMEs, ADR, and/or `ROADMAP.md` updated when contracts or milestones change.
6. **Baselines** — `eval/baseline/*` read and updated only when metrics intentionally change.
7. **CI** — `uv run pytest`, `uv run python scripts/check_docs.py`, and `uv run python scripts/render_status.py --check` green.
