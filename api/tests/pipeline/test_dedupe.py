from app.pipeline.dedupe import dedupe_and_flag
from app.pipeline.discover import RawPlace


def P(i, name, **tags):
    return RawPlace(
        osm_type="node",
        osm_id=i,
        name=name,
        lat=30.0,
        lon=-97.0,
        tags={"addr:city": "Austin", **tags},
    )


def test_merges_same_domain_and_same_phone_and_fuzzy_names():
    places = [
        P(1, "KC Dental", website="https://www.kcdental.com"),
        P(2, "K.C. Dental PLLC", website="http://kcdental.com/about"),  # same domain
        P(3, "Austin Dental Works", phone="(512) 555-0100"),
        P(4, "Austin Dental Works Inc", **{"contact:phone": "+1 512 555 0100"}),  # same phone
        P(5, "Lone Star Pediatric Dental"),
        P(6, "Lone Star Pediatric Dental Care"),  # fuzzy >= 90
    ]
    out = dedupe_and_flag(places, "US")
    assert [c.place.osm_id for c in out] == [1, 3, 5]
    assert out[0].domain == "kcdental.com" and out[1].phone_e164 == "+15125550100"


def test_merged_record_keeps_most_tags_and_fills_gaps():
    places = [
        P(1, "KC Dental", website="https://kcdental.com"),
        P(
            2,
            "KC Dental",
            website="https://kcdental.com",
            phone="512-918-0888",
            opening_hours="Mo-Fr",
        ),
    ]
    out = dedupe_and_flag(places, "US")
    assert len(out) == 1 and out[0].place.osm_id == 2 and out[0].phone_e164 == "+15129180888"


def test_chain_detection_by_repetition_and_brand_tag():
    places = [P(i, "Castle Dental") for i in range(3)] + [
        P(9, "Aspen Dental", brand="Aspen Dental"),
        P(10, "KC Dental"),
    ]
    out = dedupe_and_flag(places, "US")
    flags = {c.place.osm_id: c.is_chain_suspected for c in out}
    assert flags[9] is True and flags[10] is False
    assert any(flags[i] for i in (0, 1, 2))  # the surviving Castle Dental is flagged
