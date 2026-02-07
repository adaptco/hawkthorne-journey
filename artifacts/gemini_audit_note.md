# Gemini Audit Note

## Scope
This audit note documents a forensic-archaeology pass over the Tea Garden Clutch ingress event and its corridor artifacts. The objective is to produce machine-verifiable, replay-court-admissible records with explicit worldline binding and digest hygiene.

## Capsule identity
- **Output capsule type**: `OutputCapsule.v1`
- **Replay verdict type**: `ReplayVerdictCapsule.v1`
- **Worldline**: `tea-garden-1a2b3c4d`
- **Event / receipt / idempotency key**: `ce1738012800xyz`
- **Timestamp (UTC ISO-8601)**: `2026-02-05T19:48:00.000Z`

## What was corrected
1. **Lossless payload preservation**
   - The full original ingress payload is now preserved verbatim under `ingest.event.payload` (including camera vectors, movement metrics, and raw digest field).
2. **Worldline + replay binding**
   - The replay verdict now binds to worldline id, source event id, tick, and stream for deterministic cross-engine checks.
3. **Corridor-grade digest rule clarity**
   - The artifact explicitly separates raw `payloaddigest` (payload-level hex) from envelope-level `payload_sha256` (`sha256:`-prefixed), and assigns enforcement ownership to ingest service.
4. **Fossil-ledger inscription semantics**
   - Output capsule includes Merkle write boundary, root, ledger entry id, admissibility, and sealed immutability status.

## Invariants satisfied
- **Determinism**: Stable event identifiers and worldline/tick references across all artifacts.
- **Idempotency safety**: Shared `idempotency_key` and receipt/event alignment.
- **Replay admissibility**: Proof bundle contains digest and receipt anchors required for replay-court verification.
- **Governance explainability**: Human-readable rationale maps directly to machine fields without hidden transformations.
