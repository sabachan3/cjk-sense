"""cjk-sense: catch pages whose kanji come out in another region's font, or whose lang is wrong.

    cjk-sense check http://localhost:3000/ja --expect ja

Opens each page in Chromium and reports:
  han-font        kanji (or hanzi, hanja) drawn with a Chinese, Japanese or Korean font that does
                  not match the page's language, on macOS, Windows, iOS or Android
  lang-mismatch   <html lang> names a language written in a different script than the text
  lang-missing    <html> has no lang
  wrong-language  with --expect: the page is not in the language you asked for

The font check is a prediction from font-family and lang per platform, so it gives the same
answer on a CI machine with no CJK fonts. Where the browser running the check does have the
fonts, the fonts it actually used are reported as confirmation. No model, no network service.
Exit code 1 when a page fails, 2 when the tool itself cannot run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
# installed: services are shipped inside the package. In the repository: the services/ directory.
INSTALLED = (PACKAGE / "_services").is_dir()
SERVICES_DIR = PACKAGE / "_services" if INSTALLED else PACKAGE.parent / "services"
for service in ("detect", "fonts", "snapshot", "check"):
    sys.path.insert(0, str(SERVICES_DIR / service))
sys.path.insert(0, str(SERVICES_DIR if INSTALLED else PACKAGE.parent))

import check_lib  # noqa: E402
import detect_lib  # noqa: E402
import fonts_lib  # noqa: E402
import snapshot_lib  # noqa: E402
from contracts import schema  # noqa: E402

LOCALES = {"ja": "ja-JP", "zh": "zh-CN", "ko": "ko-KR"}
BROWSER_HINT = ("No browser to drive. Either install the bundled one:\n"
                "    playwright install chromium-headless-shell\n"
                "or use an installed browser: --channel chrome (or msedge)")


def analyse(snapshot: dict, expect: str | None, platforms: tuple[str, ...]) -> dict:
    """Snapshot plus what the rules need: detected language and predicted font region per group."""
    schema.validate_snapshot(snapshot)
    if "error" in snapshot:
        return snapshot
    page = {key: snapshot[key] for key in ("url", "html_lang")}
    page["final_url"] = snapshot.get("final_url", snapshot["url"])
    page["detected"] = detect_lib.detect(detect_lib.count_scripts(snapshot["text"]))
    page["declared_class"] = detect_lib.language_class(snapshot["html_lang"])
    page["html_region"] = detect_lib.cjk_region(snapshot["html_lang"])
    page["expect"], page["expect_class"] = expect, detect_lib.language_class(expect)
    webfonts = set(snapshot["webfonts"])
    page["groups"] = []
    for group in snapshot["groups"]:
        region = detect_lib.cjk_region(group["lang"])
        page["groups"].append({
            **group, "lang_region": region, "measured": fonts_lib.measured_region(group.get("fonts", [])),
            "predicted": {platform: list(fonts_lib.resolve(group["stack"], region, platform, webfonts))
                          for platform in platforms}})
    return page


# json.dumps escapes the C0 controls itself. With ensure_ascii off it leaves DEL, the C1 controls
# (0x9b starts an escape sequence on some terminals), the line separators and the direction
# overrides as they are, and all of them can come from a page.
_JSON_UNSAFE = re.compile("[" + "".join(f"{chr(first)}-{chr(last)}" for first, last in (
    (0x7F, 0x9F), (0x2028, 0x2029), (0x202A, 0x202E), (0x2066, 0x2069))) + "]")


def json_text(report: dict) -> str:
    """The report as JSON that is safe to print: same data, risky characters written as escapes."""
    text = json.dumps(report, ensure_ascii=False, indent=2)
    return _JSON_UNSAFE.sub(lambda match: f"\\u{ord(match.group()):04x}", text)


def run(snapshots: list[dict], expect: str | None, platforms: tuple[str, ...]) -> dict:
    pages = [check_lib.check_page(analyse(snapshot, expect, platforms), platforms) for snapshot in snapshots]
    for page in pages:
        for finding in page["findings"]:
            schema.validate_finding(finding)
    return check_lib.build_report(pages, platforms)


def take_snapshots(urls: list[str], args: argparse.Namespace) -> list[dict]:
    locale = args.locale or LOCALES.get(detect_lib.primary(args.expect))
    return asyncio.run(snapshot_lib.take_all(urls, locale=locale, channel=args.channel, timeout=args.timeout,
                                             wait=args.wait, workers=args.workers))


def read_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.urls)
    if args.urls_file:
        urls += [line.strip() for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.startswith("#")]
    return list(dict.fromkeys(urls))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cjk-sense", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check one or more pages")
    check.add_argument("urls", nargs="*", help="page URLs (http, https or file)")
    check.add_argument("--urls-file", help="text file with one URL per line")
    check.add_argument("--expect", help="language the pages should be in, for example ja, zh, ko, en")
    check.add_argument("--platforms", default=",".join(fonts_lib.PLATFORMS),
                       help="platforms to predict fonts for (default: %(default)s)")
    check.add_argument("--fail-on", choices=("fail", "warn", "never"), default="fail")
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.add_argument("--out", help="also write the JSON report to this file")
    check.add_argument("--channel", help="drive an installed browser (chrome, msedge) instead of the bundled one")
    check.add_argument("--locale", help="browser language sent to the site (default: from --expect)")
    check.add_argument("--timeout", type=int, default=30000, help="page load timeout in ms")
    check.add_argument("--wait", type=int, default=0, help="extra ms to wait after load, for client-side rendering")
    check.add_argument("--workers", type=int, default=4)
    return parser


def main(argv: list[str] | None = None, snapshots=take_snapshots) -> int:
    args = build_parser().parse_args(argv)
    urls = read_urls(args)
    if not urls:
        print("no URLs given", file=sys.stderr)
        return 2
    platforms = tuple(part.strip() for part in args.platforms.split(",") if part.strip())
    unknown = [platform for platform in platforms if platform not in fonts_lib.PLATFORMS]
    if unknown or not platforms:
        print(f"unknown platform {', '.join(unknown)}; choose from {', '.join(fonts_lib.PLATFORMS)}", file=sys.stderr)
        return 2
    try:
        taken = snapshots(urls, args)
    except ImportError:
        print("playwright is not installed: pip install playwright", file=sys.stderr)
        return 2
    except Exception as error:
        hint = BROWSER_HINT if "Executable doesn't exist" in str(error) or "playwright install" in str(error) else ""
        print(f"could not start the browser: {str(error).splitlines()[0][:200]}\n{hint}".rstrip(), file=sys.stderr)
        return 2
    report = run(taken, args.expect, platforms)
    if args.out:
        Path(args.out).write_text(json_text(report) + "\n", encoding="utf-8")
    print(json_text(report) if args.format == "json" else check_lib.format_text(report))
    return check_lib.exit_code(report, args.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
