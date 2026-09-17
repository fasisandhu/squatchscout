# SquatchScout — Design Spec

**Date:** 2026-09-17 · **Status:** approved by owner, pre-implementation
**Tagline:** *Ranked, verified, explained — which small businesses a searcher should call first.*

---

## 1. Context and goal

Caprae Capital's Full Stack Developer take-home asks for one or two impactful features that improve their lead-generation product, SaaSquatch Leads (saasquatchleads.com), in **≤ 5 hours of code**, plus a 1–2 minute video and a README that documents the full architecture: database, caching, hosting (static vs serverless), deployment process, cloud provider, exact stack.

Rubric (40 pts): Business use case 10 · UX/UI 10 · Technicality 10 · Design 5 · Other 5. The phrase that recurs: *"prioritize high-impact leads, minimize irrelevant data."* Bonus for dedupe, enrichment, validation, resilience to flaky sources, ethical collection, CRM-shaped export.

Job description signals the tool should also demonstrate: FastAPI + React, deliberate DB schema design, **Ubuntu server deployment and maintenance of deployed services**, and contribution to **AI/ML development workflows**.

**Approach chosen:** Quality-first. One feature done deeply — a scored, verified, explainable lead-ranking flow that mirrors SaaSquatch's *Search* input but changes what comes back — with a data-quality (dedupe/validate) layer built in.

## 2. Persona, job-to-be-done, non-goals

**Persona.** An acquisition entrepreneur ("searcher") or a Caprae sourcing analyst hunting owner-operated small businesses in fragmented service industries.

**Job.** "Given an industry and a place, show me the businesses worth my time first, and prove why."

**Non-goals (stated in README as deliberate):** authentication / multi-user; Persons or LinkedIn search (ToS; stated as an ethics position); live CRM API integration (CSV in CRM column shape instead); kanban pipeline; paid data sources; LLM-generated prose summaries or LLM-produced scores (explainability must stay deterministic and auditable).

## 3. User flow

1. User types a sentence (*"dentists in Austin, ideally owners near retirement"*) **or** fills the manual form (industry select, location, result cap). The NL box fills the form; the form is always visible and editable.
2. Presses **Scout**. Leads stream into the table within seconds as each finishes the fast pipeline stages; a status strip shows the current stage and count.
3. Weight sliders in the right rail re-rank the table instantly (client-side). Summary tiles update.
4. As the LLM extraction queue drains, rows refine in place (score/tier may change; a subtle "updated" pulse).
5. Clicking a row opens a drawer: factor bars with plain-English reasons, contacts with verification badges, signals with their source (OSM / regex / LLM), and an on-demand **Draft call opener** button.
6. User selects rows (or all) and exports **CSV** or **HubSpot-shaped CSV**, with the current weights embedded.

## 4. Architecture overview

```
 Browser (Vercel CDN, static Vite build)
   │  HTTPS  (fetch + EventSource/SSE)
   ▼
 Caddy (auto-HTTPS reverse proxy)  ── Ubuntu 24.04 VM on AWS EC2 (t3.micro)
   ▼                                   Docker Compose: api · postgres · caddy
 FastAPI (uvicorn, single worker)
   ├─ Pipeline runner (async): geocode → discover → dedupe → enrich → extract → verify → score → persist/stream
   ├─ LLM client: Groq (OpenAI-compatible), model pool + token-bucket throttle
   └─ SQLModel/SQLAlchemy + Alembic
   ▼
 Postgres 16 (Docker volume, nightly pg_dump)

 External: Nominatim (geocode) · Overpass API ×2 mirrors (discover) · business websites (enrich) · DNS MX (verify) · Groq (extract, intent, opener)
```

Why this split: the UI is static content → CDN. The API needs a **persistent process** because SSE streams and multi-second polite crawls exceed serverless function limits and don't suit stateless invocations. Postgres colocated on the VM keeps the demo self-contained and exercises the Ubuntu-ops story; `DATABASE_URL` swaps to a managed Postgres (Neon) without code changes.

## 5. Pipeline

Each stage is a module under `api/app/pipeline/` with a pure-ish async function, typed inputs/outputs (Pydantic), and its own tests. `runner.py` orchestrates and emits events.

### 5.1 Geocode — `geocode.py`
- Input: free-text location. Output: `GeoBox(name, country_code, s, w, n, e)`.
- Nominatim `/search?format=json&limit=1`, custom User-Agent, 1 req/s max. If the bounding box is larger than ~2° in either dimension (a whole state/country), shrink to a 0.5° box around the centroid and tell the user via a `status` event ("Large area — searching the city center").
- Cached forever in `geocode_cache` keyed by normalized query.

### 5.2 Discover — `discover.py`, `industries.py`
- Curated industry map (single source of truth, one file). Each entry: `key`, `label`, list of OSM tag selectors (OR'd). Initial set (16):

| key | label | OSM selectors |
|---|---|---|
| dentist | Dentists | amenity=dentist; healthcare=dentist |
| veterinary | Veterinary clinics | amenity=veterinary |
| plumber | Plumbers | craft=plumber |
| hvac | HVAC contractors | craft=hvac |
| electrician | Electricians | craft=electrician |
| roofer | Roofers | craft=roofer |
| landscaping | Landscaping | craft=gardener |
| auto_repair | Auto repair | shop=car_repair |
| car_wash | Car washes | amenity=car_wash |
| accounting | Accounting & bookkeeping | office=accountant |
| insurance | Insurance agencies | office=insurance |
| laundry | Laundry & dry cleaning | shop=laundry; shop=dry_cleaning |
| pharmacy | Independent pharmacies | amenity=pharmacy |
| childcare | Childcare centers | amenity=childcare; amenity=kindergarten |
| funeral | Funeral homes | shop=funeral_directors |
| optometry | Optometrists & opticians | healthcare=optometrist; shop=optician |

- Overpass QL template (union of `node` and `way` per selector, `out center tags {limit};`), `[timeout:25]`. Endpoints tried in order: `https://overpass-api.de/api/interpreter`, `https://overpass.kumi.systems/api/interpreter`; retry once per endpoint with backoff on 429/504/network error. All failing → `error` event with a friendly message; nothing crashes.
- Raw response cached 24 h in `overpass_cache` keyed by `sha256(industry_key|bbox rounded 3dp|limit)`.
- Output per element: `RawPlace(osm_type, osm_id, name, lat, lon, tags)`. Elements without a `name` are dropped.

### 5.3 Dedupe and chain detection — `dedupe.py`
- Normalize: domain (lowercase, strip scheme/`www.`/path), phone → E.164 with region from geocode country code, name → lowercase, strip punctuation and legal suffixes (`llc`, `inc`, `pllc`, `dds`, `pc`…).
- Duplicate if same normalized domain, **or** same E.164 phone, **or** `rapidfuzz.fuzz.token_set_ratio(name_a, name_b) ≥ 90` within the same city. Keep the record with more tags; merge missing fields.
- Chain suspected if the normalized name (minus location words) occurs ≥ 3 times in the result set, or tags include `brand`/`brand:wikidata`. Sets `is_chain_suspected=True` — it is a scoring input and a table badge, not a filter.

### 5.4 Enrich — `crawl.py`
- Runs only for leads with a website. Async `httpx` client, global concurrency 8, **1 in-flight request per domain**, 6 s timeout, 1 MB body cap, HTML only, 2 retries on network errors only.
- Robots: fetch `/robots.txt` once per domain (cached), parse with `urllib.robotparser`, obey for our UA. Disallowed → mark `enrichment_status=blocked_by_robots`, skip politely.
- Pages: homepage, then up to two of `/contact`, `/contact-us`, `/about`, `/about-us` if linked from the homepage. Max 3 pages per domain.
- Output `PageBundle(domain, pages: list[PageText], fetched_at)` where `PageText` holds `url`, `title`, `meta_description`, `visible_text` (selectolax, scripts/styles removed), `raw_head` (for generator/builder detection), `links`.
- Cached 7 days in `enrichment_cache` by domain (stores the extracted text excerpt and the regex/LLM signals and contacts, not full HTML).

### 5.5 Extract — `extract_regex.py`, `extract_llm.py`
**Regex pass (always runs):**
- Emails: RFC-ish regex, drop image/asset false positives, drop `example.com`, `sentry.io`, `wixpress.com`.
- Phones: `phonenumbers.PhoneNumberMatcher` with region.
- Socials: facebook/instagram/linkedin-company/yelp/x links.
- `founded_year`: patterns `(est\.?|established|since|founded|serving .{0,40} since)\s*(19|20)\d{2}`; sanity 1850..current year.
- `family_owned`: `family[- ]owned|owner[- ]operated|locally owned`.
- `owner_name`: `owner[,:]?\s+(Dr\.?\s+)?[A-Z][a-z]+ [A-Z][a-z]+` and `Dr\. [A-Z][a-z]+ [A-Z][a-z]+, (owner|founder)`.
- `owner_operated`: derived — `True` when `family_owned` matched or `owner_name` was found; otherwise unknown (`None`), which is what makes the LLM gate below meaningful.
- `is_chain`: derived from dedupe's `is_chain_suspected` (`True`) or a `brand` tag; otherwise unknown.
- `hiring`: `we'?re hiring|careers|join our team|now hiring`.
- `site_builder`: `<meta name="generator" content="WordPress|Wix|Squarespace|Weebly|GoDaddy|Duda">`, plus host/script hints (`wixstatic`, `squarespace.com`, `godaddysites`).
- `has_booking`: `book (an|your) appointment|schedule online|zocdoc|calendly|acuity|localmed|housecall pro|jobber`.
- `has_chat`: `intercom|drift|tawk|livechat|podium|birdeye`.
- `copyright_year`: last `©|copyright\s*(19|20)\d{2}` on the page.
- `contact_page_found`: any fetched contact/about page returned 200.

**LLM pass (gap-filling, env-gated, see §7):** runs only if a website was fetched **and** any of `founded_year`, `owner_operated`, `owner_name`, `is_chain` is still unknown after regex. Input: title + meta + up to ~700 tokens of the most relevant sentences (those containing `since|founded|est|family|owner|our team|about|locations`), then the first paragraph as filler. Output schema in §7.2.

**Merge policy:** regex value wins where present; LLM fills blanks; LLM may override a regex value only when `confidence ≥ 0.85` and the values conflict. Every value is stored as a `signals` row with `source ∈ {osm, regex, llm}` and `confidence`, so the UI can show provenance and the eval can compare.

### 5.6 Verify — `verify.py`
- Email: syntax → MX lookup via `dnspython` (3 s timeout, cached per domain) → disposable-domain blocklist (bundled, ~1k entries) → `verified | unverified | invalid`. No SMTP handshake (intrusive, unreliable, often blocked).
- Phone: `phonenumbers.is_valid_number` → `valid | possible | invalid`.
- Website: `reachable` if any page returned 2xx/3xx.

### 5.7 Score — `score.py`
See §6. Pure function over a `LeadFacts` object; deterministic; unit-tested against golden cases.

### 5.8 Persist and stream — `runner.py`
- Fast path per lead: dedupe → enrich → regex extract → verify → score → write → emit `lead`.
- LLM path: enqueue; as each completes → re-merge → re-score → update rows → emit `lead_updated`.
- Stream stays open until fast path completes **and** the LLM queue drains or 90 s elapse after fast-path completion, whichever first. Then `done { lead_count, llm_pending }`. Later LLM updates persist and appear on refresh or `GET /leads`.
- Search row tracks `status ∈ {running, done, failed}`.

## 6. Scoring model

Score 0–100 from five factors. Each factor returns `(points, max_points, reasons: list[str])` and is stored per lead in `factor_scores`. Default weights equal the factor maxima. **Total = Σ_f (points_f / max_f) × weight_f**, weights normalized to sum 100.

| Factor | Max | Points |
|---|---|---|
| **Reachability** | 25 | verified email +12 (unverified +6) · valid phone +8 · contact page found +3 · site reachable +2 |
| **Establishment** | 20 | founded ≥10 yrs +8 (≥5 +5, known <5 +2) · OSM completeness up to +7 (full address +3, opening_hours +2, phone or website in OSM +2) · site reachable +5 |
| **Digital-maturity gap** (AI upside; more gap → more points) | 20 | no website at all +20 · else DIY builder +7 · no online booking +5 · no chat widget +3 · copyright year ≥2 yrs stale +5 |
| **Buy-box fit** | 20 | independent (not chain-suspected) +12 · physical address present +4 · real business name +4 (name is not just the category word — OSM has many POIs literally named "Dentist" or "Dental Clinic"; detected by comparing the normalized name against the industry's label/synonym list) |
| **Succession signals** | 15 | founded ≥20 yrs +8 (≥15 +5) · owner name found +4 · family-owned/owner-operated phrase +3 |

Tiers: **A ≥ 70 · B ≥ 55 · C ≥ 40 · D < 40**.

Weight presets (selectable in UI; the NL intent parser may choose one) as R/E/D/B/S:
- `balanced` — 25/20/20/20/15 (defaults)
- `succession` — 25/15/10/20/30
- `digital_upside` — 25/10/35/20/10
- `reachability_first` — 40/15/15/20/10

**Client-side re-rank:** the browser holds per-factor `points/max` and recomputes totals and tiers when sliders move — zero round trips. The same function ships in Python (`score.py`) and TypeScript (`web/src/lib/rank.ts`) and is tested in both against shared golden JSON so they cannot drift.

## 7. AI design (Groq)

### 7.1 Provider and constraints
- Groq, OpenAI-compatible, via the `groq` Python SDK. Free tier per model: **30 RPM · 1,000 RPD · 8,000 TPM · 200,000 TPD.** 429 responses carry `retry-after`.
- Model pool, in order: `openai/gpt-oss-20b` → `qwen/qwen3.8-27b`. Both support strict `json_schema`. Separate quotas per model, so the pool roughly doubles daily budget.
- Env-gated: no `GROQ_API_KEY` → every AI path is disabled and the UI hides AI affordances; everything else works.

### 7.2 Three uses, each with a non-AI fallback
1. **Search intent** — one call per NL search (~300 tokens). Strict schema: `{ industry_key: enum|null, location: string|null, limit: int|null, weight_preset: enum, rationale: string }`. Result fills the form; user can edit before running. Fallback: manual form.
2. **Signal extraction** — strict schema: `{ founded_year: int|null, owner_operated: bool|null, owner_name: string|null, family_owned: bool|null, is_chain: bool|null, hiring: bool|null, services: string[], confidence: number }`. Gap-filling only (§5.5). Fallback: regex-only signals.
3. **Call opener** — on demand from the drawer; 3 lines, grounded strictly in stored signals (prompt forbids inventing facts). Fallback: button hidden.

### 7.3 Throttle, fallback, budget
- Token bucket per model: 6 requests/min and 7,000 tokens/min (estimated from input length + `max_tokens`). Adjusted downward from `x-ratelimit-remaining-*` headers when present.
- On 429: honor `retry-after` once (cap 20 s) on the same model, then move to the next model in the pool, then skip and mark `llm_status=skipped_rate_limit`. Never blocks the stream.
- Per-search cap: 40 extraction calls. Daily soft cap tracked in-process (resets at UTC midnight) to avoid burning the demo's quota; beyond it, extraction is skipped with `llm_status=skipped_budget`.
- Results cached by domain in `enrichment_cache.llm_signals` (7 days). Cache hits cost nothing.

### 7.4 Evaluation
`evals/extraction_eval.py`: 10 saved business homepages under `evals/golden/*.html` with hand-labeled `labels.json` (`founded_year`, `owner_operated`, `family_owned`, `is_chain`). Reports per-field accuracy for **regex-only** vs **regex+LLM**, writes `evals/results.md`, and the table is copied into the README. Runs offline for regex; LLM part needs the key.

### 7.5 Why not more AI
Documented in README: deterministic factor reasons are auditable and stable; an LLM paragraph is neither. Scores must be reproducible for a sourcing workflow. LLM-invented OSM tags risk hallucination; the intent parser chooses *from* the curated list instead.

## 8. Data model

SQLModel models, Alembic migrations from the first commit. Postgres 16 in prod; SQLite for local dev and tests (JSON columns via SQLAlchemy `JSON`, which maps to `JSONB` on Postgres via a variant).

- **searches** — `id (uuid pk)`, `industry_key`, `location_query`, `geocoded_name`, `country_code`, `bbox_s/w/n/e`, `limit`, `nl_query (nullable)`, `weight_preset`, `status`, `lead_count`, `created_at`, `finished_at`.
- **leads** — `id (uuid pk)`, `search_id (fk, idx)`, `osm_type`, `osm_id`, `name`, `normalized_name`, `lat`, `lon`, `street`, `housenumber`, `city`, `state`, `postcode`, `country`, `website`, `normalized_domain (idx)`, `osm_tags (json)`, `is_chain_suspected`, `enrichment_status`, `llm_status`, `score`, `tier`, `created_at`, `updated_at`. Unique `(search_id, osm_type, osm_id)`.
- **contacts** — `id`, `lead_id (fk, idx)`, `kind ∈ {email, phone, social}`, `value`, `normalized_value`, `source ∈ {osm, website, llm}`, `verification_status`, `meta (json)`.
- **signals** — `id`, `lead_id (fk, idx)`, `key`, `value (text)`, `source ∈ {osm, regex, llm}`, `confidence (float)`, `created_at`. Index `(lead_id, key)`.
- **factor_scores** — `id`, `lead_id (fk, idx)`, `factor`, `points`, `max_points`, `reasons (json array)`. Unique `(lead_id, factor)`.
- **geocode_cache** — `query_norm (pk)`, `result (json)`, `created_at`.
- **overpass_cache** — `key (pk)`, `payload (json)`, `created_at`, `expires_at (idx)`.
- **enrichment_cache** — `domain (pk)`, `text_excerpt`, `regex_signals (json)`, `llm_signals (json)`, `contacts (json)`, `robots_blocked (bool)`, `fetched_at`, `expires_at (idx)`.

Retention: searches and children older than 30 days are deleted by `api/scripts/purge_old.py`, run from host cron (documented in runbook). Caches expire by `expires_at`.

Migrations run at container start: `alembic upgrade head && uvicorn …` (single instance, acceptable).

## 9. API contract

Base path `/api`. JSON errors `{ "error": { "code", "message" } }`; all handlers wrapped so exceptions become clean 4xx/5xx with CORS headers intact.

| Method & path | Purpose |
|---|---|
| `GET /healthz` | `{status, db, llm_enabled, version}` — used by deploy rollback check |
| `GET /api/industries` | curated list `[ {key, label} ]` and weight presets |
| `POST /api/intent` | `{ text }` → intent schema (§7.2) or 503 `llm_disabled` |
| `POST /api/searches` | `{ industry_key, location, limit≤100, weight_preset?, nl_query? }` → `{ id }` and starts the pipeline |
| `GET /api/searches/{id}/stream` | SSE. Events: `status {stage, message, count}` · `lead {…full lead}` · `lead_updated {lead_id, signals, factor_scores, score, tier, llm_status}` · `done {lead_count, llm_pending}` · `error {message}` |
| `GET /api/searches/{id}` | search row incl. `status`, `lead_count`, `llm_pending` (leads still queued for LLM extraction) |
| `GET /api/searches/{id}/leads` | all leads with contacts, signals, factor_scores |
| `GET /api/leads/{id}` | one lead, full |
| `POST /api/leads/{id}/opener` | `{ opener: string }` or 503 `llm_disabled` |
| `GET /api/searches/{id}/export?format=csv\|hubspot&ids=a,b,c&weights=25,20,20,20,15` | CSV download |

Lead payload shape (TS type hand-mirrored from the Pydantic schema and covered by a shared golden JSON test):
`{ id, name, address:{street,housenumber,city,state,postcode,country}, lat, lon, website, domain, is_chain_suspected, enrichment_status, llm_status, score, tier, contacts:[{kind,value,source,verification_status}], signals:[{key,value,source,confidence}], factor_scores:[{factor,points,max_points,reasons}] }`

**Export columns.**
- `hubspot`: `Company name, Company Domain Name, Phone Number, Street Address, City, State/Region, Postal Code, Country/Region, Industry, Website URL, Description` + custom `SquatchScout Score, Tier, Verified Email, Founded Year, Owner Operated, Chain Suspected, Data Sources`. `Description` = factor reasons joined by `; `. Attribution and weights go in the trailing `Data Sources` column (HubSpot's importer does not skip comment rows).
- `csv`: all lead fields flat, one row per lead, contacts collapsed to `emails`, `phones`, `socials` columns; first row is a comment line `# SquatchScout export · weights R/E/D/B/S=… · data © OpenStreetMap contributors (ODbL) + business websites`.

## 10. Frontend

**Stack:** Vite · React 19 · TypeScript · Tailwind CSS v4 · TanStack Table · TanStack Query (non-stream fetches) · native `EventSource` · lucide-react. No component library; a small set of hand-built primitives.

**Layout (desktop ≥ 1024 px):** top search bar; main column = status strip + results table; right rail (320 px) = weights panel, summary tiles, export. **< 1024 px:** rail collapses into a bottom sheet; table becomes card list. Body never scrolls horizontally; the table scrolls inside its container.

**Components:** `SearchBar` (NL input with sparkle affordance when LLM enabled; manual `IndustrySelect`, `LocationInput`, `LimitInput`; primary **Scout** button) · `StatusStrip` · `ResultsTable` (name, city, `ScoreChip` with tier color, verified-email badge, phone, chain/independent tag, LLM "refined" dot; sortable; row checkboxes) · `LeadDrawer` (`FactorBars`, `ContactsList`, `SignalsList` with source pills, `OpenerPanel`) · `WeightsPanel` (5 sliders + preset chips + reset) · `SummaryTiles` (leads found, % with verified email, tier distribution mini-bar, LLM refined count) · `ExportMenu` · `EmptyState` (explains the flow, offers two example queries) · `ErrorToast` · `AttributionFooter` (© OpenStreetMap contributors).

**State:** `useReducer` for the search session — `leads: Record<id, Lead>`, `order`, `status`, `weights`, `selected`, `llmPending`. SSE handlers dispatch `lead_received`, `lead_updated`, `status`, `done`, `error`. Re-rank is a memoized selector using `rank.ts`.

**Late LLM updates:** when `done` arrives with `llm_pending > 0`, the client polls `GET /api/searches/{id}` every 10 s; whenever `llm_pending` drops, it fetches `GET /api/searches/{id}/leads` and dispatches `lead_updated` for changed rows. Polling stops when `llm_pending` reaches 0 or after 8 minutes (the per-search cap of 40 calls at ~6/min bounds the queue at ~7 min). The status strip shows "Refining N leads with AI…" during this phase.

**Config:** `src/config.ts` reads `VITE_API_URL`; falls back to same-origin `/api` so the app never throws at import.

**States handled:** empty · streaming · done with 0 results (suggest widening) · partial failure (some leads blocked/unreachable — shown, not hidden) · API unreachable (banner with retry) · LLM disabled (AI affordances hidden, footer note).

**Visual language:** dark navy to read as a native SaaSquatch feature. Tokens: `bg #0b1220`, `surface #111a2e`, `border #1f2a44`, `text #e6edf7`, `muted #8b9bb4`, accent gradient `#14b8a6 → #3b82f6`, tiers A emerald · B sky · C amber · D slate. Typography: Inter (system fallback), tabular numerals for scores. One accent, generous spacing, no decorative gradients beyond the primary button and score chips.

**Accessibility:** keyboard-navigable table and drawer, `aria-live` status strip, focus trap in drawer, contrast ≥ 4.5:1 for text, sliders as native `<input type="range">` with labels.

## 11. Configuration (API env vars)

| Var | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./dev.db` | Postgres URL in prod |
| `GROQ_API_KEY` | unset | unset → AI disabled |
| `GROQ_MODELS` | `openai/gpt-oss-20b,qwen/qwen3.8-27b` | pool order |
| `LLM_DAILY_SOFT_CAP` | `600` | requests/day across pool |
| `FRONTEND_ORIGINS` | `http://localhost:5173` | comma-separated CORS allowlist |
| `CRAWLER_USER_AGENT` | `SquatchScoutBot/0.1 (+{PUBLIC_URL}/about)` | |
| `CRAWLER_CONTACT` | unset | appended to UA when set |
| `PUBLIC_URL` | `http://localhost:5173` | for UA and attribution |
| `OVERPASS_ENDPOINTS` | two mirrors | comma-separated |
| `NOMINATIM_ENDPOINT` | `https://nominatim.openstreetmap.org` | |
| `MAX_LEADS_PER_SEARCH` | `60` | hard max 100 |
| `ENRICH_CACHE_TTL_DAYS` / `OVERPASS_CACHE_TTL_HOURS` | `7` / `24` | |
| `LOG_LEVEL` | `INFO` | JSON logs |

`.env` loaded with `override=False` so platform env wins. `deploy/.env.example` documents all of them.

## 12. Hosting and deployment

### 12.1 Server
- **AWS EC2 t3.micro, Ubuntu 24.04 LTS**, region us-east-1 (or nearest). Security group: 22 from owner IP only, 80/443 from anywhere. 1 GB swap file added by setup script.
- `deploy/setup-ubuntu.sh` (idempotent): apt update/upgrade, install Docker Engine + Compose plugin from Docker's apt repo, `ufw` (22/80/443), create `/opt/squatchscout`, copy compose files, install and enable the systemd unit, install cron entries (backup, purge).
- Hostname for TLS: owner's domain if available, else `api.<ip>.sslip.io` (Let's Encrypt works with sslip.io). Set in `Caddyfile` via `${API_HOST}`.

### 12.2 Containers — `deploy/docker-compose.yml`
- `api`: image `ghcr.io/<owner>/squatchscout-api:${API_TAG}` (public package), `env_file: .env`, `depends_on: postgres (healthy)`, `restart: unless-stopped`, log driver `json-file` with `max-size 10m, max-file 3`. Command runs `alembic upgrade head` then uvicorn on `$PORT` (8000), 1 worker.
- `postgres`: `postgres:16-alpine`, volume `pgdata`, healthcheck `pg_isready`.
- `caddy`: `caddy:2`, ports 80/443, volumes `caddy_data`, `caddy_config`, `Caddyfile` mounted. `reverse_proxy api:8000` with `flush_interval -1` so SSE streams are not buffered.
- `deploy/squatchscout.service`: `docker compose -f /opt/squatchscout/docker-compose.yml up -d` on boot, `Restart=on-failure`.

### 12.3 CI/CD — `.github/workflows/`
- `ci.yml` (PR + push): Python 3.13 — `ruff check`, `ruff format --check`, `pytest`; Node 24 — `pnpm install --frozen-lockfile`, `tsc --noEmit`, `vitest run`, `vite build`.
- `deploy.yml` (push to `main`, after CI): build API image with `docker/build-push-action`, push to GHCR tagged `sha-<short>` and `latest` → SSH to VM (`appleboy/ssh-action`, key in GitHub secret) → run `/opt/squatchscout/deploy.sh sha-<short>`.
- `deploy/deploy.sh <tag>`: save current `API_TAG` to `.previous_tag`, write new tag to `.env`, `docker compose pull api`, `docker compose up -d api`, poll `https://$API_HOST/healthz` up to 30× (2 s) → success; on failure restore `.previous_tag`, `up -d api`, exit 1 (workflow shows red).

### 12.4 Frontend — Vercel
- Project root `web/`, framework Vite, `VITE_API_URL=https://<API_HOST>` for production. `vercel.json` rewrites all routes to `/index.html`. Deployment Protection **off**. Auto-deploys from `main`.

### 12.5 Wiring and verification
- `FRONTEND_ORIGINS` = Vercel production URL (Starlette's CORS middleware takes explicit origins or a regex; use `allow_origin_regex` for `*.vercel.app` previews if needed).
- Verify checklist: `curl /healthz`; CORS preflight returns `access-control-allow-origin`; a real search streams end-to-end in the browser; export downloads; `docker compose logs` clean.

### 12.6 Backups and housekeeping (host cron)
- `deploy/backup.sh`: `03:00` daily `pg_dump | gzip` → `/opt/squatchscout/backups/YYYY-MM-DD.sql.gz`, keep 7.
- `api/scripts/purge_old.py` via `docker compose exec api`: `04:00` daily, deletes searches > 30 days and expired caches.

### 12.7 "Production would differ" paragraph (README)
ECS Fargate or EKS behind an ALB, RDS Postgres with automated backups, ElastiCache for the throttle/caches, S3+CloudFront for the UI, Secrets Manager, CloudWatch — and a job queue (SQS/Celery) for the crawl/LLM stages instead of in-process tasks.

## 13. Observability and operations

- Structured JSON logs (stdlib `logging` with a JSON formatter): request id, search id, stage, duration, external call outcomes, LLM model/tokens/429s.
- `/healthz` checks DB connectivity and reports `llm_enabled` and git SHA (baked at build via `APP_VERSION` arg).
- `docs/runbook.md` covers: check service status · tail logs · restart api · deploy a specific tag · roll back · run/inspect migrations · restore a backup · rotate `GROQ_API_KEY` · disk-full triage · Ubuntu security updates · certificate notes (Caddy auto-renews) · known free-tier limits.

## 14. Testing

**Python (`pytest`, `pytest-asyncio`, `respx` for httpx mocking):**
- `industries`: every selector is well-formed Overpass QL; query builder output matches golden string.
- `dedupe`: domain/phone/fuzzy cases; chain detection thresholds.
- `extract_regex`: each extractor against fixture HTML snippets (positive + negative).
- `verify`: MX mocked (present / NXDOMAIN / timeout), disposable list, phone validity.
- `score`: golden `LeadFacts → factor points` cases; total/tier boundaries; shared golden JSON with TS.
- `llm`: throttle math; 429 → fallback → skip path with a fake client; merge policy.
- `runner`: end-to-end with recorded Overpass JSON fixture and mocked sites; asserts event order and persisted rows (SQLite).
- `export`: column order and attribution placement.

**TypeScript (`vitest`):** `rank.ts` against the same golden JSON as Python; reducer transitions for `lead`/`lead_updated`/`done`.

**Eval:** §7.4. **No E2E browser suite** — deliberately out of scope for the time budget; manual verification checklist in §12.5.

## 15. Ethics and compliance

- Only publicly published business information; no personal profiles; no LinkedIn or people-search scraping (stated).
- `robots.txt` honored; identifiable User-Agent with contact; per-domain serial requests; small page caps; no CAPTCHA circumvention — blocked sites are marked, not bypassed.
- OpenStreetMap data is ODbL: attribution "© OpenStreetMap contributors" shown in the UI footer and included in every export. Nominatim and Overpass usage policies respected (UA, ≤1 req/s to Nominatim, cached results).
- Retention: 30-day purge; no data sold or shared. README has a short "Data & ethics" section.

## 16. Repository layout

```
squatchscout/
├─ README.md · LICENSE (MIT) · .gitignore
├─ .github/workflows/ ci.yml · deploy.yml
├─ api/
│  ├─ pyproject.toml · alembic.ini · alembic/versions/ · Dockerfile · .dockerignore
│  ├─ app/
│  │  ├─ main.py · config.py · db.py · models.py · schemas.py · logging_setup.py
│  │  ├─ routers/ health.py · industries.py · intent.py · searches.py · leads.py · export.py
│  │  ├─ pipeline/ runner.py · geocode.py · industries.py · discover.py · dedupe.py · crawl.py · extract_regex.py · extract_llm.py · verify.py · score.py
│  │  ├─ llm/ client.py · throttle.py · schemas.py · prompts.py
│  │  └─ services/ cache.py · export.py · events.py
│  ├─ scripts/ purge_old.py
│  └─ tests/ (mirrors app/) + fixtures/
├─ web/
│  ├─ package.json · vite.config.ts · tsconfig.json · index.html · vercel.json
│  └─ src/ main.tsx · App.tsx · config.ts · api/{client,sse,types}.ts · lib/rank.ts · state/searchReducer.ts · components/… · styles/
├─ deploy/ docker-compose.yml · Caddyfile · squatchscout.service · setup-ubuntu.sh · deploy.sh · backup.sh · .env.example
├─ evals/ golden/*.html · labels.json · extraction_eval.py · results.md
├─ notebooks/ demo.ipynb
├─ data/ sample-search-<city>-<industry>.csv
└─ docs/ architecture.md · runbook.md · time-log.md · video-script.md · superpowers/specs/ · superpowers/plans/
```

The confidential handbook `.docx` lives outside this repo and is gitignored by pattern.

## 17. Deliverables beyond code

- **README.md** sections, in order: one-line pitch + screenshot/GIF · live demo link · the problem and persona · what it does in 60 seconds · architecture diagram · stack table (exact versions) · data sources & ethics · scoring model · AI design + eval results table · database schema · caching & performance · hosting & deployment (with the "production would differ" paragraph) · runbook link · local setup · tests · **5-hour time log summary** (link to `docs/time-log.md`) · what I'd build next · disclosure that AI-assisted tooling was used in development.
- **`docs/time-log.md`**: table of dated sessions, task, minutes; core ≤ 300 min called out.
- **`notebooks/demo.ipynb`**: connects via `DATABASE_URL` (or API), loads a finished search into pandas, score histogram, tier-by-industry SQL, verified-email-rate-by-source SQL, live weight re-rank demo.
- **`data/`**: one real export (CSV) from a completed search, attribution included.
- **`docs/video-script.md`**: 2-minute script + shot list (0:00 problem · 0:20 demo flow · 1:20 architecture and ops · 1:50 what's next).
- Essay drafts and the submission email are produced in chat with the owner, not committed.

## 18. Time budget and logging

Core (logged, ≤ 5 h): pipeline 1.5 h · LLM extraction 0.5 h · scoring/verify/dedupe 1 h · UI 1.5 h · Docker + Compose + first deploy 0.5 h.
Unbounded afterwards: Alembic polish, CI + rollback workflow, runbook, tests, eval, notebook, README, video, essays.
Every session is recorded in `docs/time-log.md` as it happens.

## 19. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Overpass slow/down | two mirrors, retry/backoff, 24 h cache, friendly error |
| OSM contact data sparse | design treats "no web presence" as a signal; enrichment adds contacts; README states coverage honestly |
| Groq free-tier limits | throttle, model pool, gap-filling only, per-search and daily caps, cache; pre-warm before video |
| t3.micro memory | single uvicorn worker, swap, alpine Postgres, log rotation |
| Crawl blocked / slow sites | robots respected, 6 s timeout, marked not hidden |
| Let's Encrypt issuance | Caddy handles; sslip.io fallback hostname |
| Scope creep vs 5 h | spec non-goals; time log; plan tasks sized ≤ 30 min |

## 20. Out of scope / future

Auth and teams · saved searches and alerts · additional discovery providers behind the existing stage interface (e.g., a Places API) · job queue for crawl/LLM stages · LinkedIn-free people enrichment via company websites' team pages · direct HubSpot API push.
