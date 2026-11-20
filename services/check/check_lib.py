"""Turn an analysed page into findings, a report and an exit code.

Input is the analysed page described in contracts/README.md: the snapshot plus the detected
language and, for every group of Han text, the predicted font region per platform.
"""

from __future__ import annotations

import unicodedata

CJK = ("ja", "zh", "ko")
LANGUAGE = {"ja": "Japanese", "zh": "Chinese", "ko": "Korean"}
HAN_WORD = {"ja": "kanji", "zh": "hanzi", "ko": "hanja"}
FONT_EXAMPLES = {"ja": '"Hiragino Sans", "Yu Gothic UI", Meiryo, "Noto Sans JP"',
                 "zh": '"PingFang SC", "Microsoft YaHei", "Noto Sans SC"',
                 "ko": '"Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR"'}
FAIL_SHARE = 0.2    # share of a page's Han text in another region's font that fails the page
WARN_SHARE = 0.02   # below this (or below WARN_CHARS characters) nothing is reported
WARN_CHARS = 10
MIN_HAN = 10        # pages with fewer Han characters are not checked for fonts
MAX_FONT_FINDINGS = 5
ORDER = {"fail": 2, "warn": 1, "ok": 0}
REPORT_VERSION = 1


def _visible(char: str) -> str:
    """A character as it may be shown: itself when printable, a space for any kind of white space,
    nothing for the rest (controls, direction marks and overrides, zero-width characters, tags,
    lone surrogates, private use, unassigned)."""
    if char.isprintable():
        return char
    return " " if char in "\n\t" or unicodedata.category(char) == "Zs" else ""


def clean(text: object, limit: int = 300) -> str:
    """Page-controlled text made safe for a terminal: only printable characters and plain spaces remain."""
    return "".join(_visible(char) for char in str(text))[:limit]


def name(detected: str | None) -> str:
    if detected in LANGUAGE:
        return LANGUAGE[detected]
    return f"{detected.capitalize()} script" if detected else "unknown"


def lang_findings(page: dict) -> list[dict]:
    detected, html_lang = page.get("detected"), (page.get("html_lang") or "").strip()
    findings = []
    expect = page.get("expect")
    if expect and detected and page.get("expect_class") and detected != page["expect_class"]:
        findings.append({"rule": "wrong-language", "severity": "fail",
                         "message": f"expected {expect}, but the page text is {name(detected)}",
                         "fix": "the page is not translated, or this URL does not serve that language"})
    suggestion = f'set <html lang="{detected}">' if detected in CJK else "set <html lang> to the language of the text"
    if not html_lang:
        findings.append({"rule": "lang-missing", "severity": "warn", "message": "<html> has no lang attribute",
                         "fix": suggestion})
    elif detected and page.get("declared_class") and page["declared_class"] != detected:
        findings.append({
            "rule": "lang-mismatch", "severity": "fail",
            "message": f'<html lang="{html_lang}"> but the text is {name(detected)}',
            "fix": suggestion + ". Screen readers choose the voice from it, browsers offer translation from it, "
                                "and it picks the Han letterforms when font-family names no CJK font"})
    return findings


def _foreign_passage(group: dict, region: str, html_region: str | None) -> bool:
    """Text the page itself marks as another CJK language inside a correctly declared document."""
    return html_region == region and group.get("lang_region") in CJK and group["lang_region"] != region


def han_findings(page: dict, platforms: tuple[str, ...]) -> list[dict]:
    region = page.get("detected")
    if region not in CJK:
        return []
    groups = [group for group in page["groups"] if not _foreign_passage(group, region, page.get("html_region"))]
    total = sum(group["chars"] for group in groups)
    if total < MIN_HAN:
        return []

    def wrong(found: str | None) -> bool:
        return found in CJK and found != region

    shares = {platform: 0 for platform in platforms}
    measured_chars, flagged = 0, []
    for group in groups:
        where = [platform for platform in platforms if wrong(group["predicted"][platform][0])]
        seen = wrong(group.get("measured"))
        for platform in where:
            shares[platform] += group["chars"]
        measured_chars += group["chars"] if seen else 0
        if where or seen:
            flagged.append((group, where, seen))
    worst = max([*shares.values(), measured_chars])
    if worst < WARN_CHARS or worst / total < WARN_SHARE:
        return []
    severity = "fail" if worst / total >= FAIL_SHARE else "warn"
    flagged.sort(key=lambda item: -item[0]["chars"])
    kept = [item for index, item in enumerate(flagged) if index == 0 or item[0]["chars"] / total >= WARN_SHARE]
    word, wanted = HAN_WORD[region], LANGUAGE[region]
    findings = []
    for group, where, seen in kept[:MAX_FONT_FINDINGS]:
        if where:
            got = group["predicted"][where[0]][0]
            named = list(dict.fromkeys(group["predicted"][platform][1] for platform in where
                                       if group["predicted"][platform][1]))
            font = named[0] if named else None
            place = "on " + ", ".join(where)
            if named:
                quoted = ", ".join(f'"{item}"' for item in named)
                reason = f'{quoted} {"comes" if len(named) == 1 else "come"} before any {wanted} font in font-family'
                fix = (f'list {wanted} fonts first for this language, for example :lang({region}) '
                       f'{{ font-family: {FONT_EXAMPLES[region]}, sans-serif }}, or remove {quoted}')
            else:
                reason = f'the text is under lang="{group["lang"]}" and font-family names no {wanted} font'
                fix = f'set lang="{region}" on <html> or on this element'
        else:
            got, font, named, place = group["measured"], None, [], "in this browser"
            used = ", ".join(family for family, _ in group.get("fonts", []))
            reason = f"the browser used {used}; the font list alone did not predict it"
            fix = f"check which font in font-family supplies these characters and put a {wanted} font before it"
        findings.append({
            "rule": "han-font", "severity": severity,
            "message": f"{word} drawn in a {LANGUAGE[got]} font {place}: {reason}", "fix": fix,
            "platforms": where, "confirmed_here": seen, "share": round(group["chars"] / total, 4),
            "chars": group["chars"], "where": group.get("where", ""), "sample": group.get("sample", ""),
            "font_family": group["stack"], "lang": group["lang"], "font": font, "fonts": named,
            "used_here": [family for family, _ in group.get("fonts", [])] if seen else []})
    return findings


def check_page(page: dict, platforms: tuple[str, ...]) -> dict:
    """One page of the report: findings and a verdict of 'fail', 'warn' or 'ok'."""
    if page.get("error"):
        findings = [{"rule": "page-error", "severity": "fail", "message": f"could not load: {page['error']}",
                     "fix": "check the URL and that the server is running"}]
    else:
        findings = lang_findings(page) + han_findings(page, platforms)
    verdict = max((finding["severity"] for finding in findings), key=ORDER.get, default="ok")
    return {"url": page["url"], "final_url": page.get("final_url", page["url"]), "html_lang": page.get("html_lang"),
            "language": page.get("detected"), "verdict": verdict, "findings": findings}


def build_report(pages: list[dict], platforms: tuple[str, ...]) -> dict:
    summary = {"pages": len(pages), **{verdict: sum(1 for page in pages if page["verdict"] == verdict)
                                       for verdict in ("fail", "warn", "ok")}}
    return {"version": REPORT_VERSION, "platforms": list(platforms), "summary": summary, "pages": pages}


def exit_code(report: dict, fail_on: str) -> int:
    if fail_on == "never":
        return 0
    limit = ORDER[fail_on]
    return 1 if any(ORDER[page["verdict"]] >= limit for page in report["pages"]) else 0


def format_text(report: dict) -> str:
    lines = []
    for page in report["pages"]:
        language = name(page["language"]) if page["language"] else "language not determined"
        lines.append(f"{page['verdict'].upper():4} {clean(page['url'])}  ({language}, lang={clean(page['html_lang'])!r})")
        for finding in page["findings"]:
            lines.append(f"  [{finding['severity']}] {finding['rule']}: {clean(finding['message'])}")
            if finding["rule"] == "han-font":
                lines.append(f"      {finding['share']:.0%} of the page's Han text, first at <{clean(finding['where'], 80)}> "
                             f"\"{clean(finding['sample'], 40)}\"")
                lines.append(f"      font-family: {clean(finding['font_family'], 200)}")
                if finding["confirmed_here"]:
                    lines.append(f"      confirmed in this browser: {clean(', '.join(finding['used_here']), 120)}")
            if finding["fix"]:
                lines.append(f"      fix: {clean(finding['fix'], 400)}")
    summary = report["summary"]
    lines.append(f"{summary['pages']} page(s): {summary['fail']} fail, {summary['warn']} warn, {summary['ok']} ok")
    return "\n".join(lines)
