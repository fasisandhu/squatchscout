import json


def intent_messages(text: str, industries: list[dict], presets: list[str]) -> tuple[str, str]:
    system = (
        "You turn a searcher's natural-language request into a structured search for small "
        "businesses. Choose industry_key ONLY from the provided list (or null if none fits). "
        "Extract the location as the user wrote it. limit is an integer 5-100 or null. Pick "
        "weight_preset: 'succession' if they mention retirement, aging owners or succession; "
        "'digital_upside' if they mention outdated websites, no online presence or "
        "modernization; 'reachability_first' if they stress contactability; else 'balanced'. "
        "rationale: one sentence. Never invent industries."
    )
    user = json.dumps({"request": text, "industries": industries, "presets": presets})
    return system, user


def extraction_messages(page_text: str, osm_name: str) -> tuple[str, str]:
    system = (
        "You read messy text scraped from a small business website and return clean structured "
        "facts. Only state what the text supports; use null when unsure. display_name is the "
        "business's proper name (fix casing, drop slogans). founded_year is a 4-digit year only "
        "if stated. owner_name must appear verbatim in the text. address fields only if present. "
        "services: up to 8 short phrases. confidence 0-1 for the whole answer."
    )
    user = json.dumps({"osm_listing_name": osm_name, "page_text": page_text})
    return system, user


def opener_messages(summary: dict) -> tuple[str, str]:
    system = (
        "Write a 3-line cold-call opener for an acquisition entrepreneur calling a small "
        "business owner. Ground every sentence in the provided facts; do not invent details, "
        "numbers or names. Warm, direct, no sales jargon. Return JSON {opener: string} with "
        "exactly three lines separated by \\n."
    )
    return system, json.dumps(summary)
