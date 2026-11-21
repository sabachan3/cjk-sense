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
import errno
import json
import os
import sys
import unicodedata
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


# Decided by Unicode category, not by a list. Six categories are written as escapes; other spaces
# and unassigned code points stay as they are.
# Cc controls (json.dumps escapes only the C0 ones), Cf format characters (direction marks,
# overrides and isolates, zero-width characters, tags), Zl and Zp separators, Cs lone surrogates
# (which cannot be encoded, so printing one would raise) and Co private use. All can come from a page.
_JSON_UNSAFE_CATEGORIES = {"Cc", "Cf", "Zl", "Zp", "Cs", "Co"}


def _json_escape(char: str) -> str:
    code = ord(char)
    if code > 0xFFFF:  # JSON escapes are UTF-16: a character outside the BMP takes a surrogate pair
        code -= 0x10000
        return f"\\u{0xD800 + (code >> 10):04x}\\u{0xDC00 + (code & 0x3FF):04x}"
    return f"\\u{code:04x}"


def utf8(stream) -> bool:
    return (getattr(stream, "encoding", None) or "utf-8").lower().replace("-", "").replace("_", "") in ("utf8", "utf8sig")


def write_out(text: str) -> None:
    """Print to stdout whatever its encoding is. Redirected output on Windows is often a legacy code
    page that cannot hold every character of a CJK page: what it lacks is written as a backslash escape."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(text.encode(encoding, "backslashreplace").decode(encoding))


def json_text(report: dict, ascii_only: bool = False) -> str:
    """The report as JSON that is safe to print or store: same data, invisible characters as escapes.
    With `ascii_only` every non-ASCII character is an escape, for an output that is not UTF-8."""
    if ascii_only:
        return json.dumps(report, ensure_ascii=True, indent=2)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    return "".join(_json_escape(char) if char != "\n" and unicodedata.category(char) in _JSON_UNSAFE_CATEGORIES else char
                   for char in text)


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
        # utf-8-sig: a list saved by a Windows editor starts with a byte order mark
        lines = [line.strip() for line in Path(args.urls_file).read_text(encoding="utf-8-sig").splitlines()]
        urls += [line for line in lines if line and not line.startswith("#")]
    return list(dict.fromkeys(urls))


def check_out_is_writable(out: Path) -> None:
    """Raise OSError when the report could not be written, leaving nothing behind and following no
    link to do so. Only a file this call created itself is removed again."""
    if out.exists():                      # an existing file, also through a link: opening for append changes nothing
        with out.open("a", encoding="utf-8"):
            return
    if out.is_symlink():                  # a link whose target does not exist yet: create nothing, ask about its folder
        folder = Path(os.path.realpath(out)).parent
        if not (folder.is_dir() and os.access(folder, os.W_OK)):
            raise PermissionError(errno.EACCES, "cannot write the file this link points to", str(out))
        return
    descriptor = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL)   # O_EXCL: fails instead of following a link put there meanwhile
    try:
        made = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    now = os.lstat(out)
    if (now.st_ino, now.st_dev) == (made.st_ino, made.st_dev):        # still the file made above
        os.unlink(out)


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
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.workers < 1 or args.timeout < 0 or args.wait < 0:
        parser.error("--workers must be 1 or more, --timeout and --wait 0 or more")
    try:
        urls = read_urls(args)
        if args.out:  # fail now, not after the browser has visited every page
            check_out_is_writable(Path(args.out))
    except (OSError, UnicodeError) as error:
        print(f"cjk-sense: {check_lib.clean(error)}", file=sys.stderr)
        return 2
    if not urls:
        print("no URLs given", file=sys.stderr)
        return 2
    platforms = tuple(part.strip() for part in args.platforms.split(",") if part.strip())
    unknown = [platform for platform in platforms if platform not in fonts_lib.PLATFORMS]
    if unknown or not platforms:
        print(f"{'unknown platform ' + check_lib.clean(', '.join(unknown)) if unknown else 'no platform given'}; choose from {', '.join(fonts_lib.PLATFORMS)}", file=sys.stderr)
        return 2
    try:
        taken = snapshots(urls, args)
    except ImportError:
        print("playwright is not installed: pip install playwright", file=sys.stderr)
        return 2
    except Exception as error:
        hint = BROWSER_HINT if "Executable doesn't exist" in str(error) or "playwright install" in str(error) else ""
        first = check_lib.clean((str(error).splitlines() or [type(error).__name__])[0], 200)
        print(f"could not start the browser: {first}\n{hint}".rstrip(), file=sys.stderr)
        return 2
    report = run(taken, args.expect, platforms)
    write_out(json_text(report, ascii_only=not utf8(sys.stdout)) if args.format == "json" else check_lib.format_text(report))
    if args.out:
        try:
            Path(args.out).write_text(json_text(report) + "\n", encoding="utf-8")
        except OSError as error:
            print(f"cjk-sense: {check_lib.clean(error)}", file=sys.stderr)
            return 2
    return check_lib.exit_code(report, args.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
