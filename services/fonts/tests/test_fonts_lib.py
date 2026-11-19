import fonts_lib as lib

ANTD_OLD = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"


def test_classify_handles_localised_and_latin_names():
    assert lib.classify("蘋方-簡") == "zh"
    assert lib.classify("PingFang SC") == "zh"
    assert lib.classify("Hiragino Sans GB") == "zh"   # the GB variant is the Chinese one
    assert lib.classify("Hiragino Kaku Gothic ProN") == "ja"
    assert lib.classify(".Hiragino Kaku Gothic Interface") == "ja"
    assert lib.classify("Noto Sans JP") == "ja"
    assert lib.classify("Apple SD Gothic Neo") == "ko"
    assert lib.classify("Inter") is None and lib.classify("Pretendard") is None


def test_parse_stack_strips_quotes_and_blanks():
    assert lib.parse_stack("'PingFang SC', \"Yu Gothic\", , sans-serif") == ["PingFang SC", "Yu Gothic", "sans-serif"]


def test_generic_family_follows_lang_then_system():
    assert lib.resolve("sans-serif", "ja", "mac") == ("ja", None)
    assert lib.resolve("sans-serif", "zh", "windows") == ("zh", None)
    assert lib.resolve("sans-serif", None, "mac") == ("system", None)
    assert lib.resolve("Arial", None, "android") == ("system", None)


def test_named_font_wins_over_lang_where_installed():
    assert lib.resolve("'PingFang SC', 'Hiragino Sans', sans-serif", "ja", "mac") == ("zh", "PingFang SC")
    assert lib.resolve("'PingFang SC', sans-serif", "ja", "windows") == ("ja", None)   # not installed there
    assert lib.resolve("'Hiragino Sans', sans-serif", "zh", "mac") == ("ja", "Hiragino Sans")


def test_old_ant_design_list_breaks_japanese_on_desktop_and_ios():
    assert lib.resolve(ANTD_OLD, "ja", "mac") == ("zh", "PingFang SC")      # -apple-system has no kanji
    assert lib.resolve(ANTD_OLD, "ja", "ios") == ("zh", "PingFang SC")
    assert lib.resolve(ANTD_OLD, "ja", "windows") == ("zh", "Microsoft YaHei")
    assert lib.resolve(ANTD_OLD, "ja", "android") == ("ja", None)           # none of the named fonts exist


def test_generic_before_named_font_stops_only_under_a_cjk_lang():
    assert lib.resolve("sans-serif, 'PingFang SC'", "ja", "mac") == ("ja", None)
    assert lib.resolve("sans-serif, 'PingFang SC'", None, "mac") == ("zh", "PingFang SC")


def test_windows_system_ui_follows_the_display_language():
    assert lib.resolve("system-ui, 'Microsoft YaHei'", "zh", "windows") == ("system", None)
    assert lib.resolve("system-ui, 'PingFang SC'", "ja", "mac") == ("zh", "PingFang SC")


def test_web_fonts_apply_on_every_platform_only_when_loaded():
    for platform in lib.PLATFORMS:
        assert lib.resolve("'Noto Sans SC', sans-serif", "ja", platform, {"Noto Sans SC"}) == ("zh", "Noto Sans SC")
        assert lib.resolve("'Noto Sans JP', 'PingFang SC'", "zh", platform, {"Noto Sans JP"})[0] == "ja"
    assert lib.resolve("'Noto Sans SC', sans-serif", "ja", "android") == ("ja", None)
    assert lib.resolve("'Brand Font', sans-serif", "ja", "mac", {"Brand Font"}) == ("ja", None)
    assert lib.resolve("Pretendard, 'Noto Sans JP'", "ja", "windows", {"Pretendard", "Noto Sans JP"}) == ("ja", "Noto Sans JP")


def test_measured_region_takes_the_majority():
    assert lib.measured_region([["Hiragino Sans", 1], ["Apple SD Gothic Neo", 3]]) == "ko"
    assert lib.measured_region([["Inter", 5]]) is None
    assert lib.measured_region([]) is None


def test_every_table_entry_is_consistent():
    for name, (region, platforms) in lib.INSTALLED.items():
        assert name == name.lower() and region in ("ja", "zh", "ko") and platforms <= set(lib.PLATFORMS)
        assert lib.classify(name) == region, name
    assert set(lib.EXAMPLES) == {"ja", "zh", "ko"}
