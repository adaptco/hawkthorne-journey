# Gemini Audit Note

## Capsule summary
The output capsule captures a divergence rejection event at `2026-02-04T12:00:00.000Z` with a fail-closed rollback action. The capsule ties the event to a workflow, artifact hash, and a specific prompt, and records the last valid Merkle root for replay alignment.

## Validation rationale
- **Deterministic anchors**: `merkle_root`, `workflow_sha`, and `artifact_sha` provide immutable identifiers for verifying the capsule lineage.
- **Replay continuity**: `can_proxy.last_valid_root` explicitly defines the rollback anchor for replay consistency.
- **Drift adjudication**: `drift_delta.tolerance_exceeded` is `true`, justifying the fail-closed verdict.

## Invariants satisfied
- **Immutability**: The capsule preserves hashes and timestamps without mutation.
- **Auditability**: The event type, action, and drift data are explicitly recorded.
- **Replay safety**: Rollback references a last valid root to prevent divergence propagation.
