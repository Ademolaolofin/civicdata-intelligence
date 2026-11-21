# Hartlepool independent holdout handoff

Atlas — Lead Development Agent, CivicData Intelligence

The frozen baseline is integration commit
`fbcd9b1056bb76fd69e114e33e2a21bd5a6a4111`, with the reviewed PR #6 tree
and pilot release `25215aa18c427360`. The release used for the prior
regression run has SHA-256
`3ea921e1e5f56a29c581c00062c1e512d553409fa72c224f25e333fa1b99de28`.
If official sources are fetched anew, verify the reviewed input hashes and
compare the release payload. Record its new full hash if the only
difference is the retrieval timestamp. Preserve the existing classifier
and evidence rules until the initial holdout is scored.

## Technical Oversight handoff

Give an independent author only the [standalone author packet](hartlepool-independent-author-packet.md)
and frozen evidence release. Keep the author
blind to the classifier examples and regression prompts. Ask for 20
single-turn, 10 multi-turn and 10 unsupported or ambiguous cases. Mark
each expected response as answer, clarify or decline. Use public or
synthetic locations and keep the question set and answer key private
until the first run. Record their SHA-256 digests before replay. A reviewer
can run the replay locally or transfer the frozen fixture through an
approved private channel. The development agent should receive scored
outcomes before using any failed questions to tune the system.

The JSON manifest has a `baseline` commit, `release` ID and a `cases`
array. Each case has a unique `id`, `category` (`single`, `followup`
or `unsupported`), an LSOA `area`, and a `turns` array of question strings.
Optionally seed `context` with `metric` (an ID or null) and `model`
(`mhclg` or `dfe`). Each follow-up inherits the preceding answer's
context. The answer key is separate. It should give each turn’s expected
action, supported figures, units, geography, period, comparator, source
and evidence destination where applicable.

## What an independent reviewer can do

- **Write and freeze the cases:** The standalone packet and public
  evidence release are sufficient. A text editor or spreadsheet can be
  used to prepare the questions and separate answer key. Record a SHA-256
  digest of each file before execution. Atlas's workspace and source
  code are unnecessary for authorship.
- **Run and score browser cases:** The scorer can check out the frozen
  commit in a separate environment and rebuild with the public sources
  and locked frontend dependencies. Use the
  [clean build instructions](https://github.com/Ademolaolofin/civicdata-intelligence/pull/6#issuecomment-7063480312)
  and [prototype guide at the frozen commit](https://github.com/Ademolaolofin/civicdata-intelligence/blob/fbcd9b1056bb76fd69e114e33e2a21bd5a6a4111/prototypes/explorer-v03/README.md#optional-local-postcode-and-evidence-pilot).
  The app can be served on the reviewer's own loopback address. Use the
  same release and verify its fingerprint before recording outputs.
  The scorer needs the private questions and answer key. They can record
  responses and evidence destinations manually, without Atlas's
  environment, a cloud service or any model runtime.
- **Handle baseline context:** Start a new lookup between unrelated
  cases. Preserve the session between turns of a follow-up. If a case
  needs a current indicator or model, specify a preparatory turn in
  the frozen plan. Cases that require injecting state the interface
  cannot reproduce need a separately shared replay tool or should be
  designed as browser-executable cases before the freeze.

The optional automated replay tool stays outside this documentation PR.
It can be considered for separate review if manual verification is
insufficient. Neither scoring nor verification of evidence links
depends on that tool.

Keep the manifest, key and results in private local storage. An independent reviewer
scores the responses against the frozen answer key, distinguishes generic
refusal from a useful clarification, verifies each evidence link and
reports counts, denominators and failures by category.

The narrow vocabulary gate in the baseline can refuse valid questions
with unfamiliar wording. Its follow-up context contains the current
indicator and comparator. Broader paraphrases, ambiguity and follow-up
scope are open evaluation questions.

## Offline model trial proposal

After the baseline score is recorded, run a small locally hosted
instruction model as an evidence selector with a bounded output schema.
For example, llama.cpp supports constraining output with a grammar or
JSON Schema. Test RAM and latency and review the model weights licence
before choosing a candidate. Use fixed public or synthetic inputs with
network access disabled. [llama.cpp grammar documentation](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)

Give the model only the resolved context and approved evidence catalogue.
Accept a structured answer intent with known evidence IDs, a clarification,
or an abstention. Verify context, geography, period, unit and comparator
eligibility in application code before rendering an answer. Use existing
deterministic calculations and source links. Treat structurally valid
but semantically unsupported output as a failure. Keep the evidence-only
view available if the model is slow, unavailable or uncertain. Compare
both systems on the same frozen holdout before considering model-written
prose. No model has been installed or run for this preparation.

The contribution to assess is source-verifiable transfer from a
postcode-linked neighbourhood and council evidence into the exact
analyst view. Compare against an evidence-only journey and record time
to find evidence, correct interpretation of geography, task completion
and independent reviewer observations. Treat an offline correctness
gain as distinct from measured user benefit. Any external participation
requires separate approval.
