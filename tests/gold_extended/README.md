# gold_extended

## Purpose

Catalog cases that may return `UNSUPPORTED_SEMANTICS` / `UNSUPPORTED_RULE` during M1 without failing the M1 exit gate.

## What belongs here

- Assertions that extended catalog entries fail closed (not silent VERIFIED)

## What does not belong here

- Expanding rules surface to make these pass before M2+
