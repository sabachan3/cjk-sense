# Contracts

Shapes passed between services. `schema.py` validates them at every boundary.

## Page snapshot (snapshot service -> command)

```json
{"url": "http://localhost:3000/ja", "final_url": "http://localhost:3000/ja",
 "html_lang": "ja", "text": "visible text, at most 200,000 characters",
 "webfonts": ["Noto Sans JP"],
 "groups": [{"stack": "\"PingFang SC\", sans-serif", "lang": "ja", "chars": 120,
             "sample": "first 40 characters", "where": "h1.hero-title",
             "fonts": [["PingFang SC", 12]]}]}
```

- One group per distinct pair of computed `font-family` and effective `lang` among visible text
  that contains Han characters. `chars` counts the Han characters. At most 40 groups.
- `fonts` are the families the browser used for a probe holding only that group's Han
  characters, with glyph counts. Empty when the machine has no font for them.
- `webfonts` are the `@font-face` families that finished loading.
- A page that failed to load is `{"url": ..., "error": "..."}`.

## Analysed page (command -> check service)

The snapshot without `text` and `webfonts`, plus:

- `detected`: `ja`, `zh`, `ko`, a script name (`latin`, `cyrillic`, ...) or null
- `declared_class`: the same vocabulary for `html_lang`, null when it cannot be checked
- `html_region`: `ja`, `zh`, `ko` or null
- `expect`, `expect_class`: the `--expect` value and its class
- per group: `lang_region`, `measured` (region of `fonts`, or null) and
  `predicted: {platform: [region, font]}` where region is `ja`, `zh`, `ko` or `system`, and
  font is the named font that decided it or null

## Report (check service -> user), version 1

```json
{"version": 1, "platforms": ["mac", "windows", "ios", "android"],
 "summary": {"pages": 1, "fail": 1, "warn": 0, "ok": 0},
 "pages": [{"url": "...", "final_url": "...", "html_lang": "ja", "language": "ja", "verdict": "fail",
            "findings": [{"rule": "han-font", "severity": "fail", "message": "...", "fix": "...",
                          "platforms": ["mac", "ios"], "confirmed_here": true, "share": 1.0, "chars": 120,
                          "where": "h1.hero-title", "sample": "...", "font_family": "...", "lang": "ja",
                          "font": "PingFang SC", "fonts": ["PingFang SC"], "used_here": ["PingFang SC"]}]}]}
```

Rules: `han-font`, `lang-mismatch`, `lang-missing`, `wrong-language`, `page-error`. Every
finding has `rule`, `severity` (`fail` or `warn`), `message` and `fix`; the other fields belong
to `han-font`. A change to these shapes bumps `version`.
