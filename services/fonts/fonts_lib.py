"""Which regional font draws Han characters, predicted per platform from CSS alone.

Han characters share code points across Japanese, Chinese and Korean while the regions draw
many of them differently. The browser walks the `font-family` list and takes the first font
that has the character; only when the list runs out (or reaches a generic family under a CJK
`lang`) does `lang` decide. So a named Chinese font ahead of any Japanese font gives a Japanese
page Chinese letterforms even with lang="ja".

The rules below were checked against real browsers with Japanese as the display language:
Chromium on macOS and Edge on Windows 11 (services/snapshot/eval_fixtures.py). iOS and Android
follow the same rules with their own font lists and have not been checked on a device.
"""

from __future__ import annotations

from collections import Counter

PLATFORMS = ("mac", "windows", "ios", "android")
_APPLE = {"mac", "ios"}

# Installed fonts that cover Han: lower-case family name -> (region, platforms that ship it).
INSTALLED = {
    "pingfang sc": ("zh", _APPLE), "pingfang tc": ("zh", _APPLE), "pingfang hk": ("zh", _APPLE),
    "hiragino sans gb": ("zh", {"mac"}), "stheiti": ("zh", {"mac"}), "heiti sc": ("zh", _APPLE),
    "heiti tc": ("zh", _APPLE), "songti sc": ("zh", {"mac"}), "songti tc": ("zh", {"mac"}),
    "stsong": ("zh", {"mac"}), "kaiti sc": ("zh", {"mac"}),
    "hiragino sans": ("ja", _APPLE), "hiragino kaku gothic pron": ("ja", _APPLE),
    "hiragino kaku gothic pro": ("ja", {"mac"}), "hiragino mincho pron": ("ja", _APPLE),
    "hiragino maru gothic pron": ("ja", {"mac"}), "yugothic": ("ja", {"mac"}),
    "yu gothic": ("ja", {"mac", "windows"}), "yu mincho": ("ja", {"mac", "windows"}), "osaka": ("ja", {"mac"}),
    "apple sd gothic neo": ("ko", _APPLE),
    "microsoft yahei": ("zh", {"windows"}), "microsoft yahei ui": ("zh", {"windows"}),
    "simsun": ("zh", {"windows"}), "nsimsun": ("zh", {"windows"}), "simhei": ("zh", {"windows"}),
    "microsoft jhenghei": ("zh", {"windows"}), "microsoft jhenghei ui": ("zh", {"windows"}),
    "mingliu": ("zh", {"windows"}), "pmingliu": ("zh", {"windows"}),
    "yu gothic ui": ("ja", {"windows"}), "meiryo": ("ja", {"windows"}), "meiryo ui": ("ja", {"windows"}),
    "ms gothic": ("ja", {"windows"}), "ms pgothic": ("ja", {"windows"}), "ms ui gothic": ("ja", {"windows"}),
    "ms mincho": ("ja", {"windows"}), "ms pmincho": ("ja", {"windows"}),
    "biz udgothic": ("ja", {"windows"}), "biz udpgothic": ("ja", {"windows"}),
    "malgun gothic": ("ko", {"windows"}),
}
# On Windows the system UI font follows the display language (Yu Gothic UI on a Japanese system)
# and covers Han itself. On Apple systems and Android it is a Latin font, so the browser keeps
# walking the list: on macOS "-apple-system, 'PingFang SC'" draws kanji in PingFang.
SYSTEM_UI = {"system-ui": {"windows"}, "ui-sans-serif": {"windows"}}
GENERIC = {"sans-serif", "serif", "monospace", "cursive", "fantasy", "ui-serif", "ui-monospace", "ui-rounded"}

# Substrings that identify a font's region, including the localised names macOS reports.
# Pretendard is absent on purpose: it has Hangul and Latin only, so Han passes through it.
_REGION_MARKS = (
    ("zh", ("hiragino sans gb", "冬青黑", "pingfang", "蘋方", "苹方", "heiti", "黑体", "黑體", "songti", "宋体", "宋體",
            "stsong", "yahei", "simsun", "simhei", "jhenghei", "mingliu", "kaiti", "fangsong", "noto sans sc", "noto sans tc",
            "noto sans hk", "noto serif sc", "noto serif tc", "noto sans cjk sc", "noto sans cjk tc",
            "source han sans sc", "source han sans cn", "source han sans tc", "source han serif sc", "思源",
            "alibaba puhuiti", "harmonyos sans sc", "misans", "lxgw")),
    ("ja", ("hiragino", "ヒラギノ", "yu gothic", "yugothic", "yu mincho", "游", "meiryo", "メイリオ", "noto sans jp",
            "noto serif jp", "noto sans cjk jp", "noto sans japanese", "source han sans jp", "source han serif jp",
            "源ノ角", "osaka", "m plus", "mplus", "zen kaku", "zen maru", "zen old", "biz ud", "kosugi", "sawarabi",
            "klee", "筑紫", "tsukushi", "ms gothic", "ms pgothic", "ms mincho", "ipa", "line seed jp", "murecho",
            "shippori", "kiwi maru", "dotgothic", "pretendard jp", "spoqa han sans")),
    ("ko", ("apple sd gothic", "malgun", "noto sans kr", "noto serif kr", "noto sans cjk kr", "nanum")),
)
EXAMPLES = {"ja": '"Hiragino Sans", "Yu Gothic UI", Meiryo, "Noto Sans JP"',
            "zh": '"PingFang SC", "Microsoft YaHei", "Noto Sans SC"',
            "ko": '"Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR"'}


def classify(name: str) -> str | None:
    """Region of a font family name: 'ja', 'zh', 'ko', or None when unknown."""
    lowered = name.lower().strip()
    if lowered in INSTALLED:
        return INSTALLED[lowered][0]
    for region, marks in _REGION_MARKS:
        if any(mark in lowered for mark in marks):
            return region
    return None


def parse_stack(font_family: str) -> list[str]:
    names = (part.strip().strip("'\"").strip() for part in font_family.split(","))
    return [name for name in names if name]


def resolve(font_family: str, lang_region: str | None, platform: str,
            webfonts: frozenset[str] | set[str] = frozenset()) -> tuple[str, str | None]:
    """Predict the region of the font that draws Han text.

    `lang_region` is 'ja', 'zh', 'ko' or None (the effective lang of the text). Returns
    (region, font): region is 'ja', 'zh', 'ko', or 'system' when the page leaves the choice to
    the reader's display language; font is the named font that decided it, or None when `lang`
    or the system did.
    """
    loaded = {name.lower() for name in webfonts}
    for name in parse_stack(font_family):
        lowered = name.lower()
        if lowered in loaded:
            region = classify(lowered)
            if region:
                return region, name
            continue  # an unrecognised web font is assumed to have no Han
        if lowered in INSTALLED:
            region, platforms = INSTALLED[lowered]
            if platform in platforms:
                return region, name
            continue
        if platform in SYSTEM_UI.get(lowered, ()):
            return "system", None
        if lowered in GENERIC and lang_region:
            break  # under a CJK lang the generic family maps to that region's font
    return (lang_region, None) if lang_region else ("system", None)


def measured_region(fonts: list) -> str | None:
    """Region that drew most glyphs of a probe, from (family, glyph count) pairs; None if unknown."""
    tally = Counter()
    for family, glyphs in fonts:
        tally[classify(family) or "unknown"] += glyphs
    if not tally:
        return None
    region = tally.most_common(1)[0][0]
    return None if region == "unknown" else region
