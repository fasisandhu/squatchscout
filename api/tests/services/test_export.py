import csv
import io

from app.schemas import AddressOut, ContactOut, FactorScoreOut, LeadOut, SignalOut
from app.services.export import HUBSPOT_COLUMNS, to_csv, to_hubspot_csv

W = {"reachability": 25, "establishment": 20, "digital_gap": 20, "buybox": 20, "succession": 15}


def lead(**over):
    base = dict(
        id="L1",
        name="KC DENTAL",
        display_name="KC Dental",
        lat=1.0,
        lon=2.0,
        website="https://kcdental.com",
        domain="kcdental.com",
        is_chain_suspected=False,
        enrichment_status="ok",
        llm_status="done",
        score=81.5,
        tier="A",
        address=AddressOut(
            street="12400 W Parmer Ln",
            housenumber=None,
            city="Austin",
            state="TX",
            postcode="78727",
            country="US",
        ),
        address_source="llm",
        contacts=[
            ContactOut(
                kind="email",
                value="hello@kcdental.com",
                source="website",
                verification_status="verified",
            ),
            ContactOut(
                kind="phone", value="+15129180888", source="osm", verification_status="valid"
            ),
        ],
        signals=[
            SignalOut(key="founded_year", value="1998", source="regex", confidence=1.0),
            SignalOut(key="owner_operated", value="true", source="llm", confidence=0.9),
        ],
        factor_scores=[
            FactorScoreOut(
                factor="reachability",
                points=25,
                max_points=25,
                reasons=["verified email (MX ok) +12"],
            ),
            FactorScoreOut(
                factor="establishment", points=20, max_points=20, reasons=["founded 1998"]
            ),
            FactorScoreOut(
                factor="digital_gap", points=10, max_points=20, reasons=["no chat widget +3"]
            ),
            FactorScoreOut(factor="buybox", points=20, max_points=20, reasons=["independent"]),
            FactorScoreOut(factor="succession", points=15, max_points=15, reasons=["owner named"]),
        ],
    )
    return LeadOut(**{**base, **over})


def test_generic_csv_has_comment_header_and_flat_columns():
    out = to_csv([lead()], W)
    first, rest = out.split("\n", 1)
    assert first.startswith("# SquatchScout export")
    assert "weights R/E/D/B/S=25/20/20/20/15" in first
    assert "OpenStreetMap" in first
    rows = list(csv.DictReader(io.StringIO(rest)))
    assert rows[0]["display_name"] == "KC Dental"
    assert rows[0]["emails"] == "hello@kcdental.com"
    assert rows[0]["phones"] == "+15129180888"
    assert rows[0]["founded_year"] == "1998"
    assert rows[0]["tier"] == "A"


def test_hubspot_csv_columns_and_attribution_column():
    out = to_hubspot_csv([lead()], W)
    rows = list(csv.DictReader(io.StringIO(out)))
    assert list(rows[0].keys()) == HUBSPOT_COLUMNS
    r = rows[0]
    assert r["Company name"] == "KC Dental"
    assert r["Company Domain Name"] == "kcdental.com"
    assert r["Phone Number"] == "+15129180888"
    assert r["Street Address"] == "12400 W Parmer Ln"
    assert r["State/Region"] == "TX"
    assert r["Postal Code"] == "78727"
    assert "verified email" in r["Description"]
    assert "; " in r["Description"]
    assert r["Verified Email"] == "hello@kcdental.com"
    assert r["Founded Year"] == "1998"
    assert r["Owner Operated"] == "true"
    assert "OpenStreetMap" in r["Data Sources"]
    assert "25/20/20/20/15" in r["Data Sources"]
    assert not out.startswith("#")  # HubSpot's importer does not skip comment rows


def test_score_recomputed_from_weights():
    heavy = {
        "reachability": 100,
        "establishment": 0,
        "digital_gap": 0,
        "buybox": 0,
        "succession": 0,
    }
    rows = list(csv.DictReader(io.StringIO(to_hubspot_csv([lead()], heavy))))
    assert rows[0]["SquatchScout Score"] == "100.0"
    assert rows[0]["Tier"] == "A"
