#!/usr/bin/env python3
"""
Render the Homebrew formula from the pinned dependency lock file.

Usage:
    python scripts/update_homebrew_formula.py \
        --version 0.1.0 \
        --tarball dist/clodputer-0.1.0.tar.gz

The script will:
  * Compute the SHA256 of the release tarball
  * Resolve PyPI download URLs + SHA256 for each dependency listed in
    packaging/homebrew/requirements.lock
  * Rewrite packaging/homebrew/Formula/clodputer.rb with the new artefacts
"""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path
from typing import Iterable, List, Tuple
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
FORMULA_PATH = ROOT / "packaging" / "homebrew" / "Formula" / "clodputer.rb"
LOCK_PATH = ROOT / "packaging" / "homebrew" / "requirements.lock"

FORMULA_TEMPLATE = """# frozen_string_literal: true

require "language/python/virtualenv"

class Clodputer < Formula
  include Language::Python::Virtualenv

  desc "Autonomous Claude Code automation system"
  homepage "https://github.com/remyolson/clodputer"
  url "{tarball_url}"
  sha256 "{tarball_sha}"
  license "MIT"
  head "https://github.com/remyolson/clodputer.git", branch: "main"

  depends_on "python@3.11"

{resources}
  def install
    virtualenv_install_with_resources
  end

  test do
    help_output = shell_output("#{{bin}}/clodputer --help")
    assert_match "Clodputer CLI", help_output
  end
end
"""


def parse_lockfile(path: Path) -> List[Tuple[str, str]]:
    dependencies: List[Tuple[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = line.split(";", 1)[0].strip()
        if "==" not in requirement:
            raise ValueError(f"Lock entry must pin a version: {raw_line}")
        name, version = requirement.split("==", 1)
        dependencies.append((name.strip(), version.strip()))
    return dependencies


def pypi_url_and_sha(name: str, version: str) -> Tuple[str, str]:
    api_url = f"https://pypi.org/pypi/{name}/{version}/json"
    with urlopen(api_url) as response:  # nosec: trusted PyPI API
        payload = json.load(response)
    files = payload.get("urls") or []
    if not files:
        raise RuntimeError(f"No distribution files published for {name}=={version}")
    sdist = next((f for f in files if f.get("packagetype") == "sdist"), files[0])
    return sdist["url"], sdist["digests"]["sha256"]


def build_resource_block(name: str, url: str, sha256: str) -> str:
    block = textwrap.dedent(
        f"""\
        resource "{name}" do
          url "{url}"
          sha256 "{sha256}"
        end
        """
    ).strip("\n")
    return textwrap.indent(block, "  ") + "\n\n"


def compute_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render Homebrew formula from lock file.")
    parser.add_argument("--version", required=True, help="Released version (e.g. 0.1.0)")
    parser.add_argument(
        "--tarball",
        default=None,
        help="Path to the release tarball (defaults to dist/clodputer-<version>.tar.gz)",
    )
    parser.add_argument(
        "--tarball-url",
        default=None,
        help="Public URL for the tarball (defaults to GitHub release URL based on version).",
    )
    parser.add_argument(
        "--output",
        default=FORMULA_PATH,
        type=Path,
        help="Formula path to overwrite (default: packaging/homebrew/Formula/clodputer.rb)",
    )
    parser.add_argument(
        "--lock",
        default=LOCK_PATH,
        type=Path,
        help="Pinned dependency lock file (default: packaging/homebrew/requirements.lock)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    tarball_path = Path(args.tarball or ROOT / "dist" / f"clodputer-{args.version}.tar.gz")
    if not tarball_path.exists():
        raise SystemExit(f"Tarball not found at {tarball_path}. Run `python -m build --sdist` first.")
    tarball_url = (
        args.tarball_url
        or f"https://github.com/remyolson/clodputer/releases/download/v{args.version}/{tarball_path.name}"
    )
    tarball_sha = compute_sha(tarball_path)

    dependencies = parse_lockfile(args.lock)
    resource_blocks = []
    for name, version in dependencies:
        url, sha256 = pypi_url_and_sha(name, version)
        resource_blocks.append(build_resource_block(name, url, sha256))

    formula = FORMULA_TEMPLATE.format(
        tarball_url=tarball_url,
        tarball_sha=tarball_sha,
        resources="".join(resource_blocks),
    )
    args.output.write_text(formula, encoding="utf-8")
    print(f"Updated {args.output} with {len(resource_blocks)} resources.")


if __name__ == "__main__":
    main()
