"""Browser eval: pages with a known answer, checked end to end in a real browser.

    scripts/eval.sh                      # macOS, bundled Chromium
    scripts/eval.sh --channel msedge     # Windows, installed Edge

Three things must hold for every fixture:
  1. the report contains exactly the expected rules,
  2. where the browser has CJK fonts, the region of the font it used equals the region
     predicted for this operating system (display language assumed to match the page),
  3. the command line run on a file:// copy gives the same verdict.
Exit 1 when any fixture fails. The pass threshold is 100%: every case is deterministic.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cjk_sense import cli  # noqa: E402  (puts the service libraries on the path)

import fonts_lib  # noqa: E402
import snapshot_lib  # noqa: E402

JA = "これは日本語のページです。直接、海の画像を骨組みから作り直します。設定を保存しました。" * 3
ZH = "这是一个中文页面。直接从骨架重新制作海的图像。设置已保存，请稍后再试。" * 3
KO = "이것은 한국어 페이지입니다. 설정이 저장되었습니다. 나중에 다시 시도하세요." * 3
EN = "This is an English page. Your settings have been saved. Please try again later. " * 3
ANTD = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
CJK_BOTH = "'PingFang SC', 'Microsoft YaHei', sans-serif"
JA_BOTH = "'Hiragino Sans', Meiryo, sans-serif"

# (name, html lang, body font-family, body html, expected rules)
FIXTURES = (
    ("ja, generic font", "ja", "sans-serif", f"<p>{JA}</p>", set()),
    ("ja, Japanese fonts listed", "ja", "'Hiragino Sans', 'Yu Gothic UI', Meiryo, sans-serif", f"<p>{JA}</p>", set()),
    ("ja, system-ui then Japanese fonts", "ja", "system-ui, -apple-system, 'Hiragino Sans', Meiryo, 'PingFang SC', sans-serif",
     f"<p>{JA}</p>", set()),
    ("ja, lang left as en", "en", "sans-serif", f"<p>{JA}</p>", {"lang-mismatch"}),
    ("ja, no lang", "", "Arial, sans-serif", f"<p>{JA}</p>", {"lang-missing"}),
    ("ja, lang says zh", "zh-CN", "sans-serif", f"<p>{JA}</p>", {"lang-mismatch", "han-font"}),
    ("ja, lang says ko", "ko", "sans-serif", f"<p>{JA}</p>", {"lang-mismatch", "han-font"}),
    ("ja, old Ant Design list", "ja", ANTD, f"<p>{JA}</p>", {"han-font"}),
    ("ja, Chinese fonts first", "ja", CJK_BOTH, f"<p>{JA}</p>", {"han-font"}),
    ("ja, Chinese font after Latin fonts", "ja", "Inter, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif",
     f"<p>{JA}</p>", {"han-font"}),
    ("ja, generic before Chinese fonts", "ja", "sans-serif, 'PingFang SC', 'Microsoft YaHei'", f"<p>{JA}</p>", set()),
    ("ja, one component with Chinese fonts", "ja", "sans-serif",
     f"<p>{JA}</p><div style=\"font-family:{CJK_BOTH}\">{JA}</div>", {"han-font"}),
    ("ja, quoted Chinese marked with lang", "ja", "sans-serif", f"<p>{JA}{JA}</p><blockquote lang=\"zh\">{ZH}</blockquote>", set()),
    ("ja, hidden Chinese-font text is ignored", "ja", "sans-serif",
     f"<p>{JA}</p><div style=\"display:none;font-family:{CJK_BOTH}\">{JA}</div>", set()),
    ("zh, generic font", "zh-CN", "sans-serif", f"<p>{ZH}</p>", set()),
    ("zh, Chinese fonts listed", "zh-CN", CJK_BOTH, f"<p>{ZH}</p>", set()),
    ("zh, Japanese fonts first", "zh-CN", JA_BOTH, f"<p>{ZH}</p>", {"han-font"}),
    ("zh, lang left as ja", "ja", "sans-serif", f"<p>{ZH}</p>", {"lang-mismatch", "han-font"}),
    ("ko, generic font", "ko", "sans-serif", f"<p>{KO}</p>", set()),
    ("en, generic font", "en", "sans-serif", f"<p>{EN}</p>", set()),
    ("en, lang says ja", "ja", "sans-serif", f"<p>{EN}</p>", {"lang-mismatch"}),
    ("en with a Japanese product name", "en", CJK_BOTH, f"<p>{EN}{EN}</p><p>東京</p>", set()),
)
PLATFORM = {"darwin": "mac", "win32": "windows"}
LOCALE = {"ja": "ja-JP", "zh": "zh-CN", "ko": "ko-KR"}


def html(lang: str, stack: str, body: str) -> str:
    attribute = f' lang="{lang}"' if lang else ""
    return f'<!doctype html><html{attribute}><meta charset="utf-8"><body style="font-family:{stack}">{body}</body></html>'


async def run_fixtures(channel: str | None, platform: str | None, work: Path) -> tuple[int, int, list]:
    from playwright.async_api import async_playwright

    failures, compared, files = 0, 0, []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel=channel)
        page = await (await browser.new_context()).new_page()
        for index, (name, lang, stack, body, expected) in enumerate(FIXTURES):
            document = html(lang, stack, body)
            path = work / f"{index:02d}.html"
            path.write_text(document, encoding="utf-8")
            files.append((path.as_uri(), expected))
            await page.set_content(document)
            snapshot = {"url": f"fixture:{name}", **(await snapshot_lib.inspect(page))}
            report = cli.run([snapshot], None, fonts_lib.PLATFORMS)
            result = report["pages"][0]
            found = {finding["rule"] for finding in result["findings"]}
            problems = [] if found == expected else [f"rules {sorted(found)} != expected {sorted(expected)}"]
            analysed = cli.analyse(snapshot, None, fonts_lib.PLATFORMS)
            # the reader's display language decides 'system'; this machine's is taken to be Japanese
            for group in analysed["groups"] if platform else []:
                if not group["measured"]:
                    continue
                predicted = group["predicted"][platform][0]
                compared += 1
                if predicted != "system" and predicted != group["measured"]:
                    problems.append(f"predicted {predicted} on {platform}, browser used {group['measured']} {group['fonts']}")
            failures += bool(problems)
            print(f"{'ok  ' if not problems else 'FAIL'} {name}: {sorted(found) or 'no findings'}"
                  + "".join(f"\n       {problem}" for problem in problems))
        await browser.close()
    return failures, compared, files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", help="use an installed browser, for example msedge or chrome")
    args = parser.parse_args()
    platform = PLATFORM.get(sys.platform)
    work = Path(tempfile.mkdtemp(prefix="cjk-sense-eval-"))
    failures, compared, files = asyncio.run(run_fixtures(args.channel, platform, work))

    # 3. the same pages through the command line and take_all
    class Quiet:
        def write(self, text):
            return len(text)

        def flush(self):
            pass

    stdout, sys.stdout = sys.stdout, Quiet()
    try:
        argv = ["check", *(uri for uri, _ in files), "--out", str(work / "report.json"), "--fail-on", "warn"]
        code = cli.main(argv + (["--channel", args.channel] if args.channel else []))
    finally:
        sys.stdout = stdout
    pages = json.loads((work / "report.json").read_text(encoding="utf-8"))["pages"]
    cli_bad = sum({finding["rule"] for finding in page["findings"]} != expected
                  for page, (_, expected) in zip(pages, files))
    expected_code = 1 if any(expected for _, expected in files) else 0
    print(f"command line: {len(pages) - cli_bad}/{len(pages)} pages match, exit code {code} (expected {expected_code})")
    failures += cli_bad + (code != expected_code)
    print(f"{platform or sys.platform}: {len(FIXTURES) - min(failures, len(FIXTURES))}/{len(FIXTURES)} fixtures pass, "
          f"{compared} font predictions compared with the browser")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
