# Terminology

## Purpose

Precise shared vocabulary for loops, proofs, coverage, and evaluation. Prefer these definitions over casual MTG slang when writing issues, adjudications, or docs.

Deeper denominator and class docs: [ADJUDICATION.md](ADJUDICATION.md), [EVALUATION.md](EVALUATION.md).

## Context

```mermaid
graph LR;
  candidate[Candidate] --> witness[Witness];
  witness --> proof[Proof];
  proof --> adjudication[Adjudication];
  adjudication --> baseline[Baseline];
```

---

## Core objects

### Loop

A **repeatable sequence of actions** under modeled rules such that a proof-specific projection of state (`LoopRelevantState`) recurs and stated outputs / consequences hold. Loops are typed (for example arbitrary-repeatable vs resource-bounded) with output type, consequence, and delta per iteration.

### Witness (`LoopWitness`)

The **input contract** to the verifier: essential cards, card semantics, initial state, optional setup actions, loop actions, relevant-state projection, expected outputs, assumptions, and coverage. Search (or a human author) builds witnesses; the verifier checks the given witness.

### Proof (`LoopProof`)

The **output contract** of verification: versions, executed (or recorded) actions, recurrence result, output deltas, status (`VERIFIED` or a typed rejection), rejection reason when applicable, semantic coverage, and a `proof_hash`. A proof is auditable evidence about a witness.

### Recurrence

Success of the proof-specific **`LoopRelevantState`** after the loop body: each dimension compared with `EXACT`, `MINIMUM`, or `MAXIMUM` as declared. Recurrence is over the dependency set the proof claims.

### Candidate

An **accepted discovery queued for review**: a pair (or witness) that search + verifier already treated as machine-accepted, packaged with join reasons, prerequisite analysis, reference status, and explanation for adjudication. Product claims about validity still require human adjudication.

---

## Card roles and prerequisites

### Essential card

A card that is treated as a **functional piece** of the interaction (typically the two searched Oracle IDs on the two-card path). Prerequisite analysis further checks which essential IDs actually **participate** (appear as actors) in loop steps; a named essential that never acts is a precision smell, not proof of a two-piece loop.

### Generic prerequisite

A setup assumption that is **fungible fodder or ambient setup** (for example generic mana, a disposable creature to sacrifice). It stays outside the two essential functional pieces. Valid discoveries may still be labeled with generic prerequisites when those assumptions are justified.

### Functional external requirement

A requirement for an **additional non-generic functional piece** outside the two essential cards (another specific permanent, an opponent choice that amounts to a missing piece, etc.). Such interactions are labeled `FUNCTIONAL_EXTERNAL_REQUIREMENT` rather than strict two-card.

### Strict two-card

Exactly **two essential functional pieces** participate; generics may appear; functional external requirements are absent. Derived from participation / prerequisite analysis (search asking for two names is necessary but not sufficient).

---

## Verification outcomes

### Verified

`VerificationStatus.VERIFIED`: the executor accepted the witness under modeled rules and recurrence. Claim limits (full Comprehensive Rules, human novelty, reference membership, casual “infinite”): [root README](../README.md) and [PHILOSOPHY.md](PHILOSOPHY.md).

### Unsupported

Semantics or rules needed for the claim are outside the modeled surface. Common surfaces: unmatched Oracle fragments, `UNSUPPORTED_SEMANTICS` / `UNSUPPORTED_RULE` rejection statuses, or assumption kind `unsupported`. Prefer this outcome over inventing behavior.

---

## Compiler coverage

### COMPLETE

Every Oracle ability clause matched a deterministic pattern; `unsupported_fragments` is empty. Eligible for verification on coverage grounds.

### PARTIAL_IRRELEVANT_TO_PROOF

Some clauses unmatched, but callers marked those gaps as **irrelevant to the proof** (`treat_unsupported_as_relevant=False`). Still a partial compile; use only when irrelevance is justified.

### PARTIAL_RELEVANT_TO_PROOF

Unmatched fragments are treated as **proof-relevant**. **Fail-closed:** typed rejection (never `VERIFIED`). Default when real Oracle text outruns the pattern library.

---

## Evaluation and reference

### Reference recovery

Measuring whether known conventional two-card reference entries (for example Spellbook-shaped rows) are **rediscovered** by compile → join → search → verify. Pair labels score evaluation; blind discovery uses compiled capabilities and joins only.

### Eligible

A reference row that is **in scope for recall**: semantics compile completely enough to be supported, and other eligibility gates pass. Recall is defined **only** over eligible / supported entries. If eligible is zero, recall is undefined or reported as null.

### Absent from reference (`ABSENT_FROM_REFERENCE`)

An accepted discovery **not found** in the reference corpus. Remains `ABSENT_FROM_REFERENCE` until human adjudication upgrades it to `NOVEL`.

### Novel (`NOVEL`)

Human-upgraded label: absent from reference **and** reviewed as a genuine new finding. Machines must not self-assign this.

### Adjudication

Human classification of a candidate into the adjudication vocabulary (valid strict two-card, duplicate / equivalent interaction, functional external, unjustified initial state, rules/semantics false positive, invalid candidate data, needs rules research, …). Persisted with proof hash and engine version. See [ADJUDICATION.md](ADJUDICATION.md).

### Hard negative

A curated witness expected to produce a specific typed rejection. Used to lock fail-closed behavior (M1 contract).

### Baseline

A **frozen** evaluation summary checked into `eval/baseline/` (for example gold-pool precision distribution, Spellbook recovery counts). Narrative docs link baselines; cite the files for figures.

### Precision

Among **adjudicated** candidates in the precision denominator (excluding classes such as `INVALID_CANDIDATE_DATA`), the share labeled valid (for example `VALID_STRICT_TWO_CARD` or `VALID_GENERIC_PREREQUISITE`). Exact inclusions/exclusions: [EVALUATION.md](EVALUATION.md).

### Recall

Among **eligible** reference entries, the share rediscovered. Unsupported / ineligible rows stay outside the denominator.

---

## Related reading

- [PHILOSOPHY.md](PHILOSOPHY.md) — why these distinctions exist
- [ADJUDICATION.md](ADJUDICATION.md) — class meanings and workbench practice
- [EVALUATION.md](EVALUATION.md) — formulas, stages, baseline files
- [../ROADMAP.md](../ROADMAP.md) — frozen product decisions table
