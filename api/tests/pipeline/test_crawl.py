from pathlib import Path

import httpx
import respx

from app.pipeline import crawl as crawl_mod
from app.pipeline.crawl import clean_html, crawl_site

FIX = Path(__file__).parent.parent / "fixtures"
HOME = (FIX / "site_home.html").read_text(encoding="utf-8")
CONTACT = (FIX / "site_contact.html").read_text(encoding="utf-8")


def test_clean_html_strips_boilerplate_and_dedupes_lines():
    title, meta, text, links, head = clean_html(HOME)
    assert title == "KC Dental | Austin Family Dentist"
    assert "since 1998" in meta
    assert "We use cookies" not in text and "var x" not in text and "Home About Contact" not in text
    assert "Family-owned and operated since 1998" in text
    assert "/about-us" in links and "/contact" in links
    assert 'name="generator" content="WordPress' in head


@respx.mock
async def test_crawl_fetches_home_and_linked_contact_pages():
    respx.get("https://kcdental.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://kcdental.com/").mock(return_value=httpx.Response(200, html=HOME))
    respx.get("https://kcdental.com/contact").mock(return_value=httpx.Response(200, html=CONTACT))
    respx.get("https://kcdental.com/about-us").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as c:
        res = await crawl_site("https://kcdental.com", c)
    assert res.status == "ok"
    urls = [p.url for p in res.bundle.pages]
    assert urls[0] == "https://kcdental.com/" and "https://kcdental.com/contact" in urls
    assert len(urls) == 2  # /about-us returned 500 and is excluded
    assert res.bundle.pages[0].text_quality == "good"


@respx.mock
async def test_crawl_respects_robots():
    respx.get("https://blocked.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
    )
    async with httpx.AsyncClient() as c:
        res = await crawl_site("https://blocked.com", c)
    assert res.status == "blocked_by_robots" and res.bundle is None


@respx.mock
async def test_crawl_unreachable_and_thin_pages():
    respx.get("https://down.com/robots.txt").mock(side_effect=httpx.ConnectError("x"))
    respx.get("https://down.com/").mock(side_effect=httpx.ConnectError("x"))
    respx.get("https://thin.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://thin.com/").mock(
        return_value=httpx.Response(200, html="<html><body><div id=root></div></body></html>")
    )
    async with httpx.AsyncClient() as c:
        assert (await crawl_site("https://down.com", c)).status == "unreachable"
        thin = await crawl_site("https://thin.com", c)
    assert thin.status == "ok" and thin.bundle.pages[0].text_quality == "empty"


@respx.mock
async def test_crawl_caps_body_at_max_bytes(monkeypatch):
    real_get = crawl_mod._get
    recorded: list[bytes] = []

    async def recording_get(client, url):
        result = await real_get(client, url)
        if result is not None:
            recorded.append(result[2])
        return result

    monkeypatch.setattr(crawl_mod, "_get", recording_get)

    big_html = "<html><body><p>" + ("x" * 1_500_000) + "</p></body></html>"
    respx.get("https://big.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://big.com/").mock(return_value=httpx.Response(200, html=big_html))
    async with httpx.AsyncClient() as c:
        res = await crawl_site("https://big.com", c)

    assert res.status == "ok"
    assert len(res.bundle.pages[0].visible_text) <= crawl_mod.MAX_TEXT
    # the cap is enforced in _get (on the wire), before _page/clean_html ever see the body
    assert recorded and all(len(body) <= crawl_mod.MAX_BYTES for body in recorded)
    assert max(len(body) for body in recorded) == crawl_mod.MAX_BYTES
