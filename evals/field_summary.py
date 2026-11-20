"""Summarise a report over many pages (the field run recorded in docs/results.md).

    python evals/field_summary.py runs/field.json

Every field count quoted in README.md and docs/results.md is a value printed here; the
percentages there are those counts divided by the number of Japanese pages.
"""

from __future__ import annotations

import json
import sys
from collections import Counter


def _primary(lang: str | None) -> str:
    return (lang or "").strip().lower().replace("_", "-").split("-")[0] or "none"


def _font_failure(page: dict) -> dict | None:
    """How a page fails the font rule: where it was predicted, whether the browser confirmed it, and why."""
    fonts = [finding for finding in page["findings"] if finding["rule"] == "han-font" and finding["severity"] == "fail"]
    if not fonts:
        return None
    platforms = {platform for finding in fonts for platform in finding["platforms"]}
    confirmed = any(finding["confirmed_here"] for finding in fonts)
    if not platforms:
        kind, cause = "browser_only", "browser_only"
    else:
        kind = "predicted_and_confirmed" if confirmed else "predicted_not_confirmed"
        named = any(finding.get("fonts") or finding.get("font") for finding in fonts if finding["platforms"])
        cause = "font_named_before_own_region" if named else "text_under_other_lang"
    return {"platforms": platforms, "confirmed": confirmed, "kind": kind, "cause": cause}


def summarise(report: dict, language: str = "ja") -> dict:
    pages = report["pages"]
    with_rule, platforms, confirmed = Counter(), Counter(), 0
    font_fail = 0
    for page in pages:
        for rule in {finding["rule"] for finding in page["findings"]}:
            with_rule[rule] += 1
        failure = _font_failure(page)
        if failure:
            font_fail += 1
            confirmed += failure["confirmed"]
            platforms.update(failure["platforms"])
    own = [page for page in pages if page["language"] == language]
    failures = [failure for failure in map(_font_failure, own) if failure]
    own_platforms = Counter(platform for failure in failures for platform in failure["platforms"])

    def has(page: dict, rule: str, severity: str | None = None) -> bool:
        return any(finding["rule"] == rule and severity in (None, finding["severity"]) for finding in page["findings"])

    among = {
        "pages": len(own),
        "han_font_fail": len(failures),
        "han_font_fail_by_platform": dict(own_platforms),
        "han_font_fail_by_kind": dict(Counter(failure["kind"] for failure in failures)),
        "han_font_fail_by_cause": dict(Counter(failure["cause"] for failure in failures)),
        "han_font_warn_only": sum(1 for page in own if has(page, "han-font", "warn") and not has(page, "han-font", "fail")),
        "lang_mismatch": sum(1 for page in own if has(page, "lang-mismatch")),
        "lang_mismatch_by_declared_lang": dict(Counter(_primary(page["html_lang"]) for page in own if has(page, "lang-mismatch"))),
        "lang_missing": sum(1 for page in own if has(page, "lang-missing")),
    }
    return {"pages": len(pages), "verdicts": report["summary"],
            "language": dict(Counter(page["language"] or "undetermined" for page in pages)),
            "pages_with_rule": dict(with_rule), "han_font_fail_pages": font_fail,
            "han_font_fail_by_platform": dict(platforms), "han_font_fail_confirmed_in_browser": confirmed,
            f"among_{language}_pages": among}


if __name__ == "__main__":
    print(json.dumps(summarise(json.load(open(sys.argv[1], encoding="utf-8"))), ensure_ascii=False, indent=1))
