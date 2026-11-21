export type Model = "mhclg" | "dfe";

export type Peer = {
  rank: number;
  name: string;
  code: string;
  value: string;
  geography: string;
  status: string;
  proximity?: string;
};

export type Period = {
  label: string;
  value: number | null;
  geography: string;
  comparators: Record<Model, { available: number; comparable: number; peers: Peer[] }>;
};

export type Metric = {
  id: string;
  label: string;
  definition: string;
  unit: string;
  periods: Period[];
};

export type Release = {
  schema: 1;
  id: string;
  authority: { code: string; name: string; type: string };
  eyfsSource: { name: string; publisher: string; version: string; url: string };
  models: Record<Model, { label: string; release: string; geography: string; url: string }>;
  deprivation: { score: number; rank: number; sourceCode: string; release: string; geography: string; url: string };
  metrics: Metric[];
};

export function display(value: number | null) {
  return value === null ? "Unavailable" : value.toFixed(2);
}
