"""The end-to-end verdict (evals/e2e.py) is decided by pure functions; each way a run can go wrong is pinned."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
import e2e  # noqa: E402


def report(verdict="fail", rules=("han-font",), summary=None, version=1):
    page = {"verdict": verdict, "findings": [{"rule": rule} for rule in rules]}
    return json.dumps({"version": version, "summary": summary or {"pages": 1}, "pages": [page]})


def test_good_single_page_run():
    good, line = e2e.judge_page("p.html", 1, report(), "", "fail", {"han-font"}, 1)
    assert good and line.startswith("ok  ") and "han-font" in line


def test_crash_is_a_fail_line_with_exit_code_and_last_stderr_line():
    stderr = "Traceback (most recent call last):\n  File x\nModuleNotFoundError: No module named 'check_lib'\n"
    good, line = e2e.judge_page("p.html", 1, "", stderr, "fail", {"han-font"}, 1)
    assert not good and line.startswith("FAIL p.html:")
    assert "exit 1" in line and "No module named 'check_lib'" in line and "Traceback" not in line


def test_exit_two_without_output_is_a_fail_line():
    good, line = e2e.judge_page("p.html", 2, "", "could not start the browser: x", "ok", set(), 0)
    assert not good and "exit 2" in line and "could not start the browser" in line


def test_json_that_is_not_a_report_fails():
    for stdout in ("[]", '{"pages": 3}', '{"summary": {}}', "null"):
        good, line = e2e.judge_page("p.html", 0, stdout, "", "ok", set(), 0)
        assert not good and line.startswith("FAIL")


def test_wrong_verdict_wrong_rule_and_wrong_exit_code_each_fail():
    assert not e2e.judge_page("p", 1, report(verdict="warn"), "", "fail", {"han-font"}, 1)[0]
    assert not e2e.judge_page("p", 1, report(rules=("lang-mismatch",)), "", "fail", {"han-font"}, 1)[0]
    good, line = e2e.judge_page("p", 0, report(), "", "fail", {"han-font"}, 1)
    assert not good and "expected fail" in line and "exit 1" in line


def test_empty_page_list_fails_without_raising():
    stdout = json.dumps({"version": 1, "summary": {}, "pages": []})
    assert not e2e.judge_page("p", 0, stdout, "", "ok", set(), 0)[0]


def test_all_pages_run():
    summary = {"pages": 3, "fail": 2, "warn": 0, "ok": 1}
    assert e2e.judge_all(1, report(summary=summary), "")[0]
    assert not e2e.judge_all(0, report(summary=summary), "")[0]                      # wrong exit code
    assert not e2e.judge_all(1, report(summary={**summary, "fail": 1}), "")[0]       # wrong counts
    assert not e2e.judge_all(1, report(summary=summary, version=2), "")[0]           # wrong report version
    good, line = e2e.judge_all(1, "", "boom")
    assert not good and "exit 1" in line and "boom" in line


def shaped(pages):
    return json.dumps({"version": 1, "summary": {}, "pages": pages})


def test_wrongly_typed_reports_are_fail_lines_not_exceptions():
    for pages in ([3], ["x"], [None], [{"verdict": "ok", "findings": 5}], [{"verdict": "ok", "findings": None}],
                  [{"verdict": "ok", "findings": [1]}], [{"verdict": "ok", "findings": "han-font"}]):
        good, line = e2e.judge_page("p.html", 0, shaped(pages), "", "ok", set(), 0)
        assert not good and line.startswith("FAIL p.html:"), pages


def test_rule_of_the_wrong_type_is_a_fail_line():
    for rule in ([1], {"a": 1}, 5, None):
        good, line = e2e.judge_page("p.html", 1, shaped([{"verdict": "fail", "findings": [{"rule": rule}]}]), "",
                                    "fail", {"han-font"}, 1)
        assert not good and line.startswith("FAIL p.html:"), rule


def test_all_pages_run_with_a_summary_of_the_wrong_type_fails_without_raising():
    for summary in (5, None, [1], "x"):
        stdout = json.dumps({"version": 1, "summary": summary, "pages": []})
        assert not e2e.judge_all(1, stdout, "")[0]


def test_output_that_is_not_utf8_is_read_without_raising(tmp_path):
    body = tmp_path / "fake.py"
    body.write_text("import sys\nsys.stdout.buffer.write(bytes([0xff, 0xfe, 0x80]))\n"
                    "sys.stderr.buffer.write(bytes([0xff]) + b'bad bytes')\nsys.exit(3)\n", encoding="utf-8")
    if sys.platform == "win32":  # no shebang there: a batch file that runs the same script
        script = tmp_path / "fake.cmd"
        script.write_text(f'@"{sys.executable}" "{body}" %*\r\n', encoding="utf-8")
    else:
        script = tmp_path / "fake"
        script.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{body}" "$@"\n', encoding="utf-8")
        script.chmod(0o755)
    code, stdout, stderr = e2e.invoke(str(script), ["http://x/"], None)
    assert code == 3
    good, line = e2e.judge_page("p.html", code, stdout, stderr, "ok", set(), 0)
    assert not good and "exit 3" in line and "bad bytes" in line


def test_a_command_that_cannot_be_started_is_a_fail_line(tmp_path):
    code, stdout, stderr = e2e.invoke(str(tmp_path / "absent"), ["http://x/"], None)
    good, line = e2e.judge_page("p.html", code, stdout, stderr, "ok", set(), 0)
    assert not good and "FileNotFoundError" in line


def perfect_runner(command, urls, channel):
    """Stands in for the installed command: answers every page with exactly what PAGES expects."""
    pages = []
    for url in urls:
        _, _, verdict, rules, _ = e2e.PAGES[url.rsplit("/", 1)[1]]
        pages.append({"verdict": verdict, "findings": [{"rule": rule} for rule in sorted(rules)]})
    counts = {name: sum(page["verdict"] == name for page in pages) for name in ("fail", "warn", "ok")}
    code = 1 if counts["fail"] else 0
    return code, json.dumps({"version": 1, "summary": {"pages": len(pages), **counts}, "pages": pages}), ""


def test_main_exits_zero_only_when_every_check_passes(tmp_path, capsys):
    argv = ["--command", "unused", "--work", str(tmp_path / "site")]
    assert e2e.main(argv, runner=perfect_runner) == 0
    assert "e2e: 4/4 checks pass" in capsys.readouterr().out

    def one_wrong(command, urls, channel):
        code, stdout, stderr = perfect_runner(command, urls, channel)
        return (0, stdout, stderr) if len(urls) == 1 and urls[0].endswith("wrong-lang.html") else (code, stdout, stderr)

    assert e2e.main(argv, runner=one_wrong) == 1
    assert "e2e: 3/4 checks pass" in capsys.readouterr().out

    def crash(command, urls, channel):
        return 1, "", "ModuleNotFoundError: No module named 'check_lib'"

    assert e2e.main(argv, runner=crash) == 1
    out = capsys.readouterr().out
    assert "e2e: 0/4 checks pass" in out and out.count("FAIL") == 4 and "Traceback" not in out


def test_version_check_wants_exactly_the_built_version_and_exit_zero():
    assert e2e.judge_version(0, "cjk-sense 0.1.0\n", "", "0.1.0") == (True, "ok   --version: cjk-sense 0.1.0, exit 0")
    for code, stdout in ((0, "cjk-sense 0.1.1\n"), (0, "0.1.0\n"), (2, "cjk-sense 0.1.0\n"), (0, ""),
                         (0, "cjk-sense 0.1.0\nmore\n")):
        good, line = e2e.judge_version(code, stdout, "boom", "0.1.0")
        assert not good and line.startswith("FAIL --version:") and "boom" in line, (code, stdout)


def test_help_check_wants_the_usage_text_and_exit_zero():
    assert e2e.judge_help(0, "usage: cjk-sense [-h] [--version] {check} ...\n", "")[0]
    for code, stdout in ((2, "usage: cjk-sense [-h] {check} ..."), (0, ""), (0, "usage: other {check}"), (0, "usage: cjk-sense")):
        good, line = e2e.judge_help(code, stdout, "boom")
        assert not good and line.startswith("FAIL --help:") and "boom" in line, (code, stdout)


def test_main_with_expect_version_adds_the_two_checks_and_the_label(tmp_path, capsys):
    argv = ["--command", "unused", "--work", str(tmp_path / "site"), "--expect-version", "0.1.0", "--label", "sdist"]
    asked = []

    def plain(command, arguments):
        asked.append(arguments)
        return (0, "cjk-sense 0.1.0\n", "") if arguments == ["--version"] else (0, "usage: cjk-sense {check}\n", "")

    assert e2e.main(argv, runner=perfect_runner, plain=plain) == 0
    assert asked == [["--version"], ["--help"]] and "e2e sdist: 6/6 checks pass" in capsys.readouterr().out

    def stale(command, arguments):   # an installed command from another build
        return (0, "cjk-sense 0.0.9\n", "") if arguments == ["--version"] else (0, "usage: cjk-sense {check}\n", "")

    assert e2e.main(argv, runner=perfect_runner, plain=stale) == 1
    out = capsys.readouterr().out
    assert "e2e sdist: 5/6 checks pass" in out and "FAIL --version" in out


def test_a_command_that_cannot_be_started_fails_the_version_check(tmp_path):
    good, line = e2e.judge_version(*e2e.invoke_args(str(tmp_path / "absent"), ["--version"]), "0.1.0")
    assert not good and "FileNotFoundError" in line
