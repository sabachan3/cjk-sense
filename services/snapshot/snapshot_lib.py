"""Open a page in Chromium and record what the checks need: text, lang, font lists, fonts used.

The output is the page snapshot described in contracts/README.md. Playwright is imported only
inside the functions that drive a browser, so the rest of the package works without it.
"""

from __future__ import annotations

MAX_TEXT = 200_000
MAX_GROUPS = 40

EXTRACT = r"""
([maxText, maxGroups]) => {
  const HAN = /[\u3400-\u4dbf\u4e00-\u9fff]/g;
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'TEXTAREA', 'OPTION', 'SELECT', 'TITLE']);
  const where = el => {
    const id = el.id ? '#' + el.id : '';
    const cls = typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return (el.tagName.toLowerCase() + id + cls).slice(0, 80);
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const groups = new Map(), parts = [];
  let node, size = 0, next = 0;
  while ((node = walker.nextNode())) {
    const text = node.nodeValue, el = node.parentElement;
    if (!el || SKIP.has(el.tagName) || !text.trim()) continue;
    if (!el.getClientRects().length) continue;
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden') continue;
    if (size < maxText) { parts.push(text); size += text.length; }
    const han = text.match(HAN);
    if (!han) continue;
    const holder = el.closest('[lang]');
    const lang = holder ? holder.getAttribute('lang') : '';
    const key = style.fontFamily + '\u0000' + lang;
    let group = groups.get(key);
    if (!group) {
      if (groups.size >= maxGroups) continue;
      group = {stack: style.fontFamily, lang, chars: 0, sample: text.trim().slice(0, 40), where: where(el), probe: 'p' + (next++)};
      groups.set(key, group);
      const span = document.createElement('span');
      span.setAttribute('data-cjk-sense-probe', group.probe);
      span.textContent = [...new Set(han)].slice(0, 12).join('');
      el.appendChild(span);
    }
    group.chars += han.length;
  }
  const webfonts = [...new Set([...document.fonts].filter(f => f.status === 'loaded')
    .map(f => f.family.replace(/["']/g, '')))];
  return {html_lang: document.documentElement.getAttribute('lang'), text: parts.join('\n').slice(0, maxText),
          groups: [...groups.values()], webfonts};
}
"""
REMOVE_PROBES = "() => document.querySelectorAll('[data-cjk-sense-probe]').forEach(e => e.remove())"


async def inspect(page) -> dict:
    """Snapshot of the page currently loaded in a Playwright `page` (without url fields)."""
    data = await page.evaluate(EXTRACT, [MAX_TEXT, MAX_GROUPS])
    session = await page.context.new_cdp_session(page)
    try:
        await session.send("DOM.enable")
        await session.send("CSS.enable")
        root = (await session.send("DOM.getDocument"))["root"]["nodeId"]
        for group in data["groups"]:
            probe = group.pop("probe")
            try:
                node = await session.send("DOM.querySelector",
                                          {"nodeId": root, "selector": f'[data-cjk-sense-probe="{probe}"]'})
                found = await session.send("CSS.getPlatformFontsForNode", {"nodeId": node["nodeId"]})
                group["fonts"] = [[font["familyName"], font["glyphCount"]] for font in found["fonts"]]
            except Exception:  # the probe sits in an element the browser never lays out
                group["fonts"] = []
    finally:
        await session.detach()
        await page.evaluate(REMOVE_PROBES)
    data["groups"].sort(key=lambda group: -group["chars"])
    return data


async def take(browser, url: str, locale: str | None = None, timeout: int = 30000, wait: int = 0) -> dict:
    """Load `url` in a fresh context and return its snapshot, or {"url", "error"} when it fails."""
    options = {"viewport": {"width": 1280, "height": 900}, **({"locale": locale} if locale else {})}
    context = await browser.new_context(**options)
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass  # pages that never go idle are inspected as they stand
        if wait:
            await page.wait_for_timeout(wait)
        await page.evaluate("() => document.fonts.ready.then(() => true)")
        return {"url": url, "final_url": page.url, **(await inspect(page))}
    except Exception as error:
        return {"url": url, "error": f"{type(error).__name__}: {str(error).splitlines()[0][:200]}"}
    finally:
        await context.close()


async def take_all(urls: list[str], locale: str | None = None, channel: str | None = None,
                   timeout: int = 30000, wait: int = 0, workers: int = 4) -> list[dict]:
    """Snapshots for all urls, in order."""
    import asyncio

    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel=channel)
        gate = asyncio.Semaphore(workers)

        async def one(url: str) -> dict:
            async with gate:
                return await take(browser, url, locale, timeout, wait)

        try:
            return list(await asyncio.gather(*(one(url) for url in urls)))
        finally:
            await browser.close()
