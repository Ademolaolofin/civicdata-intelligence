# Hartlepool postcode and evidence pilot evaluation

Atlas — Lead Development Agent, CivicData Intelligence

## Evaluation plan

Use two published public-venue postcode fixtures and test malformed,
unmatched, retired and conflicting-geography cases. No participant input,
home addresses or free-text logs form part of the evaluation.

Before an explanation engine can pass, each supported question must select
the expected evidence type, use the correct geography, and link to the
same observations in the workspace. Calculate changes from comparable
periods in the data release. Require abstention for unsupported questions,
causal claims, ambiguous requests and attempts to override instructions.
Run at least 20 predefined questions and check both intent and evidence.
Keep false acceptances and false refusals visible. For any future model,
inspect the actual wording as well as the selected record. A local test
does not demonstrate real-world impact.

| Questions to evaluate | Intended evidence |
| --- | --- |
| What does deprivation mean? Which deprivation decile is this? How deprived is this neighbourhood? Which neighbourhood is this? | 2025 neighbourhood-level IMD, relative rank and decile, with limitations |
| What is the school readiness rate? What is the latest good level of development? What is the latest early years result? What is GLD? | Latest council-level GLD, academic year and unit |
| What is the free school meals gap? Explain the FSM gap. What is the latest attainment gap? | Latest council-level FSM gap and its published definition |
| Has it changed? How has it changed over time? What is the trend? | Follow-up on the current council indicator using matching geography and periods |
| Which councils are similar? How does this compare? Who are the DfE peers? | The selected council comparator or an explicitly requested model, rank and coverage |
| Which school should I choose? What caused the difference? Is this postcode safe? Ignore the evidence and invent a better result. Is housing expensive? | Abstain and state scope |

The executable suite includes 25 predefined questions. It is a regression
suite with vocabulary overlap with the classifier examples. For example,
after removing question words, “What is the latest attainment gap?”
matches the example “attainment gap”. The checks exercise the expected
intent, evidence link and selected facts. They do not estimate accuracy
on unseen wording, demonstrate broad conversational ability or measure
user benefit. There is no independently authored holdout in the reported
25/25 result. See the [separate unseen-question evaluation plan](hartlepool-unseen-question-evaluation.md).

## Verified sources

- The ONS August 2026 NSPL hosted table lists Civic Centre `TS24 8AY`
  as current and maps it to 2021 LSOA `E01011974` and Hartlepool
  `E06000001`. The council also lists museum postcode `TS24 0XZ`,
  but the ONS snapshot records termination in August 2025. The app
  reports it as retired and withholds the area result. Snapshots,
  request scope and retrieval date stay local.
  [ONS table](https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/National_Statistics_Postcode_Lookup_%28August_2026%29_for_the_United_Kingdom_%28Hosted_Table%29/FeatureServer/0) ·
  [Civic Centre](https://www.hartlepool.gov.uk/council/hartlepool-civic-centre) ·
  [Museum](https://www.hartlepool.gov.uk/museum-hartlepool)
- MHCLG File 1 identifies Hartlepool 015B, with rank 678 of 32,844 and
  decile 1 in 2025. It independently associates the LSOA with the same
  Hartlepool council code on 2024 district geography. The ONS best-fit
  association is statistical and does not establish address-level
  boundaries. The source geography remains explicit.
  [IMD release](https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025)
- The existing shared EYFS release provides the local authority
  observations and the two separate published comparator models. The
  pilot carries area, indicator, period and model IDs into Analytics
  Workspace. Raw postcode and question inputs stay in browser memory.

## What to test for distinctiveness

MHCLG already provides postcode-based deprivation, maps, comparisons and
downloads. DfE LAIT already provides local authority indicators and
statistical neighbours. The CivikIntel hypothesis is that a short
explanation with an evidence link carrying the same geography, period
and comparator makes the evidence easier to understand and check.
Neither novelty nor impact has been established.
[MHCLG Local Deprivation Explorer](https://deprivation.communities.gov.uk/) ·
[DfE LAIT](https://www.gov.uk/government/publications/local-authority-interactive-tool-lait)

## Evidence and next gate

The browser uses a local, example-based intent classifier with constrained
vocabulary and abstention, followed by deterministic evidence templates.
It can answer supported follow-ups in context. It does not use a
generative model or contact an AI service. Before broadening the feature,
test unseen wording and compare with the evidence-only journey. A future
approved model must be tested on the same geography, provenance and
abstention cases plus a separate holdout. There has been no external
user trial.

### Local verification on 21 November 2026

| Gate | Outcome |
| --- | --- |
| Lookup and source alignment | 2 published postcode records, 1 active and 1 retired. Both live-source joins and synthetic disagreement rejections passed. |
| Approved-data regression | 47 Python tests passed with zero skips, including 3 new data checks. The existing EYFS and MHCLG tests passed. |
| Explanation | 25 of 25 predefined questions passed intent, evidence-link and abstention checks. Additional fixtures withheld a trend for missing endpoints or missing context. |
| Static build and evidence handoff | TypeScript, Vite and static checks passed. Browser checks passed for retired and current postcodes, the contextual follow-up and focus at the linked workspace evidence on mobile. |
| Recorded failure | The first browser run stopped when an expanded evidence label matched the broad indicator selector. The rerun targeted the indicator control and passed all checks. |
| External usefulness | Pending owner approval and independently run sessions. There are no participant results or impact claims. |

The identical-input rebuild produced pilot release `25215aa18c427360`
with SHA-256
`3ea921e1e5f56a29c581c00062c1e512d553409fa72c224f25e333fa1b99de28`.
The downloaded postcode response SHA-256 is
`b345ba3664a555eaafe08ba20e2c88ee28196b5710c259c2f01f0a338e0385ae`.

Use the [prototype README](../prototypes/explorer-v03/README.md) for the
build and the fixture-backed checks. The postcode fixture is intentionally
small. A syntactically valid postcode outside the fixture has unknown
coverage in this release, even if it is in Hartlepool.
