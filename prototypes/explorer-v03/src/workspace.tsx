import { useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import type { Model, Release } from "./data";
import { NeighbourhoodEvidence, WorkspaceResults } from "./views";

function Workspace({ release }: { release: Release }) {
  const params = new URLSearchParams(window.location.search);
  const requestedArea = params.get("area");
  const area = requestedArea && release.pilot?.areas[requestedArea] ? requestedArea : null;
  const firstMetric = release.metrics.find(metric => metric.id === params.get("metric")) ?? release.metrics[0];
  const [metric, setMetric] = useState(firstMetric);
  const [year, setYear] = useState(firstMetric.periods.find(period => period.label === params.get("period"))?.label
    ?? firstMetric.periods.at(-1)!.label);
  const [model, setModel] = useState<Model>(params.get("model") === "dfe" ? "dfe" : "mhclg");
  const [draftMetric, setDraftMetric] = useState(metric.id);
  const [draftYear, setDraftYear] = useState(year);
  const [draftModel, setDraftModel] = useState(model);
  const [announcement, setAnnouncement] = useState("");
  const period = metric.periods.find(item => item.label === year)!;
  const draftPeriods = release.metrics.find(item => item.id === draftMetric)!.periods;
  useEffect(() => {
    const anchor = window.location.hash.slice(1);
    if (["neighbourhood-evidence", "indicator-evidence", "peers"].includes(anchor)) {
      document.getElementById(anchor)?.focus();
    }
  }, []);

  function apply(metricId: string, periodLabel: string, modelId: Model) {
    const nextMetric = release.metrics.find(item => item.id === metricId) ?? release.metrics[0];
    const nextPeriod = nextMetric.periods.find(item => item.label === periodLabel) ?? nextMetric.periods.at(-1)!;
    setMetric(nextMetric);
    setYear(nextPeriod.label);
    setModel(modelId);
    setDraftMetric(nextMetric.id);
    setDraftYear(nextPeriod.label);
    setDraftModel(modelId);
    setAnnouncement(`Showing ${nextMetric.label}, ${nextPeriod.label}, ${release.models[modelId].label}.`);
    const url = new URL(window.location.href);
    url.search = new URLSearchParams({
      authority: release.authority.code, metric: nextMetric.id, period: nextPeriod.label, model: modelId,
      ...(area ? { area } : {}),
    }).toString();
    window.history.replaceState(null, "", url);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    apply(draftMetric, draftYear, draftModel);
  }

  return <>
    {area && release.pilot && <NeighbourhoodEvidence pilot={release.pilot} area={area}/>}
    <form className="filters panel" onSubmit={submit}>
      <label>Authority<select defaultValue={release.authority.code}>
        <option value={release.authority.code}>{release.authority.name}</option>
      </select></label>
      <label>Indicator<select name="metric" value={draftMetric} onChange={event => {
        const next = release.metrics.find(item => item.id === event.target.value)!;
        setDraftMetric(next.id);
        if (!next.periods.some(item => item.label === draftYear)) setDraftYear(next.periods.at(-1)!.label);
      }}>
        {release.metrics.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select></label>
      <label>Reporting period<select name="year" value={draftYear} onChange={event => setDraftYear(event.target.value)}>
        {draftPeriods.map(item => <option key={item.label}>{item.label}</option>)}
      </select></label>
      <label>Comparator<select name="model" value={draftModel} onChange={event =>
        setDraftModel(event.target.value === "dfe" ? "dfe" : "mhclg")}>
        {(Object.keys(release.models) as Model[]).map(key =>
          <option key={key} value={key}>{release.models[key].label}</option>)}
      </select></label>
      <button className="button">Apply filters</button>
    </form>
    <p className="visually-hidden" role="status">{announcement}</p>
    <WorkspaceResults release={release} metric={metric} period={period} model={model}
      onPeriod={value => apply(metric.id, value, model)}/>
  </>;
}

const container = document.getElementById("workspace");
if (container?.dataset.release) {
  fetch(container.dataset.release).then(async response => {
    if (!response.ok) throw new Error("Release unavailable");
    const release: Release = await response.json();
    if (release.schema !== 1) throw new Error("Unsupported release schema");
    createRoot(container).render(<Workspace release={release}/>);
  }).catch(() => {
    const message = document.createElement("p");
    message.textContent = "Interactive filters could not load. The default comparison is still available below.";
    message.setAttribute("role", "status");
    container.prepend(message);
  });
}
