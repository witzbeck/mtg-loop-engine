# discovery

## Purpose

Blind rediscovery tests: gold_core cards without pair labels must still yield verified two-card witnesses via search + the same verifier.

## Context

```mermaid
graph TB;
  pool[goldCoreCardPool] --> index[InteractionIndex];
  index --> discover[discoverLoops];
  discover --> explorer[explorer];
  explorer --> verifier[Verifier];
  goldKeys[goldCorePairKeys] --> recall[recallAssert];
  verifier --> recall;
```

## What belongs here

- Join-index coverage and discovery-recall tests
- `test_compiled_discovery.py`: M3.5 seam (Oracle fixtures → compiler → blind search)

## What does not belong here

- Tests that pass known pairings into the explorer
