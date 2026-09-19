# Sample dataset

One complete SquatchScout run, exported in both formats the app offers.

| File | What it is |
|---|---|
| `sample-search-austin-dentist.csv` | The generic export: every field the app holds, including the per-lead scoring reasons. |
| `sample-search-austin-dentist-hubspot.csv` | The same leads reshaped into HubSpot's company-import columns, ready to upload. |

## How it was generated

| | |
|---|---|
| Query | Dentists · Austin, TX · limit 60 |
| Geocoded to | Austin, Travis County, Texas, United States |
| Weights | `balanced` — reachability 25, establishment 20, digital_gap 20, buybox 20, succession 15 |
| Run on | 2026-09-19, against a cold database so nothing was served from cache |
| Wall clock | 137 s end to end, of which the AI refinement pass was the last 90 s |
| Search id | `b29bb1e3c9444bc49a3338e6a14caa4a` |

The same run is what [`../notebooks/demo.ipynb`](../notebooks/demo.ipynb) walks through, so
the charts there and the rows here describe the same 54 businesses.

## What is in it

| | Leads |
|---|---|
| Total | 54 |
| Tier A / B / C / D | 7 / 4 / 27 / 16 |
| Score range | 22 to 95 |
| Had a website in OpenStreetMap | 18 |
| Site crawled successfully | 12 |
| Reachable but the crawl failed | 6 |
| No website at all | 36 |
| At least one contact | 18 |
| At least one MX-verified email | 7 |
| Flagged as a likely chain | 2 |
| Refined by the language model | 12 |

Two thirds of these businesses have no website. That is the honest coverage number for
this market, and it is also the point: `digital_gap` scores a missing website as upside
rather than as missing data, because an owner who never built one is an owner who is not
optimising for growth.

## The contact data

Phone numbers and email addresses here are **public business contact details**, taken from
two places only: the OpenStreetMap record itself, and the business's own website, crawled
in line with its `robots.txt` under a named user agent. No personal or residential data,
no LinkedIn, no people-search sources, no contact was bought or inferred.

Emails carry a verification status from an MX lookup plus a disposable-domain check;
phone numbers are validated with `phonenumbers`. A value marked `unverified` failed one of
those checks and should be treated as a guess.

## Attribution

Business locations, names and many of the contact details come from OpenStreetMap.

> Data © OpenStreetMap contributors, available under the
> [Open Database License](https://opendatacommons.org/licenses/odbl/).

That line is carried in the first row of both CSV files as well, so it travels with the
data if someone opens only the export.

## A note on the generic file

The generic CSV is written with a UTF-8 byte-order mark so Excel opens accented business
names correctly. The HubSpot file deliberately has no BOM, because HubSpot's importer
treats it as part of the first column name.
