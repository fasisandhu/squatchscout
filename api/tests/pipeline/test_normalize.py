from app.pipeline.industries import INDUSTRIES
from app.pipeline.normalize import (
    display_name,
    is_generic_name,
    normalize_domain,
    normalize_name,
    normalize_phone,
)


def test_domain():
    assert normalize_domain("https://www.KCDentalAustin.com/contact?x=1") == "kcdentalaustin.com"
    assert normalize_domain("kcdental.com") == "kcdental.com"
    assert normalize_domain(None) is None and normalize_domain("not a url") is None


def test_phone():
    assert normalize_phone("(512) 918-0888", "US") == "+15129180888"
    assert normalize_phone("+1-512-918-0888", "US") == "+15129180888"
    assert normalize_phone("12", "US") is None


def test_name_normalization_strips_suffixes_and_punct():
    assert normalize_name("Hammons Family Dental, PLLC") == "hammons family dental"
    assert normalize_name("KC DENTAL L.L.C.") == "kc dental"


def test_display_name():
    assert display_name("HAMMONS FAMILY DENTAL LLC") == "Hammons Family Dental LLC"
    assert display_name("Smiles by Design - Dentist in Austin") == "Smiles by Design"
    assert display_name("Dr. J. Smith DDS") == "Dr. J. Smith DDS"


def test_generic_name():
    d = INDUSTRIES["dentist"]
    assert is_generic_name("Dentist", d) and is_generic_name("Dental Clinic", d)
    assert not is_generic_name("KC Dental", d)
