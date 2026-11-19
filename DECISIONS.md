# Decisions

Newest first. Each entry: what was decided, why, and what was rejected.

## 2026-11-20: The agent Stop hook is optional and does nothing without the tool

- Decision: `.claude/settings.json` runs `agent-sense hook stop` only when `agent-sense` is on
  the PATH, and otherwise succeeds silently.
- Why: the repository is public; contributors without the tool must not see errors.
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
- Why: the defect targeted is cross-language letterforms; telling the Chinese variants apart
  by text alone is unreliable.
- Rejected: `zh-Hans` and `zh-Hant` as separate regions.

## 2026-11-19: `han-font` fails at 20% of the page's Han text and warns from 2%

- Decision: `FAIL_SHARE = 0.2`, `WARN_SHARE = 0.02`, `WARN_CHARS = 10` in `check_lib.py`.
- Why: one component with a foreign font list should be reported without failing a page
  that is otherwise right; a few characters are usually a product name or a quotation.
- Rejected: failing on any Han text in another region's font.

## 2026-11-19: An unrecognised web font is assumed to have no Han characters

- Decision: `resolve()` skips a loaded web font whose name matches no region.
- Why: most web fonts are Latin; assuming Han coverage would hide the fallback that really
  draws the text.
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
