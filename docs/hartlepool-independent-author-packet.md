# Hartlepool independent evaluation — author and scorer packet

Atlas — Lead Development Agent, CivicData Intelligence

This packet is sufficient for an independent author to design and label
questions. The coordinator should share this packet and the frozen public
evidence only. An author who has inspected the classifier examples or
regression questions is ineligible. The development agent should receive
the aggregate score and failure categories after the first run is recorded.

## Author brief

Create 40 natural questions from the needs of residents and analysts.
Vary vocabulary, sentence structure and how much context is supplied.
Use public pilot locations or synthetic inputs. Keep the question manifest
and the independently written answer key in separate files. Avoid personal
postcodes, addresses, identifiers or information about individuals.

| Category | Count | Coverage |
| --- | ---: | --- |
| Answerable single turn | 20 | Cover neighbourhood deprivation, council early-years figures and definitions, changes over time, and council comparisons. Include different periods and phrasing. |
| Contextual follow-up | 10 | Use two to four turns. Include a retained indicator or model, a change of subject and missing or ambiguous context. Mark what context should carry over. |
| Unsupported or ambiguous | 10 | Mix information outside coverage, unsupported dates, incompatible geography, missing evidence, causal or predictive requests and attempts to override evidence limits. Some should require clarification and some should require a refusal. |

Allocate the category based on the task, then label every turn in the key
as **answer**, **clarify** or **decline**. Do not assume a question is
unanswerable just because the current interface may reject its wording.
Use the task’s evidence needs and the catalogue below as the basis.
Keep scripted questions under 160 characters to fit the pilot UI.

## Frozen evidence catalogue

Use release `25215aa18c427360`. The reviewed full release SHA-256 is
`3ea921e1e5f56a29c581c00062c1e512d553409fa72c224f25e333fa1b99de28`.
The statistical neighbourhood and council are separate areas.

| Evidence | Geography | Coverage and meaning |
| --- | --- | --- |
| Postcode association | ONS August 2026 best-fit lookup | Civic Centre public postcode `TS24 8AY` links to statistical neighbourhood `E01011974` and Hartlepool council `E06000001`. Museum public postcode `TS24 0XZ` is recorded as retired in August 2025. Association is statistical, and does not establish an address boundary. A postcode missing from the pilot cannot be assigned an area by inference. |
| Index of Multiple Deprivation | Hartlepool 015B (`E01011974`), 2021 statistical neighbourhood | IMD 2025 rank **678 of 32,844** in England and decile **1**. Decile 1 is the most deprived tenth and rank 1 is most deprived. This is relative neighbourhood evidence and does not describe a household, individual or the whole council. Only one release is included. |
| Good level of development (`19346`) | Hartlepool council (`E06000001`) | Share of assessed children achieving a good level of development at age five, in per cent. |
| Free school meals development gap (`27666`) | Hartlepool council (`E06000001`) | GLD rate for children ineligible for free school meals minus the rate for eligible children, in percentage points. |
| MHCLG broad neighbours (`mhclg`) | Council relationships, 2026 release | 15 published peers for Hartlepool. The released series has 15 numeric and 15 eligible peers for each of the two indicators in each available year. |
| DfE Children’s Services neighbours (`dfe`) | English upper-tier councils, April 2023 geography; published 28 May 2025 | 10 published peers for Hartlepool. The released series has 10 numeric and 10 eligible peers for each of the two indicators in each available year. Applying this model to earlier outcomes is contextual. |

| Academic year | Hartlepool GLD (per cent) | Hartlepool FSM gap (percentage points) |
| --- | ---: | ---: |
| 2021/22 | 64.44 | 16.54 |
| 2022/23 | 64.51 | 19.38 |
| 2023/24 | 65.53 | 17.17 |
| 2024/25 | 65.04 | 19.25 |

These are display values rounded to two decimal places. For a change
between periods, subtract the unrounded source values in the release,
then round the difference. The two peer models define separate ranked
groups. A peer rank indicates similarity under that model. A difference
over time or across peers does not establish a cause. If you need a
particular peer row, use the frozen release rather than this summary.
For unavailable-evidence cases, use a year, geography or measure absent
from the frozen release. The two listed target series contain values in
all four years. Do not change the release to create a missing value.

[ONS postcode lookup methodology](https://www.ons.gov.uk/methodology/geography/geographicalproducts/postcodeproducts) ·
[MHCLG IMD 2025](https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025) ·
[DfE EYFS 1.0.1](https://api.education.gov.uk/statistics/v1/data-sets/019ac0fb-e082-7202-871f-439d6d036893/csv?dataSetVersion=1.0.1) ·
[MHCLG broad comparator methodology](https://www.gov.uk/government/publications/local-outcomes-framework/local-government-outcomes-statistical-neighbours-model) ·
[DfE comparator release](https://www.gov.uk/government/publications/local-authority-interactive-tool-lait)

## Files and freeze

Give each case a neutral unique ID. The question manifest contains the
baseline `fbcd9b1056bb76fd69e114e33e2a21bd5a6a4111`, release ID, and a
list of cases with `id`, `category` (`single`, `followup`, `unsupported`),
LSOA `area` and `turns`. Where a task starts with a selected indicator
and comparator, add `context` with `metric` (metric ID or null) and
`model` (`mhclg` or `dfe`).

In the separate answer key, record each turn’s expected action, minimum
useful facts, approved source and evidence destination where applicable.
Include expected indicator, area, date, unit, comparator and any limitation
that changes the meaning. Define acceptable rounding or alternative
wording before testing. The three destinations are the neighbourhood
evidence section, council indicator and trend evidence section, and
published peer evidence section of Analytics Workspace.

Freeze and hash both files before the first run. Keep the key private
and separate from the engine input. Record the date, baseline, release
and hashes. Keep session-level results private through initial scoring.
Share aggregate outcomes and failure categories in the review record.

## Scoring guidance

- **Answer:** Award a pass only if the response answers the task, uses the
  right area, period, unit and comparator, and its link opens the matching
  evidence. Judge meaning and provenance. Exact wording is unnecessary.
  Record a false refusal if the evidence could support the answer.
- **Clarify:** The response should identify what is ambiguous and ask for
  or identify the missing detail. A generic refusal is safe but does not
  pass a clarification case.
- **Decline:** The response should explain the relevant evidence or scope
  limitation without asserting a guess or linking to unrelated evidence.
- **Multi-turn cases:** Score each turn for correctness and safety, then
  count a case as useful only when it completes the expected journey with
  the right context. Keep single-turn and follow-up denominators separate.

Report both turn and case counts, eligible denominators, all misses and
blocking failures. The proposed gate is at least 80% useful coverage of
answerable cases, every factual claim traceable to the correct evidence,
and every required clarification or decline handled correctly.
Fabricated figures, wrong geographic attribution and invalid comparisons
block progression. Record the first run before opening any tuning task.
Move used failures into regression and reserve fresh questions for the
next independent check.
