# Contributing

How humans and agents contribute to this repository. **`CONTRIBUTING.md` and [`AGENTS.md`](AGENTS.md) are authoritative.**

In-repository docs are canonical. Session notes outside the repository are not durable strategy.

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

See the root [`README.md`](README.md) for the full CLI quick-start list. Keep Oracle bulk JSON and local snapshots under gitignored `data/`.

## Feature-branch policy

- All non-trivial work lands on a `feature/<slug>` branch (commit non-trivial changes off `main`).
- Keep `main` mergeable: CI green before merge.
- Prefer **squash merge** for pull requests by default to keep main-branch history concise and easy to scan.
- Keep separate commits only when preserving commit-by-commit history provides clear review, rollback, or auditing value.
- If using a non-squash strategy, state the reason in the PR description before merging.

## Land and return

When a feature branch is finished, close the loop so the next change starts from current `main`.

### When this applies

After work is ready to open a PR, land, or otherwise declare the branch complete.

### Merge authorization (standing preference)

When asked to open a PR or finish the branch:

1. Wait until required CI checks are **green**.
2. Confirm the **CI merge gate** below: critical behavior for this PR is covered by what CI runs.
3. Then **land** (prefer squash unless the PR says otherwise) without waiting for a second “merge it,” unless told to wait, review first, or hold.

If CI is red/pending, or critical behavior is untested in CI, stop and report — do not merge around the gate.

### Sequence

1. Ensure the branch is pushed and a PR against `main` exists (create one when asked to finish or open a PR).
2. Land under the authorization above once CI and the coverage gate pass.
3. After the PR is merged:
   - `git checkout main`
   - `git pull` (or `git pull --ff-only origin main`) so local `main` matches the remote
   - Delete the local feature branch (`git branch -d feature/<slug>`; use `-D` only when confirmed obsolete)
   - Delete the remote feature branch when GitHub did not already
4. Confirm with `git status` / `git branch` that the working tree is on up-to-date `main` and ready for the next `feature/<slug>`.

### Do not

- Stay checked out on a merged feature branch “for convenience”
- Force-push or delete `main`
- Merge with a dirty working tree that would be lost; commit, stash, or ask first
- Treat a draft PR, “WIP,” or “do not merge” label as landable

## CI merge gate

Green CI authorizes merge only when the change’s critical behavior is exercised by what CI runs.

### What CI runs today

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

- `uv run pytest` — executable contracts (gold, hard negatives, discovery, semantics, eval, …) **and** ≥92% **line** coverage on measured library code
- Branch coverage is reported in a second CI pytest pass (`--cov-branch`, no fail-under) so the line floor is not mixed with branch opportunities
- `uv run python scripts/check_docs.py` — docs hygiene
- `uv run python scripts/render_status.py --check` — STATUS ↔ baseline sync

Treat **95%** as a later quality milestone: raise only after P0 verifier soundness stays green, recurrence/pruning contracts exist, and remaining misses are classified by product value — not by padding.

### Before treating green CI as merge OK

Confirm the PR’s **critical path** is covered by that suite (or by a CI step added in the same PR):

| Change kind | Expect coverage in CI |
| --- | --- |
| Verifier / rules / proofs | Tests that assert `VERIFIED` or typed rejection |
| Compiler / patterns | Semantic / gold compile tests |
| Search / joins | Discovery or seam tests |
| Eval metrics / baselines | Eval tests and/or STATUS check |
| Docs / governance only | Docs + STATUS checks (pytest may be unchanged) |

If critical behavior is **not** covered, do **not** merge on green alone: add tests (preferred) or get an explicit “merge anyway.” Do not weaken tests to green the badge.

### Do not

- Merge with red or pending required checks
- Assume “tests exist somewhere” if they are not run in CI
- Weaken or skip tests to manufacture a green badge
- Count coverage-padding or vacuous tests as satisfying this gate (see [`tests/README.md`](tests/README.md))

## Testing

- Run `uv run pytest` locally before opening or updating a PR.
- Behavior changes need tests in the same change (regression tests preferred when fixing adjudicated or gold failures).
- Do not weaken assertions or broaden modeled rules solely to pass existing tests — see [`AGENTS.md`](AGENTS.md).
- Critical path for a PR must be covered by the CI suite before treating green CI as merge OK (see **CI merge gate** above).
- Contract tests and coverage floor: [`tests/README.md`](tests/README.md); product rails in [`AGENTS.md`](AGENTS.md).

## Documentation expectations

- Update package / folder `README.md` files when the local operating contract changes.
- Update [`ROADMAP.md`](ROADMAP.md) at milestone exit (and when next-milestone goals shift).
- Record durable product decisions as ADRs under [`docs/decisions/`](docs/decisions/).
- Agents: complete the preflight in [`AGENTS.md`](AGENTS.md) before coding.

## Baseline-update expectations

- Frozen summaries live under [`eval/baseline/`](eval/baseline/).
- If your change affects gold-pool adjudication distribution, Spellbook recovery eligibility, or other recorded metrics:
  - Regenerate summaries via the project’s eval CLIs / scripts (see `eval/` package docs).
  - Update committed baseline JSON when the new numbers are intentionally frozen.
  - Refresh any STATUS / evaluation prose that cites those numbers from the baseline files.
- If metrics are unchanged, leave baseline files alone.

## Pull request expectations

- Use the GitHub PR template checkboxes; check only items you verified.
- Prefer small, reviewable PRs scoped to one milestone concern (or one explicit M4 follow-through item).
- Call out architecture-contract impact and any ADR touches in the PR body.
- Product rails: [`AGENTS.md`](AGENTS.md) Hard boundaries (blind discovery, deterministic `VERIFIED` path).

## Milestone-impact checklist

Before merge, confirm:

1. **Milestone fit** — Work belongs to the active roadmap item (or an explicit follow-through listed in `ROADMAP.md`).
2. **Frozen decisions** — Align with the frozen product table and Accepted ADRs; escalate conflicts rather than reinterpreting them in the PR.
3. **Deferred scope** — No scaffolding for explicitly deferred architecture.
4. **Tests** — Relevant unit / discovery / eval / gold tests updated or added.
5. **Docs** — Package READMEs, ADR, and/or `ROADMAP.md` updated when contracts or milestones change.
6. **Baselines** — `eval/baseline/*` read and updated only when metrics intentionally change.
7. **CI** — `uv run pytest`, `uv run python scripts/check_docs.py`, and `uv run python scripts/render_status.py --check` green.
