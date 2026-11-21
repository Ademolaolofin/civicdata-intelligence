# Hartlepool offline model experiment — decision brief

Atlas — Lead Development Agent, CivicData Intelligence

After recording the first independent classifier score, test one compact
instruction model offline as a question-to-evidence selector. The benefit
to test is whether people can ask in their own words, refer to the previous
indicator or comparison, and still reach the correct underlying evidence.

| | Existing explanation system | Proposed offline model |
| --- | --- | --- |
| How it works | Matches familiar wording to a fixed explanation and evidence. | Interprets more varied wording and follow-up context, then chooses from approved evidence or asks for clarification. |
| Likely benefit and limitation | Predictable with familiar questions and fast on ordinary hardware. It can decline valid questions that are phrased differently. | Could answer more of the same valid questions. It can still misunderstand wording or select the wrong evidence, even when its output looks correct. |
| Practical requirements | Existing local browser and the approved data release. | A compatible machine, approved model weights, licence and memory checks, and a latency budget. Both use the same data and source links. |
| How to judge it | Record the first independently scored baseline. | Test the same frozen cases and look for more useful answers and follow-ups while maintaining correct sources, geography and refusals. Record speed as well as correctness. |

Use the existing release and renderer. Give the model resolved area and
conversation context plus an allowlist of evidence IDs. Require a
structured selection of intent and evidence, a specific clarification,
or a decline. Application code validates the selection, including
geography, period, unit and comparator. Existing deterministic rules
calculate any changes and display the official source links. The model
supplies neither figures nor URLs in the first experiment. Host the
runtime locally with networking disabled and use only frozen public or
synthetic evaluation inputs. [Example local runtime and grammar support](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)

This requires one compatible machine, a model and weights licence
review, and a short CPU or GPU memory and latency check. Feasibility is
provisional until a candidate is tested on the intended hardware.
Structured output can still select the wrong evidence, so semantic
validation, explicit abstention and an evidence-only fallback remain
necessary. This experiment does not demonstrate arbitrary-topic coverage,
public readiness or user impact.

Compare both systems on the same frozen 40 cases. Keep model prompts
and routing rules fixed before the run. Report useful answer counts
and denominators for single turns and follow-ups, correct clarification
and abstention rates, source-link accuracy, any blocking grounding
failure and latency on the same hardware. Report paired wins and losses.
Require improved useful coverage with no fabricated or misattributed claims
and no loss of mandatory clarification or refusal. Set an acceptable
latency budget with the owner before testing. A later, separately approved
user trial can test task completion, time to find evidence and correct
geographic interpretation against the evidence-only experience.

Owner decisions are to nominate a blinded author and independent scorer,
agree a private handoff, and decide later whether to approve a candidate
model and machine for the experiment. No model has been installed or run.
