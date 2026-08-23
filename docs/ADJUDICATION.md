# Adjudication guide

## Purpose

Human review of engine-accepted discoveries. The Streamlit workbench is a research instrument; this document is the durable class guide (also summarized in the workbench sidebar).

Canonical enums live in `mtg_loop_engine.eval.schema` (`AdjudicationClass`, `ReferenceStatus`).

## Decision flow (accepted candidate)

```mermaid
graph TB;
  cand[Accepted verified candidate] --> data{Real cards with usable Oracle?};
  data -->|no| inv[INVALID_CANDIDATE_DATA];
  data -->|yes| part{Both essential cards act in the loop?};
  part -->|no| dup[DUPLICATE_OR_EQUIVALENT_INTERACTION];
  part -->|yes| legal{Legal under modeled rules?};
  legal -->|no| fp[RULES_OR_SEMANTICS_FALSE_POSITIVE];
  legal -->|unsure| needs[NEEDS_RULES_RESEARCH];
  legal -->|yes| setup{Initial state justified?};
  setup -->|no| unjust[UNJUSTIFIED_INITIAL_STATE];
  setup -->|yes| third{Third functional piece?};
  third -->|specific ability required| ext[FUNCTIONAL_EXTERNAL_REQUIREMENT];
  third -->|any substitute OK| gen[VALID_GENERIC_PREREQUISITE];
  third -->|exactly two essential| strict[VALID_STRICT_TWO_CARD];
```

---

## `AdjudicationClass`

### `valid_strict_two_card`

**Rule:** Both cards actively participate in every iteration; no third functional piece is required. Generic fodder (mana of the right colors, untapped permanence the cards themselves provide, etc.) may be assumed only when intrinsic to the pair.

**Example:** Basalt Monolith + Rings of Brighthearth.

**Counts toward precision:** yes (valid).

### `valid_generic_prerequisite`

**Rule:** The loop needs a third object (e.g. "any creature to sacrifice"), but that object's identity is irrelevant—any legal substitute works.

**Example:** Token Breeder + Intruder Alarm (seeded creature token fodder; any token works). See calibration case `CC-005` in [`eval/calibration/adjudication_cases.jsonl`](../eval/calibration/adjudication_cases.jsonl).

**Boundary vs `unjustified_initial_state`:** Generic prerequisite assumes fodder the loop can reasonably obtain or that is explicitly modeled as intrinsic/generic setup. Unjustified initial state means the engine assumed board state the pair cannot establish under stated assumptions (e.g. five tokens when the loop only creates one per iteration).

**Counts toward precision:** yes (valid).

### `functional_external_requirement`

**Rule:** A specific third card *type* or ability is required that is not "any creature/artifact"—it must have a particular functional ability. Not strict two-card.

**Example:** Deadeye Navigator + Peregrine Drake framed as needing a land that taps for 5+ (specific functional ability, not generic fodder).

**Boundary vs `valid_generic_prerequisite`:** If any legal substitute of the same broad category works, prefer generic prerequisite. If a particular ability or card type is essential, use functional external requirement.

**Counts toward precision:** no (invalid for strict/valid precision).

### `unjustified_initial_state`

**Rule:** The starting board the engine assumed (e.g. tokens pre-seeded) is not something the combo itself can set up in a normal game under the stated assumptions.

**Example:** Engine seeds 5 tokens; the pair only ever creates 1 per loop iteration.

**Counts toward precision:** no.

### `rules_or_semantics_false_positive`

**Rule:** The engine made a rules or semantics mistake—the loop is not actually legal under the Comprehensive Rules intent for the modeled interaction (wrong timing, wrong zone, once-per-turn, etc.).

**Example:** Engine ignores "activate only as a sorcery."

**Counts toward precision:** no.

### `duplicate_or_equivalent_interaction`

**Rule:** One of the two "essential" cards never acts in the loop—it is a bystander, not a participant. Often the same interaction as a known one-card or different-pair witness.

**Example:** Basalt Monolith loops by itself; the second searched card just watches.

**Counts toward precision:** no. Discovery now rejects these via the search participant gate; remaining historical labels are regression fixtures only until the next baseline freeze.

### `invalid_candidate_data`

**Rule:** One or both cards are not usable real Magic cards for this evaluation—test fixture stand-in, missing Oracle text, or lookup failure.

**Example:** "Impact Tremors Lite" is a gold-core fixture, not a real card.

**Counts toward precision:** **excluded from the denominator entirely** (inventory only).

### `needs_rules_research`

**Rule:** Reviewer is unsure. Prefer this over a confident wrong label.

**Example:** Edge cases involving obscure replacement interactions.

**Boundary vs `rules_or_semantics_false_positive`:** False positive means the modeled rules/semantics path is confidently wrong under current engine understanding. Needs rules research means insufficient evidence to choose — not a disguised rejection.

**Counts toward precision:** no (treat as not yet resolved for precision claims).

---

## Calibration cases

Executable taxonomy examples live in [`eval/calibration/`](../eval/calibration/). Calibration is curated; adjudications are observational. LAR Tier A measures class/boundary coverage against calibration inventory.

---

## `ReferenceStatus`

Independent of adjudication class. Answers "how does this relate to Commander Spellbook (or another reference corpus)?"

### `in_reference`

**Rule:** The pair (or equivalent interaction) appears in the reference corpus used for this evaluation run.

**Does not imply:** the engine proof is correct—still adjudicate class separately.

### `absent_from_reference`

**Rule:** The accepted discovery is not in the reference corpus.

**Does not mean:** false positive. Spellbook is incomplete ground truth. Do not tighten joins solely to suppress these.

### `novel`

**Rule:** Human adjudication upgrades an absent-from-reference result after review. Machines must not auto-label `NOVEL`.

**Requires:** human judgment that the interaction is meaningfully new relative to known corpora and prior adjudications.

---

## Precision denominator (reminder)

Valid for precision:

- `valid_strict_two_card`
- `valid_generic_prerequisite`

Excluded from denominator:

- `invalid_candidate_data`

All other classes count as adjudicated but not valid.

See [`EVALUATION.md`](EVALUATION.md) and frozen numbers in [`STATUS.md`](STATUS.md).
