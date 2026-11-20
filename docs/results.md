# Results

Dates: 2026-11-19, with reruns on 2026-11-20 marked as such. Version 0.1.0.

## Browser eval: 22 pages with a known answer

`scripts/eval.sh` builds 22 small pages (Japanese, Chinese, Korean and English text under
different `lang` values and font lists) and checks three things: the report holds exactly the
expected rules, the font the browser used matches the prediction for that operating system,
and the command line gives the same result on `file://` copies.

| browser | fixtures passing | font predictions compared with the browser |
|---|---:|---:|
| Chromium on macOS (Japanese display language) | 22/22 | 21, all matching |
| Edge on Windows 11 (Japanese display language) | 22/22 | 21, all matching |

The pass threshold is 100%: every case is deterministic. iOS and Android have not been run.

A compared prediction is one where the browser reported the font it used. Predictions of
`system` (the page leaves the choice to the reader's display language) are counted among the
21 but accept any font, so "all matching" is a statement about the predictions that name a region.

Both rows were first measured on 2026-11-19 and rerun on 2026-11-20 after the output changes
(JSON escaping, text cleaning, exit codes), with the same result on both. The Windows rerun
(Windows 11 build 26200, installed Edge, Python 3.10, display language Japanese, code page 932)
is kept in [records/windows-eval-2026-11-20.txt](records/windows-eval-2026-11-20.txt). The
2026-11-19 Windows run left no output file.

### Windows, real machine (2026-11-20)

- Gate tests: 87 passed on Windows with Python 3.10. Before this date one test could not run
  there (it used a shebang script); it now uses a batch file on Windows.
- Redirected and piped output. One local page whose first characters are a kanji outside the
  code page (U+20BB7) and a joined emoji, checked with `> file` and through a pipe, in both
  formats. The previous version wrote nothing and ended in `UnicodeEncodeError: 'cp932' codec
  can't encode character` with exit 1. This version writes the report and exits 1 for the
  `han-font` finding; the JSON, read back as code page 932, parses and holds the same characters
  as escapes. One page, one machine.

## End-to-end check of the installed package (2026-11-20)

`scripts/e2e.sh` builds the wheel, installs it into a throwaway environment and runs the
installed command against three pages served over HTTP (macOS, Chromium): 4/4 checks pass
(a clean page: ok, exit 0; a Chinese font ahead of Japanese fonts: `han-font`, exit 1; a wrong
`lang`: `lang-mismatch`, exit 1; all three in one run: 2 fail, 1 ok, exit 1). Negative control:
with one service removed from the wheel's file list, all four checks fail and the script exits 1
(exit status recorded on 2026-11-20 for each of the five listed files in turn).

## Hostile page (2026-11-20)

One page served locally whose script puts a lone surrogate, direction marks and overrides,
zero-width characters, ESC, DEL, a C1 control and a line separator into an element id, a class
name, the text and the title (macOS, Chromium). In both formats the command exits 1 with a
normal report (`han-font`, the page names Chinese fonts first). Standard output, standard
error and the `--out` file hold none of those characters raw; the JSON report still holds all
of them as escapes. Before this date the same page ended in a traceback. One page, one browser,
run by hand: no script in this repository reproduces it. The gate tests cover the same characters
through a fake page.

## Field run: Japanese pages of open-source projects

Sites: GitHub repositories that ship a Japanese locale file, reduced to 600 with a homepage of
their own; 288 of them showed a Japanese page to a first scan. `cjk-sense check --expect ja`
was then run on those 288 URLs (macOS, Chromium). On the day of the run 265 were Japanese, 21
were too mixed to call (mostly Latin text with some Japanese), 2 were not Japanese.

| among the 265 Japanese pages | pages | share |
|---|---:|---:|
| `han-font` fail | 18 | 6.8% |
| ... on macOS / iOS | 17 | 6.4% |
| ... on Windows | 8 | 3.0% |
| ... on Android | 8 | 3.0% |
| `han-font` warn (2% to 20% of the Han text) | 1 | 0.4% |
| `lang-mismatch` (24 say `en`, 4 `ko`, 1 `zh`, 1 `id`) | 30 | 11.3% |
| `lang-missing` | 17 | 6.4% |

Of the 18 font failures, 16 were predicted for macOS and confirmed there by the fonts Chromium
used. One was found only by the browser (a font list that did not predict it). One was
predicted but not confirmed: a Japanese page under `lang="ko"`. Korean fonts lack many
Japanese-only kanji forms, so that page draws part of its kanji in a Korean font and the rest
in a Japanese one; the probe happened to hold only characters the Korean font lacks.

Cause of the 18 font failures: in 13 a Chinese or Korean font is named in `font-family` ahead
of any Japanese font (typically `"PingFang SC"` and `"Microsoft YaHei"` after `-apple-system`),
in 4 the text sits under a Chinese or Korean `lang`, and 1 is the browser-only case above.

`python evals/field_summary.py runs/field.json` prints every count in this section from the
report; the percentages are those counts over the 265 Japanese pages. The list of 600 sites the
288 were drawn from is not stored in this repository (the block `among_ja_pages`: counts per platform, per kind of confirmation, per cause,
and the declared languages of the mismatches).

## What has not been measured

- No person has judged the findings. The font rule is checked against what the browser did,
  not against whether a reader notices.
- False negatives on real sites are unknown: pages the tool calls fine were not inspected.
- The sample is open-source projects with a homepage. One page per site, the front page.
- Chinese and Korean pages appear only in the browser eval, not in the field run.
