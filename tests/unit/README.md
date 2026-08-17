# unit

## Purpose

Fast tests for filters, ingest helpers, recurrence projection, and module-boundary checks without full gold suites.

## What belongs here

- `test_spellbook_filter.py`, `test_scryfall_ingest.py`, `test_recurrence.py`
- `test_search_boundary.py` (verifier must not import search)

## What does not belong here

- Full witness verification (see `gold_core/`, `hard_negatives/`)
- Blind rediscovery (see `discovery/`)
