"""Measure regex-only against regex+LLM extraction on hand-labelled pages (spec 7.4).

Run from the repo root with the API venv active:

    PYTHONPATH=api python evals/extraction_eval.py            # regex only, offline
    PYTHONPATH=api python evals/extraction_eval.py --llm      # needs GROQ_API_KEY

Writes evals/results.md and prints the same tables.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.llm.client import LLMPool
from app.pipeline.crawl import PageBundle, PageText, clean_html, quality
from app.pipeline.extract_llm import extract_with_llm, merge_signals
from app.pipeline.extract_regex import extract_signals

ROOT = Path(__file__).parent
FIELDS = ["founded_year", "owner_operated", "family_owned", "is_chain"]
BOOL_FIELDS = {"owner_operated", "family_owned", "is_chain"}
YEAR = datetime.now().year


def bundle_for(slug: str, url: str) -> PageBundle:
    """Rebuild exactly the PageBundle the crawler would hand the extractors."""
    html = (ROOT / "golden" / f"{slug}.html").read_text(encoding="utf-8", errors="ignore")
    title, meta, text, links, head = clean_html(html)
    page = PageText(
        url=url,
        title=title,
        meta_description=meta,
        visible_text=text,
        text_quality=quality(text),
        raw_head=head,
        links=links,
    )
    return PageBundle(domain=slug, pages=[page], fetched_at=datetime.now())


def as_label(v: str | None) -> object | None:
    """Undo merge_signals' stringification so predictions compare against JSON labels."""
    if v is None:
        return None
    if v in ("true", "false"):
        return v == "true"
    try:
        return int(v)
    except ValueError:
        return v


def predictions(signals: list) -> dict[str, object | None]:
    by_key = {s.key: s for s in signals}
    out: dict[str, object | None] = {}
    for f in FIELDS:
        s = by_key.get(f)
        # family_owned is a plain bool on RegexSignals, so regex reports False rather than
        # staying silent. A label of null means "the page does not say", and False is a
        # different answer from that, so it is compared as-is rather than folded into None.
        out[f] = as_label(s.value) if s else None
    return out


def _same_positive(field: str, pred: object | None, truth: object | None) -> bool:
    """Did the extractor find the positive fact when it was there, and stay quiet otherwise?

    RegexSignals.family_owned is a plain bool, so the regex layer cannot say "the page does
    not state this" -- it reports False. Downstream that is the same input to the scorer as
    a null, so this view folds False and None together for the boolean fields. Exact match
    is reported separately; for founded_year the two views are identical by construction.
    """
    if field in BOOL_FIELDS:
        return bool(pred) is bool(truth)
    return pred == truth


def table(title: str, header: list[str], rows: list[list[str]]) -> list[str]:
    return [
        title,
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
        *["| " + " | ".join(r) + " |" for r in rows],
        "",
    ]


async def main(use_llm: bool) -> None:
    labels = {
        k: v
        for k, v in json.loads((ROOT / "labels.json").read_text(encoding="utf-8")).items()
        if not k.startswith("_")
    }
    settings = Settings()
    pool = LLMPool(settings) if use_llm else None
    if use_llm and not (pool and pool.enabled):
        raise SystemExit("--llm needs GROQ_API_KEY to be set (see api/.env.example)")

    correct = {m: dict.fromkeys(FIELDS, 0) for m in ("regex", "merged")}
    positive = {m: dict.fromkeys(FIELDS, 0) for m in ("regex", "merged")}
    rows: list[tuple[str, dict]] = []
    statuses: dict[str, str] = {}

    for slug, lab in labels.items():
        bundle = bundle_for(slug, lab["url"])
        regex = extract_signals(bundle, YEAR)
        regex_pred = predictions(merge_signals(regex, None))

        llm = None
        if pool is not None:
            llm, status = await extract_with_llm(
                pool, bundle, lab["osm_name"], lab["country"], YEAR
            )
            statuses[slug] = status
            if status != "ok":
                print(f"  {slug}: llm {status}")
        merged_pred = predictions(merge_signals(regex, llm))

        for f in FIELDS:
            truth = lab.get(f)
            correct["regex"][f] += regex_pred[f] == truth
            correct["merged"][f] += merged_pred[f] == truth
            positive["regex"][f] += _same_positive(f, regex_pred[f], truth)
            positive["merged"][f] += _same_positive(f, merged_pred[f], truth)
        rows.append((slug, {f: (lab.get(f), regex_pred[f], merged_pred[f]) for f in FIELDS}))

    n = len(labels)
    mode = f"regex + LLM ({', '.join(settings.groq_models)})" if use_llm else "regex only"
    out: list[str] = [
        "# Extraction eval",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} · {n} hand-labelled homepages · {mode}",
        "",
        "Correct means the prediction equals the hand label exactly, including null for "
        "*the page does not say*. See `README.md` for how the pages were chosen and what "
        "each field asks.",
        "",
    ]
    out += table(
        "## Accuracy per field",
        ["Field", "Regex only", "Regex + LLM"],
        [
            [
                f,
                f"{correct['regex'][f]}/{n}",
                f"{correct['merged'][f]}/{n}" if use_llm else "—",
            ]
            for f in FIELDS
        ],
    )
    tot = n * len(FIELDS)
    out += [
        f"Overall exact: regex {sum(correct['regex'].values())}/{tot}"
        + (f" · regex + LLM {sum(correct['merged'].values())}/{tot}" if use_llm else ""),
        "",
    ]
    out += table(
        "## Positive-evidence agreement (False and null folded together for the booleans)",
        ["Field", "Regex only", "Regex + LLM"],
        [
            [
                f,
                f"{positive['regex'][f]}/{n}",
                f"{positive['merged'][f]}/{n}" if use_llm else "—",
            ]
            for f in FIELDS
        ],
    )
    out += [
        "This is the view that matches what the scorer consumes: it asks whether the "
        "extractor found the positive fact when the page stated one, not whether it "
        "distinguished *false* from *not stated*.",
        "",
        f"Overall positive-evidence: regex {sum(positive['regex'].values())}/{tot}"
        + (f" · regex + LLM {sum(positive['merged'].values())}/{tot}" if use_llm else ""),
        "",
    ]
    out += table(
        "## Per page — truth / regex / merged",
        ["Page", *FIELDS],
        [[slug, *[f"{t} / {r} / {m}" for t, r, m in vals.values()]] for slug, vals in rows],
    )
    if statuses:
        bad = {k: v for k, v in statuses.items() if v != "ok"}
        out += [
            f"LLM call status: {len(statuses) - len(bad)}/{len(statuses)} ok"
            + (f"; not ok: {bad}" if bad else ""),
            "",
        ]

    text = "\n".join(out)
    (ROOT / "results.md").write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="also run Groq extraction")
    asyncio.run(main(ap.parse_args().llm))
