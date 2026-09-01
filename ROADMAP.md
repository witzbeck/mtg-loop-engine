# MTG Loop Engine — Roadmap (gate document)

## North star

```
Oracle text → semantics → blind discovery → rules proof
```

Search may speculate. Verification may not. **Optimize verified precision over recall.**

No LLM-generated semantics on the path to `VERIFIED`. No binary "infinite." Loop type × output × consequence × delta.

## Milestone flow

```mermaid
graph TB;
  M0[M0 Corpus] --> M1[M1 Verifier];
  M1 --> M2[M2 Compiler];
  M2 --> M3[M3 Blind Discovery];
  M3 --> M4[M4 Evaluation];
  M4 --> M5[M5 Novel Candidates];
  M5 --> M6[M6 Incremental Scans];
  M6 --> M7[M7 Explorer];
```

**Active milestone:** M5 — Novel candidates ◐ **IN PROGRESS** (active stage: **M5.1 frontier analysis**)

Quantitative snapshot (baselines): [`docs/STATUS.md`](docs/STATUS.md). Keep volatile counts out of this file.

---

## Completed milestones

### M0 — Corpus ✓

- Scryfall Oracle bulk ingest; gitignored snapshots with manifest hashes.
- Commander Spellbook extract → DuckDB; conventional two-card filter.
- Initial physics gold spine (later split under ADR 0007 Wave 0); `gold_extended` stubs.
- Essential vs generic vs functional-external labels on every corpus entry.

### M1 — Witness verifier ✓

- `LoopWitness` in → `LoopProof` out. Verifier is witness-in / proof-out (deterministic semantics).
- Rules-aware executor: costs, tap/untap, sac, simple triggers, cost modifiers, replacements.
- Proof-specific `LoopRelevantState` (`EXACT` / `MINIMUM` / `MAXIMUM`).
- Fail-closed: `PARTIAL_RELEVANT_TO_PROOF` → typed rejection.
- Typed rejection vocabulary (`RESOURCE_DEFICIT`, `STATE_NOT_RECURRENT`, …).
- All `gold_core` positives `VERIFIED`; hard negatives produce correct typed rejection.

### M2 — Deterministic compiler ✓

- Oracle text → `CardSemantics` via deterministic pattern library.
- 19/19 gold Oracle fixtures compile `COMPLETE`; `fragment_coverage = 1.0`.
- `compile-coverage` CLI.

### M3 — Blind discovery ✓

- Capability signatures + inverted-index joins → bounded BFS → same verifier.
- Historical physics suite: 10/10 pairs rediscovered without pair labels (now `discover-physics`).
- Explorer is the single acceptance oracle; `discover_loops` does not re-verify.
- `corpus.builders` shared between fixtures and discovery so witness shapes stay comparable.

### M4 — Evaluation ✓

Exit criteria: **precision correctness** + **minimum real-Oracle eligibility** (not broad Spellbook recall).

| Gate | Evidence |
|------|----------|
| Participant enforcement | `explore_pair` requires `VERIFIED` + `strict_two_card`; Basalt bystander regressions in `tests/eval/test_classify_store.py` |
| Gold-pool precision | `eval/baseline/m4_gold_pool_summary.json` — precision **1.0** (1 eligible extra: Alarm+Gond) |
| ≥1 eligible Spellbook pair | `eval/baseline/m4_spellbook_recovery_summary.json` — **eligible=1** / **rediscovered=1** (Gravecrawler + Phyrexian Altar) |
| Baselines + STATUS | `scripts/render_status.py --check`; [`docs/STATUS.md`](docs/STATUS.md) |

Also shipped: M3.5 seam, eval schema/workbench, CI, real-Oracle curriculum start (irrelevant statics, zone recursion, any-color, cast-from-GY). **Compiler curriculum continues under M5** as coverage growth.

Historical playbook: [`docs/runbooks/M4_FOLLOW_THROUGH.md`](docs/runbooks/M4_FOLLOW_THROUGH.md).

---

## M5 — Novel candidate adjudication ◐ IN PROGRESS

Blind discovery among real **COMPLETE**-compiled Oracle cards from Spellbook name sets. Absence is a label; humans own `NOVEL`.

Operate a learning loop (not a mechanic backlog):

```
measure frontier → smallest reusable gap → discover → adjudicate → contracts → measure again
```

### Goals

- Discover among COMPLETE cards compiled from local Scryfall for Spellbook names.
- In Spellbook → `IN_REFERENCE`; not in Spellbook → `ABSENT_FROM_REFERENCE` (never auto-`NOVEL`).
- Human adjudication upgrades absence → `NOVEL` only (ADR 0005); report `NOVEL` outside the precision denominator.
- Leave joins open unless a precision bug is proven (ADR 0004).

### Stages

| Stage | Objective | Exit |
| --- | --- | --- |
| **M5.1 — Frontier analysis** | Rank missing semantics by cards/pairs unlocked (not raw fragment frequency) | Live frontier report; Slice 8+ chosen from P0/P1 with PR evidence |
| **M5.2 — Curriculum cycles** | Grow COMPLETE without weakening soundness | Frontier-justified slices with positive + adversarial contracts |
| **M5.3 — Candidate adjudication** | Dispose every `ABSENT_FROM_REFERENCE` from meaningful runs | Human classifications; false `VERIFIED` → regressions |
| **M5.4 — Exit hardening** | Certified reproducible M5 run | Explicit exit gate below; novel combo **not** required |

**M5.1 tool:** `scripts/spellbook_compiler_priority.py` → `eval.compiler_frontier` (live under gitignored `data/eval/`). `pair_unlock` = both-COMPLETE counterfactual; rediscovery stays separate. Curriculum PRs cite compact P0/P1 evidence — no perpetually updated `frontier_latest.md`.

**Coverage floor:** keep **92%** for M5. Require a classified coverage-miss inventory before exit. Raise toward 95% only when contract tests naturally support it. Exit condition is epistemic (no known high-priority soundness path to false `VERIFIED`), not percentage-driven.

**Oracle gaps:** Mikaeus / Saffi compete via the frontier (no privileged sequencing); the report always includes staged `oracle_gaps`.

### M5 exit gate (M5.4)

- Reproducible local run: pinned Oracle/Spellbook → compile → blind discover → verify → reference classify → adjudicate.
- All absences from the certified run disposed (or explicitly deferred with reason).
- No known high-priority soundness path to false `VERIFIED`.
- Finding a novel combo is **not** required.

### Remaining

0. **Corpus / evaluation integrity (campaign; ahead of 95% and broad M5 recall)** ◐ —
   ADR [0007](docs/decisions/0007-corpus-provenance-physics-vs-oracle.md) (**Accepted**;
   trust-boundary impl landed). `Provenance` + audited `ORACLE_EXACT` subset + frozen
   divergent quarantine + `is_precision_eligible_ids` / physics vs Oracle pools.
   Inventory:
   [`docs/decisions/reviews/corpus-provenance-inventory.md`](docs/decisions/reviews/corpus-provenance-inventory.md).
   ADR [0008](docs/decisions/0008-verifier-owned-mandatory-recurrence.md) (**Accepted**):
   verifier-owned once-per-turn + pending-trigger recurrence dims.
   ADR [0009](docs/decisions/0009-claim-bound-proof-hash.md) (**Accepted**): claim-bound
   `proof_hash` / proof schema **0.2.0**.
   **Wave 0 (claims boundary):** ✓ `gold_core` holds only Oracle-exact positives;
   historical synthetic/divergent witnesses live in `corpus.physics_fixtures`;
   `verify-gold` / `discover-gold` are Oracle-only; `verify-physics` /
   `discover-physics` cover the moved suite.
   **Net-state gate:** ✓ additive `events` / `net_state` / `claim_consequence`
   (proof schema **0.3.0**); gross counters alone do not justify `ACCUMULATES`.
   **Claim consequence derivation:** ✓ verifier derives `ACCUMULATES` /
   `REPEATABLE_EVENT` / `LETHAL` from net state + gross outputs under recurrence;
   mismatches with `expected_claim_consequence` → `NOT_A_LOOP`.
   **Waves 1–2:** ✓ nine Oracle gold positives
   (`core_guard_gond` … `core_rosie_scurry`, `core_heliod_ballista`, `core_bloodchief_mindcrank`) as **frozen witness artifacts**
   (independent of search; `all_gold_core` loads JSON only). Heliod/Ballista re-promoted with
   printed 0/0 Ballista (≥2 p1p1), paid `{1}{W}` grant-lifelink setup, and
   `seed_grant_lifelink` still quarantined from Oracle product VERIFIED.
   Wave 3 remainders (`core_saffi_champion`, `core_mikaeus_triskelion`) stay staged in
   `oracle_gaps` and **compete via the M5.1 frontier** (no privileged sequencing) until
   delayed triggers / undying+grant compile reuse justifies promotion.
   Keep **line coverage floor at 92%** until percentages measure faithful
   claims. Path-grammar fail-closed + creature-scoped ``events.death`` ✓.

   **Wave 3 physics slice (undying + SBA + self-ping):** ✓ executor primitives
   landed (`damage_marked`, `apply_state_based_actions`, `seed_grant_undying`,
   `DealDamage` `any_target`). Mikaeus remains in `oracle_gaps` until audited
   Oracle + grant/anthem compile + gold witness — do not promote yet. Saffi
   delayed triggers still out of scope.

1. **Absent-discovery path** ✓ — `eval/reference_absent.py` + `scripts/spellbook_absent_discovery.py`.
1b. **M5.1 compiler frontier** ✓ — `eval/compiler_frontier.py` + extended `spellbook_compiler_priority.py` (P0/P1/P2 by pair unlock; oracle_gaps visible).
2. **Grow COMPLETE pool (M5.2)** — prefer **self-starting** two-card physics (path **a**). **Slice 8+ is blocked on M5.1 frontier evidence** (not intuition). Curriculum ritual: [`docs/runbooks/M5_NOVEL_CANDIDATES.md`](docs/runbooks/M5_NOVEL_CANDIDATES.md).
   - **Slice 1 (aura channel)** ✓ — Freed / Pemmin’s; COMPLETE **17→19**.
   - **Slices 2–3 (activated artifacts + Intruder Alarm)** ✓ — Staff of Domination suite, live Basalt/Alarm; COMPLETE **19→24**.
   - **Slice 4 (life-drain + statics)** ✓ — Vito/Bond/Exquisite patterns; GAIN_LIFE / OPPONENT_LOSE_LIFE triggers; Flash/Devoid/Evolve/land-tapped statics.
   - **Slice 5 (self-starters)** ✓ — power-tap mana (Viridian Joiner); ETB damage (Impact / Purphoros / Alliance); ETB untap-self (Midnight Guard); anthem/devotion/lifelink-reminder as proof-irrelevant.
   - **Slice 6 (token auras + false-COMPLETE fix)** ✓ — Presence of Gond host-tap tokens; narrow Enchant irrelevant so Splinter Twin/Bear Umbra fail closed; Aphetto/Morph.
   - **Slice 7 (life-untap / self-ETB untap-all / counter-mana)** ✓ — Famished Paladin; Village Bell-Ringer; Gyre Sage (`equal_to_source_p1p1_counters` + 4-counter seed); Pestermite (may tap-or-untap → untap).
   - **Slice 8 (mill / graveyard feedback)** ✓ — Mindcrank + Bloodchief Ascension; Path-b′ `seed_lose_life`; `core_bloodchief_mindcrank` frozen.
   - **Slice 9 (scaled tap-mana)** ✓ — Bloom Tender / Sanctum Weaver / Circle of Dreams Druid / Priest of Titania / Axebane / Overgrown / Karametra / Archdruid; `ManaScaleKind` + explorer seeds.
   - **Slice 10 (equipment {Q})** ✓ — Umbral Mantle equipped-creature `{3}{Q}` grant; `UntapSymbolCost` + host activation in explorer; frontier P1 (**8** pair unlocks vs Mana Reflection **4**).
   - **Slice 11 (tap-mana multiplier)** ✓ — Mana Reflection / Nyxbloom Ancient `ReplacementMultiplyTapMana`; frontier P1 (**4** pairs each vs Power Artifact **2**).
   - **Slice 12+** ○ — choose from live frontier P0/P1; cite compact pair-unlock evidence in the curriculum PR.
   - **Path b (Bond/Blood)** ✓ — explicit generic life-gain seed; `core_bond_blood` frozen; disclosed on witness.
   - **Path b (Mindcrank / Bloodchief)** ✓ — explicit generic opponent life-loss seed (`seed_lose_life`, drain-sized); disclosed on witness.
   - **Rules-evidence rails** ✓ — [`docs/RULES_EVIDENCE.md`](docs/RULES_EVIDENCE.md), [`AGENTS.md`](AGENTS.md), [`.cursor/rules/rules-evidence.mdc`](.cursor/rules/rules-evidence.mdc), [`.agents/skills/rules-evidence/`](.agents/skills/rules-evidence/).

3. **Workbench adjudication (M5.3)** ◐ — first seed **post–slice 10** (2026-09-01): **3** `ABSENT_FROM_REFERENCE` candidates exported to gitignored `data/eval/spellbook_absent.jsonl` (Axebane Guardian + Pemmin's Aura; Axebane + Umbral Mantle; Overgrown Battlement + Umbral Mantle). Run `--persist-workbench` after each curriculum PR; human review in workbench (`spellbook_absent` corpus); `NOVEL` only with record.
4. **Optional baseline / M5.4 exit** — freeze an absent-discovery summary only when intentionally certifying; then apply the M5 exit gate above.

Playbook: [`docs/runbooks/M5_NOVEL_CANDIDATES.md`](docs/runbooks/M5_NOVEL_CANDIDATES.md).

### First local probe (not a baseline)

After each curriculum slice: run `spellbook_compiler_priority.py` (frontier) + `spellbook_absent_discovery.py` before choosing the next Slice 12+ gap. Remeasure on each curriculum PR.

---

## M6 — Incremental scans

- **Scan manifest** first: snapshot hashes, engine/semantics schema version, commit SHA, COMPLETE Oracle IDs, discovered pair identities, verification statuses, proof hashes.
- Full bounded re-scan is acceptable initially; **report incremental diffs** (cards added/removed/Oracle-changed, newly COMPLETE, discoveries added/removed, proof-hash churn). Optimize skip-work only after diffs are trustworthy.
- Track proof hash stability across engine versions. No generic performance scaffolding ahead of correctness.

---

## M7 — Explorer

- Local web UI beyond the adjudication workbench — a **lens** over certified proofs, classifications, provenance, and adjudications (not an alternate truth source).
- Card images via Scryfall URL (art stays gitignored).
- Search, filter, and browse verified loops; inspect sequence, net state, recurrence, rejection reasons, reference/novel status.
- FastAPI or equivalent; first cut without Postgres. No compile/repair/infer-loop logic in the UI.

---

## Explicitly deferred (do not plan or scaffold)

- LLM-generated semantics on any path to `VERIFIED`
- Three-card discovery
- Z3 / SMT solving
- Full Comprehensive Rules implementation
- ManaBox integration
- Deployed / public UI
- Performance optimization passes

---

## Frozen product decisions

| Topic | Decision |
|-------|----------|
| Choice ownership | Combo player favorable; opponent adversarial; cooperation → `OPPONENT_COOPERATION_REQUIRED` |
| Two-card definition | Exactly two essential functional pieces; generic fodder OK; functional external is not strict |
| Verifier contract | Witness-in / proof-out; search never inside verifier |
| Mandatory recurrence | Verifier merges once-per-turn + pending-trigger dims (ADR 0008); witnesses cannot omit them to soft-pass |
| Claim-bound proof_hash | `proof_hash` binds full claim payload; proof schema 0.2.0 (ADR 0009) |
| Identity vs state construction | Exactness ≠ full-card model; printed P/T/costs enter when consumed (ADR 0010) |
| Fail-closed coverage | `PARTIAL_RELEVANT_TO_PROOF` → never `VERIFIED` |
| Determinism | V1 deterministic-only; nondeterministic → typed rejection |
| LLM ban | No LLM on the `VERIFIED` path, indefinitely |
| Data hygiene | Oracle bulk JSON stays under gitignored `data/` |
| Loop model | No binary `infinite`; loop type × output × consequence × delta |
| Spellbook absence | `ABSENT_FROM_REFERENCE`, not false positive; `NOVEL` only after adjudication |
| Precision goal | Adjudicated precision over raw recall |

Longer rationale: [`docs/decisions/`](docs/decisions/) and [`docs/EVALUATION.md`](docs/EVALUATION.md).

---

## Governance

- **Review at milestone start:** re-read this file and confirm goals, constraints, and deferred items are still accurate.
- **Update at milestone exit:** the PR that completes a milestone must mark it done and refresh the next milestone's gates.
- **Feature branches:** all non-trivial work on a `feature/<slug>` branch; CI green before merge into `main`. Policy: [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Canonical docs:** In-repository documentation is canonical. Session notes outside the repository are ephemeral execution aids—not durable strategy. Durable decisions land in this roadmap, ADRs, `docs/`, and issues/PRs.
