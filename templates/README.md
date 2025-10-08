# Template Library

The files in this directory are *symlinks* to the real templates that ship with
the Python package under `src/clodputer/templates/`. Keeping them in two places
serves different audiences:

- `src/clodputer/templates/` is packaged with `pip install clodputer`, so users
  who install the project receive the latest templates automatically.
- `templates/` (this folder) provides convenient access while browsing the git
  repository or reading the docs—copy from here when creating new tasks.

If you add or update a template, modify the file under
`src/clodputer/templates/` and update the symlink here to match.
