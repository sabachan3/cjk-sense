"""What may be published: the file lists and metadata rules of evals/package_contents.py, and the
release files of this repository that have to agree with each other before a version goes out."""

import re
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
import package_contents as contents  # noqa: E402
import release_ready  # noqa: E402

import cjk_sense  # noqa: E402

README = "# cjk-sense\n\nSee [results](https://github.com/sabachan3/cjk-sense/blob/main/docs/results.md).\n"
METADATA = """Metadata-Version: 2.4
Name: cjk-sense
Version: 0.1.0
Summary: Find pages
Project-URL: Homepage, https://github.com/sabachan3/cjk-sense
Project-URL: Repository, https://github.com/sabachan3/cjk-sense
Project-URL: Issues, https://github.com/sabachan3/cjk-sense/issues
Project-URL: Changelog, https://github.com/sabachan3/cjk-sense/blob/main/CHANGELOG.md
Author: sabachan3
License-Expression: MIT
License-File: LICENSE
Keywords: cjk,fonts
Classifier: Programming Language :: Python :: 3.10
Requires-Python: >=3.10
Requires-Dist: playwright>=1.49
Description-Content-Type: text/markdown

""" + README


def test_good_metadata_has_no_problem():
    assert contents.metadata_problems(METADATA, "0.1.0") == []


def test_each_metadata_defect_is_reported():
    def problems(old, new, version="0.1.0"):
        assert old in METADATA
        return " | ".join(contents.metadata_problems(METADATA.replace(old, new), version))

    assert "Version is '0.1.0', expected '0.2.0'" in " | ".join(contents.metadata_problems(METADATA, "0.2.0"))
    assert "License-Expression" in problems("License-Expression: MIT\n", "")
    assert "License-File" in problems("License-File: LICENSE\n", "")
    assert "Requires-Python" in problems(">=3.10", ">=3.9")
    assert "Author is missing" in problems("Author: sabachan3\n", "")
    assert "Author-email must not be set" in problems("Author: sabachan3\n", "Author: sabachan3\nAuthor-email: a <a@example.org>\n")
    assert "Maintainer-email must not be set" in problems("Author: sabachan3\n", "Author: s\nMaintainer-email: a@example.org\n")
    assert "Project-URL Changelog" in problems("Project-URL: Changelog, https://github.com/sabachan3/cjk-sense/blob/main/CHANGELOG.md\n", "")
    assert "Project-URL Homepage" in problems("Homepage, https://github.com/sabachan3/cjk-sense", "Homepage, https://example.org/x")
    assert "Requires-Dist" in problems("Requires-Dist: playwright>=1.49\n", "Requires-Dist: playwright>=1.49\nRequires-Dist: requests\n")
    assert "Requires-Dist" in problems("Requires-Dist: playwright>=1.49\n", "")
    assert "Python minor version" in problems("Classifier: Programming Language :: Python :: 3.10\n", "")
    assert "not the README" in problems("# cjk-sense", "# something else")
    assert "'docs/results.md'" in problems("(https://github.com/sabachan3/cjk-sense/blob/main/docs/results.md)", "(docs/results.md)")


def test_relative_links_finds_every_form_and_accepts_absolute_ones_and_anchors():
    text = ("[a](docs/a.md) ![shot](img/shot.png) [b](https://example.org/b) [c](#rules) [d](<docs/d e.md>)\n"
            "[ref]: ../up.md\n[good]: https://example.org/\n<img src=\"logo.svg\"> <a href='/abs'>x</a> <img src=https://example.org/i.png>\n"
            "[mail](mailto:someone@example.org) [e]( ./e.md )")
    assert contents.relative_links(text) == ["docs/a.md", "img/shot.png", "docs/d", "./e.md", "../up.md", "logo.svg", "/abs"]
    assert contents.relative_links("no links, only `code(x)` and (parentheses)") == []


def test_file_lists_report_extra_missing_and_double_entries():
    wheel = sorted(contents.expected_wheel("0.1.0"))
    assert contents.list_problems("wheel", wheel, contents.expected_wheel("0.1.0")) == []
    assert len(wheel) == 13 and "cjk_sense/_services/contracts/schema.py" in wheel
    for extra in ("runs/field.json", "cjk_sense/__pycache__/cli.cpython-312.pyc", ".claude/settings.json",
                  "docs/records/windows-eval-2026-11-20.txt", "cjk_sense/_services/check/tests/test_check_lib.py"):
        assert contents.list_problems("wheel", wheel + [extra], contents.expected_wheel("0.1.0")) == [f"wheel: unexpected file {extra}"]
    gone = [name for name in wheel if not name.endswith("fonts_lib.py")]
    assert contents.list_problems("wheel", gone, contents.expected_wheel("0.1.0")) == [
        "wheel: missing file cjk_sense/_services/fonts/fonts_lib.py"]
    assert contents.list_problems("wheel", wheel + wheel[:1], contents.expected_wheel("0.1.0")) == [f"wheel: {wheel[0]} is listed twice"]
    sdist = contents.expected_sdist("0.1.0")
    assert len(sdist) == 15 and "cjk_sense-0.1.0/CHANGELOG.md" in sdist and "cjk_sense-0.1.0/LICENSE" in sdist
    assert not any(part in name for name in sdist for part in ("/tests/", "/evals/", "/docs/", "/runs/", "/scripts/", ".claude"))


def write_dist(folder, version="0.1.0", wheel_extra=(), sdist_extra=(), init_version=None, link=False):
    folder.mkdir()
    with zipfile.ZipFile(folder / f"cjk_sense-{version}-py3-none-any.whl", "w") as archive:
        for name in sorted(contents.expected_wheel(version)) + list(wheel_extra):
            text = METADATA if name.endswith("METADATA") else ""
            if name == "cjk_sense/__init__.py":
                text = f'__version__ = "{init_version or version}"\n'
            archive.writestr(name, text)
    staging = folder / "staging"
    for name in sorted(contents.expected_sdist(version)) + list(sdist_extra):
        path = staging / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(METADATA if name.endswith("PKG-INFO") else "", encoding="utf-8")
    with tarfile.open(folder / f"cjk_sense-{version}.tar.gz", "w:gz") as archive:
        archive.add(staging / f"cjk_sense-{version}", arcname=f"cjk_sense-{version}")
        if link:
            entry = tarfile.TarInfo(f"cjk_sense-{version}/link")
            entry.type, entry.linkname = tarfile.SYMTYPE, "/etc/hosts"
            archive.addfile(entry)
    return folder


def test_check_dist_passes_on_exactly_the_expected_archives_and_lists_them(tmp_path):
    lines, problems = contents.check_dist(write_dist(tmp_path / "dist"), "0.1.0")
    assert problems == []
    assert "cjk_sense-0.1.0-py3-none-any.whl: 13 files" in lines and "cjk_sense-0.1.0.tar.gz: 15 files" in lines
    assert "  cjk_sense/cli.py" in lines and "  cjk_sense-0.1.0/README.md" in lines


def test_check_dist_reports_private_files_a_stale_version_and_links(tmp_path):
    _, problems = contents.check_dist(write_dist(tmp_path / "a", wheel_extra=["cjk_sense/runs/field.json"],
                                                 sdist_extra=["cjk_sense-0.1.0/runs/field_urls.txt"]), "0.1.0")
    assert problems == ["wheel: unexpected file cjk_sense/runs/field.json",
                        "sdist: unexpected file cjk_sense-0.1.0/runs/field_urls.txt"]
    _, problems = contents.check_dist(write_dist(tmp_path / "b", init_version="0.0.9"), "0.1.0")
    assert problems == ["wheel: cjk_sense.__version__ is '0.0.9', the distribution is '0.1.0'"]
    _, problems = contents.check_dist(write_dist(tmp_path / "c", link=True), "0.1.0")
    assert "sdist: cjk_sense-0.1.0/link is a link or a special file" in problems
    _, problems = contents.check_dist(write_dist(tmp_path / "d"), "0.2.0")       # archives of another version
    assert len(problems) == 2 and "expected one wheel cjk_sense-0.2.0-py3-none-any.whl" in problems[0]
    (tmp_path / "empty").mkdir()
    assert len(contents.check_dist(tmp_path / "empty", "0.1.0")[1]) == 2


def test_main_exit_status_and_last_line(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[build-system]\nversion = "9"\n[project]\nname = "cjk-sense"\nversion = "0.1.0"\n[tool.x]\nversion = "8"\n',
                         encoding="utf-8")
    assert contents.main([str(write_dist(tmp_path / "good")), "--pyproject", str(pyproject)]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "package contents: ok for version 0.1.0"
    bad = write_dist(tmp_path / "bad", sdist_extra=["cjk_sense-0.1.0/.env"])
    assert contents.main([str(bad), "--pyproject", str(pyproject)]) == 1
    out = capsys.readouterr().out
    assert "FAIL sdist: unexpected file cjk_sense-0.1.0/.env" in out and out.splitlines()[-1].endswith("1 problem(s) for version 0.1.0")
    pyproject.write_text("[project]\nname = 'x'\n", encoding="utf-8")
    assert contents.main([str(bad), "--pyproject", str(pyproject)]) == 1


# --- the release files of this repository ---

def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_one_version_in_pyproject_the_package_and_the_changelog():
    version = contents.project_version(read("pyproject.toml"))
    assert version and re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert cjk_sense.__version__ == version == contents.source_version(read("cjk_sense/__init__.py"))
    assert re.search(rf"^## {re.escape(version)} \((\d{{4}}-\d{{2}}-\d{{2}}|not released yet)\)$", read("CHANGELOG.md"), re.MULTILINE)


def test_readme_has_no_link_that_breaks_on_pypi():
    assert contents.relative_links(read("README.md")) == []


def test_pyproject_names_no_email_address_and_matches_the_licence_file():
    pyproject = read("pyproject.toml")
    assert "@" not in pyproject and "email" not in pyproject
    assert 'license = "MIT"' in pyproject and 'license-files = ["LICENSE"]' in pyproject
    assert read("LICENSE").startswith("MIT License\n")


def test_every_file_the_wheel_takes_from_outside_the_package_is_in_the_expected_list():
    forced = re.findall(r'^"[^"]+" = "([^"]+)"$', read("pyproject.toml"), re.MULTILINE)
    assert len(forced) == 5 and set(forced) <= contents.expected_wheel("0.1.0")


def test_workflow_actions_are_pinned_to_a_commit_with_the_version_in_a_comment():
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert {path.name for path in workflows} >= {"ci.yml", "release.yml"}
    for path in workflows:
        uses = re.findall(r"^\s*(?:- )?uses:\s*(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
        assert uses, path.name
        for value in uses:
            assert value.startswith("./") or re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40} # v\d+\.\d+\.\d+", value), (path.name, value)


def test_release_workflow_publishes_only_on_a_release_or_by_hand_and_asks_for_no_token():
    text = read(".github/workflows/release.yml")
    triggers = text[text.index("\non:\n"):text.index("\npermissions:")]
    assert re.findall(r"^  (\w+):", triggers, re.MULTILINE) == ["release", "workflow_dispatch"]
    assert "types: [published]" in triggers
    assert "id-token: write" in text and "pypa/gh-action-pypi-publish@" in text
    assert not re.search(r"^\s*(password|user|repository-url)\s*:", text, re.MULTILINE) and "secrets." not in text
    assert text.index("uses: ./.github/workflows/ci.yml") < text.index("scripts/e2e.sh --dist") < text.index("pypa/gh-action-pypi-publish@")


def test_release_ready_wants_the_tag_the_package_and_a_dated_changelog_entry_to_agree(tmp_path, capsys):
    pyproject, init = '[project]\nname = "cjk-sense"\nversion = "0.1.0"\n', '__version__ = "0.1.0"\n'
    dated, undated = "# Changelog\n\n## 0.1.0 (2026-12-01)\n", "# Changelog\n\n## 0.1.0 (not released yet)\n"
    assert release_ready.release_problems("v0.1.0", pyproject, init, dated) == []
    assert "expected the tag 'v0.1.0'" in release_ready.release_problems("0.1.0", pyproject, init, dated)[0]
    assert "expected the tag 'v0.1.0'" in release_ready.release_problems("v0.1.1", pyproject, init, dated)[0]
    assert "__init__.py says '0.0.9'" in release_ready.release_problems("v0.1.0", pyproject, '__version__ = "0.0.9"\n', dated)[0]
    assert "write the release date" in release_ready.release_problems("v0.1.0", pyproject, init, undated)[0]
    assert "no entry" in release_ready.release_problems("v0.1.0", pyproject, init, "# Changelog\n\n## 0.1.00 (2026-12-01)\n")[0]
    assert release_ready.release_problems("v0.1.0", "[project]\n", init, dated) == ["pyproject.toml has no version"]
    (tmp_path / "cjk_sense").mkdir()
    for name, text in (("pyproject.toml", pyproject), ("cjk_sense/__init__.py", init), ("CHANGELOG.md", dated)):
        (tmp_path / name).write_text(text, encoding="utf-8")
    assert release_ready.main(["v0.1.0"], root=tmp_path) == 0 and "release ready: yes, v0.1.0" in capsys.readouterr().out
    assert release_ready.main(["v9"], root=tmp_path) == 1 and "FAIL the tag is 'v9'" in capsys.readouterr().out
    assert release_ready.main([], root=tmp_path) == 2
