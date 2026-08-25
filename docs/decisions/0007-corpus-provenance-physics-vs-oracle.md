# ADR 0007 — Corpus provenance: physics fixtures vs Oracle truth

## Status

Proposed

## Context

Gold positives, compiler fixtures, and M4 gold-pool precision all consume
`semantics/oracle_fixtures.py`. That module documents entries as “canonical Oracle”
with `is_fixture=False` meaning “real card,” while the file also states wording is
“tuned to deterministic patterns.”

Evaluation (`eval/gold_extras.py`) treats `is_fixture=False` pairs as
**precision-eligible real-card** discoveries. Several `is_fixture=False` texts
materially diverge from Magic Oracle (examples audited on `main`):

| Name | Corpus claim | Problem |
| --- | --- | --- |
| Training Grounds | “Activated abilities you control cost {1} less” | Real card: creature abilities, {2}, with a mana floor; Basalt is an artifact — the gold Basalt+Grounds positive is not an actual MTG combo under true Oracle |
| Hardened Scales | Free “Put a +1/+1 counter…” activated | Real card: replacement when counters would be placed |
| Gravecrawler | `{B}: Return … from GY` | Real: cast from GY requiring a Zombie; live Scryfall eval path already models the cast/Zombie gate better than this fixture |
| Reassembling Skeleton | `{1}: Return …` | Real: `{1}{B}`, returns tapped — net mana claims vs Ashnod gold are suspect |
| Persistent Phoenix | Dies-return creature, `is_fixture=False` | Invented name/physics used as a “real” precision pair |

Stronger verifier/search tests (#23–#25) made this sharper: the suite now defends
`VERIFIED` well against many false physics claims, while product precision can still
cite a denominator that confuses **teaching fixtures** with **Oracle truth**.

This is the same epistemology as ADR 0001 / 0003 / 0004: search may speculate;
verification must mean something; precision must not be optimized against a soft label.

## Decision

1. **Three provenance classes** (names may be enum-backed in code):
   - **`SYNTHETIC`** — teaching / physics stand-in. Synthetic `oracle_id` and display name
     when invented. **Never** precision-eligible. May simplify rules deliberately.
   - **`ORACLE_EXACT`** — text byte-identical to a committed, audited Oracle snapshot
     row for that card. Eligible for product precision only when both essentials are
     `ORACLE_EXACT` (and other ADR 0004 rules hold).
   - **`ORACLE_DIVERGENT`** — uses a real card **name** but non-exact / pattern-tuned
     text. Allowed temporarily for physics gold, but **must not** be precision-eligible;
     CI must fail if such an entry is treated as real for metrics.

2. **Replace boolean `is_fixture`** (or keep it as a derived view:
   `is_fixture ≡ provenance != ORACLE_EXACT`) so eval cannot silently treat tuned
   texts as real.

3. **Commit a small audited Oracle text snapshot** under repo control (gitignored bulk
   Scryfall remains for full ingest; the audited subset is explicit and reviewed).
   CI asserts every `ORACLE_EXACT` fixture matches that snapshot.

4. **Gold loops that need tuned physics** must be renamed/re-ided as `SYNTHETIC`
   (e.g. a “Cost Reducer” stand-in instead of claiming Training Grounds), **or**
   rebuilt on true Oracle + explicit generic prerequisites — not left as false
   real-card claims.

5. **Rebuild `eval/baseline/m4_gold_pool_summary.json`** after taxonomy correction.
   Do **not** massage precision back to 1.0. Document the discontinuity in the PR.

6. **Coverage floor stays at 92%** during this campaign. Do not pursue 95% until
   provenance + verifier-owned dependency completeness + proof identity (follow-on
   ADRs) are addressed enough that the percentage measures faithful claims.

## Non-decisions (follow-on)

- Verifier-owned mandatory recurrence dimensions (once-per-turn, pending triggers)
  — separate ADR / implementation slice; search must continue to call shared logic
  without `verify` importing `search`.
- Stronger claim/`proof_hash` binding — separate ADR; version proof schema.
- Full Scryfall bulk in CI — out of scope; audited subset only.

## Consequences

- Short-term: some gold positives and gold-pool “real” extras will be reclassified;
  precision denominator may shrink or drop below 1.0 — that is honesty, not regression.
- Compiler/discovery seams that depended on tuned text keep working via `SYNTHETIC`
  fixtures with honest names.
- M5 real-Oracle curriculum remains the path for product truth; gold_core becomes
  explicitly dual-purpose (physics school vs Oracle-backed claims).
- Agents and docs must stop citing M4 gold-pool precision as real-card evidence until
  the baseline is rebuilt under this taxonomy.
