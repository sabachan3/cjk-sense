import json

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
    listing.write_text("# pages\nhttp://a/ja\n\nhttp://b/ja\nhttp://a/ja\n")
    out_file = tmp_path / "report.json"
    code, _, seen = run(capsys, [snapshot("http://a/ja"), snapshot("http://b/ja")], "--urls-file", str(listing),
                        "--out", str(out_file))
    assert code == 0 and seen["urls"] == ["http://a/ja", "http://b/ja"]
    assert json.loads(out_file.read_text())["summary"]["pages"] == 2
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
