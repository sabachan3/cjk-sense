"""End-to-end check of the installed command (driven by scripts/e2e.sh).

Serves three pages from a local HTTP server and runs the installed `cjk-sense` on them, one
process per page and once for all three. Verdicts, rules and exit codes must match exactly.
Only the standard library is used here: the command under test lives in its own environment.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import subprocess
import sys
import threading
from pathlib import Path

JA = "これは日本語のページです。直接、海の画像を骨組みから作り直します。設定を保存しました。" * 3

# file name -> (html lang, font-family, expected verdict, expected rules, expected exit code)
PAGES = {
    "clean.html": ("ja", "'Hiragino Sans', 'Yu Gothic UI', Meiryo, sans-serif", "ok", set(), 0),
    "chinese-font-first.html": ("ja", "-apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif",
                                "fail", {"han-font"}, 1),
    "wrong-lang.html": ("en", "sans-serif", "fail", {"lang-mismatch"}, 1),
}


def write_site(site: Path) -> None:
    site.mkdir(parents=True, exist_ok=True)
    for name, (lang, stack, *_) in PAGES.items():
        (site / name).write_text(
            f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>{name}</title>'
            f'<body style="font-family:{stack}"><h1>{JA}</h1></body></html>', encoding="utf-8")


def serve(site: Path) -> http.server.ThreadingHTTPServer:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def check(command: str, urls: list[str], channel: str | None) -> tuple[int, dict]:
    argv = [command, "check", *urls, "--format", "json"] + (["--channel", channel] if channel else [])
    done = subprocess.run(argv, capture_output=True, text=True, timeout=180)
    if done.returncode == 2:
        raise SystemExit(f"the command could not run:\n{done.stderr}")
    return done.returncode, json.loads(done.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True, help="path of the installed cjk-sense")
    parser.add_argument("--work", required=True, type=Path, help="directory to write the pages into")
    parser.add_argument("--channel", help="installed browser to drive (chrome, msedge)")
    args = parser.parse_args()
    write_site(args.work)
    server = serve(args.work)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    failures = 0
    try:
        for name, (_, _, verdict, rules, exit_code) in PAGES.items():
            code, report = check(args.command, [f"{base}/{name}"], args.channel)
            page = report["pages"][0]
            found = {finding["rule"] for finding in page["findings"]}
            good = (page["verdict"], found, code) == (verdict, rules, exit_code)
            failures += not good
            print(f"{'ok  ' if good else 'FAIL'} {name}: verdict {page['verdict']}, rules {sorted(found)}, exit {code}"
                  + ("" if good else f"  (expected {verdict}, {sorted(rules)}, exit {exit_code})"))
        code, report = check(args.command, [f"{base}/{name}" for name in PAGES], args.channel)
        expected = {"pages": 3, "fail": 2, "warn": 0, "ok": 1}
        good = report["summary"] == expected and code == 1 and report["version"] == 1
        failures += not good
        print(f"{'ok  ' if good else 'FAIL'} all three in one run: summary {report['summary']}, exit {code}")
    finally:
        server.shutdown()
    print(f"e2e: {len(PAGES) + 1 - failures}/{len(PAGES) + 1} checks pass")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
