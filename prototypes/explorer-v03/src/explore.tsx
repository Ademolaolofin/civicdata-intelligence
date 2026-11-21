import { useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import type { Model, Release } from "./data";
import { answer, inspectLink, resolvePostcode } from "./pilot";
import { Indicator, NeighbourhoodEvidence } from "./views";

function Explore({ release }: { release: Release }) {
  const pilot = release.pilot!;
  const [postcode, setPostcode] = useState("");
  const [result, setResult] = useState<ReturnType<typeof resolvePostcode>>();
  const [context, setContext] = useState<{ metric: string | null; model: Model }>({ metric: null, model: "mhclg" });
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ReturnType<typeof answer>>();
  const metric = release.metrics[0];
  const period = metric.periods.at(-1)!;
  const area = result?.state === "resolved" ? result.area : null;
  const message = result?.state === "invalid" ? "Enter a full UK postcode, such as TS24 8AY."
    : result?.state === "outside" ? "This postcode is outside the verified pilot lookup. No area has been assumed."
    : result?.state === "retired" ? `The ONS snapshot records this postcode as retired in ${String(result.date).slice(0, 4)}-${String(result.date).slice(4)}. No area has been selected.`
    : result?.state === "unresolved" ? "The neighbourhood link could not be verified. No area has been selected."
    : area ? "The postcode is linked to a statistical neighbourhood in Hartlepool." : "";

  function lookup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResult(resolvePostcode(pilot, postcode));
    setQuestion("");
    setResponse(undefined);
    setContext({ metric: null, model: "mhclg" });
  }

  function ask(value: string) {
    if (!area) return;
    const output = answer(release, area, value, context);
    setResponse(output);
    setContext(output.context);
  }

  return <>
    <form className="panel finder" onSubmit={lookup}>
      <label htmlFor="pilot-postcode">Public test postcode</label>
      <input id="pilot-postcode" autoComplete="off" maxLength={12} value={postcode}
        onChange={event => setPostcode(event.target.value)} aria-describedby="pilot-help"/>
      <p id="pilot-help">Try Hartlepool Civic Centre, TS24 8AY. This limited lookup runs in your browser. Use a public test location.</p>
      <button className="button">Find area</button>
    </form>
    <p role="status" className="section-item">{message}</p>
    {area && <>
      <div className="cards">
        <NeighbourhoodEvidence pilot={pilot} area={area}/>
        <section aria-label="Local authority evidence">
          <p className="meta">Local authority · {release.authority.name}</p>
          <Indicator metric={metric} period={period}/>
        </section>
      </div>
      <a href={inspectLink(release, area, metric.id, period.label, "mhclg", "indicator-evidence")}>Inspect the evidence in Analytics Workspace</a>
      <section className="panel section-item" aria-labelledby="question-heading">
        <h2 id="question-heading">Ask about the evidence</h2>
        <p>Local question matching selects a verified explanation. Try “What is GLD?” and then “How has it changed over time?”</p>
        <form className="finder" onSubmit={event => { event.preventDefault(); ask(question); }}>
          <label htmlFor="pilot-question">Question</label>
          <input id="pilot-question" autoComplete="off" value={question} maxLength={160}
            onChange={event => setQuestion(event.target.value)}/>
          <button className="button">Explain</button>
        </form>
        <div aria-live="polite" className="section-item">
          {response && <><p>{response.text}</p>{response.href && <a href={response.href}>Inspect supporting evidence</a>}</>}
        </div>
      </section>
    </>}
  </>;
}

const container = document.getElementById("explore");
if (container?.dataset.release) {
  fetch(container.dataset.release).then(async response => {
    if (!response.ok) throw new Error("Release unavailable");
    const release: Release = await response.json();
    if (release.schema !== 1 || !release.pilot) throw new Error("Pilot release unavailable");
    createRoot(container).render(<Explore release={release}/>);
  }).catch(() => {
    container.textContent = "The local pilot release could not load. You can still open the Hartlepool profile.";
  });
}
