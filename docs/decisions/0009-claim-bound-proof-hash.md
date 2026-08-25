# ADR 0009 — Claim-bound proof_hash

## Status

Accepted

## Context

`LoopProof.proof_hash` previously hashed roughly
`witness_id + status + loop_actions + expected_outputs` (rejects: id + status +
reason). Candidate identity and adjudications use
`left_id__right_id::proof_hash`.

That payload omitted card semantics, initial state, setup, classification,
prerequisites, recurrence projection, coverage, and determinism. A materially
different claim could keep the same hash, so a stored adjudication could appear
bound to a proof it never reviewed.

## Decision

1. Bump `proof_schema_version` to **0.2.0**.
2. `proof_hash` is a **claim hash**: SHA-256 (32 hex) over a canonical JSON
   claim payload (`proofs.claim.build_claim_payload`) that includes at least:
   - non-volatile versions: proof/engine/rules/semantic schema versions
     (**not** `git_sha`, snapshots, or timestamps)
   - status + rejection reason
   - witness id, determinism, semantic coverage
   - essential cards and card semantics IR (sorted by `oracle_id`)
   - classification, initial state, setup + loop actions
   - relevant-state dimensions used for the check (effective state when the
     verifier merged mandatory dims; otherwise declared)
   - expected outputs, prerequisites, assumptions (sorted)
3. Serialization is `json.dumps(..., sort_keys=True, separators=(",", ":"))`.
4. Metamorphic tests: claim-relevant edits change the hash; reordering
   essential cards / assumptions / dimensions does not.

## Consequences

- Re-verification under 0.2.0 yields new hashes; regenerate gold-pool extras
  JSONL / DuckDB seeds when refreshing adjudications.
- Pre-0.2.0 hashes are not comparable; treat as a schema discontinuity.
- Follow-on: optional separate `normalized_claim_hash` after `normalize_proof`
  (out of scope here).
