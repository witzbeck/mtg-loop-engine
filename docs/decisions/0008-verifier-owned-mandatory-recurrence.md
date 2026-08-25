# ADR 0008 — Verifier-owned mandatory recurrence dimensions

## Status

Accepted

## Context

`LoopRelevantState` is witness-authored. Search’s `derive_relevant_state` already
adds once-per-turn paths when building discovery witnesses, but a hand-authored
(or adversarial) witness can omit those dimensions. Recurrence only checks
declared paths, so omitting `once_per_turn_used` (or pending-trigger depth) lets
a one-shot interaction appear arbitrarily repeatable.

ADR 0001 requires verification not to soften proof obligations. Mandatory
physics that the model already executes must not depend on search remembering
to propose the right dimensions.

## Decision

1. The **verifier** owns a small set of **mandatory recurrence dimensions**.
   Before `check_recurrence`, it computes `effective_relevant_state(witness, before)`
   = declared dimensions ∪ mandatory dimensions, with **mandatory winning** on
   path conflicts.
2. Initial mandatory set (expand only with tests + docs):
   - **Once-per-turn:** for each `activate` of an `ActivatedAbility.once_per_turn`
     ability in `loop_actions`, require
     `permanents.<actor>.once_per_turn_used.<ability_id>` `EXACT` to the
     pre-loop value (normally `False`).
   - **Pending triggers:** `pending_triggers.count` `EXACT` to
     `len(before.pending_triggers)` so a loop cannot leave (or consume) the
     queue without declaring it.
3. Search continues to call the **same helpers** when proposing witnesses
   (`once_per_turn_dimensions`, `pending_trigger_dimensions`) so discovery and
   verification stay aligned. `verify` must not import `search`.
4. Summoning-sickness-in-recurrence and richer trigger identity remain follow-ons.

## Consequences

- Omitting once-per-turn (or pending count) from a witness no longer yields
  `VERIFIED` for Alarm + once-a-turn tapper–class loops.
- Gold/hand witnesses that already declare these dims are unchanged.
- Discovery fingerprints already track once-per-turn and pending triggers;
  this closes the verifier-side hole for non-search witnesses.
