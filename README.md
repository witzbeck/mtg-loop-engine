# MTG Loop Engine

## What is MTG Loop Engine?

MTG Loop Engine is an explainable interaction-discovery system for Magic: The Gathering. It compiles Oracle card text into deterministic semantic actions, searches for two-card repeatable loops, verifies candidates against a modeled rules surface, and emits structured proofs a human can audit.

Discovery may speculate. Verification may not.

## Why does it exist?

Known-combo databases answer “is this pair already catalogued?” This project asks a harder question: can we **automatically discover** two-card loops from Oracle text and **prove** that a proposed sequence is repeatable under modeled rules?

Commander Spellbook and similar corpora are reference material for evaluation and recovery metrics—not the product. The engine’s job is blind discovery plus conservative verification, with humans in the loop when the machine’s claim matters.

## Core philosophy

- **Discovery may speculate. Verification may not.** Search can propose; only the witness-in / proof-out verifier can accept.
- **Precision-first.** Prefer fewer trustworthy `VERIFIED` results over broad, untrusted recall.
- **Human adjudication is part of the system.** Machine acceptance is not the final word on whether a discovery is a valid strict two-card interaction.
- **Loop model, not boolean “infinite.”** Outcomes are typed: loop type × output × consequence × delta—not a binary infinite flag.
- **False confidence is worse than an unsupported result.** Fail closed when semantics or rules coverage is incomplete in a proof-relevant way.

See [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md) for the fuller argument.

## What does VERIFIED mean? / not mean

**`VERIFIED` means:** given this `LoopWitness` (cards, modeled semantics, setup, and loop actions), the rules-aware executor ran the sequence and confirmed proof-specific recurrence of `LoopRelevantState`, producing a structured `LoopProof` with status `verified`.

**`VERIFIED` does not mean:**

- The Comprehensive Rules in full were simulated.
- Real-world Oracle text outside the modeled fragment set was fully understood.
- A human has adjudicated the discovery as a novel or valid strict two-card combo.
- Spellbook (or any reference corpus) lists the pair.
- The interaction is “infinite” in the casual sense—only that the modeled loop recurs under the stated projection and outputs.

Unsupported or partial proof-relevant semantics never earn `VERIFIED`.

## How it works

```mermaid
graph LR;
  oracle[Oracle] --> compiler[Compiler];
  compiler --> interactions[Interactions];
  interactions --> search[Search];
  search --> verifier[Verifier];
  verifier --> proof[Proof];
  proof --> eval[Eval];
  eval --> human[Human];
  human --> corpus[Corpus];
```

Oracle text is compiled into semantic IR. Capability joins and bounded search propose witnesses. The verifier either emits a proof or a typed rejection. Evaluation and human adjudication feed back into corpus, taxonomy, and tests.

Package wiring: [src/mtg_loop_engine/README.md](src/mtg_loop_engine/README.md). Cross-cutting map: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Current maturity

| Milestone | Status |
|-----------|--------|
| M0 Corpus | ✓ Complete |
| M1 Verifier | ✓ Complete |
| M2 Compiler | ✓ Complete |
| M3 Blind discovery | ✓ Complete |
| M4 Evaluation | ◐ In progress |
| M5 Novel candidates | ○ Not started |
| M6 Incremental scans | ○ Not started |
| M7 Explorer | ○ Not started |

Track goals, follow-through work, and frozen product decisions in [ROADMAP.md](ROADMAP.md). For current numbers and baselines, see [docs/STATUS.md](docs/STATUS.md) and committed summaries under [`eval/baseline/`](eval/baseline/).

## Quick start

```bash
uv sync
uv run pytest
```

Core smoke commands (one sentence each):

```bash
# Confirm gold_core positives verify and hard negatives reject as expected.
uv run mtg-loop-engine verify-gold

# Report deterministic compiler coverage on gold Oracle fixtures.
uv run mtg-loop-engine compile-coverage

# Blind-discover gold_core pairs without pair labels; explorer is the acceptance oracle.
uv run mtg-loop-engine discover-gold
```

Evaluation / adjudication:

```bash
uv run mtg-loop-engine eval-gold-extras
uv run mtg-loop-engine eval-spellbook --variants eval/fixtures/spellbook_conventional_sample.jsonl
uv run --group eval mtg-loop-engine adjudicate-workbench
```

Optional data fetches (local, gitignored snapshots):

```bash
uv run mtg-loop-engine fetch-scryfall
uv run mtg-loop-engine fetch-spellbook --pages 3
```

CLI details: [docs/CLI.md](docs/CLI.md).

## Repository map

| Path | Role |
|------|------|
| [`src/mtg_loop_engine/`](src/mtg_loop_engine/README.md) | Installable library |
| [`src/mtg_loop_engine/cards/`](src/mtg_loop_engine/cards/README.md) | Scryfall / Oracle ingest |
| [`src/mtg_loop_engine/semantics/`](src/mtg_loop_engine/semantics/README.md) | Deterministic compiler + IR |
| [`src/mtg_loop_engine/interactions/`](src/mtg_loop_engine/interactions/README.md) | Capability signatures / joins |
| [`src/mtg_loop_engine/search/`](src/mtg_loop_engine/search/README.md) | Bounded blind discovery |
| [`src/mtg_loop_engine/verify/`](src/mtg_loop_engine/verify/README.md) | Witness verifier |
| [`src/mtg_loop_engine/proofs/`](src/mtg_loop_engine/proofs/README.md) | Witness / proof contracts |
| [`src/mtg_loop_engine/state/`](src/mtg_loop_engine/state/README.md) | Game-state model |
| [`src/mtg_loop_engine/rules/`](src/mtg_loop_engine/rules/README.md) | Modeled rules surface |
| [`src/mtg_loop_engine/corpus/`](src/mtg_loop_engine/corpus/README.md) | Gold fixtures and builders |
| [`src/mtg_loop_engine/eval/`](src/mtg_loop_engine/eval/README.md) | Evaluation + adjudication workbench |
| [`src/mtg_loop_engine/benchmark/`](src/mtg_loop_engine/benchmark/README.md) | Spellbook extract / reference helpers |
| [`eval/`](eval/README.md) | Committed fixtures, adjudications, baselines |
| [`tests/`](tests/README.md) | Pytest suites |
| [`docs/`](docs/README.md) | Narrative and operating docs |
| [`data/`](data/README.md) | Gitignored local snapshots (never commit Oracle bulk) |
| [`scripts/`](scripts/README.md) | Helper scripts |

## How to contribute

Start with [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) (agent / contributor operating notes). Align work with [ROADMAP.md](ROADMAP.md), browse [docs/](docs/README.md), and record durable product choices under [docs/decisions/](docs/decisions/).

## Project boundaries

**This is not:**

- A combo database or Spellbook replacement
- A deckbuilder, pricing tool, collection manager, or ManaBox integration
- A full Comprehensive Rules engine or SMT/Z3 solver
- An LLM-authored semantics path to `VERIFIED`
- A deployed public UI or FastAPI/Postgres explorer (M7 is deferred)

Three-card discovery and performance-optimization passes are also explicitly out of scope for now—see ROADMAP deferred list.

## Source-of-truth hierarchy

When sources disagree, use the artifact that answers that kind of question—do not guess.

| Question type | Authoritative source |
| --- | --- |
| Why is the system designed this way? | [`docs/decisions/`](docs/decisions/), frozen decisions in [`ROADMAP.md`](ROADMAP.md) |
| What does the implementation actually enforce? | Schemas, tests, golden proofs, engine code under `src/` |
| What has been measured? | [`eval/baseline/`](eval/baseline/) (summarized in [`docs/STATUS.md`](docs/STATUS.md)); prose numbers are summaries only |
| What milestone is complete vs gated? | [`ROADMAP.md`](ROADMAP.md) |
| How do I learn the system? | This README, package READMEs, [`docs/`](docs/README.md)—must not silently override the contracts above |

If an agent finds disagreement across layers, reconcile it in the same change or document it as an unresolved defect.

Glossary: [docs/TERMINOLOGY.md](docs/TERMINOLOGY.md).

## AI–human flourishing

The useful system is a partnership: the machine proposes candidates and proves what it can under explicit models; humans adjudicate borderline cases, improve taxonomy and tests, and keep false confidence out of the corpus. Each loop of propose → prove → adjudicate → harden semantics should make both sides sharper—more precise automation, clearer human judgment—not a handoff that replaces either. That principle is spelled out in [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md).
