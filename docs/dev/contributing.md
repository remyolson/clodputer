# Developer Guidelines

This document supplements the root-level [CONTRIBUTING.md](../../CONTRIBUTING.md) with implementation-specific practices.

## Branching & Commits

- Use feature branches (`feature/cron-install`) for non-trivial work.
- Commit early and often; keep messages descriptive (`Add cron scheduling integration`).
- Update `docs/implementation/PROGRESS.md` alongside code changes.

## Code Style

- Python 3.9+ type annotations everywhere.
- Run `ruff` and `black` before committing (`black src tests`).
- Keep functions small and focused; prefer explicit helper functions over nested logic.
- Add docstrings for public classes/functions.

## Testing Expectations

- Every new feature should include unit tests.
- Use temporary directories (`tmp_path`) to avoid touching user state.
- When bug fixing, add a regression test.
- Run the full test suite before opening a pull request.

## Diagnostics First

- If a component exposes new state (queue, cron, watcher), add checks to `clodputer doctor`.
- Keep error messages actionable—include hints and references to user docs.

## Documentation

- Update user docs (`docs/user/`) and developer docs (`docs/dev/`) when behaviour changes.
- Provide new task examples in `templates/` if a feature benefits from them.

## Release Checklist

See [release.md](release.md) for tagging, changelog, and publishing steps.
