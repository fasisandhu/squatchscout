import re
from datetime import datetime
from typing import Literal
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel
from selectolax.parser import HTMLParser

from app.config import get_settings
from app.models import utcnow
from app.pipeline.normalize import normalize_domain

TIMEOUT = 6.0
MAX_BYTES = 1_000_000
MAX_TEXT = 20_000
MAX_PAGES = 3
SECONDARY_PATHS = ("/contact", "/contact-us", "/about", "/about-us")
STRIP_TAGS = ("script", "style", "nav", "header", "footer", "noscript", "svg", "iframe", "form")
BANNER_HINT = re.compile(r"cookie|consent|gdpr|banner|popup|modal", re.I)


class PageText(BaseModel):
    url: str
    title: str = ""
    meta_description: str = ""
    visible_text: str = ""
    text_quality: Literal["good", "thin", "empty"] = "empty"
    raw_head: str = ""
    links: list[str] = []


class PageBundle(BaseModel):
    domain: str
    pages: list[PageText]
    fetched_at: datetime


class CrawlResult(BaseModel):
    status: Literal["ok", "blocked_by_robots", "unreachable"]
    bundle: PageBundle | None = None


def clean_html(html: str) -> tuple[str, str, str, list[str], str]:
    tree = HTMLParser(html)
    head = tree.head.html if tree.head else ""
    title = tree.css_first("title").text(strip=True) if tree.css_first("title") else ""
    meta_node = tree.css_first('meta[name="description"]')
    meta = meta_node.attributes.get("content", "") if meta_node else ""
    links = [a.attributes.get("href", "") for a in tree.css("a[href]")]
    for tag in STRIP_TAGS:
        for n in tree.css(tag):
            n.decompose()
    for n in tree.css("[class], [id]"):
        ident = f"{n.attributes.get('class', '')} {n.attributes.get('id', '')}"
        if BANNER_HINT.search(ident):
            n.decompose()
    body = tree.body.text(separator="\n") if tree.body else tree.text(separator="\n")
    seen: set[str] = set()
    lines: list[str] = []
    for raw in body.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 2 or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    text = "\n".join(lines)[:MAX_TEXT]
    return title, meta, text, links, head or ""


def quality(text: str) -> Literal["good", "thin", "empty"]:
    n = len(text)
    return "empty" if n < 80 else "thin" if n < 400 else "good"


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    ua = get_settings().user_agent
    for attempt in range(3):
        try:
            r = await client.get(
                url,
                headers={"User-Agent": ua, "Accept": "text/html"},
                timeout=TIMEOUT,
                follow_redirects=True,
            )
            return r
        except httpx.TransportError:
            if attempt == 2:
                return None
    return None


async def _allowed(client: httpx.AsyncClient, base: str) -> bool | None:
    """True/False from robots.txt; treated as allowed if robots.txt itself is unreachable."""
    r = await _get(client, urljoin(base, "/robots.txt"))
    if r is None or r.status_code >= 400:
        return True
    rp = robotparser.RobotFileParser()
    rp.parse(r.text.splitlines())
    return rp.can_fetch(get_settings().user_agent.split("/")[0], base)


def _page(url: str, r: httpx.Response) -> PageText | None:
    ctype = r.headers.get("content-type", "")
    if r.status_code >= 400 or (
        "html" not in ctype and not r.text.lstrip().lower().startswith("<")
    ):
        return None
    html = r.text[:MAX_BYTES]
    title, meta, text, links, head = clean_html(html)
    return PageText(
        url=url,
        title=title,
        meta_description=meta,
        visible_text=text,
        text_quality=quality(text),
        raw_head=head,
        links=links,
    )


async def crawl_site(url: str, client: httpx.AsyncClient) -> CrawlResult:
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}/"
    domain = normalize_domain(url) or parsed.netloc
    if not await _allowed(client, base):
        return CrawlResult(status="blocked_by_robots")
    home = await _get(client, base)
    if home is None:
        return CrawlResult(status="unreachable")
    first = _page(base, home)
    if first is None:
        return CrawlResult(status="unreachable")
    pages = [first]
    wanted = [
        urljoin(base, h)
        for h in first.links
        if urlparse(urljoin(base, h)).path.rstrip("/").lower() in SECONDARY_PATHS
    ]
    seen = {base}
    for u in wanted:
        if len(pages) >= MAX_PAGES or u in seen:
            continue
        seen.add(u)
        r = await _get(client, u)
        p = _page(u, r) if r is not None else None
        if p:
            pages.append(p)
    return CrawlResult(
        status="ok", bundle=PageBundle(domain=domain, pages=pages, fetched_at=utcnow())
    )
