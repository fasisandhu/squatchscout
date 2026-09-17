from dataclasses import dataclass, field


@dataclass(frozen=True)
class Industry:
    key: str
    label: str
    selectors: list[tuple[str, str]]  # OSM (key, value) pairs, OR'd
    synonyms: list[str] = field(default_factory=list)  # generic-name detection (spec §6)


_LIST = [
    Industry(
        "accounting",
        "Accounting & bookkeeping",
        [("office", "accountant")],
        ["accountant", "accounting", "bookkeeping", "cpa", "tax service"],
    ),
    Industry(
        "auto_repair",
        "Auto repair",
        [("shop", "car_repair")],
        ["auto repair", "car repair", "automotive", "mechanic"],
    ),
    Industry("car_wash", "Car washes", [("amenity", "car_wash")], ["car wash"]),
    Industry(
        "childcare",
        "Childcare centers",
        [("amenity", "childcare"), ("amenity", "kindergarten")],
        ["childcare", "child care", "daycare", "day care", "preschool", "kindergarten"],
    ),
    Industry(
        "dentist",
        "Dentists",
        [("amenity", "dentist"), ("healthcare", "dentist")],
        ["dentist", "dental", "dental clinic", "dental office", "dentistry"],
    ),
    Industry(
        "electrician", "Electricians", [("craft", "electrician")], ["electrician", "electric"]
    ),
    Industry(
        "funeral",
        "Funeral homes",
        [("shop", "funeral_directors")],
        ["funeral home", "funeral", "mortuary"],
    ),
    Industry(
        "hvac",
        "HVAC contractors",
        [("craft", "hvac")],
        ["hvac", "heating and cooling", "air conditioning", "heating & air"],
    ),
    Industry(
        "insurance",
        "Insurance agencies",
        [("office", "insurance")],
        ["insurance", "insurance agency"],
    ),
    Industry(
        "landscaping",
        "Landscaping",
        [("craft", "gardener")],
        ["landscaping", "landscape", "lawn care"],
    ),
    Industry(
        "laundry",
        "Laundry & dry cleaning",
        [("shop", "laundry"), ("shop", "dry_cleaning")],
        ["laundry", "laundromat", "dry cleaning", "dry cleaners", "cleaners"],
    ),
    Industry(
        "optometry",
        "Optometrists & opticians",
        [("healthcare", "optometrist"), ("shop", "optician")],
        ["optometrist", "optometry", "optician", "eye care", "vision center"],
    ),
    Industry(
        "pharmacy", "Independent pharmacies", [("amenity", "pharmacy")], ["pharmacy", "drug store"]
    ),
    Industry("plumber", "Plumbers", [("craft", "plumber")], ["plumber", "plumbing"]),
    Industry("roofer", "Roofers", [("craft", "roofer")], ["roofer", "roofing"]),
    Industry(
        "veterinary",
        "Veterinary clinics",
        [("amenity", "veterinary")],
        ["veterinary", "veterinarian", "vet clinic", "animal hospital", "animal clinic"],
    ),
]

INDUSTRIES: dict[str, Industry] = {i.key: i for i in _LIST}


def list_industries() -> list[dict]:
    return [
        {"key": i.key, "label": i.label} for i in sorted(INDUSTRIES.values(), key=lambda x: x.key)
    ]
