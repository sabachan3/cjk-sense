"""What the built distributions may hold (driven by scripts/e2e.sh, before anything is installed).

    python evals/package_contents.py DIST_DIR

DIST_DIR holds one sdist and one wheel. Both file lists must be exactly the expected ones, so a
new file reaches PyPI only after it was added here on purpose: nothing from runs/, docs/records/,
.claude/ or a cache can ride along. The metadata must carry the fields PyPI shows, name no email
address, and its long description (the README) may not hold a link PyPI cannot follow.
The decisions are pure functions with gate tests (tests/test_package_contents.py).
Only the standard library is used here.
"""

from __future__ import annotations

import argparse
import email
import re
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("check", "detect", "fonts", "snapshot")
PACKAGE_FILES = ("__init__.py", "__main__.py", "cli.py")
REPOSITORY = "https://github.com/sabachan3/cjk-sense"
REQUIRED_URLS = ("Homepage", "Repository", "Issues", "Changelog")


def expected_wheel(version: str) -> set[str]:
    info = f"cjk_sense-{version}.dist-info"
    return ({f"cjk_sense/{name}" for name in PACKAGE_FILES}
            | {f"cjk_sense/_services/{service}/{service}_lib.py" for service in SERVICES}
            | {"cjk_sense/_services/contracts/schema.py"}
            | {f"{info}/{name}" for name in ("METADATA", "WHEEL", "RECORD", "entry_points.txt", "licenses/LICENSE")})


def expected_sdist(version: str) -> set[str]:
    top = f"cjk_sense-{version}"
    return ({f"{top}/cjk_sense/{name}" for name in PACKAGE_FILES}
            | {f"{top}/services/{service}/{service}_lib.py" for service in SERVICES}
            | {f"{top}/contracts/{name}" for name in ("__init__.py", "schema.py")}
            | {f"{top}/{name}" for name in ("README.md", "CHANGELOG.md", "LICENSE", "pyproject.toml", "PKG-INFO",
                                             ".gitignore")})


def list_problems(kind: str, names: list[str], expected: set[str]) -> list[str]:
    """One line per file that is in the archive but not expected, or expected but not there."""
    found = set(names)
    return ([f"{kind}: unexpected file {name}" for name in sorted(found - expected)]
            + [f"{kind}: missing file {name}" for name in sorted(expected - found)]
            + [f"{kind}: {name} is listed twice" for name in sorted(found) if names.count(name) > 1])


def relative_links(markdown: str) -> list[str]:
    """Link and image targets that only work inside the repository. PyPI shows the README alone,
    so every target must be an absolute URL or an anchor on the same page."""
    targets = re.findall(r"\]\(\s*<?([^)\s>]+)", markdown)                              # [text](target), ![alt](target)
    targets += re.findall(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?\s*$", markdown, re.MULTILINE)  # [name]: target
    targets += re.findall(r"""(?:src|href)\s*=\s*["']?([^"'\s>]+)""", markdown)         # raw HTML
    return [target for target in targets if not re.match(r"(https://|http://|mailto:|#)", target)]


def metadata_problems(text: str, version: str) -> list[str]:
    """Problems in a METADATA or PKG-INFO file."""
    message = email.message_from_string(text)
    problems = []
    wanted = {"Name": "cjk-sense", "Version": version, "License-Expression": "MIT", "License-File": "LICENSE",
              "Requires-Python": ">=3.10", "Description-Content-Type": "text/markdown"}
    for field, value in wanted.items():
        if message.get(field) != value:
            problems.append(f"metadata: {field} is {message.get(field)!r}, expected {value!r}")
    for field in ("Summary", "Author", "Keywords"):
        if not (message.get(field) or "").strip():
            problems.append(f"metadata: {field} is missing")
    for field in ("Author-email", "Maintainer-email"):   # public rule of this repository: a name, no address
        if message.get(field):
            problems.append(f"metadata: {field} must not be set ({message.get(field)!r})")
    urls = dict(value.split(", ", 1) for value in message.get_all("Project-URL", []) if ", " in value)
    for label in REQUIRED_URLS:
        if not urls.get(label, "").startswith(REPOSITORY):
            problems.append(f"metadata: Project-URL {label} is {urls.get(label)!r}, expected a URL under {REPOSITORY}")
    if message.get_all("Requires-Dist", []) != ["playwright>=1.49"]:
        problems.append(f"metadata: Requires-Dist is {message.get_all('Requires-Dist', [])}, expected only playwright>=1.49")
    if not any(value.startswith("Programming Language :: Python :: 3.") for value in message.get_all("Classifier", [])):
        problems.append("metadata: no classifier names a Python minor version")
    description = message.get_payload() if isinstance(message.get_payload(), str) else ""
    if "# cjk-sense" not in description:
        problems.append("metadata: the long description is not the README")
    problems += [f"metadata: the README links to {target!r}, which PyPI cannot follow" for target in relative_links(description)]
    return problems


def source_version(init_text: str) -> str | None:
    found = re.search(r'^__version__ = "([^"]+)"$', init_text, re.MULTILINE)
    return found.group(1) if found else None


def project_version(pyproject_text: str) -> str | None:
    """`version` of the [project] table, read without a TOML parser (Python 3.10 has none)."""
    table = re.search(r"^\[project\]$(.*?)(?=^\[)", pyproject_text + "\n[", re.MULTILINE | re.DOTALL)
    found = re.search(r'^version = "([^"]+)"$', table.group(1), re.MULTILINE) if table else None
    return found.group(1) if found else None


def check_dist(dist: Path, version: str) -> tuple[list[str], list[str]]:
    """(lines to print, problems) for a directory holding the two distributions."""
    lines, problems = [], []
    wheels, sdists = sorted(dist.glob("*.whl")), sorted(dist.glob("*.tar.gz"))
    if [path.name for path in wheels] != [f"cjk_sense-{version}-py3-none-any.whl"]:
        problems.append(f"expected one wheel cjk_sense-{version}-py3-none-any.whl, found {[path.name for path in wheels]}")
    if [path.name for path in sdists] != [f"cjk_sense-{version}.tar.gz"]:
        problems.append(f"expected one sdist cjk_sense-{version}.tar.gz, found {[path.name for path in sdists]}")
    if problems:
        return lines, problems
    with zipfile.ZipFile(wheels[0]) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        info = f"cjk_sense-{version}.dist-info"
        texts = {name: archive.read(name).decode("utf-8") for name in (f"{info}/METADATA", "cjk_sense/__init__.py")
                 if name in names}
    lines += [f"{wheels[0].name}: {len(names)} files"] + [f"  {name}" for name in sorted(names)]
    problems += list_problems("wheel", names, expected_wheel(version))
    if f"{info}/METADATA" in texts:
        problems += [f"wheel {problem}" for problem in metadata_problems(texts[f"{info}/METADATA"], version)]
    if "cjk_sense/__init__.py" in texts and source_version(texts["cjk_sense/__init__.py"]) != version:
        problems.append(f"wheel: cjk_sense.__version__ is {source_version(texts['cjk_sense/__init__.py'])!r}, "
                        f"the distribution is {version!r}")
    with tarfile.open(sdists[0]) as archive:
        members = archive.getmembers()
        names = [member.name for member in members if not member.isdir()]
        for member in members:
            if not (member.isfile() or member.isdir()):
                problems.append(f"sdist: {member.name} is a link or a special file")
        info_member = next((member for member in members if member.name == f"cjk_sense-{version}/PKG-INFO"
                            and member.isfile()), None)
        pkg_info = archive.extractfile(info_member).read().decode("utf-8") if info_member else None
    lines += [f"{sdists[0].name}: {len(names)} files"] + [f"  {name}" for name in sorted(names)]
    problems += list_problems("sdist", names, expected_sdist(version))
    if pkg_info is not None:
        problems += [f"sdist {problem}" for problem in metadata_problems(pkg_info, version)]
    return lines, problems


def main(argv: list[str] | None = None) -> int:
    """Exit status: 0 when both distributions hold exactly what they should, 1 otherwise."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dist", type=Path, help="directory with the sdist and the wheel")
    parser.add_argument("--pyproject", type=Path, default=ROOT / "pyproject.toml", help="where the version is read from")
    args = parser.parse_args(argv)
    version = project_version(args.pyproject.read_text(encoding="utf-8"))
    if not version:
        print(f"package contents: no version in {args.pyproject}")
        return 1
    lines, problems = check_dist(args.dist, version)
    for line in lines + [f"FAIL {problem}" for problem in problems]:
        print(line)
    print(f"package contents: {'ok' if not problems else f'{len(problems)} problem(s)'} for version {version}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
