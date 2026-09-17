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

