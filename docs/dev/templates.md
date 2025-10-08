# Template Contribution Guide

Clodputer ships a curated library of task templates under
`src/clodputer/templates/`. Community templates are welcome—follow the process
below to propose additions.

## 1. Authoring checklist

- Use lower-case, hyphen-separated filenames (e.g. `calendar-sync.yaml`).
- Provide `name`, `description`, and either a `schedule` or `trigger`.
- Restrict `allowed_tools` to the minimum set required by the workflow.
- Reference secrets via `{{ secrets.MY_SECRET }}`, never inline credentials.
- Include meaningful logging in `on_success` / `on_failure`.
- Add contextual comments when advanced behaviour is required.

## 2. Local validation

```bash
# Ensure formatting, lint, and tests pass
ruff check src tests
pytest

# Verify the template renders through the helper module
python - <<'PY'
from clodputer.templates import available, export
print(available())
export("calendar-sync.yaml", "/tmp/calendar-sync.yaml")
PY
```

## 3. Submit a pull request

1. Add the YAML file to `src/clodputer/templates/`.
2. Create (or update) an entry in `templates/`—symlink to the packaged file.
3. Document the use case in `docs/user/quick-start.md` or another appropriate
   guide if it introduces a new workflow.
4. Update `CHANGELOG.md` under the "Added" section.

Label the PR with **`templates`** so reviewers can prioritise it.

## 4. Review criteria

- **Safety**: No destructive operations by default; prompts must be explicit.
- **Clarity**: Prompts should be single-shot and include success criteria.
- **Portability**: Avoid hard-coded absolute paths; use `context` variables.
- **Testing**: Provide manual test notes in the PR description.

Once merged, the maintainer will regenerate the packaging artefacts so the new
template ships with the next release.
