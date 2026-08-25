# Gold Oracle fixture provenance inventory

Working inventory for ADR 0007 (Proposed). Status as of campaign start on `main`
after #23–#25. **Do not treat `is_fixture=False` as Oracle-faithful.**

| oracle_id | Name | Today `is_fixture` | Proposed class | Notes |
| --- | --- | --- | --- | --- |
| `oracle:basalt-monolith` | Basalt Monolith | False | ORACLE_EXACT (candidate) | Text looks close; must match audited snapshot before EXACT |
| `oracle:training-grounds` | Training Grounds (legacy id) | False | **SYNTHETIC** → `synthetic:generic-activated-cost-reducer` / **Synthetic Cost Reducer** | Retire real name from physics gold; real Training Grounds only when audited EXACT exists |
| `oracle:intruder-alarm` | Intruder Alarm | False | ORACLE_EXACT (candidate) | Verify vs snapshot (target wording) |
| `oracle:token-tapper` | Eager Apprentice | True | SYNTHETIC | Already honest fixture; prefer `synthetic:` id when touching |
| `oracle:phyrexian-altar` | Phyrexian Altar | False | ORACLE_EXACT (candidate) | |
| `oracle:gravecrawler` | Gravecrawler | False | **ORACLE_DIVERGENT** (quarantine) → EXACT or SYNTHETIC | Activated return ≠ cast-from-GY + Zombie |
| `oracle:phoenix` | Persistent Phoenix | False | **SYNTHETIC** | Invented card used as “real” in gold_extras precision |
| `oracle:viscera-seer` | Viscera Seer | False | ORACLE_EXACT (candidate) | |
| `oracle:blood-artist` | Blood Artist | False | ORACLE_EXACT (candidate) | Simplified life-loss text — verify |
| `oracle:scaled-gun` | Scaled Gun | False | **SYNTHETIC** | Invented name |
| `oracle:hardened-scales` | Hardened Scales | False | **ORACLE_DIVERGENT** → SYNTHETIC (quarantine exit) | Invented activated put-counter |
| `oracle:reassembling-skeleton` | Reassembling Skeleton | False | **ORACLE_DIVERGENT** (quarantine) | Wrong cost / tapped return |
| `oracle:ashnods-altar` | Ashnod's Altar | False | ORACLE_EXACT (candidate) | |
| `oracle:rest-in-peace` | Rest in Peace | False | ORACLE_EXACT (candidate) | Simplified; verify |
| `oracle:etb-ping` | Impact Tremors Lite | True | SYNTHETIC | |
| `oracle:self-untap-tapper` | Perpetual Apprentice | True | SYNTHETIC | |
| `oracle:soul-warden` | Soul Warden | False | ORACLE_EXACT (candidate) | |
| `oracle:suicidal-phoenix` | Ember Phoenix | True | SYNTHETIC | |
| `oracle:token-breeder` | Token Breeder | True | SYNTHETIC | |

## Precision impact (gold_extras “real” set today)

Currently treated as precision-eligible (`is_fixture=False` both sides):

- Ashnod + Persistent Phoenix
- Phyrexian Altar + Persistent Phoenix
- Phyrexian Altar + Reassembling Skeleton

Under ADR 0007, **all three** leave the precision denominator until Phoenix is
synthetic and Skeleton/Gravecrawler-class texts are EXACT or explicitly divergent
non-precision.

## Next implementation steps

1. Accept ADR 0007 (or revise after Q1–Q2).
2. Introduce `Provenance` enum; migrate fixtures; derive eval exclusion from it.
3. Commit audited Oracle subset; CI exact-match for `ORACLE_EXACT`.
4. Rename/rebuild Basalt+“Training Grounds” physics gold.
5. Rebuild `m4_gold_pool_summary.json` with honest notes — no forced 1.0.
