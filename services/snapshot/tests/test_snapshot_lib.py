import asyncio

import snapshot_lib as lib


class FakeSession:
    def __init__(self, fonts):
        self.fonts, self.detached = fonts, False

    async def send(self, method, params=None):
        if method == "DOM.getDocument":
            return {"root": {"nodeId": 1}}
        if method == "DOM.querySelector":
            probe = params["selector"].split('"')[1]
            if probe not in self.fonts:
                raise RuntimeError("no node")
            return {"nodeId": probe}
        if method == "CSS.getPlatformFontsForNode":
            return {"fonts": [{"familyName": family, "glyphCount": count} for family, count in self.fonts[params["nodeId"]]]}
        return {}

    async def detach(self):
        self.detached = True


class FakePage:
    def __init__(self, data, fonts):
        self.data, self.session, self.scripts = data, FakeSession(fonts), []
        self.context = self

    async def evaluate(self, script, argument=None):
        self.scripts.append(script)
        return self.data if script == lib.EXTRACT else None

    async def new_cdp_session(self, page):
        return self.session


def test_inspect_attaches_fonts_sorts_groups_and_cleans_up():
    data = {"html_lang": "ja", "text": "x", "webfonts": [], "groups": [
        {"stack": "a", "lang": "", "chars": 2, "sample": "s", "where": "p", "probe": "p0"},
        {"stack": "b", "lang": "ja", "chars": 9, "sample": "s", "where": "p", "probe": "p1"},
        {"stack": "c", "lang": "ja", "chars": 5, "sample": "s", "where": "p", "probe": "p2"}]}
    page = FakePage(data, {"p0": [("PingFang SC", 2)], "p1": [("Hiragino Sans", 9)]})
    result = asyncio.run(lib.inspect(page))
    assert [group["stack"] for group in result["groups"]] == ["b", "c", "a"]
    assert result["groups"][0]["fonts"] == [["Hiragino Sans", 9]]
    assert result["groups"][1]["fonts"] == []          # the probe was never laid out
    assert all("probe" not in group for group in result["groups"])
    assert page.session.detached and page.scripts[-1] == lib.REMOVE_PROBES


def test_page_script_keeps_its_escapes_and_limits():
    # the script must stay ASCII: literal CJK ranges in a regex are easy to corrupt unnoticed
    assert lib.EXTRACT.isascii()
    assert "data-cjk-sense-probe" in lib.EXTRACT and "data-cjk-sense-probe" in lib.REMOVE_PROBES
    assert lib.MAX_GROUPS > 0 and lib.MAX_TEXT > 0
