# cjk-sense

Catches two defects on localised web pages that existing linters let through:

- **Kanji drawn with another region's font.** Japanese, Chinese and Korean share code points
  for Han characters, but each region draws many of them differently (直, 骨, 海, 画). A
  `font-family` list copied from a Chinese project, or a wrong `lang`, gives a Japanese page
  Chinese letterforms. The same happens in every direction between the three.
- **A `lang` attribute that does not match the text.** A Japanese page left as
  `<html lang="en">` passes accessibility checkers, which only test that `lang` exists and is a
  valid code.

No model and no service: it opens the page in Chromium and applies fixed rules.

```
$ cjk-sense check http://localhost:3000/ja --expect ja
FAIL http://localhost:3000/ja  (Japanese, lang='ja')
  [fail] han-font: kanji drawn in a Chinese font on mac, windows, ios: "PingFang SC", "Microsoft YaHei" come before any Japanese font in font-family
      100% of the page's Han text, first at <h1.hero-title> "設定を保存しました"
      font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif
      confirmed in this browser: 蘋方-簡
      fix: list Japanese fonts first for this language, for example :lang(ja) { font-family: "Hiragino Sans", "Yu Gothic UI", Meiryo, "Noto Sans JP", sans-serif }, or remove "PingFang SC", "Microsoft YaHei"
1 page(s): 1 fail, 0 warn, 0 ok
```

(`蘋方-簡` is the name a Japanese-language macOS reports for PingFang SC.)

## Install

```bash
uvx --from git+https://github.com/sabachan3/cjk-sense cjk-sense check https://example.com/ja
```

or `pip install git+https://github.com/sabachan3/cjk-sense`. It needs a Chromium to drive, one of:

```bash
playwright install chromium-headless-shell   # bundled browser
cjk-sense check URL --channel chrome         # or an installed Chrome / Edge (msedge)
```

## Rules

| rule | severity | meaning |
|---|---|---|
| `han-font` | fail at 20% of the page's Han text, warn from 2% | Han characters go to a font of another region on macOS, Windows, iOS or Android |
| `lang-mismatch` | fail | `<html lang>` names a language written in a different script than the text |
| `lang-missing` | warn | `<html>` has no `lang` |
| `wrong-language` | fail | with `--expect`: the page is not in that language (untranslated, or the wrong route) |
| `page-error` | fail | the page did not load |

Exit code 1 when a page fails (`--fail-on warn` or `never` to change that), 2 when the tool
could not run.

## How the font rule works

The browser walks `font-family` and takes the first font that has the character. `lang` only
decides when the list runs out, or when it reaches a generic family such as `sans-serif` under
a CJK `lang`. Consequences that surprise people:

- `lang="ja"` does not protect a page. In `-apple-system, "PingFang SC", sans-serif` the system
  font has no kanji, so macOS and iOS use PingFang. On Windows the same list reaches
  `"Microsoft YaHei"`.
- A font only breaks the platforms that ship it. PingFang affects Apple systems, YaHei affects
  Windows. Web fonts that loaded affect all of them.
- With `lang="en"` and no CJK font named, the reader's display language decides. Japanese
  readers see Japanese letterforms, others may not. cjk-sense reports the wrong `lang`, not a
  font defect.

cjk-sense reads the computed `font-family` and effective `lang` of every piece of Han text and
predicts the result per platform from a table of the CJK fonts each platform ships. The
prediction does not depend on the machine running the check, so it works on a Linux CI runner
with no CJK fonts. When the browser running the check does have the fonts, the fonts it really
used are shown as "confirmed in this browser", and a mismatch nobody predicted is reported too.

Text marked as another language inside a correctly declared page (`<blockquote lang="zh">` on a
Japanese page) is not a defect and is left out.

## Options

```
cjk-sense check URL [URL ...] [--urls-file FILE]
  --expect LANG        language the pages should be in (ja, zh, ko, en, ...); also sets the browser language
  --platforms LIST     mac,windows,ios,android (default: all)
  --fail-on LEVEL      fail | warn | never
  --format text|json   --out FILE writes the JSON report as well
  --channel NAME       chrome or msedge instead of the bundled browser
  --locale TAG         browser language sent to the site, for sites that choose by Accept-Language
  --wait MS            extra wait for client-side rendering   --timeout MS   --workers N
```

CI example: [docs/github-actions.yml](docs/github-actions.yml).

## How well it works

See [docs/results.md](docs/results.md). In short:

- 22 purpose-built pages give the expected findings in Chromium on macOS and in Edge on
  Windows 11, and every font prediction matched the font the browser used.
- On 265 Japanese pages of open-source projects, 6.8% failed the font rule (6.4% on Apple
  systems, 3.0% on Windows) and 11.3% declared a `lang` of another script.

## Limits

- Languages are told apart by script. Japanese, Chinese and Korean are distinguished; English
  and French are not, so `lang="fr"` on an English page is not detected.
- Simplified and Traditional Chinese are treated as one region.
- iOS and Android results are predictions from their font lists and have not been checked on a
  device. Linux desktops are not covered.
- The font table lists the fonts that ship with each system and the common web fonts. A
  self-hosted font with an unusual name is treated as having no Han characters; the
  "confirmed in this browser" check catches that case on macOS and Windows only.
- One state of the page is checked: what is visible after load. Text behind menus, tabs and
  dialogs is not.
- The rule does not judge whether a given character looks different between regions. Many do
  not; the page is flagged because the font is wrong for the language.

## Development

```bash
scripts/setup.sh                   # once per clone: pre-commit hook, browser, then the gate
scripts/test.sh                    # gate tests, under 2 s, no browser, also the pre-commit hook
scripts/eval.sh                    # browser eval on macOS
scripts/eval.sh --channel msedge   # browser eval on Windows
scripts/e2e.sh                     # build the wheel, install it, run it against pages served over HTTP
```

| path | what it is |
|---|---|
| `services/detect/` | language of the visible text, from script counts |
| `services/fonts/` | font tables and the per-platform prediction |
| `services/snapshot/` | the browser: computed `font-family`, effective `lang`, fonts really used |
| `services/check/` | rules, report, exit code, text output |
| `contracts/` | the shapes passed between them, and their validator |
| `cjk_sense/` | the command; the only place that wires services together |
| `evals/` | browser eval, end-to-end check, field-run summary |

Working on this repository with a coding agent: start from [CLAUDE.md](CLAUDE.md), the current
state is in [PROGRESS.md](PROGRESS.md). Related project:
[l10n-sense](https://github.com/sabachan3/l10n-sense) checks whether translated strings mean the
right thing.

MIT licence.
