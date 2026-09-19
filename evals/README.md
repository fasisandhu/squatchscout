# Extraction eval

Does asking a language model to read a small-business homepage actually beat regular
expressions? This folder answers that with numbers instead of an opinion.

```bash
cd api && .venv/Scripts/activate && cd ..
PYTHONPATH=api python evals/extraction_eval.py          # regex only, no network
PYTHONPATH=api python evals/extraction_eval.py --llm    # adds Groq, needs GROQ_API_KEY
```

Both modes rewrite `results.md`, which is committed for the shipping configuration.

## What is being measured

Four fields, taken from the same `ExtractionResult` the live pipeline stores:

| Field | The question the label answers |
|---|---|
| `founded_year` | The year the business itself was founded or opened, as a 4-digit year the page actually states. Not a copyright year, not a dentist's graduation year, not a reviewer's "I've been coming since 1988". |
| `owner_operated` | Does the page indicate an owner is actively involved in running the business? A named owner or founder, the phrase owner-operated, or a small family-owned firm all count. |
| `family_owned` | Does the page say the business is family owned? "Family dentistry" and "care for the whole family" describe the customers, not the ownership, and do not count. |
| `is_chain` | Does the business operate or belong to more than one location under the same brand? |

`null` means the page genuinely does not say. That is a real answer, not a missing one:
a tool that guesses on a silent page is worse than one that stays quiet.

Both extractors run against the same `PageBundle` the crawler would build, so the
comparison includes the title and meta description, not just the visible body text.

## Two accuracy views, and why

**Exact match** compares the prediction to the label including `null`.

**Positive-evidence agreement** folds `False` and `null` together for the three boolean
fields. This exists because `RegexSignals.family_owned` is a plain `bool`, so the regex
layer has no way to say "the page does not state this" — it reports `False`. Downstream
that is the same input to the scorer as a `null`, so scoring it wrong 12 times would
measure a type signature rather than an extraction failure. For `founded_year` the two
views are identical by construction.

Read the exact table for extraction quality and the positive-evidence table for the
effect on ranking.

## How the pages were chosen, including the bias

Sixteen real homepages, fetched on 2026-09-19 and stored verbatim in `golden/`.

1. Ten came straight out of the app's own discovery stage: Nominatim plus Overpass for
   six industries across six US cities, keeping every OSM record that carried a
   `website` tag, then picking a spread of industries and site builders.
2. Six more were added from the same discovery pool **after probing for founding-year
   language**, because the first ten contained only one page that stated a founding
   year and a column of almost all `null` measures very little.

Step 2 is a deliberate selection bias and it inflates the `founded_year` base rate well
above what the tool sees in the wild. The honest number from step 1 is that **1 of 10
randomly sampled small-business homepages stated a founding year**. Treat the
`founded_year` row as a comparison between the two extractors on pages that have
something to find, not as an estimate of real-world coverage.

The set deliberately includes hard cases:

- **gary-wilbert-roofing** is a parked "Coming Soon" page with 50 characters of text.
  Every label is `null`. Any non-null answer here is a hallucination.
- **mountain-view-service** has no founding date, but a customer review says "I've been
  taking vehicles here since 1988". The correct answer is `null`.
- **hurless-brothers** was founded by two brothers who announce on the page that they
  are handing the shop to two unrelated new owners. Owner-operated is true, family-owned
  is false, despite "Brothers" in the business name.
- **castle-dental** is a national brand; **sonrisas-dental**, **kunik-orthodontics** and
  **blue-wrench** are independent businesses with two or three locations each.
- **a-better-auto-repair** is a Wix site and **germanstar-auto** a Squarespace one.

## What the eval changed

Two things, neither of which was visible before there were numbers.

**The extraction call was not deterministic.** `complete_json` never set `temperature`,
so it ran at the provider default and reading the same page twice could give different
answers. The first attempt to improve the prompt appeared to cost 3 points out of 64;
repeating both arms at `temperature=0` showed the real difference was 1 changed
judgement out of 64. Fact extraction now runs at `temperature=0`, with a test asserting
the value reaches the client. Without that, this whole folder measures noise.

**Writing a description for every schema field did not help.** The four fields were
being sent to the model as bare names with no definition, which looked like an obvious
gap. Adding the same wording the ground truth uses, plus a system prompt warning that
customer reviews are not statements of fact, changed exactly one of 64 judgements and
moved neither score. It was reverted: the descriptions cost roughly 400 extra tokens on
every call against an 8,000-token-per-minute free-tier budget, and bought nothing
measurable on this model and this set.

| Configuration | Exact | Positive evidence |
|---|---|---|
| Regex only | 31/64 | 54/64 |
| Regex + LLM, bare schema, `temperature=0` (shipping) | 41/64 | 58/64 |
| Regex + LLM, described schema, `temperature=0` | 41/64 | 58/64 |

## Where the LLM helps, and where it does not

The entire exact-match gain is `is_chain`, which goes from 1/16 to 8/16 because
`RegexSignals` has no such field at all — chain detection in the pipeline proper is a
dataset-level check on repeated names and OSM `brand` tags, so a single page cannot
answer it. The model also recovers `kc-dental`'s 2006, which the regex misses because
"founded in July 2006" puts a month between the keyword and the year.

Against that, the model still misses real chains. Castle Dental is a national brand and
the model calls it independent. It also cannot retract a regex mistake: on
`mountain-view-service` the regex reads 1988 out of a customer review, the model
correctly returns null, and `merge_signals` only overrides on a non-null higher-confidence
value — so the wrong year survives into the final record. That is a merge-policy
limitation the eval surfaced, not a model failure.

## The labels are hand-made, and one of them was wrong

`labels.json` carries a `note` on every page recording the sentence the label rests on,
so a reader can disagree with a specific judgment rather than the whole table.

One label was wrong on the first pass. `tech-ridge-dental` was labelled "no founding
year, family ownership not stated" from its body text. The regex disagreed and returned
2011, which prompted a re-check: the page's own title and meta description read
"Serving Austin since 2011" and "a local, family-owned dental office".
The extractor was right and the label was wrong. Every label was then re-verified
against title and meta as well as body text. This is recorded rather than quietly fixed
because it is the failure mode an eval is supposed to catch, and it cuts both ways.

## Reproducibility

The HTML snapshots are committed, so the numbers are stable even as these businesses
redesign their sites. They were fetched once each, with the crawler's own user agent,
following redirects. Git normalised line endings on the first commit, so the files are
byte-identical to what was served apart from CRLF becoming LF; they are marked `binary`
in `.gitattributes` from that point on, so nothing rewrites them again. The extractors
collapse whitespace before matching, and the regex-only run produces the same 31/64 and
54/64 either way.

Two candidate sites returned 403 to the crawler's user agent and one returned 502. They
were dropped rather than re-fetched behind a disguised user agent, which is itself a
small honest signal about real-world crawl coverage.
