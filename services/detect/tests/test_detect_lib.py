import detect_lib as lib

JA = "これは日本語のページです。設定を保存しました。" * 3
ZH = "这是一个中文页面。设置已保存。请稍后再试。" * 3
KO = "이것은 한국어 페이지입니다. 설정이 저장되었습니다." * 3
EN = "This is an English page. Your settings have been saved. " * 3


def detect(text):
    return lib.detect(lib.count_scripts(text))


def test_cjk_languages_are_told_apart():
    assert detect(JA) == "ja"
    assert detect(ZH) == "zh"
    assert detect(KO) == "ko"


def test_other_scripts_resolve_to_the_script():
    assert detect(EN) == "latin"
    assert detect("Это страница на русском языке. Настройки сохранены. " * 3) == "cyrillic"
    assert detect("هذه صفحة باللغة العربية. تم حفظ الإعدادات. " * 3) == "arabic"


def test_too_little_text_gives_no_answer():
    assert detect("設定") is None
    assert detect("") is None
    assert detect("OK 12345 !!!") is None


def test_japanese_ui_with_brand_names_and_code_is_still_japanese():
    assert detect(JA + " GitHub Actions workflow README.md npm install " * 4) == "ja"


def test_quotation_does_not_flip_the_page():
    # a Japanese paragraph on an English page: not Japanese, and not confidently Latin either
    assert detect(EN * 20 + "こんにちは、ありがとうございます、よろしくお願いします。") is None
    assert detect(EN * 20 + " 日本語 中文 한국어") == "latin"      # a language menu changes nothing
    # a Chinese page that quotes one Japanese sentence stays Chinese
    assert detect(ZH * 10 + "ありがとうございます、よろしくお願いします。") == "zh"


def test_kanji_heavy_japanese_needs_enough_kana():
    assert detect("東京都千代田区永田町一丁目七番一号 国会議事堂 参議院 衆議院 本会議 委員会 議事録 検索 " * 3) == "zh"
    assert detect("東京都の天気を表示します。国会議事堂の見学について案内します。" * 3) == "ja"


def test_language_class_and_region():
    assert lib.language_class("ja-JP") == "ja"
    assert lib.language_class("zh_Hant") == "zh"
    assert lib.language_class("EN-us") == "latin"
    assert lib.language_class("ru") == "cyrillic"
    assert lib.language_class("sr") is None      # written in two scripts: not checkable
    assert lib.language_class("") is None and lib.language_class(None) is None
    assert lib.cjk_region("ko-KR") == "ko" and lib.cjk_region("en") is None


def test_describe():
    assert lib.describe("ja") == "Japanese" and lib.describe("latin") == "Latin script" and lib.describe(None) == "unknown"
