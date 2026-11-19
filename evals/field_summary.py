"""Summarise a report over many pages (the field run recorded in docs/results.md).

    python evals/field_summary.py runs/field.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter


def summarise(report: dict) -> dict:
    pages = report["pages"]
    with_rule, platforms, confirmed = Counter(), Counter(), 0
    font_fail = 0
    for page in pages:
        for rule in {finding["rule"] for finding in page["findings"]}:
            with_rule[rule] += 1
        fonts = [finding for finding in page["findings"] if finding["rule"] == "han-font" and finding["severity"] == "fail"]
        if fonts:
            font_fail += 1
            confirmed += any(finding["confirmed_here"] for finding in fonts)
            for platform in {platform for finding in fonts for platform in finding["platforms"]}:
                platforms[platform] += 1
    return {"pages": len(pages), "verdicts": report["summary"],
            "language": dict(Counter(page["language"] or "undetermined" for page in pages)),
            "pages_with_rule": dict(with_rule), "han_font_fail_pages": font_fail,
            "han_font_fail_by_platform": dict(platforms), "han_font_fail_confirmed_in_browser": confirmed}


if __name__ == "__main__":
    print(json.dumps(summarise(json.load(open(sys.argv[1], encoding="utf-8"))), ensure_ascii=False, indent=1))
