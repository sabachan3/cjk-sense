# Progress

Updated: 2026-11-20. Keep this file short and current; history belongs in git.

## Current State

- Version 0.1.0, public, installable from the repository URL. Not on PyPI.
- Five rules: `han-font`, `lang-mismatch`, `lang-missing`, `wrong-language`, `page-error`.
- Gate: 87 tests, under 1 s (also passes on Windows, checked by hand 2026-11-20), runs as the pre-commit hook.
- Browser eval: 22/22 on macOS (Chromium) rerun 2026-11-20; 22/22 on Windows 11 (Edge) rerun
  2026-11-20.
- End-to-end check of the installed wheel: 4/4 on macOS, 2026-11-20.
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

## In Progress

Nothing.

## Known Issues

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

A new session can start 1 or 2 alone. 3 to 5 need the owner.

1. Add the hostile page of `docs/results.md` as fixtures in `evals/eval_fixtures.py` (a page whose
   script sets a lone surrogate, direction marks and zero-width characters), so that result is
   reproduced by `scripts/eval.sh` instead of by hand. Done when the eval passes with them on macOS.
2. Field run on Chinese and Korean pages: collect URLs the way `docs/results.md` describes for
   Japanese, run `cjk-sense check --urls-file ... --expect zh --out runs/field.zh.json`, summarise
   with `evals/field_summary.py`, and add the counts to `docs/results.md`. Takes network and time.
3. Owner: browser eval on an iOS and an Android device. Open question to settle first: how to
   read the font a mobile browser used; without that the eval can only compare rules, not fonts.
4. Owner: have a reader judge a sample of `han-font` findings.
5. Owner: decide on PyPI publication.
