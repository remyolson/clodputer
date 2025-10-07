# Release Procedure

This guide captures the steps for preparing and publishing a new Clodputer release.

## 1. Pre-Release Checklist

- [ ] All checkboxes in `docs/implementation/PROGRESS.md` are complete for the target milestone.
- [ ] `pytest`, `ruff check`, and `black --check` pass locally.
- [ ] Documentation updated (README, user/dev docs, templates).
- [ ] `CHANGELOG.md` has an entry for the new version.
- [ ] `clodputer doctor` passes on a clean environment.

## 2. Version Bump

1. Update `pyproject.toml` (`[project] version`).
2. Update the badge/version references in README if necessary.
3. Commit with message `Bump version to vX.Y.Z`.

## 3. Tagging

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

## 4. GitHub Release

- Title: `vX.Y.Z`
- Body: Copy the corresponding entry from `CHANGELOG.md`.
- Attach any release assets (optional).

## 5. Distribution (future)

- Publish to PyPI or Homebrew once packaging is ready.
- Update installation instructions to reflect new distribution channels.

## 6. Post-Release

- Move unfinished tasks (if any) to the next milestone in `PROGRESS.md`.
- Announce the release (blog post, social channels, etc.).
- Monitor issues and collect feedback for the next iteration.
