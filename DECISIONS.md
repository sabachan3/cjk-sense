# Decisions

Newest first. Each entry: what was decided, why, and what was rejected.

Entries dated before 2026-11-20 were written down on 2026-11-20. Where a reason is not backed
by a measurement in `docs/results.md`, it is the author's reasoning, not a measured fact.

## 2026-11-22: The published files are checked against exact lists, and the release uploads the files that were run

- Decision: `evals/package_contents.py` holds the exact file list of the wheel (13) and of the
  sdist (15) and the metadata rules (SPDX licence, an author name and no email address, project
  URLs, no README link that PyPI cannot follow). `scripts/e2e.sh` builds both archives, compares,
  runs `twine check --strict`, installs each and runs it; with `--dist DIR` it hands over the
  two files only after all of that passed, and `release.yml` uploads from there. The sdist holds
  what builds the wheel plus README, changelog and licence; tests, evals, scripts and agent
  documents are not in it.
- Why: the repository holds things that must not be published by accident (`runs/` with the
  field-run URLs when a clone has them, kept records, agent settings). A list of forbidden
  patterns only catches what someone thought of; an exact list fails on anything new. Building
  again inside the publish job would upload files nobody installed.
- Rejected: a deny list of paths; trusting `.gitignore` alone (hatchling follows it, but an
  `include` line can still pull a tracked private file in); an sdist with the tests (they need
  `conftest.py`, the pinned requirements and the scripts as well, so it would be most of the
  repository for no user of the command); a second build in the release workflow.

## 2026-11-22: Publishing through PyPI trusted publishing, started only by a GitHub release or by hand

- Decision: `.github/workflows/release.yml` runs on `release: published` and on manual dispatch
  with the version typed in. It calls `ci.yml`, checks that the tag is `v` + the version and that
  the changelog entry has a date (`evals/release_ready.py`), then publishes with
  `pypa/gh-action-pypi-publish` under the `pypi` environment with `id-token: write` and nothing
  else. Every action in both workflows is pinned to a commit; a gate test refuses a bare tag.
- Why: no token exists that could leak or expire, and a push can never publish. A tag such as
  `v4` can be moved to other code by whoever controls the action's repository; a commit cannot.
- Rejected: an API token in repository secrets; publishing from a laptop with `twine upload`
  (works, but what is uploaded is then not what CI ran); publishing on every tag push (a tag
  pushed by mistake would publish, and a version number cannot be reused).
- Cost: pinned commits do not move by themselves; they are raised by hand with the look-up
  written at the top of `ci.yml`. Actions stay on the major versions CI already ran green
  (`checkout` v4, `setup-uv` v6); newer majors exist and were not tried.

## 2026-11-22: Classifiers name only what CI runs

- Decision: Python 3.10, 3.12 and 3.13 and the three systems of the CI gate are listed;
  `requires-python` stays `>=3.10`. `Development Status :: 4 - Beta`.
- Why: a classifier is read as "tested". 3.11 and 3.14 pass the gate by hand on one Mac but are
  not in CI. Adding CI jobs was left out of the release preparation because a new job could not
  be seen green before the push.
- Rejected: listing 3.11 and 3.14 on the strength of one local run; an upper bound on
  `requires-python` (it would refuse installs that work).

## 2026-11-22: A URL list may start with a byte order mark

- Decision: `--urls-file` is read as `utf-8-sig`, and a comment line may be indented.
- Why: a list saved by a Windows editor gave its first URL an invisible leading character, and
  that page was reported as `page-error` instead of being checked (found in review).
- Rejected: documenting "save without a byte order mark" (the tool is meant to run on Windows).

## 2026-11-20: Versions for the gate and the browser are pinned; the Windows browser eval stays by hand

- Decision: `requirements-gate.txt` and `requirements-browser.txt`, compiled from their `.in`
  files, are what the gate, the evals and CI install. `scripts/e2e.sh` installs the wheel under
  the browser pins as constraints. The Windows browser eval is not a CI job; it is rerun by hand
  on a Windows machine and its output is kept under `docs/records/`.
- Why: an unpinned test runner or browser driver can turn the checks red with no change here.
  The hosted Windows runner has an English display language and no Japanese fonts by default, so
  an eval there would test the runner's setup, not the tool (reasoning, not measured beyond the
  first failing CI run).
- Rejected: installing a language pack on the runner in every CI run (slow, and still not the
  machine a user has); dropping the Windows eval.

## 2026-11-20: Text output removes invisible characters, JSON escapes them

- Decision: decided by Unicode category. `check_lib.clean()` drops Cc, Cf, Zl, Zp, Cs
  and Co from text output and error messages and turns other white space into a plain space.
  Unassigned code points are kept (changed 2026-11-20: `str.isprintable()` also rejected kanji
  newer than the running Python's Unicode tables, so a report differed between Python versions).
  Known cost in text output: the zero-width joiner goes too, so a joined emoji prints as its
  parts, and the full-width space prints as an ordinary space. JSON keeps both. `cli.json_text()` writes every character of category Cc,
  Cf, Zl, Zp, Cs or Co as a `\uXXXX` escape, on stdout and in the `--out` file.
- Why: page text is untrusted and reaches terminals and CI logs. Text is for reading, so
  dropping is fine. JSON is data, so nothing may be lost: an escape keeps the value and shows
  the reader that the character is there. A first version listed ranges and missed direction
  marks, zero-width characters and lone surrogates; a lone surrogate crashed the command.
- Rejected: `ensure_ascii=True` (every kanji and kana in the report becomes an escape, which
  makes samples unreadable in a tool about CJK text); a list of dangerous ranges (it was
  incomplete once already); removing characters from JSON (the report would no longer say what
  the page holds).

## 2026-11-20: The agent Stop hook is optional and does nothing without the tool

- Decision: `.claude/settings.json` runs `agent-sense hook stop` only when `agent-sense` is on
  the PATH, and otherwise succeeds silently.
- Why: the repository is public and `agent-sense` is the author's own unpublished tool, so
  nobody else has it. Nothing in this repository needs it; without it the hook is a no-op.
- Rejected: keeping the hook in an untracked local settings file (each clone would have to
  set it up again and the check would be forgotten).

## 2026-11-20: End-to-end check installs the wheel and serves pages over HTTP

- Decision: `scripts/e2e.sh` builds the wheel, installs it into a throwaway environment and
  runs the installed command from outside the repository against a local HTTP server.
- Why: the browser eval imports the services from the working tree and uses `file://` pages,
  so a file missing from `force-include` or a difference over HTTP would pass it.
- Rejected: adding it to the gate (it needs a browser and takes several seconds).

## 2026-11-19: Predict the font from CSS per platform, and use the browser only to confirm

- Decision: `fonts_lib.resolve()` predicts the region for macOS, Windows, iOS and Android from
  `font-family`, `lang` and a table of shipped fonts. The fonts the browser really used are
  reported as confirmation when the machine has them.
- Why: a CI runner on Linux has no CJK fonts, and one machine can only show its own platform.
- Rejected: reporting only the fonts the running browser used.

## 2026-11-19: Fixed rules, no model

- Decision: every rule is a deterministic function of the page snapshot.
- Why: the same page must give the same answer in CI, and the check must run offline.
- Rejected: asking a vision or language model whether the glyphs look right.

## 2026-11-19: Languages are told apart by script only

- Decision: `detect_lib` separates Japanese, Chinese and Korean by kana, Han and Hangul counts
  and resolves other languages to their script.
- Why: no dependency and no ambiguity for the three languages the font rule is about.
- Rejected: a language-identification library. Cost: `lang="fr"` on an English page passes.

## 2026-11-19: Simplified and Traditional Chinese are one region

- Decision: the regions are `ja`, `zh`, `ko`.
- Why: the defect targeted is cross-language letterforms. Reasoning, not measured: many
  characters are shared by both Chinese variants, so short text does not say which one it is.
- Rejected: `zh-Hans` and `zh-Hant` as separate regions.

## 2026-11-19: `han-font` fails at 20% of the page's Han text and warns from 2%

- Decision: `FAIL_SHARE = 0.2`, `WARN_SHARE = 0.02`, `WARN_CHARS = 10` in `check_lib.py`.
- Why: one component with a foreign font list should be reported without failing a page
  that is otherwise right. The lower bound rests on an assumption, not a measurement: a few
  characters in another region's font are expected to be a name or a quotation.
- Rejected: failing on any Han text in another region's font.

## 2026-11-19: An unrecognised web font is assumed to have no Han characters

- Decision: `resolve()` skips a loaded web font whose name matches no region.
- Why: assuming Han coverage would hide the fallback that really draws the text. That an
  unrecognised web font is more often Latin-only than CJK is an assumption; it was not counted.
- Rejected: treating unknown fonts as covering Han. Cost: a self-hosted CJK font with an
  unusual name is missed unless the browser confirmation sees it.

## 2026-11-19: Services ship inside the wheel through `force-include`

- Decision: the wheel copies each `*_lib.py` and `contracts/schema.py` into
  `cjk_sense/_services/`; the command picks that directory when installed.
- Why: keeps one directory per service in the repository and one installable package.
- Rejected: one Python package per service (several distributions for a small tool).

## 2026-11-19: The browser eval threshold is 100%

- Decision: any failing fixture fails the eval.
- Why: every case is deterministic, so a miss is a defect and not noise.
