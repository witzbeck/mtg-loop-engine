# ADR 0007 — Corpus provenance: physics fixtures vs Oracle truth

## Status

Accepted

## Context

Gold positives, compiler fixtures, and M4 gold-pool precision all consume
`semantics/oracle_fixtures.py`. That module documents entries as “canonical Oracle”
with `is_fixture=False` meaning “real card,” while the file also states wording is
“tuned to deterministic patterns.”

Evaluation (`eval/gold_extras.py`) treats `is_fixture=False` pairs as
**precision-eligible real-card** discoveries. Several `is_fixture=False` texts
materially diverge from Magic Oracle (examples audited on `main` before migration):

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

1. **Three provenance classes** (enum-backed in code):
   - **`SYNTHETIC`** — teaching / physics stand-in. Synthetic `oracle_id` (e.g.
     `synthetic:…`) and visibly synthetic display name when invented. **Never**
     precision-eligible. May simplify rules deliberately. Example: replace the tuned
     Training Grounds physics object with `synthetic:generic-activated-cost-reducer`
     / **Synthetic Cost Reducer**; real Training Grounds exists only when an audited
     Oracle record is committed.
   - **`ORACLE_EXACT`** — the card’s **rules-relevant source record**, for every source
     field currently consumed by compilation or verification, matches the committed
     audited Oracle snapshot after **representation-only** canonicalization (e.g.
     Unicode NFC, CRLF→LF). **Never** normalize game text semantically. Eligible for
     product precision only when **both** essential cards are `ORACLE_EXACT` (and other
     ADR 0004 rules hold). Today’s consumed fields include at least: stable id,
     canonical name, Oracle text, type line / engine-derived types; as the compiler
     grows (mana cost, colors, keywords, faces, …), those fields enter the exactness
     contract.
   - **`ORACLE_DIVERGENT`** — **migration quarantine** for legacy/test material that
     uses a real-card identity with non-exact source semantics. **Never** product-
     precision eligible. **Not** a normal authoring destination: after the initial
     migration inventory is frozen, CI **must reject new** divergent records. Each
     existing divergent entry migrates toward honest `SYNTHETIC` identity or
     `ORACLE_EXACT`.

2. **Replace boolean `is_fixture`** with `Provenance` (or keep `is_fixture` only as a
   derived compatibility view that must **not** mean “precision-eligible”). Precision
   eligibility is centralized (e.g. `is_precision_eligible(pair)`), not rediscovered
   per eval module.

3. **Commit a small audited Oracle source-record subset** under repo control
   (gitignored bulk Scryfall remains for full ingest). CI asserts every
   `ORACLE_EXACT` fixture matches that snapshot after canonicalization, and asserts
   the frozen divergent inventory does not grow.

4. **API separation** so the honest thing is easy:
   - `physics_gold_card_pool()` — may include `SYNTHETIC` (and temporary divergent
     physics until migrated)
   - `oracle_gold_card_pool()` — `ORACLE_EXACT` only
   Product evaluation must **request** Oracle-backed material deliberately rather than
   filter a mixed pool after the fact.

5. **Rebuild `eval/baseline/m4_gold_pool_summary.json`** after taxonomy correction.
   Do **not** massage precision back to 1.0. If the precision-eligible denominator is
   empty, record `precision: null` / not yet measurable — that is the start of the
   trustworthy series. Document the discontinuity; old `1.0` figures are historical
   and not comparable.

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

- Short-term: gold-pool “real” extras that depended on Persistent Phoenix /
  divergent Skeleton leave the precision denominator; precision may be `null`.
- Compiler/discovery seams that needed tuned cost reduction keep working via
  **Synthetic Cost Reducer**, not a false Training Grounds identity.
- `SYNTHETIC` is deliberately scoped evidence about **engine physics**;
  `ORACLE_EXACT` is evidence about **Magic**. Keeping those claims separate
  strengthens both.
- Agents and docs must not cite pre-migration M4 gold-pool `precision: 1.0` as
  current real-card evidence.
