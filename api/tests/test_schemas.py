from app.models import Contact, Lead, Signal, new_id
from app.pipeline.industries import INDUSTRIES
from app.schemas import build_facts, lead_to_out


def make_lead(**over):
    base = dict(
        id=new_id(),
        search_id="s",
        osm_type="node",
        osm_id=1,
        name="Dental Clinic",
        display_name="Dental Clinic",
        normalized_name="dental clinic",
        lat=1.0,
        lon=2.0,
        website="https://x.com",
        normalized_domain="x.com",
        street="1 Main St",
        city="Austin",
        enrichment_status="ok",
        is_chain_suspected=False,
        osm_tags={
            "addr:housenumber": "1",
            "addr:street": "Main St",
            "addr:city": "Austin",
            "addr:postcode": "78701",
            "opening_hours": "Mo-Fr",
            "phone": "+15125550100",
        },
    )
    return Lead(**{**base, **over})


def test_build_facts_maps_rows_to_flat_facts():
    lead = make_lead()
    contacts = [
        Contact(
            lead_id=lead.id,
            kind="email",
            value="a@x.com",
            normalized_value="a@x.com",
            source="website",
            verification_status="unverified",
        ),
        Contact(
            lead_id=lead.id,
            kind="email",
            value="b@x.com",
            normalized_value="b@x.com",
            source="website",
            verification_status="verified",
        ),
        Contact(
            lead_id=lead.id,
            kind="phone",
            value="+15125550100",
            normalized_value="+15125550100",
            source="osm",
            verification_status="valid",
        ),
    ]
    signals = [
        Signal(lead_id=lead.id, key="founded_year", value="1998", source="regex"),
        Signal(lead_id=lead.id, key="owner_name", value="Karen Chen", source="llm", confidence=0.9),
        Signal(lead_id=lead.id, key="family_owned", value="true", source="regex"),
        Signal(lead_id=lead.id, key="site_builder", value="wix", source="regex"),
        Signal(lead_id=lead.id, key="copyright_year", value="2021", source="regex"),
        Signal(lead_id=lead.id, key="contact_page_found", value="true", source="regex"),
    ]
    f = build_facts(lead, contacts, signals, INDUSTRIES["dentist"])
    assert f.best_email_status == "verified" and f.best_phone_status == "valid"
    assert (
        f.founded_year == 1998
        and f.owner_name_found
        and f.family_owned
        and f.owner_operated is True
    )
    assert (
        f.osm_full_address and f.osm_opening_hours and f.osm_has_contact and f.has_physical_address
    )
    assert f.site_builder == "wix" and f.copyright_year == 2021 and f.contact_page_found
    assert f.generic_name is True  # "Dental Clinic" is a category word
    assert f.has_website and f.site_reachable


def test_lead_to_out_shape():
    lead = make_lead()
    out = lead_to_out(lead, [], [], [])
    d = out.model_dump()
    assert d["address"] == {
        "street": "1 Main St",
        "housenumber": None,
        "city": "Austin",
        "state": None,
        "postcode": None,
        "country": None,
    }
    assert d["domain"] == "x.com" and d["contacts"] == [] and d["factor_scores"] == []
