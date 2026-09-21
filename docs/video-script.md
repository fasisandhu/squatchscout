# Video script — 2 minutes

Target: 1:55 to 2:05. About 265 spoken words at a normal, unhurried pace. Every number
below is measured and is in the repo; do not round them up on camera.

## Before recording

- [ ] Warm the API with the exact search you will demo (Dentists / Austin, TX / 60) at
      https://squatchscout-omega.vercel.app. On the deployed server a cold run takes about
      92 seconds and a warm one about 4. Warm it, then reload the page.
- [ ] Browser at 1920×1080, zoom exactly 100%, bookmarks bar hidden, one tab only.
- [ ] A second tab already on the repo's README, scrolled to the architecture diagram.
- [ ] A terminal window ready with the eval table on screen (`evals/results.md`).
- [ ] Close Slack, mail and anything that shows a notification.
- [ ] Check the Groq daily budget is not exhausted — the health endpoint should report
      `llm_enabled: true` and a test search should show the *refined* badge appearing.

## Shots

### 0:00–0:18 — The problem

*On screen: the SaaSquatch Leads search page, then your app's empty state.*

> An acquisition entrepreneur is someone raising money to buy one small business and run
> it. Their bottleneck is not finding companies. It is working out which of four hundred
> local dentists is worth a phone call on Monday morning. Existing lead tools hand you the
> list. They do not tell you where to start.

### 0:18–0:50 — A search, streaming

*Type "dentists in Austin whose owners are near retirement" into the natural-language box.
Watch the form fill itself in. Press Scout. Let the rows stream.*

> So I built the ranking layer. That sentence went to a language model which filled in the
> industry, the city and the weighting preset — nothing more; it never touches the data.
>
> Now businesses are arriving from OpenStreetMap. Each one gets its website crawled,
> politely and within robots.txt, its email checked with a real MX lookup, its phone
> validated, duplicates and chains merged away, and a score from zero to a hundred across
> five factors.

### 0:50–1:12 — Why the ranking is defensible

*Drag the succession slider. Rows reorder instantly. Open a lead's drawer.*

> Moving a weight re-ranks in the browser with no network call, because every lead carries
> its factor points and the total is just arithmetic. The same arithmetic runs on the
> server, and both are tested against one shared fixture.
>
> Open any row and every point has a reason. Note this one: no website at all, plus twenty.
> That is deliberate. A profitable local business whose owner never built a website is not
> bad data — it is the whole thesis.

### 1:12–1:34 — What is underneath

*Switch to the architecture diagram in the README.*

> FastAPI on a t3.micro Ubuntu box, in Docker Compose behind Caddy, which handles TLS
> itself. Postgres with Alembic migrations. The static front end is on Vercel. Every push
> runs the tests in CI. The deploy script rebuilds on the server, then polls the health
> endpoint for the new commit hash — if it does not appear, it rolls itself back.
>
> The API is a persistent process rather than a serverless function because one search
> holds a stream open for two minutes of rate-limited crawling.

### 1:34–1:55 — The honest part

*Switch to the terminal with `evals/results.md`.*

> The AI is deliberately small. It only reads a page when the regular expressions leave a
> gap, and I measured whether that is worth anything against sixteen hand-labelled
> homepages. Regex alone gets thirty-one of sixty-four fields right. Adding the model gets
> forty-one — and almost all of that gain is one field the regexes cannot do at all.
>
> The eval also caught that my extraction was running non-deterministically, and it caught
> one of my own labels being wrong.

### 1:55–2:05 — Close

*Back to the app. Export to HubSpot CSV. Show the file opening.*

> Export straight into HubSpot's import format, attribution included. Next I would add a
> real job queue and a second discovery source. Thanks for watching.

## Numbers used, and where they come from

| Claim | Source |
|---|---|
| 92 s cold, 4 s warm | README, "Caching and performance"; measured on the deployed server |
| Five scoring factors, weights 25/20/20/20/15 | `api/app/pipeline/score.py` |
| Same arithmetic both sides, one fixture | `api/tests/fixtures/golden_scores.json` |
| 31/64 regex, 41/64 with the model | `evals/results.md` |
| Almost all the gain is one field | `is_chain`, 1/16 → 8/16, same file |
| Health-checked rollback | `deploy/deploy.sh` |

## What not to say

- Do not claim the tool finds owners' personal contact details. It does not, by design.
- Do not describe the AI as "deciding" anything. It extracts facts; the score is arithmetic.
- Do not present the eval as a benchmark. It is sixteen pages, hand-labelled by one person,
  with a stated selection bias.
