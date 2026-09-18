# Time log

Core budget: 300 minutes (Phases A–C). Phase D is outside the budget by design.

| Date | Task | Minutes | Running total | Notes |
|---|---|---|---|---|
| 2026-09-17 | 1 API scaffold, settings, /healthz | 20 | 20 | |
| 2026-09-17 | 2 DB layer, models, Alembic | 35 | 55 | |
| 2026-09-17 | 3 industry map + Overpass QL | 12 | 67 | |
| 2026-09-17 | 4 geocode + cache | 18 | 85 | fixed sync/async context-manager bug in brief's test code |
| 2026-09-18 | 5 Overpass fetch, mirrors, cache | 22 | 107 | fixed sync/async context-manager bug in brief's test code again; fixed naive/aware datetime comparison bug (SQLite drops tzinfo on DateTime columns) in cache expiry check |
| 2026-09-18 | 6 normalize, dedupe, chain flag | 26 | 133 | fixed a bug in brief's `normalize_name`: dotted suffixes like "L.L.C." split into single-letter tokens ("l","l","c") on the punctuation regex, but the suffix-filter set only stripped leading/trailing dots, so it never matched; stripped dots from both the input and the suffix set before tokenizing |
| 2026-09-18 | 7 crawler + text cleaning | 12 | 145 | brief's fixture was too short for the "good" quality threshold; added two neutral filler paragraphs (services/insurance/hours/new-patients) to `site_home.html` per controller ruling — no code bugs found, brief's `crawl.py` passed all 4 tests unmodified except one E501 docstring line |
| 2026-09-18 | 8 regex extraction | 20 | 165 | removed `footer` from `STRIP_TAGS` per controller ruling (footers carry © years/addresses) — all 5 crawl tests still passed unchanged; brief's regexes and extraction logic passed all 3 tests unmodified on first run, no bugs found |
| 2026-09-18 | 9 verification | 13 | 178 | brief's `verify.py` (MX lookup, disposable list, phone validity) passed all 3 tests unmodified on first run, no bugs found |
| 2026-09-18 | 10 scoring engine + golden fixture | 17 | 195 | hand-recomputed all 4 golden cases against the factor logic before writing the fixture — all matched the brief's JSON exactly, no arithmetic discrepancies; removed an unused `FactorScore` import from the brief's test file (ruff F401), split all `pts += n; why.append(...)` one-liners in `score.py` onto two lines (ruff E702); brief's scoring logic passed all 8 tests unmodified on first run, no bugs found |
| 2026-09-18 | 11 Groq client, throttle, schemas | 12 | 207 | (resumed after crash) — prior implementer's uncommitted draft files matched the brief exactly (only ruff-formatted for line length; no logic divergence); confirmed installed `groq==0.37.1` `RateLimitError`/`APIStatusError` signature matches the test helper's `response=`/`body=` kwargs unmodified; 7/7 llm tests + 48/48 full suite pass, ruff check/format clean, no bugs found |
| 2026-09-18 | 12 LLM extraction stage + merge | 11 | 218 | brief's `extract_llm.py` (gating, relevant-text prioritisation, validated merge policy) passed all 4 tests unmodified except ruff-format wrapping the long `RELEVANT` regex line; 4/4 new tests + 55/55 full suite pass, ruff check/format clean, no bugs found |
| 2026-09-18 | 13 event bus, schemas, build_facts | 6 | 224 | brief's `events.py` and `schemas.py` (replay buffer bus, output schemas, `build_facts`) passed all tests unmodified except ruff-format line wrapping; 4/4 new tests + 58/58 full suite pass, ruff check/format clean, no bugs found |
| 2026-09-18 | 14 pipeline runner | 16 | 240 | fixed 2 real defects per controller ruling: `LLMJob` was missing `osm_name` (brief passed the crawled page title into the LLM grounding check instead of the OSM listing name) and added `overpass_dentists_no_addr.json` so test 2's LLM address gap-fill isn't blocked by an OSM address already being set; brief's region-threading, `s.execute(delete(...))` calls, full-state `lead_updated` payload and delete-then-rewrite signal rows were already correct as written; 3/3 new tests + 62/62 full suite pass (3 consecutive runs, 0 warnings), ruff check/format clean |

