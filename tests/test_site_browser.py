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
                page.goto("http://127.0.0.1:8765/grammar/wake-da.html")
                sync.expect(page.locator("main")).to_contain_text("难怪")
                sync.expect(page.locator("main")).to_contain_text("窗户全开着")
                sync.expect(page.locator("body")).not_to_contain_text(hidden_metadata)
                page.goto("http://127.0.0.1:8765/vocab/愛.html")
                sync.expect(page.locator("main")).to_contain_text("爱恋")
                sync.expect(page.locator("main")).to_contain_text("爱就是连梦里都会见到她")
                for kind, meaning_column in (("vocab", 4), ("grammar", 3)):
                    cards = page.request.get(f"http://127.0.0.1:8765/data/{kind}-n3.json").json()
                    dataset = page.request.get(f"http://127.0.0.1:8765/dataset/json/{kind}/n3.json").json()
                    translations = {row['id']: row['zh'] for row in dataset}
                    assert len(cards) == len(translations)
                    for card in cards:
                        assert card[meaning_column].startswith('；'.join(translations[card[0]]['meanings']) + ' / ')
                        assert not hidden_metadata.search(card[meaning_column])
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
                page.locator("#fc-good").click()
                sync.expect(page.locator("#fc-status")).to_contain_text("19 to review · 1 studied · 0 / 674 learned")
                next_word = page.locator("#fc-front").inner_text()
                page.locator('#fc-kind button[data-v="kanji"]').click()
                sync.expect(page.locator("#fc-status")).to_contain_text("N5 kanji")
                page.locator("#fc-flip").click()
                page.locator("#fc-good").click()
                sync.expect(page.locator("#fc-status")).to_contain_text("1 studied")
                next_kanji = page.locator("#fc-front").inner_text()
                page.reload()
                sync.expect(page.locator("#fc-status")).to_contain_text("N5 kanji")
                sync.expect(page.locator("#fc-front")).to_have_text(next_kanji)
                sync.expect(page.locator("#fc-status")).to_contain_text("19 to review · 1 studied")
                page.locator('#fc-kind button[data-v="vocab"]').click()
                sync.expect(page.locator("#fc-front")).to_have_text(next_word)
                sync.expect(page.locator("#fc-status")).to_contain_text("19 to review · 1 studied")
                page.locator("#fc-flip").click()
                page.reload()
                sync.expect(page.locator("#fc-front")).to_have_text(next_word)
                sync.expect(page.locator("#fc-card")).to_have_class(re.compile("flipped"))
                sync.expect(page.locator("#fc-status")).to_contain_text("19 to review · 1 studied")
                page.locator("#fc-again").click()
                sync.expect(page.locator("#fc-status")).to_contain_text("19 to review · 2 studied")
                forgotten_session = page.evaluate("localStorage.getItem('openjlpt:fc:vocab:N5:session')")
                page.reload()
                sync.expect(page.locator("#fc-status")).to_contain_text("19 to review · 2 studied")
                assert page.evaluate("localStorage.getItem('openjlpt:fc:vocab:N5:session')") == forgotten_session
                # A completed session stays completed rather than adding 20 new cards.
                page.evaluate("localStorage.setItem('openjlpt:fc:vocab:N5:session', JSON.stringify({day:new Date().toDateString(),ids:[],done:20,flipped:false}))")
                page.reload()
                sync.expect(page.locator("#fc-back")).to_contain_text("Session complete!")
                page.on("dialog", lambda dialog: dialog.accept())
                page.locator("#fc-reset").click()
                sync.expect(page.locator("#fc-status")).to_contain_text("20 to review · 0 studied")
                page.locator('#fc-kind button[data-v="kanji"]').click()
                sync.expect(page.locator("#fc-status")).to_contain_text("19 to review · 1 studied")
                page.locator('#fc-kind button[data-v="vocab"]').click()
                sync.expect(page.locator("#fc-status")).to_contain_text("N5 words")
                # A late response for another level must not overwrite the active deck.
                delayed = []
                page.route("**/data/vocab-n4.json", lambda route: delayed.append(route))
                page.locator('#fc-level button[data-v="N4"]').click()
                sync.expect(page.locator("#fc-status")).to_have_text("Loading…")
                page.locator('#fc-level button[data-v="N5"]').click()
                sync.expect(page.locator("#fc-status")).to_contain_text("N5 words")
                assert delayed
                delayed[0].fulfill(json=[['wrong-deck', 'WRONG', '', '', '', '', '', '']])
                page.wait_for_timeout(100)
                sync.expect(page.locator("#fc-front")).not_to_have_text("WRONG")
                sync.expect(page.locator("#fc-status")).to_contain_text("0 / 674 learned")
                # Deterministic random draws make ordering assertions non-flaky.
                page.evaluate("Math.random = () => 0")
                session_key = 'openjlpt:fc:vocab:N5:session'
                before_shuffle = page.evaluate("key => JSON.parse(localStorage.getItem(key))", session_key)
                progress_before = page.evaluate("localStorage.getItem('openjlpt:fc:vocab:N5')")
                page.locator('#fc-shuffle').check()
                shuffled = page.evaluate("key => JSON.parse(localStorage.getItem(key))", session_key)
                assert shuffled['ids'][0] == before_shuffle['ids'][0]
                assert shuffled['ids'][1:] != before_shuffle['ids'][1:]
                assert sorted(shuffled['ids']) == sorted(before_shuffle['ids'])
                assert shuffled['done'] == before_shuffle['done']
                assert page.evaluate("localStorage.getItem('openjlpt:fc:vocab:N5')") == progress_before
                page.reload()
                sync.expect(page.locator('#fc-shuffle')).to_be_checked()
                sync.expect(page.locator('#fc-status')).to_contain_text('N5 words')
                assert page.evaluate("key => JSON.parse(localStorage.getItem(key))", session_key) == shuffled
                page.locator('#fc-kind button[data-v="kanji"]').click()
                sync.expect(page.locator('#fc-status')).to_contain_text('N5 kanji')
                page.locator('#fc-kind button[data-v="vocab"]').click()
                sync.expect(page.locator('#fc-status')).to_contain_text('N5 words')
                assert page.evaluate("key => JSON.parse(localStorage.getItem(key))", session_key) == shuffled
                page.locator('#fc-shuffle').uncheck()
                ordered = page.evaluate("key => JSON.parse(localStorage.getItem(key))", session_key)
                assert ordered['ids'] == before_shuffle['ids']
                page.evaluate("Math.random = () => 0")
                page.locator('#fc-shuffle').check()
                page.locator('#fc-level button[data-v="N3"]').click()
                sync.expect(page.locator('#fc-status')).to_contain_text('N3 words')
                new_session = page.evaluate("JSON.parse(localStorage.getItem('openjlpt:fc:vocab:N3:session'))")
                source_rows = page.request.get('http://127.0.0.1:8765/data/vocab-n3.json').json()
                assert len(new_session['ids']) == len(set(new_session['ids'])) == 20
                assert set(new_session['ids']) != {row[0] for row in source_rows[:20]}
                assert not errors, errors
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
