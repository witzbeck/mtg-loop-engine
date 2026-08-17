# MTG Loop Engine

## Purpose

Explainable interaction-discovery system for Magic: The Gathering. Compiles Oracle cards into semantic actions, searches for two-card repeatable loops, verifies them against modeled rules, and emits structured proofs. Discovery may speculate; verification may not.

## Context

```mermaid
graph TB;
  scryfall[ScryfallOracle] --> cardsPkg[cards];
  spellbook[SpellbookCorpus] --> benchmarkPkg[benchmark];
  cardsPkg --> semanticsPkg[semantics];
  semanticsPkg --> verifyPkg[verify];
  semanticsPkg --> interactionsPkg[interactions];
  interactionsPkg --> searchPkg[search];
  searchPkg --> verifyPkg;
  statePkg[state] --> verifyPkg;
  rulesPkg[rules] --> verifyPkg;
  verifyPkg --> proofsPkg[proofs];
  corpusPkg[corpus] --> verifyPkg;
  corpusPkg --> searchPkg;
  searchPkg --> evalPkg[eval];
  verifyPkg --> evalPkg;
```

## Quick start

```bash
uv sync
uv run pytest
uv run mtg-loop-engine verify-gold
uv run mtg-loop-engine compile-coverage
uv run mtg-loop-engine discover-gold
uv run mtg-loop-engine eval-gold-extras
uv run mtg-loop-engine eval-spellbook --variants eval/fixtures/spellbook_conventional_sample.jsonl
uv run --group eval mtg-loop-engine adjudicate-workbench
uv run mtg-loop-engine fetch-scryfall
uv run mtg-loop-engine fetch-spellbook --pages 3
```

## What belongs here

- Python package `mtg_loop_engine` (M0–M4: corpus, verifier, compiler, blind discovery, evaluation)
- Tests, scripts, gitignored local `data/` snapshots, and committed evaluation metadata under `eval/`

## What does not belong here

- Deckbuilding, pricing, collections, ManaBox integration
- FastAPI/Postgres explorer (M7)
- LLM-authored semantics on the path to `VERIFIED`

## M1 contract

`LoopWitness` (cards + IR + setup + loop actions) → rules-aware executor → proof-specific `LoopRelevantState` recurrence → `LoopProof` (`VERIFIED` or typed rejection).

## M3 contract

Semantic cards with hidden pair labels → capability joins → bounded search → the same conservative verifier.

## M4 contract

Gold Oracle → compiler → blind discovery → verifier (M3.5 seam). Spellbook reference recovery is measured only on eligible/supported entries. Precision is human-adjudicated; Spellbook absence is `ABSENT_FROM_REFERENCE`, not a false positive.
