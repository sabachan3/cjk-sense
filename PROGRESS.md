# Progress

Updated: 2026-11-22. Keep this file short and current; history belongs in git.

## Current State

- Version 0.1.0, public, installable from the repository URL. Not on PyPI: everything up to the
  owner's steps in [docs/release.md](docs/release.md) is prepared; the name `cjk-sense` was free on 2026-11-22.
- Five rules: `han-font`, `lang-mismatch`, `lang-missing`, `wrong-language`, `page-error`.
- Gate: 109 tests, under 1 s (also passes on Windows, checked by hand 2026-11-20), runs as the pre-commit hook.
- Browser eval: 22/22 on macOS (Chromium) rerun 2026-11-20; 22/22 on Windows 11 (Edge) rerun
  2026-11-20.
- End-to-end check of the built files: wheel 13 files and sdist 15 files exactly as expected,
  `twine check` passes, 6/6 checks for the installed wheel and 6/6 for the installed sdist on macOS, 2026-11-22.
- Field run (2026-11-19): 265 Japanese pages of open-source projects, 6.8% fail `han-font`,
  11.3% `lang-mismatch`. Details in [docs/results.md](docs/results.md).

## Completed

- 2026-11-19: 0.1.0: four services, contracts, command, browser eval on macOS and Windows, field run.
- 2026-11-20: agent documents, feature list, setup and end-to-end scripts.
- 2026-11-20: three independent reviews. Fixed: crash on a lone surrogate, raw invisible characters
  in output, tracebacks with exit 1 for unreadable or unwritable files, a hang on `--workers 0`,
  output that is not UTF-8. Details are in `git log` and `docs/results.md`.
- 2026-11-20: checked on a real Windows 11 machine (Edge eval 22/22, gate, redirected output).
- 2026-11-20: CI workflow (8 jobs, green) and pinned versions for the gate and the browser.
- 2026-11-22: independent review of everything since the third review (dbd3053..d95ff8b): PASS,
  no class A finding; gate on Python 3.10, 3.12 and 3.13, browser eval 22/22 and end-to-end 4/4
  on macOS rerun by the reviewer. Fixed from its notes: a URL list with a byte order mark, an
  indented comment line in a URL list, an empty file left behind a dangling `--out` link, the
  end-to-end install now under the browser pins; after an automated security note, the `--out`
  check follows no link and removes only its own probe file. Those fixes are not reviewed.
- 2026-11-22: release preparation. Package metadata (SPDX licence, author name without an
  address, project URLs, classifiers for what CI runs), `--version`, `CHANGELOG.md`, README
  ready for PyPI (absolute links, PyPI commands marked as not working yet, table of what was run
  where), exact file lists for wheel and sdist, the sdist installed and run as well,
  `.github/workflows/release.yml` (trusted publishing), actions pinned to commits,
  `docs/release.md` (owner's steps, yanking, licences). Privacy audit of the tree and the whole
  history: no secret, address, private path or host name found. Not reviewed independently.

## In Progress

Nothing.

## Known Issues

- `cjk_sense/cli.py` changed on 2026-11-22 (reading the URL list, the `--out` pre-check). The
  Windows browser eval record is from 2026-11-20 and was not rerun; the change does not touch
  fonts, snapshots or rules, and the Windows gate jobs in CI run the new tests. One of them makes
  a symbolic link: on a Windows account without that privilege (not the CI runners) it fails.
- The Windows record `docs/records/windows-eval-2026-11-20.txt` holds the eval output only; the
  date, Python version and code page in `docs/results.md` were written down by hand.
- The release workflow has never run: `release.yml` passes `actionlint` and its gate tests, but
  trusted publishing, the `pypi` environment and the artifact hand-over are first exercised by
  the first real release. Nothing was uploaded to PyPI or TestPyPI.
- The three workflow changes in `ci.yml` (pinned actions, `workflow_call`, the concurrency group
  named after the workflow) are not yet seen green: the first push after 2026-11-22 shows it.
- `--version` was added to `cjk_sense/cli.py` after the Windows browser eval record (same note as above).

Limits of the design:
- iOS and Android results are predictions from font lists. Never run on a device.
- Linux desktops are not covered by the font table.
- Simplified and Traditional Chinese are one region.
- A self-hosted font with an unusual name is treated as having no Han characters. The
  "confirmed in this browser" check catches that only where the machine has CJK fonts.
- Only the state of the page after load is checked, not text behind menus, tabs or dialogs.
- A page under `lang="ko"` with Japanese text can be predicted but not confirmed (one case in the field run).
- A page answered with HTTP 404 or 500 is checked like any other page.
- Text output drops the zero-width joiner, so a joined emoji in a sample prints as its parts.

Not measured:
- No person has judged the findings; false negatives on real sites are unmeasured.
- The hostile-page browser run in `docs/results.md` was by hand; no script reproduces it.
- CI runs the browser eval on macOS only (runner switched to Japanese). Windows runners have no
  Japanese fonts or display language, so the Windows browser eval is rerun by hand on the owner's
  machine after behaviour changes; CI covers Windows with the gate tests only.

## Next Steps

A new session can start 1 or 2 alone. 3 to 6 need the owner.

1. Add the hostile page of `docs/results.md` as fixtures in `evals/eval_fixtures.py` (a page whose
   script sets a lone surrogate, direction marks and zero-width characters), so that result is
   reproduced by `scripts/eval.sh` instead of by hand. Done when the eval passes with them on macOS.
2. Field run on Chinese and Korean pages: collect URLs the way `docs/results.md` describes for
   Japanese, run `cjk-sense check --urls-file ... --expect zh --out runs/field.zh.json`, summarise
   with `evals/field_summary.py`, and add the counts to `docs/results.md`. Takes network and time.
3. Owner: browser eval on an iOS and an Android device. Open question to settle first: how to
   read the font a mobile browser used; without that the eval can only compare rules, not fonts.
4. Owner: have a reader judge a sample of `han-font` findings.
5. Owner: publish 0.1.0 to PyPI by following [docs/release.md](docs/release.md): pending trusted
   publisher on PyPI, date in `CHANGELOG.md`, tag `v0.1.0`, GitHub release, verification with
   `uvx cjk-sense --help`, then the PyPI commands move to the top of the README.
6. Owner: decide whether Python 3.11 and 3.14 join the CI gate (both pass by hand on one Mac);
   only then may their classifiers be added to `pyproject.toml`.
