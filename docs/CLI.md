# CLI reference

Entry point: `uv run mtg-loop-engine` (`mtg_loop_engine.cli`).

| Command | Milestone | Purpose | Expected output |
| ------- | --------- | ------- | --------------- |
| `verify-gold` | M1 | Run `gold_core` positives and hard negatives through the witness verifier | Per-witness status + proof hash; exit `0` if all gold positives verify and hard negatives match expected rejections |
| `fetch-scryfall` | M0 | Download Scryfall Oracle Cards bulk snapshot into gitignored `data/` | JSON manifest (paths, hashes); creates local snapshot dirs |
| `fetch-spellbook` | M0 | Download Commander Spellbook sample pages into gitignored `data/` | JSON manifest; `--pages` controls how many API pages (default 2) |
| `compile-coverage` | M2 | Report deterministic compiler coverage on gold Oracle fixtures | Per-card fragment counts; JSON summary with `fragment_coverage`; exit `0` only if coverage is `1.0` on gold fixtures |
| `discover-gold` | M3 | Blind-discover `gold_core` pairs without pair labels | JSON discovery stats (`rediscovered`, `missing`, …); `VERIFIED` lines per hit; exit `0` if all gold pairs rediscovered |
| `eval-gold-extras` | M4 | Snapshot gold-pool extra discoveries and report adjudicated precision over real-card pairs | JSON: `extras_total`, real/fixture splits, `adjudicated`, `valid`, `precision`, `by_class`; persists store/JSONL |
| `eval-spellbook` | M4 | Reference recovery on a conventional two-card Spellbook-shaped JSONL | `RecoveryReport` JSON (`counts`, `rows`); optional `--out`; `--fetch-oracle` resolves names via Scryfall then compiles |
| `adjudicate-workbench` | M4 | Launch local Streamlit adjudication UI | Opens Streamlit on the workbench app; requires eval optional deps (`uv run --group eval …`) |

## Common flags

| Command | Flag | Meaning |
| ------- | ---- | ------- |
| `fetch-spellbook` | `--pages N` | Max Spellbook API pages to fetch |
| `eval-spellbook` | `--variants PATH` | JSONL of variants (default `eval/fixtures/spellbook_conventional_sample.jsonl`) |
| `eval-spellbook` | `--fetch-oracle` | Resolve missing names via Scryfall collection API, then compile |
| `eval-spellbook` | `--out PATH` | Write `RecoveryReport` JSON to path |
| *(all)* | `--version` | Print package version |

## Related docs helpers

| Command | Purpose |
| ------- | ------- |
| `uv run python scripts/render_status.py` | Refresh generated section of [`STATUS.md`](STATUS.md) from frozen baselines |
| `uv run python scripts/render_status.py --check` | Exit non-zero if `STATUS.md` is out of sync |
| `uv run python scripts/check_docs.py` | README / link / governance file checks |

See [`runbooks/M4_FOLLOW_THROUGH.md`](runbooks/M4_FOLLOW_THROUGH.md) for the post-docs engineering sequence these commands support.
