from __future__ import annotations

import copy
import hashlib
import unittest

from scripts.verify_profit_distribution_publication import (
    PublicationVerificationError,
    REQUIRED_OUTPUTS,
    verify_publication,
)


class ProfitDistributionPublicationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.artifacts = {name: f"artifact:{name}\n".encode() for name in REQUIRED_OUTPUTS}
        outputs = {
            name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in self.artifacts.items()
        }
        self.manifest = {
            "schema_version": 1,
            "source_snapshot": "data/official/us-profit-distribution-current/source.json",
            "source_snapshot_sha256": "a" * 64,
            "retrieved_at": "2026-09-10T17:53:23+00:00",
            "outputs": outputs,
        }

    def test_matching_manifest_and_artifacts_pass(self) -> None:
        result = verify_publication(
            self.manifest,
            copy.deepcopy(self.manifest),
            self.artifacts.__getitem__,
        )
        self.assertEqual(result["source_snapshot"], self.manifest["source_snapshot"])
        self.assertEqual(set(result["outputs"]), set(REQUIRED_OUTPUTS))

    def test_one_byte_publication_change_fails(self) -> None:
        artifacts = dict(self.artifacts)
        artifacts["summary.json"] += b"x"
        with self.assertRaisesRegex(PublicationVerificationError, "summary.json"):
            verify_publication(self.manifest, copy.deepcopy(self.manifest), artifacts.__getitem__)

    def test_production_manifest_hash_change_fails_before_artifact_acceptance(self) -> None:
        production = copy.deepcopy(self.manifest)
        production["outputs"]["latest.json"]["sha256"] = "b" * 64
        with self.assertRaisesRegex(PublicationVerificationError, "metadata mismatch"):
            verify_publication(self.manifest, production, self.artifacts.__getitem__)

    def test_stale_source_snapshot_identity_fails(self) -> None:
        production = copy.deepcopy(self.manifest)
        production["retrieved_at"] = "2026-09-09T00:00:00+00:00"
        with self.assertRaisesRegex(PublicationVerificationError, "retrieved_at mismatch"):
            verify_publication(self.manifest, production, self.artifacts.__getitem__)

    def test_missing_required_output_fails(self) -> None:
        production = copy.deepcopy(self.manifest)
        del production["outputs"]["productivity-distribution.csv"]
        with self.assertRaisesRegex(PublicationVerificationError, "outputs mismatch"):
            verify_publication(self.manifest, production, self.artifacts.__getitem__)


if __name__ == "__main__":
    unittest.main()
