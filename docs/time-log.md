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
| 2026-09-18 | 19 web scaffold, types, client, rank.ts (resumed after crash) | 25 | — | confirmed prior agent's scaffold already had react/react-dom/@tanstack/react-table/lucide-react/@types/node installed; installed missing tailwindcss/@tailwindcss/vite/vitest; this create-vite flavor's scaffold noise differs from the brief's assumed file names (no App.css/react.svg/public vite.svg — instead hero.png/vite.svg/icons.svg/favicon.svg), so only `src/index.css` existed to delete; fixed `ApiError` constructor parameter-property shorthand, which the scaffold's `erasableSyntaxOnly` tsconfig flag rejects, by declaring fields explicitly instead of weakening the flag; brief's `rank.ts`/`rank.test.ts` (with controller's `node:fs` golden-fixture ruling) passed all 6 tests unmodified on first run, no scoring bugs found |
| 2026-09-18 | 20 session reducer, SSE, polling hook | 12 | — | scaffold has no ESLint config (lint script uses oxlint), so per controller ruling omitted the brief's `// eslint-disable-line react-hooks/exhaustive-deps` comment (an unknown-rule directive would itself be a lint issue); used `<T>` not `<T,>` in `sse.ts`'s generic arrow since it's a `.ts` file, not `.tsx`; brief's reducer/sse/hook code passed all 9 tests unmodified on first run, no bugs found |

