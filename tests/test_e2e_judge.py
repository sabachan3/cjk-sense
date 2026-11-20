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
