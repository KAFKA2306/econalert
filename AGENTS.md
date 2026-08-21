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
5. Use the smallest relevant tests/audits and exact-head CI for implementation changes.
6. Stop at the verified fixed point; do not manufacture activity when no new release or revision exists.

## Branch lifecycle

- Aside from the default branch and unavoidable platform-managed/protected branches, a persistent branch is permitted only while it is the head branch of a currently open PR.
- Creating a work branch creates an obligation to open or reuse its canonical PR immediately; do not use branches as backlog, continuation state, backup, archive, or evidence storage.
- After a PR is merged or closed, delete its head branch after verifying PR/main state. A branch with no open PR is an orphan and must be deleted.
- Before and after work, compare repository branches with open PR heads. Do not report cleanup/fixed point while an orphan task branch remains.
- If the available tool cannot delete a branch, record that as a tooling blocker and do not claim cleanup complete. Never create another orphan branch as a workaround.

## Merge and release are separate

### PR merge conditions

A PR may merge when the repository-local change is correct on the exact reviewed revision: the bounded contract is satisfied, primary-source/provenance and vintage semantics are preserved, relevant deterministic tests/audits pass, generated artifacts are reproducible when affected, and no unresolved correctness or review blocker remains.

A future official release, live collection after merge, public API/Pages availability, or other post-merge operating evidence is **not** a merge condition unless the PR itself changes the release mechanism and that mechanism must be validated before merge.

### Product/data release conditions

Release is a separate post-merge decision. Treat a macro data/API release as complete only after the merged `main` revision is read back and the release surface in scope is actually verified: published snapshot/API/Pages output, deployment identity, release-vintage metadata, fresh upstream observation when required, and rollback/rebuild path where applicable.

A merged PR does not prove a release. A release blocker does not retroactively invalidate a correctly merged repository change. Report merge evidence and release evidence separately.

## Boundaries

- Null is not zero and an unavailable period is not an estimate.
- Observed, revised, preliminary, forecast and derived values must remain distinguishishable.
- Do not silently replace an older release vintage with a later revision when point-in-time behavior matters.
- Do not execute trades or financial-account actions.
- Never claim an unobserved external fetch, CI layer or deployment passed.

## Completion report

Report material Before -> After observations/revisions, primary source and canonical artifact, Issue/PR/commit/CI evidence, then report `merged` and `released` separately with direct evidence for each. Include branch cleanup state, public read-back only when release is in scope, manual work removed, and remaining blocker.