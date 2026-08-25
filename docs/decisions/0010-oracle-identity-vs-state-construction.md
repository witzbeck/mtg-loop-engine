# ADR 0010 — Oracle identity exactness vs state-construction completeness

## Status

Accepted

## Context

ADR 0007 defines `ORACLE_EXACT` as matching the **rules-relevant source record**
for fields currently consumed by compilation or verification. That wording is
correct, but two pressures collide:

1. **Identity** — proving the fixture is the named Magic card (text, types, …).
2. **State construction** — building a legal starting board and paying real
   activation costs (printed power/toughness, mana cost, …).

Without an explicit split, “exactness” can drift into an unmaintainable
requirement to model an entire card before using any ability — or the opposite
error: discovery silently substitutes universal `1/1` and free lifelink seeds
while the audited text is still called “exact” (Heliod + Walking Ballista).

Printed P/T and activation costs unquestionably belong in **state construction**.
They enter the **identity exactness** contract when the engine consumes them for
those purposes — not before, and not as a demand to snapshot every Scryfall field.

## Decision

1. **Two layers (same audited record, different obligations):**

   | Layer | Question | Obligation |
   | --- | --- | --- |
   | **Oracle identity exactness** | Is this fixture the named card for the fields we already claim? | `RULES_RELEVANT_FIELDS` / audited equality after representation-only canonicalize (ADR 0007) |
   | **State-construction completeness** | Can we build a legal board and pay modeled costs without inventing characteristics? | Prefer audited printed characteristics when present; do not silently invent `1/1` / free grants when those fields are audited and the claim depends on them |

2. **Growth rule:** A field enters `RULES_RELEVANT_FIELDS` (identity exactness)
   when compilation, verification, or **default/oracle product state construction**
   consumes it for acceptance of `VERIFIED` on `ORACLE_EXACT` witnesses.
   Expanding exactness is deliberate (tests + audited records + docs in the same
   change). Exactness does **not** require modeling every Oracle clause or every
   Scryfall column.

3. **Substitution ban (product path):** For `ORACLE_EXACT` discovery / gold,
   when audited printed power and toughness exist, state construction **must**
   use them (and SBA-aware counter seeds for `0/0` counter-removers). Free
   stand-in ops (`seed_grant_lifelink`, …) remain physics-only and stay
   quarantined from Oracle product `VERIFIED` (see Heliod demotion).

4. **Proof hash / claim binding:** Identity fields that gate exactness participate
   via compiled IR and witness state as today (ADR 0009). Unused Scryfall metadata
   does not enter the claim hash merely by existing on the card.

## Non-decisions

- Full card modeling before any ability use — rejected.
- Heliod re-promotion physics — landed under this boundary (paid grant + audited 0/0).
- Mana cost / P/T on every historical audited record in one PR — migrate when a
  claim consumes them.

## Consequences

- Agents and curriculum may compile a subset of Oracle text while still failing
  closed on illegal invented boards for product gold.
- Ballista-class loops require audited `0/0` + sufficient counters and paid
  partner activations — not `1/1` + free lifelink seeds.
- ADR 0007’s “fields currently consumed” sentence is clarified by this split;
  0007 remains Accepted.
