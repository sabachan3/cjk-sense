"""Which language a page's visible text is written in, as far as the script can tell.

Japanese, Chinese and Korean are told apart by kana, Han and Hangul. Other languages are only
resolved to their script (Latin, Cyrillic, ...): English and French look the same here, so a
page declared `fr` that is written in English is not detected.
"""

from __future__ import annotations

import re

RANGES = {
    "kana": r"\u3040-\u309f\u30a0-\u30ff",
    "han": r"\u3400-\u4dbf\u4e00-\u9fff",
    "hangul": r"\uac00-\ud7af\u1100-\u11ff\u3130-\u318f",
    "latin": r"A-Za-z\u00c0-\u024f",
    "cyrillic": r"\u0400-\u04ff",
    "arabic": r"\u0600-\u06ff\u0750-\u077f",
    "hebrew": r"\u0590-\u05ff",
    "thai": r"\u0e00-\u0e7f",
    "devanagari": r"\u0900-\u097f",
    "greek": r"\u0370-\u03ff",
}
_PATTERNS = {name: re.compile(f"[{chars}]") for name, chars in RANGES.items()}
MIN_LETTERS = 50        # fewer letters than this and nothing is concluded
MIN_CJK = 20            # kana, Han or Hangul characters needed to call a page CJK
MIN_CJK_SHARE = 0.1     # of all letters; below this the CJK text is a quotation on another page
MIN_KANA_SHARE = 0.2    # kana among kana + Han; a Chinese page quoting Japanese falls below

CJK = ("ja", "zh", "ko")
NAMES = {"ja": "Japanese", "zh": "Chinese", "ko": "Korean", "latin": "Latin script", "cyrillic": "Cyrillic script",
         "arabic": "Arabic script", "hebrew": "Hebrew script", "thai": "Thai", "devanagari": "Devanagari script",
         "greek": "Greek"}

# Languages whose script is unambiguous. Languages written in more than one script (sr, kk, uz,
# az, mn) and scripts not counted here are left out, which turns the check off for them.
_LANGUAGE_CLASS = {
    "ja": "ja", "zh": "zh", "ko": "ko",
    **dict.fromkeys(("ru", "uk", "bg", "mk", "be"), "cyrillic"),
    **dict.fromkeys(("ar", "fa", "ur", "ps"), "arabic"),
    **dict.fromkeys(("he", "iw", "yi"), "hebrew"),
    "th": "thai", "el": "greek", **dict.fromkeys(("hi", "mr", "ne"), "devanagari"),
    **dict.fromkeys(("en", "fr", "de", "es", "it", "pt", "nl", "sv", "da", "nb", "no", "nn", "fi", "pl", "cs", "sk", "hu",
                     "ro", "tr", "id", "ms", "vi", "tl", "fil", "ca", "hr", "sl", "lt", "lv", "et", "is", "ga", "cy",
                     "eu", "gl", "af", "sw", "sq", "mt", "lb"), "latin"),
}


def count_scripts(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in _PATTERNS.items()}


def detect(counts: dict[str, int]) -> str | None:
    """'ja', 'zh', 'ko', a script name, or None when the text is too short or too mixed to say."""
    letters = sum(counts.values())
    if letters < MIN_LETTERS:
        return None
    kana, han, hangul = counts.get("kana", 0), counts.get("han", 0), counts.get("hangul", 0)
    cjk = kana + han + hangul
    if cjk >= MIN_CJK:
        if cjk / letters < MIN_CJK_SHARE:
            return None  # a mixed page: too much CJK to call it Latin, too little to call it CJK
        if hangul > kana + han:
            return "ko"
        if kana >= MIN_CJK and kana / (kana + han) >= MIN_KANA_SHARE:
            return "ja"
        if han > kana + hangul:
            return "zh"
        return "ko" if hangul >= kana else "ja"
    others = {name: count for name, count in counts.items() if name not in ("kana", "han", "hangul")}
    name, count = max(others.items(), key=lambda item: item[1])
    return name if count / letters >= 0.5 else None


def primary(lang: str | None) -> str:
    return (lang or "").strip().lower().replace("_", "-").split("-")[0]


def language_class(lang: str | None) -> str | None:
    """The class `detect` would return for text in this language, or None when it cannot be checked."""
    return _LANGUAGE_CLASS.get(primary(lang))


def cjk_region(lang: str | None) -> str | None:
    """'ja', 'zh' or 'ko' when the lang value picks a Han letterform region, else None."""
    code = primary(lang)
    return code if code in CJK else None


def describe(detected: str | None) -> str:
    return NAMES.get(detected or "", "unknown")
