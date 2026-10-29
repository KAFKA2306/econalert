# Employment Situation canonical data

`econalert` owns the release-vintage authority for BLS Employment Situation observations.

Canonical historical snapshot: `data/official/bls-employment-situation-2026-08.json`.
Deterministic consumer views: `api/v1/employment-situation/latest.json`, `latest.csv`, and `manifest.json`.

Downstream repositories such as `investor2` should consume these generated views rather than copying NFP, unemployment, participation, earnings, or revision values into a second handwritten authority.

Rebuild and verify the committed projection with:

```text
python scripts/employment_situation.py build --snapshot data/official/bls-employment-situation-2026-08.json --output-dir api/v1/employment-situation --check
```

A new archived BLS release can be collected with the `collect` subcommand using the official `https://www.bls.gov/news.release/archives/empsit_MMDDYYYY.htm` URL and an explicit retrieval timestamp. Missing metrics, unexpected series identity, malformed release identity, non-integral-thousand payroll prose, or revision arithmetic mismatch fail closed.

`evidence_sha256` hashes the normalized historical release excerpt committed as the replay fixture; it is deliberately not named `source_sha256`, because it is not a byte-for-byte hash of the complete BLS HTML response. Direct execution of the collector against a future/current release remains `UNVERIFIED` until that network path is actually run and read back.
