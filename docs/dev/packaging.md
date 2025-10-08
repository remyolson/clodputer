# Distribution Playbook

This guide explains how to package Clodputer for public distribution across
PyPI, Homebrew, and notarised binaries.

## 1. Build artefacts

```bash
python -m build --sdist --wheel
python -m pip install --upgrade twine
twine check dist/*
```

If you are preparing a pre-release, bump the version in `pyproject.toml` first
and commit the change with `Bump version to vX.Y.Z`.

## 2. Publish to PyPI

```bash
twine upload dist/*
```

Once the upload finishes, verify that
<https://pypi.org/project/clodputer/> lists the new release and that the entry
point (`clodputer`) installs correctly in a clean virtualenv:

```bash
python -m venv /tmp/clodputer-release
. /tmp/clodputer-release/bin/activate
python -m pip install clodputer==${VERSION}
clodputer --help
```

## 3. Update the Homebrew formula

The Homebrew tap lives in `packaging/homebrew/Formula/clodputer.rb`. The formula
is generated from the pinned dependency list in
`packaging/homebrew/requirements.lock`.

After building the release tarball (`dist/clodputer-${VERSION}.tar.gz`), render
the formula:

```bash
python scripts/update_homebrew_formula.py \
  --version ${VERSION} \
  --tarball dist/clodputer-${VERSION}.tar.gz \
  --tarball-url "https://github.com/remyolson/clodputer/releases/download/v${VERSION}/clodputer-${VERSION}.tar.gz"
```

Commit the updated formula and tap files, then push them to the `main` branch.
Consumers can now install via:

```bash
brew tap remyolson/clodputer https://github.com/remyolson/clodputer.git
brew install clodputer
```

## 4. macOS signing & notarisation

1. Build a standalone wheel or binary and codesign it with your Developer ID:
   ```bash
   codesign --deep --force --options runtime --sign "Developer ID Application: Jane Doe (ABCDE12345)" path/to/binary
   ```
2. Create a notarisation archive:
   ```bash
   ditto -c -k --keepParent path/to/binary clodputer.zip
   ```
3. Submit to Apple for notarisation:
   ```bash
   xcrun notarytool submit clodputer.zip \
     --apple-id "$APPLE_ID" \
     --team-id "$TEAM_ID" \
     --password "$NOTARYTOOL_PASSWORD" \
     --wait
   ```
4. Staple the ticket:
   ```bash
   xcrun stapler staple path/to/binary
   ```

Record the request UUID in `docs/dev/release.md` for auditing.

## 5. Post-release housekeeping

- Update `docs/implementation/PROGRESS.md` and `PROGRESS-v2.md`.
- Announce the release, linking to PyPI and the Homebrew tap.
- Clean up `dist/` once the artefacts have been mirrored to GitHub Releases.
