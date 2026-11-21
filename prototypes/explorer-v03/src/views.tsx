import type { ReactNode } from "react";
import { display, type Metric, type Model, type Period, type Release } from "./data";

type Page = "home" | "profile" | "workspace";

export function Document({ page, base, release, children }: {
  page: Page; base: string; release: Release; children: ReactNode;
}) {
  const routes = {
    home: base,
    profile: `${base}authorities/${release.authority.code}/`,
    workspace: `${base}workspace/`,
  };
  const title = { home: "Explore your local area", profile: release.authority.name, workspace: "Analytics workspace" };
  return <html lang="en">
    <head>
      <meta charSet="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>{`${title[page]} | CivicData Intelligence`}</title>
      <link rel="stylesheet" href={`${base}site.css`}/>
    </head>
    <body>
      <a className="skip" href="#main">Skip to content</a>
      <header className="mast">
        <div className="wrap nav">
          <a className="brand" href={routes.home}>Civic<span>Data</span><small> Intelligence</small></a>
          <nav aria-label="Main navigation">
            <a href={routes.profile} aria-current={page === "profile" ? "page" : undefined}>Explore an area</a>
            <a href={routes.workspace} aria-current={page === "workspace" ? "page" : undefined}>Analytics workspace</a>
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1}>{children}</main>
      <footer><div className="wrap footer">
        <span>CivicData Intelligence · Local proof of concept</span>
        <a href={`${base}data/release.json`}>View data release {release.id}</a>
      </div></footer>
      {page === "workspace" && <script type="module" src={`${base}workspace.js`}/>}
    </body>
  </html>;
}

export function Home({ release }: { release: Release }) {
  return <>
    <section className="hero">
      <div className="wrap hero-grid">
        <div>
          <h1>Understand your local area</h1>
          <p>Explore deprivation, early-years development and the councils that share similar characteristics.</p>
          <a className="button secondary" href="./workspace/">Open analytics workspace</a>
        </div>
        <form className="finder panel" action={`./authorities/${release.authority.code}/`} method="get">
          <h2>Find a local authority</h2>
          <label htmlFor="authority">Authority available in this preview</label>
          <select id="authority" defaultValue={release.authority.code}>
            <option value={release.authority.code}>{release.authority.name} ({release.authority.code})</option>
          </select>
          <button className="button">View authority profile</button>
        </form>
      </div>
    </section>
    <section className="wrap section" aria-labelledby="topics">
      <h2 id="topics">What you can explore</h2>
      <div className="topics">
        <article><h3>Deprivation</h3><p>See how deprivation is measured across neighbourhoods in the authority.</p></article>
        <article><h3>Early years</h3><p>See how children develop by age five and the gap associated with free school meal eligibility.</p></article>
        <article><h3>Similar councils</h3><p>Compare the authority with its published statistical neighbours in the workspace.</p></article>
      </div>
    </section>
  </>;
}

export function Indicator({ metric, period }: { metric: Metric; period: Period }) {
  return <article className="panel indicator">
    <h3>{metric.label}</h3>
    <p className="value">{display(period.value)} {period.value !== null && <span>{metric.unit}</span>}</p>
    <p className="meta">{period.label} · {period.geography}</p>
    <p>{metric.definition}</p>
  </article>;
}

function EyfsSource({ release }: { release: Release }) {
  const source = release.eyfsSource;
  return <p className="meta">Source <a href={source.url}>{source.publisher} · {source.name}</a> · release {source.version}</p>;
}

export function Profile({ release }: { release: Release }) {
  const d = release.deprivation;
  return <div className="wrap section">
    <nav aria-label="Breadcrumb"><a href="../../">Home</a> / {release.authority.name}</nav>
    <div className="heading">
      <div><h1>{release.authority.name}</h1><p className="meta">{release.authority.type} · {release.authority.code}</p></div>
      <a className="button" href={`../../workspace/?authority=${release.authority.code}`}>Open in workspace</a>
    </div>
    <section aria-labelledby="early-years">
      <h2 id="early-years">Early-years development</h2>
      <div className="cards">{release.metrics.map(metric =>
        <Indicator key={metric.id} metric={metric} period={metric.periods.at(-1)!}/>)}</div>
      <EyfsSource release={release}/>
    </section>
    <section className="panel section-item" aria-labelledby="deprivation">
      <h2 id="deprivation">Deprivation profile</h2>
      <dl className="stats">
        <div><dt>Index of Multiple Deprivation average score</dt><dd>{d.score}</dd></div>
        <div><dt>Rank of average score (1 is most deprived)</dt><dd>{d.rank}</dd></div>
      </dl>
      <p className="meta"><a href={d.url}>English Indices of Deprivation {d.release} · File 10</a> · {d.geography} · {d.sourceCode}</p>
    </section>
  </div>;
}

export function WorkspaceResults({ release, metric, period, model, onPeriod }: {
  release: Release; metric: Metric; period: Period; model: Model; onPeriod?: (period: string) => void;
}) {
  const selected = period.comparators[model];
  const context = release.models[model];
  return <>
    <div className="cards">
      <Indicator metric={metric} period={period}/>
      <section className="panel" aria-label="Trend">
        <h2>Trend</h2>
        {onPeriod && <p className="meta">Select a year to update the comparison.</p>}
        {metric.periods.map(item => {
          const label = <><span>{item.label}</span><strong>{display(item.value)}</strong></>;
          return onPeriod
            ? <button key={item.label} type="button" className="year" aria-pressed={item.label === period.label} onClick={() => onPeriod(item.label)}>{label}</button>
            : <div key={item.label} className="year">{label}</div>;
        })}
      </section>
    </div>
    <EyfsSource release={release}/>
    <section className="panel section-item" aria-labelledby="peers">
      <h2 id="peers">Statistical neighbours</h2>
      <p><a href={context.url}>{context.label}</a> · {context.release} · {context.geography}</p>
      {model === "dfe" && <p>The May 2025 model provides context for earlier EYFS years.</p>}
      <p><strong>{selected.available} of {selected.peers.length}</strong> peers have numeric values. {selected.comparable} qualify for comparison by geography and series metadata.</p>
      <div className="scroll" role="region" aria-label="Ranked peer table" tabIndex={0}>
        <table>
          <caption>{metric.label} · {period.label} · {metric.unit}</caption>
          <thead><tr>
            {["Published rank", "Authority", "Value", "Source geography", "Comparison status", ...(model === "dfe" ? ["Proximity"] : [])]
              .map(label => <th key={label} scope="col">{label}</th>)}
          </tr></thead>
          <tbody>{selected.peers.map(peer =>
            <tr key={peer.code}>
              <td>{peer.rank}</td><th scope="row">{peer.name}<small>{peer.code}</small></th>
              <td>{peer.value}</td><td>{peer.geography}</td><td>{peer.status}</td>
              {model === "dfe" && <td>{peer.proximity}</td>}
            </tr>)}</tbody>
        </table>
      </div>
    </section>
  </>;
}
