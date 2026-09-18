from datetime import datetime

from app.llm.schemas import ExtractionResult, LLMAddress
from app.pipeline.crawl import PageBundle, PageText
from app.pipeline.extract_llm import build_llm_input, merge_signals, needs_llm
from app.pipeline.extract_regex import RegexSignals


def test_needs_llm_gate():
    full = RegexSignals(
        founded_year=1998, owner_operated=True, owner_name="K C", street_address="1 Main St"
    )
    assert not needs_llm(full, has_street=True, text_quality="good")
    assert needs_llm(
        RegexSignals(founded_year=1998, owner_operated=True, owner_name="K C"),
        has_street=False,
        text_quality="good",
    )
    assert needs_llm(RegexSignals(), has_street=True, text_quality="good")  # owner/founded unknown
    assert needs_llm(full, has_street=True, text_quality="thin")  # thin text always


def test_build_input_prioritises_relevant_sentences_and_caps_length():
    filler = "Lorem ipsum dolor sit amet. " * 300
    text = (
        filler
        + "We are a family owned practice founded in 1998 by Dr. Karen Chen. "
        + filler
        + "Our office is located at 12400 West Parmer Lane. "
        + filler
    )
    b = PageBundle(
        domain="x.com",
        fetched_at=datetime(2026, 1, 1),
        pages=[
            PageText(
                url="https://x.com/",
                title="KC Dental",
                meta_description="Austin dentist",
                visible_text=text,
                text_quality="good",
            )
        ],
    )
    out = build_llm_input(b, max_chars=600)
    assert len(out) <= 600
    assert out.startswith("KC Dental\nAustin dentist\n")
    assert "founded in 1998" in out and "located at 12400" in out
    assert out.index("founded in 1998") < out.index("Lorem")


def test_merge_regex_wins_llm_fills_gaps_and_overrides_only_when_confident():
    regex = RegexSignals(
        founded_year=1998, family_owned=True, owner_operated=True, site_builder="wix"
    )
    llm_low = ExtractionResult(
        founded_year=2001,
        owner_name="Karen Chen",
        is_chain=False,
        address=LLMAddress(street="12400 West Parmer Lane", postcode="78727"),
        confidence=0.6,
    )
    merged = {s.key: s for s in merge_signals(regex, llm_low)}
    assert merged["founded_year"].value == "1998" and merged["founded_year"].source == "regex"
    assert merged["owner_name"].value == "Karen Chen" and merged["owner_name"].source == "llm"
    assert merged["street_address"].value == "12400 West Parmer Lane"
    assert merged["postcode"].value == "78727"
    assert merged["is_chain"].value == "false"
    llm_high = llm_low.model_copy(update={"confidence": 0.9})
    merged2 = {s.key: s for s in merge_signals(regex, llm_high)}
    assert merged2["founded_year"].value == "2001" and merged2["founded_year"].source == "llm"
    assert merged2["founded_year"].confidence == 0.9


def test_merge_without_llm_serialises_regex_only():
    out = merge_signals(RegexSignals(has_booking=True, copyright_year=2021), None)
    keys = {s.key for s in out}
    assert {
        "has_booking",
        "copyright_year",
        "family_owned",
        "hiring",
        "has_chat",
        "contact_page_found",
    } <= keys
    assert all(s.source == "regex" for s in out)
    assert "founded_year" not in keys  # None values are not emitted
