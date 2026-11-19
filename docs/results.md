# Results

Date: 2026-11-19. Version 0.1.0.

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

`python evals/field_summary.py runs/field.json` prints these counts from a report.

## What has not been measured

- No person has judged the findings. The font rule is checked against what the browser did,
  not against whether a reader notices.
- False negatives on real sites are unknown: pages the tool calls fine were not inspected.
- The sample is open-source projects with a homepage. One page per site, the front page.
- Chinese and Korean pages appear only in the browser eval, not in the field run.
