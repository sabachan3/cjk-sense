# Changelog

User-facing changes per version. Measured results are in
[docs/results.md](https://github.com/sabachan3/cjk-sense/blob/main/docs/results.md).

## 0.1.0 (not released yet)

First version.

- `cjk-sense check URL [URL ...]` opens each page in Chromium (the browser Playwright installs,
  or an installed Chrome or Edge through `--channel`) and reports five rules:
  - `han-font`: Han characters drawn in a Chinese, Japanese or Korean font that does not match
    the language of the text, predicted for macOS, Windows, iOS and Android from `font-family`
    and `lang`. Fails at 20% of the page's Han text, warns from 2%. Where the browser running
    the check has the fonts, the fonts it really used are shown as confirmation.
  - `lang-mismatch`: `<html lang>` names a language written in a different script than the text.
  - `lang-missing`: `<html>` has no `lang`.
  - `wrong-language`: with `--expect`, the page is not in that language.
  - `page-error`: the page did not load.
- Options: `--urls-file` (one URL per line; `#` comments and a byte order mark are accepted),
  `--expect`, `--platforms`, `--fail-on fail|warn|never`, `--format text|json`, `--out FILE`
  (JSON report, version 1), `--channel`, `--locale`, `--wait`, `--timeout`, `--workers`,
  `--version`.
- Exit codes: 0 no failing page, 1 a page fails, 2 the tool could not run (no browser, a file that
  cannot be read or written, an option out of range). A file that cannot be written is reported
  before the browser starts.
- Text taken from a page never reaches the terminal raw: control characters, direction marks,
  zero-width characters and lone surrogates are dropped from text output and written as
  `\uXXXX` escapes in JSON.
- Output redirected to a file or a pipe on Windows works under a legacy code page.
- Python 3.10 or newer. No model and no network service; the only dependency is Playwright.

Known limits: iOS and Android results are predictions that were never run on a device, Simplified
and Traditional Chinese count as one region, and languages are told apart by script only. The
full list is in the README.
