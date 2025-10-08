# PyPI Publishing Guide

This guide explains how to publish Clodputer to PyPI so users can install with `pipx install clodputer`.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/account/register/
2. **API Token**: Generate an API token at https://pypi.org/manage/account/token/
   - Name: `clodputer-publishing` (or any name you prefer)
   - Scope: `Entire account` (for first publish) or `Project: clodputer` (after first publish)
   - Save the token securely - it starts with `pypi-`

## Publishing Steps

### 1. Build the Package (Already Done)

The package has been built and is ready in `dist/`:
```bash
ls dist/
# clodputer-0.1.0-py3-none-any.whl
# clodputer-0.1.0.tar.gz
```

### 2. Test Upload to TestPyPI (Optional but Recommended)

Test the upload process first using TestPyPI:

```bash
# Create account at https://test.pypi.org/account/register/
# Generate API token at https://test.pypi.org/manage/account/token/

# Upload to TestPyPI
python3 -m twine upload --repository testpypi dist/*

# When prompted for username, enter: __token__
# When prompted for password, enter your TestPyPI API token (starts with pypi-)
```

Test installation from TestPyPI:
```bash
pipx install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ clodputer
```

### 3. Publish to PyPI

Once you've verified the test upload works:

```bash
# Upload to real PyPI
python3 -m twine upload dist/*

# When prompted:
# Username: __token__
# Password: <your-pypi-api-token>
```

### 4. Verify Publication

After successful upload:

1. Visit https://pypi.org/project/clodputer/
2. Test installation:
   ```bash
   pipx install clodputer
   clodputer --version
   ```

## Automating with GitHub Secrets (Optional)

For future releases, you can automate publishing using GitHub Actions:

1. Go to your repository settings: https://github.com/remyolson/clodputer/settings/secrets/actions
2. Add a new repository secret:
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI API token

3. Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

Then publishing is as simple as creating a GitHub release!

## Updating the Version

For future releases:

1. Update version in `pyproject.toml`
2. Create new git tag: `git tag -a v0.2.0 -m "Release v0.2.0"`
3. Push tag: `git push origin v0.2.0`
4. Rebuild and upload: `python3 -m build && twine upload dist/*`

## Troubleshooting

**Error: "File already exists"**
- You can't reupload the same version. Increment the version in `pyproject.toml` and rebuild.

**Error: "Invalid credentials"**
- Make sure you're using `__token__` as the username (with two underscores)
- Verify your API token is correct and not expired

**Error: "Project name already exists"**
- The project name `clodputer` might be taken. Check https://pypi.org/project/clodputer/
- If needed, choose a different name in `pyproject.toml`

## Current Status

✅ Package built: `dist/clodputer-0.1.0.tar.gz` and `dist/clodputer-0.1.0-py3-none-any.whl`
⏳ Ready to publish to PyPI (follow steps above)

After publishing, users will be able to install with:
```bash
pipx install clodputer
```
