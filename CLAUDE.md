# cjk-sense: instructions for coding agents

A command-line check for web pages: Han characters drawn in another region's font (`han-font`)
and `<html lang>` that does not match the text. It drives Chromium through Playwright and applies
fixed rules. No model, no network service. Python 3.10+ (CI runs 3.10, 3.12, 3.13), version 0.1.0,
MIT, public repository. Needs `uv` for every script here.

## Start of a session

1. Read [PROGRESS.md](PROGRESS.md): current state, known issues, next steps.
2. Read [features.json](features.json): what must keep working and the command that proves it.
3. `git log -5 --stat` and `git status --short`. First time in a clone: `scripts/setup.sh`.

## Map

| path | role |
|---|---|
| `services/detect/detect_lib.py` | text -> `ja`, `zh`, `ko`, a script name, or None |
| `services/fonts/fonts_lib.py` | `INSTALLED` font table, `resolve()` = predicted region per platform |
| `services/snapshot/snapshot_lib.py` | Playwright: computed `font-family`, effective `lang`, fonts used |
| `services/check/check_lib.py` | findings, verdict, report, exit code, text output |
| `contracts/schema.py`, `contracts/README.md` | snapshot, analysed page, report v1 |
| `cjk_sense/cli.py` | the command, and the only place where services are put together |
| `services/*/tests`, `tests/` | gate tests |
| `evals/eval_fixtures.py` | browser eval, 22 pages with a known answer |
| `evals/e2e.py` | installed wheel against pages served over HTTP; its verdict functions and exit status have gate tests |
| `evals/field_summary.py` | every field count quoted in the documents (percentages are derived from them), from a report over many pages; gate-tested |
| `docs/results.md`, `docs/records/` | results by date and what has not been measured; kept output of runs on other machines |
| `requirements-*.txt`, `.github/workflows/ci.yml` | pinned versions for gate and browser (`uv pip compile --universal` from the `.in` files); CI: gate on three systems, browser eval on macOS and Windows, installed wheel |
| `DECISIONS.md` | why things are the way they are |

## Commands

```bash
scripts/setup.sh                   # hook, browser, gate
scripts/test.sh                    # gate: no browser, no network, under 2 s; also pre-commit
scripts/eval.sh                    # browser eval, macOS (about 5 s)
scripts/eval.sh --channel msedge   # browser eval, Windows with Edge
scripts/e2e.sh                     # wheel -> clean environment -> real browser over HTTP
agent-sense done --run             # only if installed (see "About agent-sense"): records that the gate passed
```

## Definition of done

All of these, shown by command output from this session, not by memory:

1. `scripts/test.sh` green after the last edit, and `agent-sense done --run` passes if that tool is installed.
2. The `verify` command of every feature the change touches exits 0. A change under
   `services/` or to `cjk_sense/cli.py` also needs `scripts/eval.sh`; a change to packaging
   (`pyproject.toml`), `cjk_sense/` or `contracts/` also needs `scripts/e2e.sh`.
3. New behaviour has a gate test, and a fixture in `evals/eval_fixtures.py` when a browser is
   involved. A bug fix has the test that would have caught it.
4. `PROGRESS.md` updated so that someone without this conversation can take the next step;
   `DECISIONS.md` gets an entry when a choice was made between options; `docs/results.md` and
   `README.md` updated when a number or a rule changed.
5. Committed and pushed to `main` after reading the diff for private details (the public-repository constraint).
   CI must end green; a red run is fixed before anything else. No debug output, no stray files.

Before reporting DONE on a change to the rules (`check_lib.py`, `detect_lib.py`) or to the font
tables (`fonts_lib.py`), run the `evaluator` subagent (`.claude/agents/evaluator.md`) on the
diff and include its verdict. If this session cannot start subagents, say so in the report
instead of skipping silently.

## Hard constraints

1. Services never import each other. Only `cjk_sense/cli.py` puts them together, through the
   shapes in `contracts/`.
2. A change to a contract shape updates `contracts/schema.py` and `contracts/README.md` and bumps
   `REPORT_VERSION` in both `contracts/schema.py` and `check_lib.py` (a gate test keeps them equal).
3. Character ranges in source are `\uXXXX` escapes (`detect_lib.RANGES`); tests build invisible
   characters with `chr()`. After writing such a file, check that the escapes are still escapes.
4. The gate stays free of browser and network and under 2 s. Browser work belongs in `evals/`.
5. A file the installed command needs must be listed under `force-include` in
   `pyproject.toml`; `scripts/e2e.sh` is the proof.
6. Text from a page never reaches a terminal raw. Categories Cc, Cf, Zl, Zp, Cs and Co are dropped
   from text output and error messages (`check_lib.clean()`) and written as `\uXXXX` escapes in
   JSON, on stdout and in `--out` (`cli.json_text()`). A new output path needs one of the two.
7. No model and no network service at run time. The only runtime dependency is `playwright`.
8. A font table entry names the platforms that ship the font. Do not add one from memory:
   confirm with the browser eval on that platform, or mark it unverified in `docs/results.md`.
   iOS and Android are predictions until run on a device.
9. Numbers in `README.md` and `docs/results.md` change only by rerunning. Field counts come from
    `runs/field.json` through `evals/field_summary.py`; `runs/` is git-ignored, so a fresh clone
    cannot recompute them (ask the owner for the file). Browser eval and end-to-end numbers are the
    printed output of `scripts/eval.sh` and `scripts/e2e.sh`; output from another machine is kept
    in `docs/records/`.
10. Thresholds are the constants at the top of `check_lib.py` and `detect_lib.py`; a change
    needs a `DECISIONS.md` entry, the gate tests that pin the boundary, and the browser eval.
    The browser eval alone does not notice a change to `MIN_SCRIPT_SHARE`; its gate test does.
11. `state` in `features.json` becomes `passing` only after its `verify` command exited 0.
    Do not weaken a test to make it pass: no skips, no removed assertions, no loosened expected
    values without a `DECISIONS.md` entry saying why the old expectation was wrong.
12. This repository is public: no secrets, no private paths, host names or personal details.
13. Work happens on `main`. Publishing to PyPI, and anything that needs a Windows machine, an
    iPhone or an Android device, is the owner's: ask, do not improvise.

## About agent-sense

The author's own unpublished tool for checking agent work; optional. Without it, ignore every line that mentions it (the hook in `.claude/settings.json` then does nothing).
With it, a Stop hook refuses to end a session while the gate has not passed on the final files.
