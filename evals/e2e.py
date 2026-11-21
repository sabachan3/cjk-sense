"""End-to-end check of the installed command (driven by scripts/e2e.sh).

Serves three pages from a local HTTP server and runs the installed `cjk-sense` on them, one
process per page and once for all three. Verdicts, rules and exit codes must match exactly.
With --expect-version the command must also print that version and its usage text.
A command that crashes or prints no report is a failed check with its exit code and last line
of stderr, never a traceback from here.
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
    # a short poll keeps shutdown() quick; the default waits up to half a second
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
    return server


def invoke_args(command: str, arguments: list[str]) -> tuple[int, str, str]:
    """Run the command with these arguments: (exit code, stdout, stderr), -1 when it could not be run."""
    try:
        done = subprocess.run([command, *arguments], capture_output=True, encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as error:
        return -1, "", f"{type(error).__name__}: {error}"
    return done.returncode, done.stdout, done.stderr


def invoke(command: str, urls: list[str], channel: str | None) -> tuple[int, str, str]:
    return invoke_args(command, ["check", *urls, "--format", "json"] + (["--channel", channel] if channel else []))


def last_line(text: str) -> str:
    return (text.strip().splitlines() or ["nothing printed"])[-1][:300]


def judge_version(code: int, stdout: str, stderr: str, version: str) -> tuple[bool, str]:
    """`--version` of the installed command must print exactly the version that was built."""
    good = code == 0 and stdout.strip() == f"cjk-sense {version}"
    if good:
        return True, f"ok   --version: {stdout.strip()}, exit 0"
    return False, (f"FAIL --version: printed {last_line(stdout)!r}, exit {code}  (expected 'cjk-sense {version}', exit 0; "
                   f"stderr: {last_line(stderr)})")


def judge_help(code: int, stdout: str, stderr: str) -> tuple[bool, str]:
    """`--help` must exit 0 and name the command and its one subcommand."""
    good = code == 0 and "usage: cjk-sense" in stdout and "check" in stdout
    if good:
        return True, "ok   --help: usage text with the check command, exit 0"
    return False, f"FAIL --help: exit {code}, no usage text for cjk-sense check  (stderr: {last_line(stderr)})"


def read_report(code: int, stdout: str, stderr: str) -> tuple[dict | None, str]:
    """The report the command printed, or None and one line saying why there is none."""
    try:
        report = json.loads(stdout)
        if isinstance(report, dict) and isinstance(report.get("pages"), list) and "summary" in report:
            return report, ""
        reason = "the output is JSON but not a report"
    except ValueError:
        reason = "the command printed no JSON report"
    last = (stderr.strip().splitlines() or ["nothing on stderr"])[-1][:300]
    return None, f"{reason} (exit {code}): {last}"


def judge_page(name: str, code: int, stdout: str, stderr: str,
               verdict: str, rules: set[str], exit_code: int) -> tuple[bool, str]:
    """Whether one single-page run matches, and the line to print for it.

    Never raises, whatever the command printed: a report of the wrong shape is a failed check."""
    report, problem = read_report(code, stdout, stderr)
    if report is None or not report["pages"]:
        return False, f"FAIL {name}: {problem or 'the report has no page'}"
    page = report["pages"][0]
    if not isinstance(page, dict):
        return False, f"FAIL {name}: the page entry is {type(page).__name__}, not an object (exit {code})"
    findings = page.get("findings", [])
    if not isinstance(findings, list) or not all(isinstance(finding, dict) for finding in findings):
        return False, f"FAIL {name}: findings is not a list of objects (exit {code})"
    found = {rule if isinstance(rule, str) else repr(rule) for rule in (finding.get("rule") for finding in findings)}
    good = (page.get("verdict"), found, code) == (verdict, rules, exit_code)
    line = f"{'ok  ' if good else 'FAIL'} {name}: verdict {page.get('verdict')!r}, rules {sorted(found)}, exit {code}"
    return good, line + ("" if good else f"  (expected {verdict}, {sorted(rules)}, exit {exit_code})")


def judge_all(code: int, stdout: str, stderr: str) -> tuple[bool, str]:
    """The same for the run over all pages at once."""
    name = f"all {len(PAGES)} in one run"
    report, problem = read_report(code, stdout, stderr)
    if report is None:
        return False, f"FAIL {name}: {problem}"
    expected = {"pages": len(PAGES), "fail": sum(1 for page in PAGES.values() if page[2] == "fail"), "warn": 0,
                "ok": sum(1 for page in PAGES.values() if page[2] == "ok")}
    good = report["summary"] == expected and code == 1 and report.get("version") == 1
    line = f"{'ok  ' if good else 'FAIL'} {name}: summary {report['summary']}, version {report.get('version')}, exit {code}"
    return good, line + ("" if good else f"  (expected {expected}, version 1, exit 1)")


def main(argv: list[str] | None = None, runner=invoke, plain=invoke_args) -> int:
    """Exit status: 0 when every check passes, 1 otherwise. `runner` and `plain` stand in for the
    command in tests. With --expect-version, `--version` and `--help` are checked as well."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True, help="path of the installed cjk-sense")
    parser.add_argument("--work", required=True, type=Path, help="directory to write the pages into")
    parser.add_argument("--channel", help="installed browser to drive (chrome, msedge)")
    parser.add_argument("--expect-version", help="also check --version (must print this version) and --help")
    parser.add_argument("--label", help="what was installed (wheel, sdist), shown in the last line")
    args = parser.parse_args(argv)
    write_site(args.work)
    server = serve(args.work)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    results = []
    try:
        if args.expect_version:
            results.append(judge_version(*plain(args.command, ["--version"]), args.expect_version))
            results.append(judge_help(*plain(args.command, ["--help"])))
        for name, (_, _, verdict, rules, exit_code) in PAGES.items():
            results.append(judge_page(name, *runner(args.command, [f"{base}/{name}"], args.channel),
                                      verdict, rules, exit_code))
        results.append(judge_all(*runner(args.command, [f"{base}/{name}" for name in PAGES], args.channel)))
    finally:
        server.shutdown()
    for _, line in results:
        print(line)
    passed = sum(good for good, _ in results)
    print(f"e2e{' ' + args.label if args.label else ''}: {passed}/{len(results)} checks pass")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
