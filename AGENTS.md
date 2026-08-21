# Repository Agent Contract

## Mission

Own official macroeconomic release observations and release-vintage evidence for this repository. Convert primary statistical releases into reproducible, timestamped observations and stable public views without turning forecasts or secondary commentary into observed facts.

## Canonical authority

- Prefer official statistical agencies, central banks, World Bank and other primary public institutions appropriate to each series.
- Preserve series identity, geography, period, release/observation time, unit, revision/vintage semantics, source URL, retrieval time and source hash where available.
- Repository snapshots and generated public views must remain reproducible from their owning evidence.
- Other finance repositories should reference this repository's versioned macro artifacts instead of copying macro facts into parallel authorities.

## Autonomous execution

1. Inspect current `main`, README, open Issues/PRs, workflows, official snapshots, generated API/views and recent CI.
2. Resume an existing canonical workline before creating new collectors or schemas.
3. Prefer: newly verified official observations; revision/vintage corrections; deterministic release comparisons; public read-back; then simplification of repeated manual steps.
4. Materialize and validate evidence before generating downstream comparisons.
5. Use the smallest relevant tests/audits, PR and exact-head CI for implementation changes, then read back merged/public state when applicable.
6. Stop at the verified fixed point; do not manufacture activity when no new release or revision exists.

## Boundaries

- Null is not zero and an unavailable period is not an estimate.
- Observed, revised, preliminary, forecast and derived values must remain distinguishable.
- Do not silently replace an older release vintage with a later revision when point-in-time behavior matters.
- Do not execute trades or financial-account actions.
- Never claim an unobserved external fetch, CI layer or deployment passed.

## Completion report

Report material Before -> After observations/revisions, primary source and canonical artifact, Issue/PR/commit/CI evidence when applicable, public read-back when applicable, manual work removed, and remaining blocker.