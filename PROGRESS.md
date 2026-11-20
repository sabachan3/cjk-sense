# Progress

Updated: 2026-11-20. Keep this file short and current; history belongs in git.

## Current State

- Version 0.1.0, public, installable from the repository URL. Not on PyPI.
- Five rules: `han-font`, `lang-mismatch`, `lang-missing`, `wrong-language`, `page-error`.
- Gate: 59 tests, under 1 s, runs as the pre-commit hook.
- Browser eval: 22/22 on macOS (Chromium) rerun 2026-11-20; 22/22 on Windows 11 (Edge) recorded
  2026-11-19.
- End-to-end check of the installed wheel: 4/4 on macOS, 2026-11-20.
- Field run (2026-11-19): 265 Japanese pages of open-source projects, 6.8% fail `han-font`,
  11.3% `lang-mismatch`. Details in [docs/results.md](docs/results.md).

## Completed

- 2026-11-19: 0.1.0, the four services, contracts, command, browser eval on macOS and Windows,
  field run, results document, GitHub Actions example.
- 2026-11-20: agent harness: `CLAUDE.md`, this file, `DECISIONS.md`, `features.json`,
  `scripts/setup.sh`, `scripts/e2e.sh` with `evals/e2e.py`, optional Stop hook, evaluator
  subagent definition. Same change: README layout and development sections rewritten, and a
  stale path in the `fonts_lib.py` docstring corrected.
- 2026-11-20: corrections after an independent review of that change. JSON output now writes
  control and direction characters from a page as escapes (`cli.json_text`); the end-to-end
  check reports a crashed command as a failed check instead of a traceback, with gate tests;
  `MIN_SCRIPT_SHARE` named in `detect_lib.py`; a gate test keeps the two `REPORT_VERSION`
  constants equal; statements in `CLAUDE.md`, `DECISIONS.md` and `features.json` corrected.

## In Progress

Nothing.

## Known Issues

- iOS and Android results are predictions from font lists. Never run on a device.
- Linux desktops are not covered by the font table.
- No person has judged the findings; false negatives on real sites are unmeasured.
- Simplified and Traditional Chinese are one region.
- A self-hosted font with an unusual name is treated as having no Han characters. The
  "confirmed in this browser" check catches that only where the machine has CJK fonts.
- Only the state of the page after load is checked, not text behind menus, tabs or dialogs.
- A page under `lang="ko"` with Japanese text can be predicted but not confirmed, because the
  probe may hold only characters the Korean font lacks (one case in the field run).
- The Windows browser eval cannot be rerun from macOS; `features.json` marks it `blocked`.
  Not rerun on Windows since 2026-11-19. Changes since then: a docstring in `fonts_lib.py`,
  a named constant in `detect_lib.py` (same value), JSON output escaping in `cli.py`. None
  changes a prediction or a rule, but that is argued, not shown by a Windows run.
- There is no CI in this repository itself: the gate runs only through the local hook.
- No lock file: `uv run --with` resolves `playwright>=1.49` and `pytest` at run time, so a
  breaking upstream release would show up as a gate or eval failure, not be prevented.

## Next Steps

1. Run the browser eval on an iOS and an Android device or emulator, and add those platforms to
   `PLATFORM` in `evals/eval_fixtures.py` when the font used can be read there.
2. Add a CI workflow for this repository: gate on every push, browser eval on macOS and
   Windows runners.
3. Field run on Chinese and Korean pages, which so far appear only in the browser eval.
4. Have a reader judge a sample of `han-font` findings, to tie the rule to what people notice.
5. Decide on PyPI publication.
