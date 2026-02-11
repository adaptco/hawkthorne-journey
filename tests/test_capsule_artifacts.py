import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(rel_path: str):
    with (ROOT / rel_path).open("r", encoding="utf-8") as f:
        return json.load(f)


class CapsuleArtifactTests(unittest.TestCase):
    def setUp(self):
        self.output_capsule = load_json("artifacts/output_capsule.json")
        self.replay_capsule = load_json("artifacts/replay_verdict_capsule.v1.json")

    def test_identity_alignment(self):
        receipt_id = self.output_capsule["ingest"]["receipt"]["receipt_id"]
        event_id = self.output_capsule["ingest"]["event"]["event_id"]
        replay_event_id = self.replay_capsule["worldline_binding"]["source_event_id"]

        self.assertEqual(receipt_id, event_id)
        self.assertEqual(event_id, replay_event_id)

    def test_worldline_alignment(self):
        output_worldline = self.output_capsule["lineage"]["worldline_id"]
        replay_worldline = self.replay_capsule["worldline_binding"]["worldline_id"]

        self.assertEqual(output_worldline, replay_worldline)

    def test_digest_prefix_normalization(self):
        payload = self.output_capsule["ingest"]["event"]["payload"]
        raw_digest = payload["payloaddigest"]
        corridor_raw = self.output_capsule["corridor_rules"]["payload_digest_internal"]
        event_sha = self.output_capsule["ingest"]["event"]["payload_sha256"]
        receipt_sha = self.output_capsule["ingest"]["receipt"]["payload_sha256"]
        replay_sha = self.replay_capsule["proofs"]["payload_sha256"]

        self.assertEqual(raw_digest, corridor_raw)
        self.assertTrue(event_sha.startswith("sha256:"))
        self.assertEqual(event_sha, f"sha256:{raw_digest}")
        self.assertEqual(receipt_sha, event_sha)
        self.assertEqual(replay_sha, event_sha)

    def test_timestamp_alignment(self):
        ts = self.output_capsule["ts_utc"]
        receipt_ts = self.output_capsule["ingest"]["receipt"]["ts_utc"]
        event_ts = self.output_capsule["ingest"]["event"]["ts_utc"]
        replay_ts = self.replay_capsule["ts_utc"]

        self.assertEqual(ts, receipt_ts)
        self.assertEqual(receipt_ts, event_ts)
        self.assertEqual(event_ts, replay_ts)


if __name__ == "__main__":
    unittest.main()
