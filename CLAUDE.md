# cjk-sense: instructions for coding agents

A command-line check for web pages: Han characters drawn in another region's font (`han-font`)
and `<html lang>` that does not match the text. It drives Chromium through Playwright and applies
fixed rules. No model, no network service. Python 3.10+, version 0.1.0, MIT, public repository.

## Start of a session

1. Read [PROGRESS.md](PROGRESS.md): current state, known issues, next steps.
2. Read [features.json](features.json): what must keep working and the command that proves it.
3. `git log -5 --stat` and `git status --short`.
4. First time in a clone: `scripts/setup.sh`.

## Map

| path | role |
|---|---|
| `services/detect/detect_lib.py` | text -> `ja`, `zh`, `ko`, a script name, or None |
| `services/fonts/fonts_lib.py` | `INSTALLED` font table, `resolve()` = predicted region per platform |
| `services/snapshot/snapshot_lib.py` | Playwright: computed `font-family`, effective `lang`, fonts used |
| `services/check/check_lib.py` | findings, verdict, report, exit code, text output |
| `contracts/schema.py`, `contracts/README.md` | snapshot, analysed page, report v1 |
| `cjk_sense/cli.py` | the command; `analyse()` and `run()` are the only wiring between services |
| `services/*/tests`, `tests/test_cli.py` | gate tests |
| `evals/eval_fixtures.py` | browser eval, 22 pages with a known answer |
| `evals/e2e.py` | installed wheel against pages served over HTTP |
| `evals/field_summary.py` | counts from a report over many pages |
| `docs/results.md` | every measured number and what has not been measured |
| `DECISIONS.md` | why things are the way they are |

## Commands

```bash
scripts/setup.sh                   # hook, browser, gate
scripts/test.sh                    # gate: no browser, no network, under 2 s; also pre-commit
scripts/eval.sh                    # browser eval, macOS (about 5 s)
scripts/eval.sh --channel msedge   # browser eval, Windows with Edge
scripts/e2e.sh                     # wheel -> clean environment -> real browser over HTTP
agent-sense done --run             # optional tool: records that the gate passed on these files
```

## Definition of done

All of these, shown by command output from this session, not by memory:

1. `scripts/test.sh` green after the last edit.
2. The `verify` command of every feature the change touches exits 0. A change to
   `fonts_lib.py`, `snapshot_lib.py` or the rules in `check_lib.py` also needs `scripts/eval.sh`;
   a change to packaging or `cli.py` also needs `scripts/e2e.sh`.
3. `agent-sense done --run` passes, when agent-sense is installed.
4. New behaviour has a gate test, and a fixture in `evals/eval_fixtures.py` when a browser is
   involved. A bug fix has the test that would have caught it.
5. `PROGRESS.md` updated; `DECISIONS.md` gets an entry when a choice was made between options;
   `docs/results.md` and `README.md` updated when a number or a rule changed.
6. Committed. No debug output, no stray files.

Before reporting DONE on a change to the rules (`check_lib.py`, `detect_lib.py`) or to the font
tables (`fonts_lib.py`), run the `evaluator` subagent (`.claude/agents/evaluator.md`) on the
diff and include its verdict.

## Hard constraints

1. Services never import each other. Only `cjk_sense/cli.py` puts them together, through the
   shapes in `contracts/`.
2. A change to a contract shape updates `contracts/schema.py` and `contracts/README.md` and
   bumps the report `version`.
3. Character ranges and control characters in source are written as `\uXXXX` escapes
   (`detect_lib.RANGES`, `check_lib._CONTROL`). After writing such a file, check the escapes
   are still escapes: some editing tools turn them into literal characters.
4. The gate stays free of browser and network and under 2 s. Browser work belongs in `evals/`.
5. A file the installed command needs must be listed under `force-include` in
   `pyproject.toml`; `scripts/e2e.sh` is the proof.
6. Text that comes from a page goes through `check_lib.clean()` before it reaches a terminal.
7. No model and no network service at run time. The only runtime dependency is `playwright`.
8. A font table entry names the platforms that ship the font. Do not add one from memory:
   confirm with the browser eval on that platform, or mark it unverified in `docs/results.md`.
9. iOS and Android are predictions. Never write that they were verified until run on a device.
10. Numbers in `README.md` and `docs/results.md` come from a run in `runs/` (git-ignored);
    change them only by rerunning.
11. Thresholds are the constants at the top of `check_lib.py` and `detect_lib.py`; a change
    needs a `DECISIONS.md` entry and the browser eval.
12. `state` in `features.json` becomes `passing` only after its `verify` command exited 0.
13. Do not weaken a test to make it pass: no skips, no removed assertions, no loosened expected
    values without a `DECISIONS.md` entry saying why the old expectation was wrong.
14. This repository is public: no secrets, no private paths, host names or personal details.

## End of a session

Run the gate, update `PROGRESS.md` (move finished items, add what is known to be broken, write
the next step so that someone without this conversation can take it), commit.
