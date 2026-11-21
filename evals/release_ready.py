"""Is this version ready to be tagged and published? (run by .github/workflows/release.yml, and by
hand before tagging: docs/release.md)

    python evals/release_ready.py v0.1.0

The tag must be `v` + the version in pyproject.toml, the package must say the same version, and
the changelog must have an entry for it with a date. Reads three files, nothing else.
The decision is a pure function with gate tests (tests/test_package_contents.py).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import package_contents

ROOT = Path(__file__).resolve().parents[1]


def release_problems(tag: str, pyproject: str, init: str, changelog: str) -> list[str]:
    version = package_contents.project_version(pyproject)
    if not version:
        return ["pyproject.toml has no version"]
    problems = []
    if tag != f"v{version}":
        problems.append(f"the tag is {tag!r}, pyproject.toml says version {version}: expected the tag 'v{version}'")
    if package_contents.source_version(init) != version:
        problems.append(f"cjk_sense/__init__.py says {package_contents.source_version(init)!r}, pyproject.toml says {version!r}")
    heading = re.search(rf"^## {re.escape(version)} \((.*)\)$", changelog, re.MULTILINE)
    if not heading:
        problems.append(f"CHANGELOG.md has no entry '## {version} (YYYY-MM-DD)'")
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", heading.group(1)):
        problems.append(f"CHANGELOG.md says '## {version} ({heading.group(1)})': write the release date there")
    return problems


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("usage: release_ready.py TAG   (for example v0.1.0)", file=sys.stderr)
        return 2
    problems = release_problems(arguments[0], *((root / name).read_text(encoding="utf-8")
                                                for name in ("pyproject.toml", "cjk_sense/__init__.py", "CHANGELOG.md")))
    for problem in problems:
        print(f"FAIL {problem}")
    print(f"release ready: {'yes, ' + arguments[0] if not problems else f'no, {len(problems)} problem(s)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
