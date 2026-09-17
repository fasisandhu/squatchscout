from pathlib import Path

import httpx
import respx

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
