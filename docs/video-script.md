# Video script — 2 minutes

285 spoken words, which lands at 1:57 at a normal 145 words per minute. Every number below
is measured and lives in this repo; do not round any of them up on camera.

The narration is kept as a separate plain-text file with no stage directions in it, so it
can be pasted straight into a teleprompter. This file is the shot list that goes with it:
one section per spoken paragraph.

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

| Paragraph | Ends at | What is on screen |
|---|---|---|
| 1 | 0:15 | SaaSquatch Leads' search page, then cut to this app's empty state |
| 2 | 0:26 | Type the plain-language query, press **Fill form**, let the fields populate |
| 3 | 0:39 | Press **Scout**. Rows stream in. Let the status line do the talking |
| 4 | 0:54 | Drag the succession slider. Rows reorder with no network activity |
| 5 | 1:08 | Open a lead. Scroll to Digital-maturity gap so "no website at all +20" is visible |
| 6 | 1:28 | The architecture diagram in the README |
| 7 | 1:48 | A terminal showing `evals/results.md`, the accuracy table on screen |
| 8 | 1:57 | Back to the app. Export the HubSpot CSV and show the downloaded file |

Two shots carry the argument, so give them the most care. Paragraph 5 is the only moment
that explains why a missing website scores *up*, which is the whole business thesis.
Paragraph 7 is the only moment that shows the work was measured rather than asserted.

If a take runs long, cut paragraph 6 down to the first sentence. The architecture is in the
README and the evaluator can read it; the thesis and the measurement are not recoverable
from anywhere else in two minutes.

## Numbers used, and where they come from

| Claim | Source |
|---|---|
| Ninety seconds of crawling per search | README, "Caching and performance"; 92 s cold on the deployed server |
| Five scoring factors, weights 25/20/20/20/15 | `api/app/pipeline/score.py` |
| Same arithmetic both sides, one fixture | `api/tests/fixtures/golden_scores.json` |
| 31/64 regex, 41/64 with the model | `evals/results.md` |
| Sixteen hand-labelled homepages | `evals/labels.json` |
| The evaluation caught two things I had wrong | `evals/README.md`, "What the eval changed" |
| Health-checked rollback | `deploy/deploy.sh` |

## What not to say

- Do not claim the tool finds owners' personal contact details. It does not, by design.
- Do not describe the AI as "deciding" anything. It extracts facts; the score is arithmetic.
- Do not present the eval as a benchmark. It is sixteen pages, hand-labelled by one person,
  with a stated selection bias.
