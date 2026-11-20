# Decisions

Newest first. Each entry: what was decided, why, and what was rejected.

Entries dated before 2026-11-20 were written down on 2026-11-20. Where a reason is not backed
by a measurement in `docs/results.md`, it is the author's reasoning, not a measured fact.

## 2026-11-20: Text output removes invisible characters, JSON escapes them

- Decision: decided by Unicode category. `check_lib.clean()` keeps only printable characters
  in text output and error messages. `cli.json_text()` writes every character of category Cc,
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
