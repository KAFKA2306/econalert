# Development checks

This repository is a small Python 3.12 codebase with no runtime third-party package manifest or lockfile. The only CI-only dependency is `pytest`.

## Bootstrap

```bash
python -m pip install pytest
```

## One check command

Run the same non-networked checks used by pull-request CI:

```bash
python scripts/check.py
```

The command compiles maintained Python files, rebuilds the committed public API, runs the test suite, exercises the synthetic and official CPI-U contract examples, verifies deterministic API output, parses committed JSON, removes Python bytecode caches, and fails if the checkout is dirty afterward.

Collection from BLS remains separate because network retrieval changes external inputs. CI validates committed snapshots instead of silently replacing them.

## Tool ownership

- formatting: no formatter is installed; there is no duplicate formatter owner to consolidate
- linting: no linter is installed; repository checks are currently tests and deterministic artifact validation
- static typing: no type checker is installed; adding one is not justified by a measured defect in the current repository
- dependency lock: not applicable until the repository adopts a package manifest/lockfile
- schema validation: performed at the external-data and contract boundaries already exercised by tests and the check command

Do not add Ruff, Pyrefly, a task runner, a pre-commit framework, or a monorepo tool solely for consistency with other repositories. Add tooling only when it replaces an existing responsibility or catches a demonstrated defect at lower total maintenance cost.
