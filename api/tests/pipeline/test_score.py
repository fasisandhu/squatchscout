import json
from pathlib import Path

import pytest

from app.pipeline.score import (
    MAX_POINTS,
    WEIGHT_PRESETS,
    LeadFacts,
    score,
    tier,
    total,
)

GOLD = json.loads((Path(__file__).parent.parent / "fixtures/golden_scores.json").read_text())


def facts(**over) -> LeadFacts:
    base = dict(
        industry_key="dentist",
        has_website=True,
        site_reachable=True,
        contact_page_found=True,
        best_email_status="verified",
        best_phone_status="valid",
        founded_year=1998,
        owner_name_found=True,
        owner_operated=True,
        family_owned=True,
        is_chain_suspected=False,
        has_physical_address=True,
        osm_full_address=True,
        osm_opening_hours=True,
        osm_has_contact=True,
        site_builder="wix",
        has_booking=False,
        has_chat=False,
        copyright_year=2021,
        generic_name=False,
    )
    return LeadFacts(**{**base, **over})


def test_ideal_lead_maxes_every_factor_except_digital_gap_partial():
    fs = {f.factor: f for f in score(facts(), reference_year=2026)}
    assert fs["reachability"].points == 25 and fs["establishment"].points == 20
    assert fs["buybox"].points == 20 and fs["succession"].points == 15
    assert fs["digital_gap"].points == 7 + 5 + 3 + 5  # wix, no booking, no chat, stale ©
    assert any("verified email" in r for r in fs["reachability"].reasons)


def test_no_website_is_full_digital_gap_but_hurts_reachability():
    fs = {
        f.factor: f
        for f in score(
            facts(
                has_website=False,
                site_reachable=False,
                contact_page_found=False,
                best_email_status="none",
                site_builder=None,
                copyright_year=None,
            ),
            reference_year=2026,
        )
    }
    assert fs["digital_gap"].points == 20 and fs["reachability"].points == 8


def test_chain_and_generic_name_lose_buybox_points():
    fs = {
        f.factor: f
        for f in score(facts(is_chain_suspected=True, generic_name=True), reference_year=2026)
    }
    assert fs["buybox"].points == 4  # address only


def test_total_tier_and_weights():
    fs = score(facts(), reference_year=2026)
    t = total(fs, WEIGHT_PRESETS["balanced"])
    assert t == 100.0
    assert (
        tier(70) == "A"
        and tier(69.9) == "B"
        and tier(55) == "B"
        and tier(40) == "C"
        and tier(39.9) == "D"
    )
    heavy = total(
        fs,
        {"reachability": 100, "establishment": 0, "digital_gap": 0, "buybox": 0, "succession": 0},
    )
    assert heavy == 100.0
    assert sum(WEIGHT_PRESETS["succession"].values()) == 100


@pytest.mark.parametrize("case", GOLD["cases"], ids=[c["name"] for c in GOLD["cases"]])
def test_golden_cases(case):
    fs = score(LeadFacts(**case["facts"]), reference_year=GOLD["reference_year"])
    got = {f.factor: f.points for f in fs}
    assert got == case["expected_points"]
    assert total(fs, WEIGHT_PRESETS["balanced"]) == pytest.approx(
        case["expected_total_balanced"], abs=0.05
    )
    assert tier(total(fs, WEIGHT_PRESETS["balanced"])) == case["expected_tier"]
    assert {f.factor: f.max_points for f in fs} == MAX_POINTS
