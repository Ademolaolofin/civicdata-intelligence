import type { Model, Pilot, Release } from "./data";

export function resolvePostcode(pilot: Pilot, input: string) {
  const compact = input.trim().toUpperCase().replace(/\s/g, "");
  if (!/^[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}$/.test(compact)) return { state: "invalid" } as const;
  const formatted = `${compact.slice(0, -3)} ${compact.slice(-3)}`;
  const entry = pilot.postcodes[formatted];
  if (!entry) return { state: "outside" } as const;
  if (entry.terminated !== null) return { state: "retired", date: entry.terminated } as const;
  if (!entry.area || !pilot.areas[entry.area]) return { state: "unresolved" } as const;
  return { state: "resolved", area: entry.area } as const;
}

const examples = {
  deprivation: ["deprivation mean", "deprivation decile", "deprived neighbourhood", "neighbourhood where"],
  development: ["school readiness rate", "good level development", "early years result", "GLD percentage"],
  gap: ["free school meals gap", "FSM gap", "attainment gap"],
  trend: ["changed over time", "trend", "changed", "earlier year changed"],
  peers: ["similar councils", "compare peers", "DfE neighbours", "MHCLG peers", "why can't we compare these areas", "some peers unavailable"],
} as const;

type Intent = keyof typeof examples;
const ignored = /\b(what|is|the|this|does|it|has|which|are|local|latest|can|you|tell|me|about|how|who|explain|of|i)\b/g;
function tokens(query: string) {
  return new Set(query.toLowerCase().replace(ignored, "").match(/[a-z0-9]+/g) ?? []);
}
const vocabulary = new Set(Object.values(examples).flatMap(samples =>
  samples.flatMap(sample => [...tokens(sample)])));

export function classify(question: string): Intent | null {
  if (question.length > 160 || /\b(ignore|invent|cause\w*|safe\w*|choose|housing|crime|transport|shops|healthcare|predict|should|rank best)\b/i.test(question)) {
    return null;
  }
  const words = tokens(question);
  if (!words.size || [...words].some(word => !vocabulary.has(word))) return null;
  const scores = Object.entries(examples).map(([intent, samples]) => ({
    intent: intent as Intent,
    score: Math.max(...samples.map(sample => {
      const reference = tokens(sample);
      const overlap = [...words].filter(word => reference.has(word)).length;
      return overlap / Math.max(words.size, reference.size);
    })),
  })).sort((a, b) => b.score - a.score);
  return scores[0].score >= 0.5 && scores[0].score - scores[1].score >= 0.2 ? scores[0].intent : null;
}

type Context = { metric: string | null; model: Model };

export function inspectLink(release: Release, area: string, metric: string, period: string, model: Model, section: string) {
  const params = new URLSearchParams({ authority: release.authority.code, area, metric, period, model });
  return `../workspace/?${params}#${section}`;
}

export function answer(release: Release, area: string, question: string, context: Context) {
  const intent = classify(question);
  const neighbourhood = release.pilot?.areas[area];
  const metricId = intent === "gap" ? "27666" : intent === "development" ? "19346" : context.metric;
  const model = intent === "peers" && /\bdfe\b/i.test(question) ? "dfe"
    : intent === "peers" && /\bmhclg\b/i.test(question) ? "mhclg" : context.model;
  const metric = release.metrics.find(item => item.id === metricId) ?? release.metrics[0];
  const latest = metric.periods.at(-1)!;
  const link = (section: string) => inspectLink(release, area, metric.id, latest.label, model, section);
  const unavailable = (text: string) => ({ text, href: null, context, status: "unsupported" as const });
  const grounded = (text: string, href: string, selection = metric.id) => ({
    text, href, context: { metric: selection, model }, status: "grounded" as const,
  });
  if (!neighbourhood || !intent) {
    return unavailable("This pilot can explain neighbourhood deprivation, council early-years measures, trends and published council peers. It cannot support that question.");
  }
  switch (intent) {
    case "deprivation":
      return {
        ...grounded(`${neighbourhood.name} is in decile ${neighbourhood.decile} in the 2025 Index of Multiple Deprivation. Decile 1 is the most deprived tenth of English statistical neighbourhoods. This is a relative neighbourhood measure; it does not describe a household.`, link("neighbourhood-evidence")),
        context,
      };
    case "development":
    case "gap":
      return grounded(
        latest.value === null
          ? `${metric.label} is unavailable for ${release.authority.name} local authority in ${latest.label}. The source does not provide a value here.`
          : `${metric.label} for ${release.authority.name} local authority was ${latest.value.toFixed(2)} ${metric.unit.toLowerCase()} in ${latest.label}. ${metric.definition}`,
        link("indicator-evidence"),
      );
    case "trend": {
      if (!context.metric) return unavailable("Choose a council early-years measure first so the pilot knows which trend you mean.");
      const first = metric.periods[0];
      if (first === latest || first.value === null || latest.value === null || first.geography !== latest.geography) {
        return unavailable("There are no comparable numeric endpoints in the selected council series.");
      }
      const difference = latest.value - first.value;
      const direction = difference < 0 ? "decreased" : "increased";
      const change = Math.abs(difference).toFixed(2);
      const summary = Number(change) === 0 ? "was unchanged to two decimal places"
        : `${direction} by ${change} percentage points`;
      return grounded(`${metric.label} for ${release.authority.name} local authority ${summary} from ${first.label} to ${latest.label}. That describes a change in the published values without establishing a cause.`, link("indicator-evidence"));
    }
    case "peers": {
      const set = latest.comparators[model];
      return grounded(`${release.models[model].label} lists ${set.peers.length} published council peers for ${release.authority.name}. For ${metric.label} in ${latest.label}, ${set.comparable} qualify for comparison. Missing values and geographic or series differences can prevent comparisons. The ranks describe model similarity.`, link("peers"));
    }
  }
}
