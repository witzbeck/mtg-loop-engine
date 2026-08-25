# Gold Oracle fixture provenance inventory

Post-migration inventory for ADR 0007 (Accepted). Precision eligibility is
`ORACLE_EXACT` × `ORACLE_EXACT` via `is_precision_eligible_ids`.

| oracle_id | Name | Provenance | Notes |
| --- | --- | --- | --- |
| `oracle:basalt-monolith` | Basalt Monolith | ORACLE_EXACT | Audited under `semantics/audited/records/` |
| `synthetic:generic-activated-cost-reducer` | Synthetic Cost Reducer | SYNTHETIC | Replaces retired `oracle:training-grounds` |
| `oracle:intruder-alarm` | Intruder Alarm | ORACLE_DIVERGENT | Simplified ETB untap; freeze allowlist |
| `synthetic:token-tapper` | Eager Apprentice | SYNTHETIC | |
| `oracle:phyrexian-altar` | Phyrexian Altar | ORACLE_DIVERGENT | Tuned `{B}` vs any-color Oracle |
| `oracle:gravecrawler` | Gravecrawler | ORACLE_DIVERGENT | Activated return ≠ live cast-from-GY |
| `synthetic:persistent-phoenix` | Persistent Phoenix | SYNTHETIC | Was false “real” precision pair |
| `oracle:viscera-seer` | Viscera Seer | ORACLE_EXACT | Audited |
| `oracle:blood-artist` | Blood Artist | ORACLE_DIVERGENT | Simplified life-loss text |
| `synthetic:scaled-gun` | Scaled Gun | SYNTHETIC | |
| `synthetic:put-counter-activated` | Synthetic Put-Counter Activated | SYNTHETIC | Exited Hardened Scales quarantine |
| `oracle:reassembling-skeleton` | Reassembling Skeleton | ORACLE_DIVERGENT | Wrong cost / return semantics |
| `oracle:ashnods-altar` | Ashnod's Altar | ORACLE_EXACT | Audited |
| `oracle:rest-in-peace` | Rest in Peace | ORACLE_DIVERGENT | Creature-only vs any-card Oracle |
| `synthetic:etb-ping` | Impact Tremors Lite | SYNTHETIC | |
| `synthetic:self-untap-tapper` | Perpetual Apprentice | SYNTHETIC | |
| `oracle:soul-warden` | Soul Warden | ORACLE_EXACT | Audited |
| `synthetic:suicidal-phoenix` | Ember Phoenix | SYNTHETIC | |
| `synthetic:token-breeder` | Token Breeder | SYNTHETIC | |

## Precision series

Pre-migration “real” extras (Ashnod+Phoenix, Phyrexian+Phoenix, Phyrexian+Skeleton)
are **not** precision-eligible. First trustworthy datum is the first
`ORACLE_EXACT`×`ORACLE_EXACT` gold-pool discovery. Until then `precision` is `null`.
