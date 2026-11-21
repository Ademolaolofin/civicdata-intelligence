import assert from "node:assert/strict";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { gzipSync } from "node:zlib";

const read = path => readFileSync(`dist/${path}`, "utf8");
const paths = ["index.html", "authorities/E06000001/index.html", "workspace/index.html"];
const [home, profile, workspace] = paths.map(read);
const release = JSON.parse(read("data/release.json"));
assert.deepEqual(readdirSync("dist/authorities"), ["E06000001"]);
assert.equal(release.schema, 1);
assert.equal(release.authority.name, "Hartlepool");
assert.deepEqual(release.metrics.map(item => item.id), ["19346", "27666"]);
assert.equal(Object.keys(release.inputHashes).length, 4);
assert.ok(Object.values(release.inputHashes).every(value => /^[a-f0-9]{64}$/.test(value)));
assert.doesNotMatch(home + profile, /<script/);
assert.match(home, /action="\.\/authorities\/E06000001\/"/);
assert.match(profile, /Deprivation profile/);
assert.match(profile, /\.\.\/\.\.\/workspace\/\?authority=E06000001/);
assert.match(workspace, /<noscript>/);
assert.match(workspace, /data-release="\.\.\/data\/release\.json"/);
assert.match(workspace, /<script type="module" src="\.\.\/workspace\.js"/);
assert.ok(existsSync("dist/workspace.js"));
assert.ok(existsSync("dist/site.css"));
for (const metric of release.metrics) {
  assert.deepEqual(metric.periods.map(period => period.label), ["2021/22", "2022/23", "2023/24", "2024/25"]);
  assert.ok(profile.includes(metric.definition));
  for (const period of metric.periods) {
    for (const [model, count] of [["mhclg", 15], ["dfe", 10]]) {
      const comparison = period.comparators[model];
      assert.deepEqual(comparison.peers.map(peer => peer.rank), Array.from({ length: count }, (_, i) => i + 1));
      assert.ok(comparison.comparable <= comparison.available && comparison.available <= count);
    }
  }
}
const defaultMetric = release.metrics[0];
assert.ok(workspace.includes(defaultMetric.definition));
const latest = defaultMetric.periods.at(-1).value;
const latestDisplay = latest === null ? "Unavailable" : latest.toFixed(2);
assert.ok(workspace.includes(latestDisplay));
assert.ok(profile.includes(latestDisplay));
for (const html of [home, profile, workspace]) {
  assert.match(html, /<html lang="en"/);
  assert.match(html, /href="#main"/);
  assert.match(html, /aria-label="Main navigation"/);
  assert.ok(html.includes(release.id));
}
const bytes = gzipSync(read("workspace.js")).length;
assert.ok(bytes < 250 * 1024);
console.log(`Three static routes verified; 1 authority, 2 metrics, 4 years, 2 models; workspace JS ${bytes} gzip bytes`);

// Exercise the same React renderer with both values without modifying the real release.
const fixture = mkdtempSync(resolve(".build/observation-render-"));
try {
  const variant = structuredClone(release);
  variant.metrics[0].periods.at(-1).value = 0;
  variant.metrics[0].periods.at(-2).value = null;
  variant.metrics[1].periods.at(-1).value = null;
  mkdirSync(join(fixture, ".build"), { recursive: true });
  mkdirSync(join(fixture, "src"), { recursive: true });
  writeFileSync(join(fixture, ".build/release.json"), JSON.stringify(variant));
  copyFileSync("src/site.css", join(fixture, "src/site.css"));
  execFileSync(process.execPath, [resolve(".build/renderer/prerender.js")], { cwd: fixture });
  const profileVariant = readFileSync(join(fixture, "dist/authorities/E06000001/index.html"), "utf8");
  const workspaceVariant = readFileSync(join(fixture, "dist/workspace/index.html"), "utf8");
  assert.match(profileVariant, /class="value">0\.00 <span>Per cent<\/span>/);
  assert.match(profileVariant, /class="value">Unavailable\s*<\/p>/);
  assert.match(workspaceVariant, /class="value">0\.00 <span>Per cent<\/span>/);
  assert.match(workspaceVariant, /<span>2023\/24<\/span><strong>Unavailable<\/strong>/);
  console.log("Static profile and workspace distinguish observed zero from unavailable data");
} finally {
  rmSync(fixture, { recursive: true });
}
