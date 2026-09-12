#!/usr/bin/env python3
"""Verify published profit-distribution artifacts against the tracked manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin
from urllib.request import urlopen

REQUIRED_OUTPUTS = (
    "latest.json",
    "summary.json",
    "corporate-profit-share.csv",
    "productivity-distribution.csv",
)


class PublicationVerificationError(RuntimeError):
    """Raised when production publication evidence does not match the contract."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_manifest(manifest: dict, *, label: str) -> None:
    for field in ("source_snapshot", "source_snapshot_sha256", "retrieved_at", "outputs"):
        if field not in manifest:
            raise PublicationVerificationError(f"{label} manifest missing {field}")

    outputs = manifest["outputs"]
    if not isinstance(outputs, dict):
        raise PublicationVerificationError(f"{label} manifest outputs must be an object")
    if set(outputs) != set(REQUIRED_OUTPUTS):
        raise PublicationVerificationError(
            f"{label} manifest outputs mismatch: expected {sorted(REQUIRED_OUTPUTS)}, got {sorted(outputs)}"
        )

    for name in REQUIRED_OUTPUTS:
        metadata = outputs[name]
        if not isinstance(metadata, dict):
            raise PublicationVerificationError(f"{label} output metadata must be an object: {name}")
        size = metadata.get("bytes")
        digest = metadata.get("sha256")
        if not isinstance(size, int) or size < 0:
            raise PublicationVerificationError(f"{label} output has invalid byte length: {name}")
        if not isinstance(digest, str) or len(digest) != 64:
            raise PublicationVerificationError(f"{label} output has invalid sha256: {name}")
        try:
            int(digest, 16)
        except ValueError as exc:
            raise PublicationVerificationError(f"{label} output has invalid sha256: {name}") from exc


def verify_publication(
    expected_manifest: dict,
    production_manifest: dict,
    fetch_output: Callable[[str], bytes],
) -> dict:
    """Fail closed unless production identity and every output byte match current main."""

    _validate_manifest(expected_manifest, label="expected")
    _validate_manifest(production_manifest, label="production")

    for field in ("source_snapshot", "source_snapshot_sha256", "retrieved_at"):
        if production_manifest[field] != expected_manifest[field]:
            raise PublicationVerificationError(
                f"production {field} mismatch: expected {expected_manifest[field]!r}, "
                f"got {production_manifest[field]!r}"
            )

    expected_outputs = expected_manifest["outputs"]
    production_outputs = production_manifest["outputs"]
    verified: dict[str, dict[str, object]] = {}

    for name in REQUIRED_OUTPUTS:
        if production_outputs[name] != expected_outputs[name]:
            raise PublicationVerificationError(
                f"production manifest metadata mismatch for {name}: "
                f"expected {expected_outputs[name]!r}, got {production_outputs[name]!r}"
            )

        data = fetch_output(name)
        metadata = production_outputs[name]
        actual_size = len(data)
        actual_digest = _sha256(data)
        if actual_size != metadata["bytes"]:
            raise PublicationVerificationError(
                f"production byte length mismatch for {name}: expected {metadata['bytes']}, got {actual_size}"
            )
        if actual_digest != metadata["sha256"]:
            raise PublicationVerificationError(
                f"production sha256 mismatch for {name}: expected {metadata['sha256']}, got {actual_digest}"
            )
        verified[name] = {"bytes": actual_size, "sha256": actual_digest}

    return {
        "source_snapshot": production_manifest["source_snapshot"],
        "source_snapshot_sha256": production_manifest["source_snapshot_sha256"],
        "retrieved_at": production_manifest["retrieved_at"],
        "outputs": verified,
    }


def _fetch(url: str) -> bytes:
    with urlopen(url, timeout=15) as response:
        if response.status != 200:
            raise PublicationVerificationError(f"HTTP {response.status}: {url}")
        return response.read()


def verify_url(base_url: str, expected_manifest_path: Path) -> dict:
    base = base_url.rstrip("/") + "/"
    prefix = urljoin(base, "api/v1/profit-distribution/")
    production_manifest_bytes = _fetch(urljoin(prefix, "manifest.json"))
    try:
        production_manifest = json.loads(production_manifest_bytes)
    except json.JSONDecodeError as exc:
        raise PublicationVerificationError("production manifest is not valid JSON") from exc

    expected_manifest = json.loads(expected_manifest_path.read_text(encoding="utf-8"))
    return verify_publication(
        expected_manifest,
        production_manifest,
        lambda name: _fetch(urljoin(prefix, name)),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--expected-manifest",
        type=Path,
        default=Path("api/v1/profit-distribution/manifest.json"),
    )
    args = parser.parse_args()

    result = verify_url(args.base_url, args.expected_manifest)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
