import io
import json
import sys

import pytest

from cjk_sense import cli

JA = "これは日本語のページです。設定を保存しました。" * 4
ANTD = '-apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'


def snapshot(url="http://localhost/ja", html_lang="ja", text=JA, stack="sans-serif", lang="ja", fonts=(), webfonts=()):
    return {"url": url, "final_url": url, "html_lang": html_lang, "text": text, "webfonts": list(webfonts),
            "groups": [{"stack": stack, "lang": lang, "chars": 60, "sample": "設定を保存", "where": "p", "fonts": list(fonts)}]}


def run(capsys, snapshots, *argv):
    seen = {}

    def fake(urls, args):
        seen["urls"], seen["args"] = urls, args
        return snapshots

    code = cli.main(["check", *argv], snapshots=fake)
    return code, capsys.readouterr(), seen


def test_clean_page_exits_zero(capsys):
    code, out, seen = run(capsys, [snapshot()], "http://localhost/ja")
    assert code == 0 and "OK" in out.out and "1 page(s): 0 fail, 0 warn, 1 ok" in out.out
    assert seen["urls"] == ["http://localhost/ja"]


def test_chinese_font_list_fails_on_mac_ios_and_windows_but_not_android(capsys):
    code, out, _ = run(capsys, [snapshot(stack=ANTD)], "http://localhost/ja", "--format", "json")
    report = json.loads(out.out)
    (finding,) = report["pages"][0]["findings"]
    assert code == 1 and finding["rule"] == "han-font" and finding["platforms"] == ["mac", "windows", "ios"]
    assert report["platforms"] == ["mac", "windows", "ios", "android"]


def test_platforms_option_limits_the_prediction(capsys):
    code, out, _ = run(capsys, [snapshot(stack='"PingFang SC", sans-serif')], "u", "--platforms", "windows,android")
    assert code == 0
    code, out, _ = run(capsys, [snapshot()], "u", "--platforms", "amiga")
    assert code == 2 and "unknown platform" in out.err


def test_lang_mismatch_and_fail_on(capsys):
    english_lang = snapshot(html_lang="en", lang="en")
    code, out, _ = run(capsys, [english_lang], "u")
    assert code == 1 and 'lang-mismatch: <html lang="en"> but the text is Japanese' in out.out
    assert run(capsys, [english_lang], "u", "--fail-on", "never")[0] == 0
    missing = snapshot(html_lang=None, lang="")
    assert run(capsys, [missing], "u")[0] == 0 and run(capsys, [missing], "u", "--fail-on", "warn")[0] == 1


def test_expect_catches_an_untranslated_route_and_sets_the_browser_language(capsys):
    english = snapshot(text="This page was never translated into Japanese at all. " * 4, html_lang="ja")
    code, out, seen = run(capsys, [english], "u", "--expect", "ja")
    assert code == 1 and "wrong-language: expected ja" in out.out
    assert seen["args"].expect == "ja"


def test_measured_fonts_are_shown_as_confirmation(capsys):
    code, out, _ = run(capsys, [snapshot(stack=ANTD, fonts=[["蘋方-簡", 12]])], "u")
    assert code == 1 and "confirmed in this browser: 蘋方-簡" in out.out


def test_web_font_that_loaded_decides_everywhere(capsys):
    page = snapshot(stack='"Noto Sans SC", sans-serif', webfonts=["Noto Sans SC"])
    code, out, _ = run(capsys, [page], "u", "--format", "json")
    assert json.loads(out.out)["pages"][0]["findings"][0]["platforms"] == ["mac", "windows", "ios", "android"]


def test_page_error_fails_and_other_pages_are_still_checked(capsys):
    code, out, _ = run(capsys, [{"url": "http://down", "error": "TimeoutError: 30000ms"}, snapshot()], "http://down", "u")
    assert code == 1 and "page-error" in out.out and "2 page(s): 1 fail, 0 warn, 1 ok" in out.out


def test_urls_file_out_file_and_no_urls(capsys, tmp_path):
    listing = tmp_path / "urls.txt"
    listing.write_text("# pages\nhttp://a/ja\n\nhttp://b/ja\nhttp://a/ja\n", encoding="utf-8")
    out_file = tmp_path / "report.json"
    code, _, seen = run(capsys, [snapshot("http://a/ja"), snapshot("http://b/ja")], "--urls-file", str(listing),
                        "--out", str(out_file))
    assert code == 0 and seen["urls"] == ["http://a/ja", "http://b/ja"]
    assert json.loads(out_file.read_text(encoding="utf-8"))["summary"]["pages"] == 2
    assert cli.main(["check"], snapshots=lambda urls, args: []) == 2


def test_browser_failures_exit_two_with_a_hint(capsys):
    def missing(urls, args):
        raise RuntimeError("BrowserType.launch: Executable doesn't exist at /x\nrun playwright install")

    assert cli.main(["check", "u"], snapshots=missing) == 2
    assert "playwright install chromium-headless-shell" in capsys.readouterr().err

    def not_installed(urls, args):
        raise ImportError("playwright")

    assert cli.main(["check", "u"], snapshots=not_installed) == 2


def test_malformed_snapshot_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        cli.run([{"url": "u", "text": "x"}], None, ("mac",))


ESC, DEL, CSI, RLO, LS, LRI = chr(0x1B), chr(0x7F), chr(0x9B), chr(0x202E), chr(0x2028), chr(0x2066)


def test_json_text_escapes_control_and_direction_characters_and_keeps_the_data():
    hostile = f"evil{DEL}{CSI}31m{RLO}{ESC}[2J{LS}{LRI} " + JA[:8]
    report = {"pages": [{"url": hostile, "findings": [{"sample": hostile}]}]}
    text = cli.json_text(report)
    assert not any(char in text for char in (ESC, DEL, CSI, RLO, LS, LRI))
    assert json.loads(text) == report      # valid JSON, nothing dropped or changed
    assert JA[:8] in text                  # ordinary CJK text stays readable


def test_json_format_and_out_file_go_through_json_text(capsys, tmp_path):
    hostile = f"p{CSI}31m{RLO}{DEL}"
    out = tmp_path / "report.json"
    code, printed, _ = run(capsys, [snapshot(url=f"http://localhost/{hostile}")], "http://localhost/x",
                           "--format", "json", "--out", str(out))
    written = out.read_text(encoding="utf-8")
    for text in (printed.out, written):
        assert not any(char in text for char in (CSI, RLO, DEL))
        assert json.loads(text)["pages"][0]["url"].endswith(hostile)


def test_text_format_strips_the_same_characters(capsys):
    hostile = f"p{CSI}31m{RLO}{DEL}{ESC}[2J"
    _, printed, _ = run(capsys, [snapshot(url=f"http://localhost/{hostile}")], "http://localhost/x")
    assert not any(char in printed.out for char in (CSI, RLO, DEL, ESC))


def test_report_version_is_the_same_in_the_contract_and_the_check_service():
    import check_lib
    from contracts import schema

    assert check_lib.REPORT_VERSION == schema.REPORT_VERSION == 1


# One character of every kind that must never reach a terminal raw. Built from integers, never typed.
INVISIBLE = [chr(code) for code in (0x1B, 0x07, 0x7F, 0x9B, 0x2028, 0x2029, 0x202E, 0x2066, 0x200E, 0x200F, 0x061C,
                                    0x200B, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0xFFF9, 0xE000, 0xE0001, 0xE0041, 0xD800)]
SURROGATE = chr(0xD800)


def hostile_snapshot():
    junk = "".join(INVISIBLE)
    stack = f'"PingFang SC", "Web{junk}Font", sans-serif'
    return snapshot(url="http://localhost/ja" + junk[:3], stack=stack, html_lang="ja" + SURROGATE,
                    text=JA + junk) | {"groups": [{"stack": stack, "lang": "ja", "chars": 60,
                                                   "sample": "設定" + junk, "where": "p#x" + junk, "fonts": []}]}


def test_json_text_escapes_every_invisible_category_and_keeps_the_data():
    data = {"sample": "設定" + "".join(INVISIBLE) + " ok", "".join(INVISIBLE): 1}
    text = cli.json_text(data)
    assert not any(char in text for char in INVISIBLE)
    assert json.loads(text) == data            # nothing lost, the lone surrogate included
    text.encode("utf-8")                       # a raw lone surrogate would raise here
    assert "設定" in text                       # ordinary CJK text stays readable


def test_json_text_writes_astral_format_characters_as_a_surrogate_pair():
    tag = chr(0xE0041)
    text = cli.json_text({"k": tag})
    assert "\\udb40\\udc41" in text and json.loads(text) == {"k": tag}


def test_page_with_lone_surrogate_and_direction_marks_gives_a_normal_report(capsys, tmp_path):
    out_file = tmp_path / "report.json"
    for fmt in ("text", "json"):
        code, out, _ = run(capsys, [hostile_snapshot()], "http://localhost/ja", "--format", fmt, "--out", str(out_file))
        assert code == 1                                         # the Chinese font list still fails the page
        out.out.encode("utf-8")                                  # printable: no lone surrogate
        written = out_file.read_text(encoding="utf-8")
        for stream in (out.out, out.err, written):
            assert not any(char in stream for char in INVISIBLE), fmt
        assert json.loads(written)["pages"][0]["findings"][0]["rule"] == "han-font"
    assert "han-font" in out.out and json.loads(out.out)["summary"]["fail"] == 1


def test_clean_keeps_spaces_and_text_and_drops_everything_invisible():
    from cjk_sense.cli import check_lib
    text = "設定 を" + chr(0x3000) + "保存" + "".join(INVISIBLE) + "\n\tend"
    assert check_lib.clean(text) == "設定 を 保存  end"


def test_browser_error_text_is_cleaned(capsys):
    def boom(urls, args):
        raise RuntimeError("cannot launch" + "".join(INVISIBLE) + "\nsecond line")

    code = cli.main(["check", "u"], snapshots=boom)
    err = capsys.readouterr().err
    assert code == 2 and "cannot launch" in err and "second line" not in err
    assert not any(char in err for char in INVISIBLE)


def test_browser_error_without_text_still_exits_two(capsys):
    def boom(urls, args):
        raise RuntimeError("")

    assert cli.main(["check", "u"], snapshots=boom) == 2
    assert "could not start the browser" in capsys.readouterr().err


def test_out_that_cannot_be_written_exits_two_before_the_browser_runs(capsys, tmp_path):
    called = []
    for bad in (tmp_path, tmp_path / "missing" / "report.json"):
        code = cli.main(["check", "http://a/ja", "--out", str(bad)], snapshots=lambda urls, args: called.append(1) or [])
        assert code == 2 and "Traceback" not in capsys.readouterr().err
    assert called == []
    report = tmp_path / "report.json"

    def boom(urls, args):
        raise RuntimeError("no browser")

    assert cli.main(["check", "http://a/ja", "--out", str(report)], snapshots=boom) == 2 and not report.exists()


def test_urls_file_that_cannot_be_read_exits_two(capsys, tmp_path):
    binary = tmp_path / "urls.bin"
    binary.write_bytes(bytes([0xFF, 0xFE, 0x00]))
    for bad in (tmp_path / "absent.txt", tmp_path, binary):
        assert cli.main(["check", "--urls-file", str(bad)], snapshots=lambda urls, args: []) == 2
    assert "Traceback" not in capsys.readouterr().err


@pytest.mark.parametrize("option,value", [("--workers", "0"), ("--workers", "-1"), ("--timeout", "-5"), ("--wait", "-1")])
def test_out_of_range_options_are_usage_errors(option, value):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["check", "http://a/ja", option, value], snapshots=lambda urls, args: [])
    assert exit_info.value.code == 2


def test_empty_platforms_has_a_sensible_message(capsys):
    assert cli.main(["check", "http://a/ja", "--platforms", ""], snapshots=lambda urls, args: []) == 2
    assert "no platform given" in capsys.readouterr().err


@pytest.mark.parametrize("fmt,encoding", [("text", "cp1252"), ("json", "cp1252"), ("text", "ascii"), ("json", "ascii")])
def test_stdout_that_is_not_utf8_gets_escapes_not_a_crash(monkeypatch, fmt, encoding):
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding=encoding, newline=""))
    page = snapshot(stack='"PingFang SC", sans-serif')
    code = cli.main(["check", "http://localhost/ja", "--format", fmt], snapshots=lambda urls, args: [page])
    sys.stdout.flush()
    text = raw.getvalue().decode(encoding)
    assert code == 1 and "han-font" in text
    if fmt == "json":
        assert json.loads(text)["pages"][0]["findings"][0]["sample"] == page["groups"][0]["sample"]


def test_clean_keeps_characters_newer_than_this_pythons_tables():
    from cjk_sense.cli import check_lib
    import unicodedata
    unassigned = next(chr(code) for code in range(0x3134F, 0x10FFFF) if unicodedata.category(chr(code)) == "Cn")
    assert check_lib.clean("a" + unassigned + "b") == "a" + unassigned + "b"   # a kanji this Python does not know yet
    assert check_lib.clean("x" * 500, 40) == "x" * 40 and len(check_lib.clean("y" * 500)) == 300


def test_every_page_controlled_field_of_the_text_report_is_cleaned(capsys):
    from cjk_sense.cli import check_lib
    bad = "".join(INVISIBLE)
    report = {"pages": [{"url": "u" + bad, "html_lang": "ja" + bad, "language": "ja", "verdict": "fail", "findings": [
        {"rule": "han-font", "severity": "fail", "message": "m" + bad, "fix": "f" + bad, "share": 0.5, "where": "w" + bad,
         "sample": "s" + bad, "font_family": "ff" + bad, "confirmed_here": True, "used_here": ["used" + bad]}]}],
        "summary": {"pages": 1, "fail": 1, "warn": 0, "ok": 0}}
    text = check_lib.format_text(report)
    assert not any(char in text for char in INVISIBLE)
    assert all(part in text for part in ("m", "fix: f", "confirmed in this browser: used", "font-family: ff"))
