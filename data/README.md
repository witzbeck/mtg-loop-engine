# data

## Purpose

Gitignored local caches for Scryfall Oracle snapshots and Commander Spellbook reference extracts.

## What belongs here

- Versioned snapshot directories with `manifest.json`
- DuckDB/parquet analytics files

## What does not belong here

- Committed Oracle bulk JSON (ToS / redistribution)
- Source code

## Notes

Populate with:

```bash
uv run mtg-loop-engine fetch-scryfall
uv run mtg-loop-engine fetch-spellbook --pages 3
```
