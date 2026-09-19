# Extraction eval

Generated 2026-09-19 17:58 · 16 hand-labelled homepages · regex + LLM (qwen/qwen3.8-27b, openai/gpt-oss-20b)

Correct means the prediction equals the hand label exactly, including null for *the page does not say*. See `README.md` for how the pages were chosen and what each field asks.

## Accuracy per field

| Field | Regex only | Regex + LLM |
|---|---|---|
| founded_year | 14/16 | 15/16 |
| owner_operated | 11/16 | 14/16 |
| family_owned | 5/16 | 4/16 |
| is_chain | 1/16 | 8/16 |

Overall exact: regex 31/64 · regex + LLM 41/64

## Positive-evidence agreement (False and null folded together for the booleans)

| Field | Regex only | Regex + LLM |
|---|---|---|
| founded_year | 14/16 | 15/16 |
| owner_operated | 12/16 | 15/16 |
| family_owned | 16/16 | 15/16 |
| is_chain | 12/16 | 13/16 |

This is the view that matches what the scorer consumes: it asks whether the extractor found the positive fact when the page stated one, not whether it distinguished *false* from *not stated*.

Overall positive-evidence: regex 54/64 · regex + LLM 58/64

## Per page — truth / regex / merged

| Page | founded_year | owner_operated | family_owned | is_chain |
|---|---|---|---|---|
| a-better-auto-repair | None / None / None | None / None / None | None / False / False | False / None / None |
| animal-hospital-signal-mtn | 1989 / 1989 / 1989 | None / None / None | None / False / False | False / None / None |
| blue-wrench | 1989 / 1989 / 1989 | None / None / None | None / False / False | True / None / None |
| castle-dental | None / None / None | False / None / None | False / False / False | True / None / True |
| cat-clinic-chattanooga | None / None / None | None / None / None | None / False / False | False / None / None |
| gary-wilbert-roofing | None / None / None | None / None / None | None / False / False | None / None / None |
| germanstar-auto | None / None / None | None / None / None | None / False / False | False / None / None |
| hurless-brothers | None / None / None | True / None / True | False / False / True | False / None / False |
| kc-dental | 2006 / None / 2006 | True / None / True | None / False / False | False / None / False |
| kunik-orthodontics | 1991 / 1991 / 1991 | True / None / None | None / False / False | True / None / None |
| mountain-view-service | None / 1988 / 1988 | True / None / True | None / False / False | False / None / False |
| plunger-plumber | None / None / None | True / True / True | True / True / True | False / None / False |
| red-bank-animal-hospital | None / None / None | None / None / None | None / False / False | False / None / None |
| sonrisas-dental | None / None / None | None / None / None | None / False / False | True / None / False |
| tech-ridge-dental | 2011 / 2011 / 2011 | True / True / True | True / True / True | False / None / False |
| wizard-auto-specialties | 1987 / 1987 / 1987 | True / True / True | True / True / True | False / None / False |

LLM call status: 16/16 ok

