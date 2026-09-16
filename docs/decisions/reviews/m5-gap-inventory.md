# M5 Gap Inventory (compiler partials)

Campaign inventory for M5.2 autonomous IR-family epics. Live frontier citation
(remeasured 2026-09-16 via `scripts/spellbook_compiler_priority.py`):

| Metric | Value |
| --- | --- |
| COMPLETE | **88** |
| Partial | **824** |
| Fragments | **1213** (P0 228 / P1 185 / P2 800) |
| Gap kinds | pattern_existing_physics 564 / reusable_new_primitive 523 / substantial_rules 126 |

**Authority:** `ROADMAP.md` M5.2–M5.4; runbook
[`../../runbooks/M5_NOVEL_CANDIDATES.md`](../../runbooks/M5_NOVEL_CANDIDATES.md).
Live dumps stay gitignored under `data/eval/`; this file is the durable backlog.

```mermaid
graph TB;
  inv[Gap Inventory] --> closeNow[CLOSE_NOW epics];
  inv --> closeBuild[CLOSE_BUILD backlog];
  inv --> rejectOos[REJECT OOS];
  closeNow --> land[Land PR remasure];
  closeBuild --> land;
  land --> cleanup[Cleanup PARK residual];
  cleanup --> done[Only REJECT OOS left];
```

## Disposition legend

| Code | Meaning | When addressed |
| --- | --- | --- |
| **CLOSE_NOW** | Existing physics + patterns/params | Epic PRs in autonomous loop |
| **CLOSE_BUILD** | New/extended IR or executor | Same loop (soft then hard) |
| **PARK** | Temporary only; cleanup ticket required | End cleanup (must reach 0) |
| **REJECT** | One-shot / false COMPLETE theater | Documented; no implementation |
| **OOS** | Outside product claim | Human must widen scope |

**Ban:** PARK because physics is missing. Missing physics → CLOSE_BUILD.

**Epic DoD** (from campaign plan): ≥2 COMPLETE unlocks **or** ≥1 Path-a rediscovery
**or** one parameterized pattern covering ≥3 cards (unless family is truly singleton);
compile + positive verify + hard negative; remasure; never auto-`NOVEL`.

## Coverage vs 824

| Bucket | Approx cards touched | Notes |
| --- | --- | --- |
| CLOSE_NOW starter epics E01–E07 | ~50 unique | First autonomous waves |
| CLOSE_BUILD soft E08–E22, E50–E75 | majority of soft/mid | Parameterized trigger/effect families |
| CLOSE_BUILD hard E30–E41 | blink/copy/PW/… | Scheduled; not deferred |
| Long-tail E80 | ~160 | Cleanup tags into families or REJECT/OOS |
| REJECT | Storm Herd class | See below |

Cards may appear under multiple epics when they have multiple unsupported fragments.
Primary walk order is the **ordered backlog** below (first undone CLOSE_* row).

## Ordered epic backlog

Status: `pending` → `done` (update when the epic PR lands). Split rows if an epic
narrows mid-flight.

### CLOSE_NOW / early soft (waves 1+)

| ID | Status | Epic | Disp | Est. cards | Sole-gap ≈ | Path-a | Notes / examples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | done | Gated / restricted tap-mana | CLOSE_NOW | 8 | 5 | yes | Metalworker, Omen Hawker, Mox Opal, Fanatic of Rhonas, Supportive Parents; extends slice 9 |
| E02 | done | Damage-dealt reflect | CLOSE_NOW | 17 | 9 | maybe | Spitemare-class, Coalhauler, Reckoner, Brash Taunter |
| E03 | done | Token-create ×2 | CLOSE_NOW | 5 | 3 | yes | Parallel Lives, Anointed Procession (+ Doubling Season token half) |
| E04 | done | Draw-trigger effects | CLOSE_NOW | 14 | 5 | maybe | Niv-Mizzet, Psychosis Crawler, Queza, … |
| E05 | done | Curiosity combat-draw auras | CLOSE_NOW | 3 | 3 | maybe | Curiosity, Keen Sense, Ophidian Eye |
| E06 | done | Grant activated abilities | CLOSE_NOW | 5 | 3 | yes | Basal Sliver, Cryptolith Rite-class |
| E07 | done | Count-scaled tap-create | CLOSE_NOW | 6 | 2 | yes | Krenko; **exclude** life-total create |

### CLOSE_BUILD soft / mid

| ID | Status | Epic | Disp | Est. cards | Sole-gap ≈ | Path-a | Primitive sketch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E08 | done | Half-library mill | CLOSE_BUILD | 7 | 6 | maybe | Mill amount = ⌊/⌈ half library⌋ |
| E09 | done | Aetherflux cast-life + pay-life | CLOSE_BUILD | 1 | 1 | yes | Cast-count life gain; Pay 50 → damage (singleton sole-gap) |
| E10 | done | Multi / targeted land untap | CLOSE_BUILD | 3 | 1 | yes | Untap N target lands |
| E11 | done | Scaled mana remainders | CLOSE_BUILD | 17 | 8 | yes | Power/toughness/land-count / entered-this-turn mana |
| E12 | done | Cast-trigger family | CLOSE_BUILD | 33 | 15 | mixed | Parameterize CAST → effects |
| E13 | pending | ETB-trigger remainders (umbrella) | CLOSE_BUILD | 141 | 58 | mixed | Split into sub-epics by effect shape |
| E13a | done | Self-ETB power/devotion/artifact scale | CLOSE_BUILD | — | — | yes | Redcap / Fanatic / Gary / Edgar |
| E13b | done | ETB untap / Warstorm / landfall / artifact-ETB | CLOSE_BUILD | 6 | — | yes | Blasting Station untap; Hyrax; Warstorm; Sporemound; Molten Gatekeeper; Yotian |
| E14 | done | Dies-trigger remainders | CLOSE_BUILD | 29 | 9 | mixed | Parameterize DIES → effects |
| E15 | pending | Attack-trigger remainders (umbrella) | CLOSE_BUILD | 52 | 21 | mixed | May need combat model slices |
| E15a | done | Attacks untap/draw/damage | CLOSE_BUILD | 3 | — | yes | Bear Umbra; Dream Trawler; Caltrops |
| E16 | done | Sac-outlet payoffs | CLOSE_BUILD | 29 | 14 | yes | Sac cost → mana/mill/damage |
| E17 | done | Scaled mill | CLOSE_BUILD | 3 | 1 | yes | Mill = power / GY count / life-loss; Bruvac ×2 |
| E18 | done | GY → hand / BF | CLOSE_BUILD | 17 | 8 | maybe | Recursion effects |
| E19 | done | Bounce remainders | CLOSE_BUILD | 24 | 14 | yes | Bounce-as-cost Forest/Elf/land; Chulane activated bounce |
| E20 | done | Counter doubling | CLOSE_BUILD | 3 | 0 | yes | Doubling Season / Primal Vigor |
| E21 | done | Proliferate | CLOSE_BUILD | 3 | 0 | yes | Viral Drake proliferate (infect PI) |
| E22 | pending | Token-create variants (umbrella) | CLOSE_BUILD | 125 | 65 | mixed | Split into E22a+; copy tokens → E34 |
| E22a | done | Eldrazi tokens + double-token siblings | CLOSE_BUILD | 5 | 3 | maybe | Brood/Hatcher/Spawnsire; Exalted; Ajani's Chosen |
| E22b | done | Combat damage → Treasures | CLOSE_BUILD | 3 | 2 | maybe | Old Gnawbone / Hireling / Smaug |
| E50 | done | Life replacement | CLOSE_BUILD | 7 | — | mixed | Twice life loss/gain; can’t-gain; Archive draw |
| E51 | done | Mill replacement | CLOSE_BUILD | 1 | — | maybe | Covered by E17 Bruvac `ReplacementDoubleMill` |
| E52 | done | Counter-put triggers | CLOSE_BUILD | 7 | — | maybe | All Will Be One; Flourishing Defenses |
| E53 | done | Adapt / levelers | CLOSE_BUILD | 5 | — | mixed | Adapt N; Broodscale/Biomancer payoffs |
| E54 | done | Impulse / top-deck | CLOSE_BUILD | 8 | — | mixed | Top rearrange PI + draw/library; Harnfel impulse; Elven Chorus PI |
| E55 | done | Cost reduction / affinity | CLOSE_BUILD | 11 | — | mixed | Spell/affinity reduce; Animar/Sami/Temur/Raptor |
| E56 | done | P/T set equal to | CLOSE_BUILD | 5 | — | mixed | CDA lands/hand/life/devotion; Ashaya Forests |
| E57 | done | Indestructible grants | CLOSE_BUILD | 3 | — | mixed | Static/equipment grants as PI |
| E58 | done | Split second | CLOSE_BUILD | 2 | — | low | Split second PI; Angel's Grace / Legolas riders PI |
| E59 | pending | Kicker / casualty / buyback | CLOSE_BUILD | 7 | — | mixed | Additional cast costs |
| E60 | done | Tap-for-draw | CLOSE_BUILD | 10 | — | yes | Arcanis/Azami/Temple Bell/Kwain |
| E61 | done | Charge counters | CLOSE_BUILD | 3 | — | mixed | Cornucopia / Repository / Coretapper |
| E62 | done | Discard engines | CLOSE_BUILD | 12 | — | mixed | Mind Over Matter; Skirge; Glint-Horn |
| E63 | REJECT | Destroy / wrath | REJECT | 11 | — | low | One-shot; see R03 |
| E65 | done | Protection / hexproof | CLOSE_BUILD | 7 | — | low | Equipped/static keyword PI |
| E66 | pending | Equipment remainders | CLOSE_BUILD | 13 | — | mixed | Beyond Mantle |
| E67 | pending | Untap remainders (umbrella) | CLOSE_BUILD | 29 | — | yes | Extra-combat untaps → E35; else E67a+ |
| E67a | done | Artifact untap | CLOSE_BUILD | 3 | — | yes | Filigree / Corridor / Clock of Omens |
| E68 | done | Damage-to-you payoffs | CLOSE_BUILD | 2 | — | maybe | Stuffy Doll / Mogg Maniac reflect |
| E69 | pending | Prepared / MDFC convert | CLOSE_BUILD | 2 | — | mixed | Cast converted |
| E70 | pending | Beginning-of-step triggers | CLOSE_BUILD | 32 | — | mixed | End step / upkeep |
| E71 | REJECT | Skip step | REJECT | 1 | — | low | See R04 |
| E72 | REJECT | Counterspell | REJECT | 4 | — | low | See R05 |
| E73 | REJECT | Mana rituals | REJECT | 7 | — | low | Covered by R02 |
| E74 | pending | Fight / enrage | CLOSE_BUILD | 4 | — | mixed | Fight target |
| E75 | pending | Aura attach remainders | CLOSE_BUILD | 4 | — | mixed | Attach / enchanted |

Large rows (**E13**, **E15**, **E22**) **must split** into sub-epics at implementation
time (effect-shape slices) while keeping this parent ID as the inventory umbrella.

### CLOSE_BUILD hard (scheduled — not parked)

| ID | Status | Epic | Disp | Est. cards | Sole-gap ≈ | Path-a | Primitive sketch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E30 | pending | Blink / exile-return (umbrella) | CLOSE_BUILD | 30 | 22 | maybe | Split E30a+ |
| E30a | done | Activated / ETB blink | CLOSE_BUILD | 3 | — | yes | Emiel; Eldrazi Displacer; Felidar Guardian |
| E31 | pending | Token-copy (+haste) (umbrella) | CLOSE_BUILD | 40 | 25 | yes | Kiki/Twin-class |
| E31a | done | Tap-copy with haste | CLOSE_BUILD | 2 | — | yes | Kiki-Jiki; Splinter Twin grant |
| E31b | done | Paid tap-copy siblings | CLOSE_BUILD | 3 | — | yes | Reflection of Kiki-Jiki; Orthion; Myr Propagator |
| E32 | pending | Ability copy | CLOSE_BUILD | 3 | 3 | yes | Rings/Bracers-class |
| E33 | pending | Spell copy / storm | CLOSE_BUILD | 17 | 12 | mixed | Copy spell; storm |
| E34 | pending | Clone / enter as copy | CLOSE_BUILD | 26 | 24 | mixed | Enter as copy of |
| E35 | pending | Extra combat | CLOSE_BUILD | 4 | 2 | maybe | Additional combat phase |
| E36 | pending | Extra turn | CLOSE_BUILD | 12 | 6 | low | Take an extra turn |
| E37 | pending | Planeswalker loyalty | CLOSE_BUILD | 17 | 16 | mixed | +/−/0 loyalty abilities |
| E38 | pending | Energy | CLOSE_BUILD | 6 | 3 | mixed | {E} counters |
| E39 | pending | Dice tables | CLOSE_BUILD | 3 | 3 | low | d20 outcomes |
| E40 | pending | Modal choose-one | CLOSE_BUILD | 12 | 11 | mixed | Choose one modes |
| E41 | pending | Saga lore | CLOSE_BUILD | 6 | 0 | mixed | Lore counters; chapters |

### Long-tail + cleanup ticket

| ID | Status | Epic | Disp | Cards | Notes |
| --- | --- | --- | --- | --- | --- |
| E80 | pending | Long-tail residual | CLOSE_BUILD | ~160 | Tag into families during cleanup; see `still` list from frontier assignment script. **Cleanup ticket C1.** |
| C1 | pending | PARK/residual cleanup | cleanup | — | Retag E80; PARK count → 0; rediscovery seam misses; absence debt; inventory freeze |
| C2 | pending | Pair/combo rediscovery misses | cleanup | — | COMPLETE but join/search miss; seam fixes only |
| C3 | pending | Absence / human NOVEL queue | cleanup | — | Non-NOVEL dispose; queue true NOVEL for humans |

**PARK list:** *(empty at inventory open — prefer CLOSE_BUILD).*

## REJECT

| ID | Status | Item | Reason |
| --- | --- | --- | --- |
| R01 | open | Storm Herd (life-total X create) | One-shot; highest pair-unlock bait; runbook rejected slices 12/35 |
| R02 | open | Pure one-shot mana rituals with no recurrence path | E73 closed as REJECT into this bucket |
| R03 | open | Destroy / wrath as sole engine | One-shot; no mandatory recurrence Path-a (E63) |
| R04 | open | Skip next untap step | Timing lockout; not modeled loop physics (E71) |
| R05 | open | Counter target spell / ability | Reactive stack interaction; not a loop engine (E72) |

## OOS

| ID | Status | Item | Reason |
| --- | --- | --- | --- |
| O01 | open | Three-card+ essential discovery | ADR 0002 / roadmap deferred |
| O02 | open | Full Comprehensive Rules / LLM-on-VERIFIED / Z3 | Roadmap deferred |
| O03 | open | Deployed UI / ManaBox | Roadmap deferred |

## Top curriculum rows (citation; not walk order)

Prefer shared-IR epics over singleton curriculum rank. Notable P0 sole+pairs:

| Pairs | Card | Fragment (abbrev) | Inventory home |
| --- | --- | --- | --- |
| 6 | Storm Herd | create X Pegasi = life total | **R01 REJECT** |
| 2 | Professor Dellian Fel | PW loyalty suite | E37 |
| 2 | Aetherflux Reservoir | cast → life per spell | E09 |
| 2 | Omen Hawker | spend-only {C}{U} | E01 |
| 2 | Metalworker | reveal artifacts → {C}{C} each | E01 |

## Resume protocol

1. First `pending` CLOSE_* / cleanup row in this file.
2. Finish any in-flight `feature/*` PR.
3. Continue autonomous loop — do not re-ask for marching orders.

## Change log

| Date | Change |
| --- | --- |
| 2026-09-16 | Initial inventory from remasured frontier (88/824); ordered backlog E01–E80 + hard E30–E41 + cleanup |
| 2026-09-16 | REJECT batch: E63/E71/E72/E73 → R03–R05 (+R02); soft/hard CLOSE continue on remaining rows |
