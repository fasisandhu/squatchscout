from datetime import datetime
from pathlib import Path

from app.pipeline.crawl import PageBundle, PageText, clean_html
from app.pipeline.extract_regex import extract_contacts, extract_signals

FIX = Path(__file__).parent.parent / "fixtures"


def page(url, html):
    title, meta, text, links, head = clean_html(html)
    return PageText(
        url=url,
        title=title,
        meta_description=meta,
        visible_text=text,
        links=links,
        raw_head=head,
        text_quality="good",
    )


def bundle(*pages):
    return PageBundle(domain="kcdental.com", pages=list(pages), fetched_at=datetime(2026, 1, 1))


def test_signals_from_fixture_site():
    b = bundle(
        page("https://kcdental.com/", (FIX / "site_home.html").read_text(encoding="utf-8")),
        page(
            "https://kcdental.com/contact",
            (FIX / "site_contact.html").read_text(encoding="utf-8"),
        ),
    )
    s = extract_signals(b, current_year=2026)
    assert s.founded_year == 1998 and s.family_owned and s.owner_operated is True
    assert s.owner_name == "Karen Chen"
    assert s.site_builder == "wordpress" and s.has_booking and not s.has_chat
    assert s.copyright_year == 2021 and s.hiring and s.contact_page_found
    assert s.street_address == "12400 West Parmer Lane" and s.postcode == "78727"


def test_contacts_dedupe_and_filter_assets():
    html = (
        "<html><body><p>hello@kcdental.com HELLO@kcdental.com logo@2x.png noreply@sentry.io "
        '(512) 918-0888 512.918.0888 <a href="https://www.instagram.com/kcdental">ig</a></p>'
        "</body></html>"
    )
    out = extract_contacts(bundle(page("https://kcdental.com/", html)), "US")
    kinds = {(c.kind, c.value) for c in out}
    assert ("email", "hello@kcdental.com") in kinds
    assert len([c for c in out if c.kind == "email"]) == 1
    assert ("phone", "+15129180888") in kinds
    assert len([c for c in out if c.kind == "phone"]) == 1
    assert ("social", "https://www.instagram.com/kcdental") in kinds


def test_unknowns_stay_none():
    s = extract_signals(
        bundle(page("https://x.com/", "<html><body><p>Hi.</p></body></html>")), 2026
    )
    assert s.founded_year is None
    assert s.owner_operated is None
    assert s.owner_name is None
    assert s.site_builder is None
