import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { Document, Home, Profile, WorkspaceResults } from "./views";
import type { Release } from "./data";

const release: Release = JSON.parse(readFileSync(".build/release.json", "utf8"));
if (release.schema !== 1 || release.authority.code !== "E06000001" || release.metrics.length !== 2) {
  throw new Error("Unexpected proof-of-concept release");
}
const dest = "dist";
const metric = release.metrics[0];
const period = metric.periods.at(-1)!;
const routes = [
  ["index.html", <Document page="home" base="./" release={release}><Home release={release}/></Document>],
  [`authorities/${release.authority.code}/index.html`,
    <Document page="profile" base="../../" release={release}><Profile release={release}/></Document>],
  ["workspace/index.html", <Document page="workspace" base="../" release={release}>
    <div className="wrap section">
      <div className="heading">
        <div><h1>Analytics workspace</h1><p className="meta">{release.authority.name} · {release.authority.code}</p></div>
        <a href={`../authorities/${release.authority.code}/`}>View authority profile</a>
      </div>
      <div id="workspace" data-release="../data/release.json">
        <noscript><p>Interactive filters require JavaScript. The default comparison is available below.</p></noscript>
        <WorkspaceResults release={release} metric={metric} period={period} model="mhclg"/>
      </div>
    </div>
  </Document>],
  ...(release.pilot ? [["explore/index.html", <Document page="explore" base="../" release={release}>
    <div className="wrap section">
      <h1>Explore the Area</h1>
      <p>Hartlepool postcode and evidence pilot</p>
      <div id="explore" data-release="../data/release.json">
        <p>Postcode lookup requires JavaScript. The Hartlepool profile remains available below.</p>
      </div>
      <p><a href="../authorities/E06000001/">Open Hartlepool profile</a></p>
    </div>
  </Document>] as const] : []),
] as const;

for (const [path, content] of routes) {
  mkdirSync(dirname(`${dest}/${path}`), { recursive: true });
  writeFileSync(`${dest}/${path}`, "<!doctype html>\n" + renderToStaticMarkup(content) + "\n");
}
mkdirSync(`${dest}/data`, { recursive: true });
copyFileSync(".build/release.json", `${dest}/data/release.json`);
copyFileSync("src/site.css", `${dest}/site.css`);
