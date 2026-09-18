from app.llm.schemas import ExtractionResult, LLMAddress


def test_validation_drops_ungrounded_and_out_of_range_fields():
    raw = ExtractionResult(
        display_name="Totally Different Co",
        founded_year=1799,
        owner_name="Jane Doe",
        services=["a"] * 12,
        address=LLMAddress(postcode="ABCDE"),
        confidence=1.7,
    )
    v = raw.validated(
        source_text="KC Dental — family owned since 1998. Dr. Karen Chen, owner.",
        osm_name="KC Dental",
        country_code="US",
        current_year=2026,
    )
    assert v.display_name is None and v.founded_year is None and v.owner_name is None
    assert len(v.services) == 8 and v.address.postcode is None and v.confidence == 1.0


def test_validation_keeps_grounded_fields():
    raw = ExtractionResult(
        display_name="KC Dental PLLC",
        founded_year=1998,
        owner_name="Karen Chen",
        address=LLMAddress(postcode="78727"),
        confidence=0.9,
    )
    v = raw.validated("… Dr. Karen Chen, owner …", "KC Dental", "US", 2026)
    assert (v.display_name, v.founded_year, v.owner_name, v.address.postcode) == (
        "KC Dental PLLC",
        1998,
        "Karen Chen",
        "78727",
    )
