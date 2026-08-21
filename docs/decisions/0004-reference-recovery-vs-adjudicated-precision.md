# ADR 0004 — Reference recovery vs adjudicated precision

## Status

Accepted

## Context

Commander Spellbook (and similar references) are useful recovery benchmarks but incomplete and differently labeled than this engine’s strict two-card / essential-piece model. Optimizing raw recall against Spellbook can reward leaky joins and weak witnesses. M4 established that adjudicated precision is the product goal.

## Decision

- **Optimize adjudicated precision over raw recall.**
- Spellbook (or other reference) recovery is measured on **eligible / supported** entries; ineligibility due to compiler coverage is a coverage problem, not a silent precision win.
- Choice ownership remains as frozen elsewhere: combo-player favorable, opponent adversarial; required cooperation → `OPPONENT_COOPERATION_REQUIRED`.
- Loop results are structured (**loop type × output × consequence × delta**), not a binary “infinite” flag.
- Never treat reference recovery rate as a license to leak pair labels into discovery (see ADR 0001).

## Consequences

- Eval baselines under `eval/baseline/` record frozen distributions; prose must cite those files, not memorized numbers.
- Join-tuning that suppresses absences to inflate precision is out of policy (see ADR 0005).
- Participant-filter and related correctness fixes take priority over recall expansion when precision is untrustworthy.
