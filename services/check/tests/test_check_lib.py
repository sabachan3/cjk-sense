import check_lib as lib

PLATFORMS = ("mac", "windows")


def group(chars=100, mac=("ja", None), windows=("ja", None), measured="ja", lang="ja", **extra):
    return {"stack": "'PingFang SC', sans-serif", "lang": lang, "lang_region": lang if lang in lib.CJK else None,
            "chars": chars, "sample": "設定を保存", "where": "p.lead", "fonts": [["PingFang SC", chars]],
            "measured": measured, "predicted": {"mac": list(mac), "windows": list(windows)}, **extra}


def page(groups=(), detected="ja", html_lang="ja", **extra):
    declared = {"ja": "ja", "zh": "zh", "ko": "ko", "en": "latin"}.get((html_lang or "").split("-")[0])
    return {"url": "http://x/ja", "html_lang": html_lang, "detected": detected, "declared_class": declared,
            "html_region": declared if declared in lib.CJK else None, "expect": None, "expect_class": None,
            "groups": list(groups), **extra}


def rules(result):
    return [(finding["rule"], finding["severity"]) for finding in result["findings"]]


def test_clean_page_is_ok():
    result = lib.check_page(page([group()]), PLATFORMS)
    assert result["verdict"] == "ok" and result["findings"] == [] and result["language"] == "ja"


def test_named_chinese_font_fails_and_names_the_font_and_platforms():
    result = lib.check_page(page([group(mac=("zh", "PingFang SC"), measured="zh")]), PLATFORMS)
    (finding,) = result["findings"]
    assert result["verdict"] == "fail" and finding["rule"] == "han-font"
    assert finding["platforms"] == ["mac"] and finding["font"] == "PingFang SC" and finding["share"] == 1.0
    assert "kanji drawn in a Chinese font on mac" in finding["message"] and '"PingFang SC" comes before' in finding["message"]
    assert ":lang(ja)" in finding["fix"] and finding["confirmed_here"] and finding["used_here"] == ["PingFang SC"]


def test_every_deciding_font_is_named_when_platforms_differ():
    both = group(mac=("zh", "PingFang SC"), windows=("zh", "Microsoft YaHei"))
    (finding,) = lib.check_page(page([both]), PLATFORMS)["findings"]
    assert finding["fonts"] == ["PingFang SC", "Microsoft YaHei"] and finding["font"] == "PingFang SC"
    assert '"PingFang SC", "Microsoft YaHei" come before' in finding["message"]
    assert 'remove "PingFang SC", "Microsoft YaHei"' in finding["fix"]


def test_wrong_lang_on_the_text_is_reported_as_a_lang_cause():
    result = lib.check_page(page([group(mac=("zh", None), windows=("zh", None), measured="zh", lang="zh")],
                                 html_lang="zh"), PLATFORMS)
    assert rules(result) == [("lang-mismatch", "fail"), ("han-font", "fail")]
    font = result["findings"][1]
    assert font["platforms"] == ["mac", "windows"] and font["font"] is None
    assert 'under lang="zh"' in font["message"] and 'set lang="ja"' in font["fix"]


def test_small_share_warns_and_tiny_share_is_ignored():
    warn = lib.check_page(page([group(900), group(100, mac=("zh", "PingFang SC"))]), PLATFORMS)
    assert warn["verdict"] == "warn" and warn["findings"][0]["share"] == 0.1
    assert lib.check_page(page([group(995), group(5, mac=("zh", "PingFang SC"))]), PLATFORMS)["verdict"] == "ok"
    assert lib.check_page(page([group(5000), group(50, mac=("zh", "PingFang SC"))]), PLATFORMS)["verdict"] == "ok"


def test_marked_chinese_passage_inside_a_japanese_page_is_not_a_defect():
    quoted = group(400, mac=("zh", None), windows=("zh", None), measured="zh", lang="zh")
    assert lib.check_page(page([group(600), quoted]), PLATFORMS)["verdict"] == "ok"


def test_measured_only_defect_is_reported_for_this_browser():
    result = lib.check_page(page([group(measured="zh")]), PLATFORMS)
    (finding,) = result["findings"]
    assert finding["platforms"] == [] and "in this browser" in finding["message"] and "PingFang SC" in finding["message"]


def test_system_dependent_text_is_not_a_font_defect():
    result = lib.check_page(page([group(mac=("system", None), windows=("system", None), lang="en")], html_lang="en"),
                            PLATFORMS)
    assert rules(result) == [("lang-mismatch", "fail")]
    assert 'lang="en"' in result["findings"][0]["message"] and "Japanese" in result["findings"][0]["message"]


def test_chinese_page_drawn_with_a_japanese_font_is_the_mirror_case():
    result = lib.check_page(page([group(mac=("ja", "Hiragino Sans"), lang="zh")], detected="zh", html_lang="zh"), PLATFORMS)
    assert result["verdict"] == "fail" and "hanzi drawn in a Japanese font" in result["findings"][0]["message"]


def test_lang_missing_warns_and_non_cjk_pages_skip_the_font_rule():
    assert rules(lib.check_page(page([group()], html_lang=None), PLATFORMS)) == [("lang-missing", "warn")]
    latin = lib.check_page(page([group(mac=("zh", "PingFang SC"))], detected="latin", html_lang="en"), PLATFORMS)
    assert latin["verdict"] == "ok"


def test_unknown_language_or_uncheckable_lang_raises_nothing():
    assert lib.check_page(page([], detected=None, html_lang="en"), PLATFORMS)["verdict"] == "ok"
    assert lib.check_page(page([group()], html_lang="sr"), PLATFORMS)["verdict"] == "ok"


def test_expect_reports_an_untranslated_page():
    result = lib.check_page(page([], detected="latin", html_lang="ja", expect="ja", expect_class="ja"), PLATFORMS)
    assert rules(result) == [("wrong-language", "fail"), ("lang-mismatch", "fail")]


def test_few_han_characters_are_not_judged():
    assert lib.check_page(page([group(5, mac=("zh", "PingFang SC"))]), PLATFORMS)["verdict"] == "ok"


def test_at_most_five_font_findings_largest_first():
    groups = [group(100 + index, mac=("zh", "PingFang SC"), stack=f"f{index}") for index in range(8)]
    findings = lib.check_page(page(groups), PLATFORMS)["findings"]
    assert len(findings) == lib.MAX_FONT_FINDINGS and findings[0]["chars"] == 107


def test_error_page_fails():
    result = lib.check_page({"url": "http://x", "error": "TimeoutError: slow"}, PLATFORMS)
    assert result["verdict"] == "fail" and rules(result) == [("page-error", "fail")]


def test_report_summary_and_exit_codes():
    pages = [lib.check_page(page([group()]), PLATFORMS), lib.check_page(page([group()], html_lang=None), PLATFORMS),
             lib.check_page(page([group(mac=("zh", "PingFang SC"))]), PLATFORMS)]
    report = lib.build_report(pages, PLATFORMS)
    assert report["summary"] == {"pages": 3, "fail": 1, "warn": 1, "ok": 1} and report["version"] == 1
    assert lib.exit_code(report, "fail") == 1 and lib.exit_code(report, "never") == 0
    warn_only = lib.build_report(pages[:2], PLATFORMS)
    assert lib.exit_code(warn_only, "fail") == 0 and lib.exit_code(warn_only, "warn") == 1


def test_text_output_strips_terminal_control_characters():
    escape, override = chr(0x1b), chr(0x202e)
    bad = group(mac=("zh", "PingFang SC"), sample=f"設定{escape}[2J{override}保存", where=f"p{escape}[31m")
    report = lib.build_report([lib.check_page(page([bad]), PLATFORMS)], PLATFORMS)
    text = lib.format_text(report)
    assert escape not in text and override not in text
    assert "FAIL http://x/ja" in text and "1 page(s): 1 fail, 0 warn, 0 ok" in text and "fix:" in text
