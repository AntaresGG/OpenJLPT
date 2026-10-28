"""Opt-in browser checks for a built site (OPENJLPT_SITE); no external session is used."""
import functools
import os
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("OPENJLPT_SITE"), reason="Set OPENJLPT_SITE to a built static site")


def test_site_chinese_search_downloads_and_mobile():
    sync = pytest.importorskip("playwright.sync_api")
    site = Path(os.environ["OPENJLPT_SITE"]).resolve()
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", 8765), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync.sync_playwright() as pw:
            kwargs = {"headless": True}
            if os.environ.get("OPENJLPT_CHROMIUM"):
                kwargs["executable_path"] = os.environ["OPENJLPT_CHROMIUM"]
            browser = pw.chromium.launch(**kwargs)
            try:
                page = browser.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto("http://127.0.0.1:8765/")
                hidden_metadata = re.compile("中文试点版|正式稿|审校|已审核|初稿|待复核")
                sync.expect(page.locator("body")).not_to_contain_text(hidden_metadata)
                page.locator("#q").fill("肥皂")
                result = page.locator("#results a").first
                sync.expect(result).to_contain_text("せっけん")
                sync.expect(result).not_to_contain_text(hidden_metadata)
                result.click()
                sync.expect(page.locator("body")).not_to_contain_text(hidden_metadata)
                sync.expect(page.locator("main")).to_contain_text("我用肥皂洗了手")
                page.goto("http://127.0.0.1:8765/grammar/te-oku.html")
                sync.expect(page.locator("main")).to_contain_text("事先做好")
                sync.expect(page.locator("main")).to_contain_text("请让空调保持开着")
                page.goto("http://127.0.0.1:8765/grammar/sou-da-hearsay.html")
                sync.expect(page.locator("body")).not_to_contain_text(hidden_metadata)
                sync.expect(page.locator("main")).to_contain_text("天气预报说明天会下雪")
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.goto("http://127.0.0.1:8765/data.html")
                links = page.locator('a[href*="/dataset/"], a[href*="/downloads/"]')
                urls = set(links.evaluate_all("(items) => items.map(x => x.href)"))
                assert urls
                for url in urls:
                    assert url.startswith("http://127.0.0.1:8765/"), url
                    response = page.request.get(url)
                    assert response.status == 200, url
                page.goto("http://127.0.0.1:8765/flashcards.html")
                sync.expect(page.locator("#fc-front")).not_to_be_empty()
                page.locator("#fc-flip").click()
                sync.expect(page.locator("body")).not_to_contain_text(hidden_metadata)
                assert not errors, errors
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
