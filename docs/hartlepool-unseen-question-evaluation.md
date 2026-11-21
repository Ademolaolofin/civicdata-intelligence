# Hartlepool unseen-question evaluation plan

Atlas — Lead Development Agent, CivicData Intelligence

This is a proposed evaluation. The 25 existing checks remain regression
evidence for the deterministic baseline. They do not count toward the
unseen-question results.

## Prepare and protect the test set

1. Freeze the baseline commit, input hashes, release ID, available evidence
   and scoring rules before the first run. Have Technical Oversight author
   the questions from user tasks and the evidence catalogue without seeing
   the classifier examples or the 25 regression prompts.
2. Prepare 40 cases with expected behaviour fixed before testing. Use
   20 answerable single-turn cases covering definitions, deprivation,
   EYFS values, trends and peer comparisons. Use 10 contextual follow-up
   cases that depend on a selected indicator or comparator, including
   changes of subject or missing context. Use 10 unsupported or ambiguous
   cases, including unverified geography, unavailable observations,
   unsupported dates, irrelevant topics and attempts to override the
   evidence rules. Label a follow-up as answer, clarify or decline in the
   answer key as appropriate.
3. Use public example locations or synthetic inputs. Record each case’s
   expected answer type, context, evidence IDs, figures, unit, geography,
   period and applicable limitations. Check privately for wording overlap
   after freezing the set. Keep prompts hidden from implementers until
   scoring. Once a failure is used to tune a system, move that case into
   regression and use a fresh holdout for the next evaluation.

## Score the outcome

| Measure | Proposed gate |
| --- | --- |
| Coverage and usefulness | At least 80% of answerable cases return the expected useful answer. Report answerable denominators and results for single turns and follow-ups separately. Count false refusals as missed coverage. |
| Evidence validity | Every factual figure and comparison in a returned answer uses the correct released evidence, unit, geography, period and comparator. Its link opens that evidence. Any fabricated or misattributed claim blocks progression. |
| Clarification and abstention | Every case requiring clarification or refusal receives that behaviour. Unsupported claims and cross-boundary guesses are blocking failures. |
| Reproducibility | Record commit, release checksums, classifier or model version, configuration, scores, failure categories and retest results. Re-run the deterministic baseline against the same frozen cases. |

Report misses by category, including wrong intent, false refusal, wrong
evidence, missing contextual carry-through and link mismatch. Keep aggregate
outcomes and public test evidence in the review record. This holdout tests
generalisation inside the Hartlepool evidence scope. It does not measure
adoption or real-world impact.

## Practical next model step

Once separately approved, test a suitable local model without network
access as a **question-to-evidence selector**. Start with synthetic
questions and the fixed public evidence release. Give the model only
the selected context and a small allowlist of approved evidence IDs.
Require it to return a structured choice of intent and evidence IDs,
an explicit clarification request, or a decline. Use the validated
Python and release rules for figures, trends and comparability.

Validate the model output against the question scope, current context
and published evidence. Only known IDs with compatible geography, period
and comparator can reach the existing answer renderer. Render the source
links from the validated evidence, and fall back to a clarification or
decline when the output fails a check. Evaluate this model selector
against the frozen baseline on the same held-out questions. Consider
model-written prose only after that step passes, with independent checks
of every factual claim. Record the model's licence, version, retrieval
scope and runtime before using it. No model selection or transfer of
user information is part of this review.

## Evidence of technical contribution and user benefit

The technical contribution under review is an evidence handoff that
connects a postcode-linked statistical neighbourhood, correctly scoped
council measures, and reproducible source-linked explanations. Existing
tools already cover postcode lookup, deprivation and comparator analysis.
The potential originality is how this pilot combines these capabilities
and makes the explanation inspectable. Treat that as a hypothesis.

For a separately approved moderated trial, compare equivalent tasks with
and without explanations. Measure whether people can identify the correct
geography, locate the source and complete the task unaided. Report counts,
task times, failure modes and changes made after feedback. Record permitted
independent reviewer observations and verifiable release history. Keep
personal endorsement records private. Product evidence documents
contribution and usefulness. It does not determine endorsement eligibility.
