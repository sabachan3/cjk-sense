"""The field numbers quoted in the documents are printed by evals/field_summary.py; its counting is pinned here."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
import field_summary  # noqa: E402


def font(severity="fail", platforms=("mac", "ios"), confirmed=True, fonts=("PingFang SC",)):
    return {"rule": "han-font", "severity": severity, "platforms": list(platforms), "confirmed_here": confirmed,
            "fonts": list(fonts), "font": fonts[0] if fonts else None}


def page(language="ja", html_lang="ja", findings=()):
    return {"language": language, "html_lang": html_lang, "findings": list(findings)}


def rule(name, severity="fail"):
    return {"rule": name, "severity": severity}


REPORT = {"summary": {"pages": 9}, "pages": [
    page(findings=[font()]),                                                   # named font, predicted and confirmed
    page(findings=[font(platforms=("mac", "ios", "windows"), confirmed=False, fonts=())]),   # under another lang, not confirmed
    page(findings=[font(platforms=(), fonts=())]),                             # found only by the browser
    page(findings=[font(severity="warn")]),                                    # warn only
    page(findings=[font(), font(severity="warn")]),                            # fail and warn: counts as a fail, not as warn only
    page(html_lang="en-US", findings=[rule("lang-mismatch")]),
    page(html_lang="ko", findings=[rule("lang-mismatch"), font(platforms=("android",), fonts=())]),
    page(html_lang="", findings=[rule("lang-missing", "warn")]),
    page(language=None, html_lang="", findings=[rule("lang-missing", "warn"), font()]),   # not a Japanese page
]}


def test_counts_among_the_pages_of_one_language():
    among = field_summary.summarise(REPORT)["among_ja_pages"]
    assert among["pages"] == 8
    assert among["han_font_fail"] == 5
    assert among["han_font_fail_by_platform"] == {"mac": 3, "ios": 3, "windows": 1, "android": 1}
    assert among["han_font_fail_by_kind"] == {"predicted_and_confirmed": 3, "predicted_not_confirmed": 1, "browser_only": 1}
    assert among["han_font_fail_by_cause"] == {"font_named_before_own_region": 2, "text_under_other_lang": 2, "browser_only": 1}
    assert among["han_font_warn_only"] == 1
    assert among["lang_mismatch"] == 2 and among["lang_mismatch_by_declared_lang"] == {"en": 1, "ko": 1}
    assert among["lang_missing"] == 1


def test_whole_report_counts_include_pages_of_any_language():
    summary = field_summary.summarise(REPORT)
    assert summary["pages"] == 9 and summary["han_font_fail_pages"] == 6
    assert summary["pages_with_rule"]["lang-missing"] == 2
    assert summary["language"] == {"ja": 8, "undetermined": 1}
