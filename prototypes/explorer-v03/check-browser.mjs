import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

const [python, playwrightPath, browserPath] = process.argv.slice(2);
assert.ok(python && playwrightPath && browserPath,
  "Pass paths to Python, the Playwright package, and a Chromium browser executable.");
const { chromium } = createRequire(import.meta.url)(playwrightPath);
const server = spawn(python, ["-u", "-m", "http.server", "0", "--bind", "127.0.0.1", "--directory", "dist"]);
let browser;
try {
  const port = await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.once("exit", code => reject(new Error(`Static host exited with status ${code}`)));
    server.stdout.on("data", chunk => {
      const match = String(chunk).match(/port (\d+)/);
      if (match) resolve(match[1]);
    });
  });
  const base = `http://127.0.0.1:${port}/`;
  browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const passive = await browser.newContext({ javaScriptEnabled: false });
  const portal = await passive.newPage();
  assert.equal((await portal.goto(base)).status(), 200);
  await portal.screenshot({ path: ".build/home.png", fullPage: true });
  await portal.keyboard.press("Tab");
  assert.equal(await portal.locator(":focus").textContent(), "Skip to content");
  await portal.getByRole("button", { name: "View authority profile" }).click();
  await portal.getByRole("heading", { name: "Hartlepool", exact: true }).waitFor();
  assert.equal(new URL(portal.url()).pathname, "/authorities/E06000001/");
  assert.equal((await portal.reload()).status(), 200);
  await portal.screenshot({ path: ".build/profile.png", fullPage: true });
  await portal.getByRole("link", { name: "Open in workspace" }).click();
  assert.equal((await portal.reload()).status(), 200);
  await portal.getByRole("heading", { name: "Analytics workspace" }).waitFor();
  assert.equal(await portal.getByRole("button", { name: "Apply filters" }).count(), 0);
  assert.equal(await portal.locator("tbody tr").count(), 15);
  await passive.close();

  const interactive = await browser.newContext({ viewport: { width: 360, height: 800 } });
  const workspace = await interactive.newPage();
  const errors = [];
  workspace.on("pageerror", error => errors.push(error.message));
  await workspace.goto(`${base}workspace/?metric=27666&period=2023%2F24&model=dfe`);
  await workspace.getByRole("button", { name: "Apply filters" }).waitFor();
  assert.equal(await workspace.getByRole("combobox", { name: /^Indicator/ }).inputValue(), "27666");
  assert.equal(await workspace.getByLabel("Reporting period").inputValue(), "2023/24");
  assert.equal(await workspace.locator("tbody tr").count(), 10);
  assert.equal(await workspace.evaluate(() =>
    document.documentElement.scrollWidth <= window.innerWidth), true);
  await workspace.getByRole("button", { name: /^2021\/22/ }).click();
  assert.equal(new URL(workspace.url()).searchParams.get("period"), "2021/22");
  await workspace.getByLabel("Comparator").selectOption("mhclg");
  await workspace.getByRole("button", { name: "Apply filters" }).click();
  assert.equal(await workspace.locator("tbody tr").count(), 15);
  assert.equal(new URL(workspace.url()).searchParams.get("model"), "mhclg");
  await workspace.setViewportSize({ width: 1280, height: 900 });
  await workspace.screenshot({ path: ".build/workspace.png", fullPage: true });
  const release = JSON.parse(readFileSync("dist/data/release.json", "utf8"));
  if (release.pilot) {
    await workspace.setViewportSize({ width: 360, height: 800 });
    await workspace.goto(`${base}explore/`);
    await workspace.getByLabel("Public test postcode").fill("TS24 0XZ");
    await workspace.getByRole("button", { name: "Find area" }).click();
    await workspace.getByText(/retired in 2025-08/).waitFor();
    assert.equal(await workspace.getByRole("heading", { name: "Neighbourhood deprivation" }).count(), 0);
    await workspace.getByLabel("Public test postcode").fill("ts248ay");
    await workspace.getByRole("button", { name: "Find area" }).click();
    await workspace.getByRole("heading", { name: "Neighbourhood deprivation" }).waitFor();
    await workspace.getByLabel("Question", { exact: true }).fill("What is GLD?");
    await workspace.getByRole("button", { name: "Explain" }).click();
    await workspace.getByText(/local authority was/).waitFor();
    await workspace.getByLabel("Question", { exact: true }).fill("How has it changed over time?");
    await workspace.getByRole("button", { name: "Explain" }).click();
    await workspace.getByText(/without establishing a cause/).waitFor();
    await workspace.getByRole("link", { name: "Inspect supporting evidence" }).click();
    await workspace.getByRole("heading", { name: "Neighbourhood deprivation" }).waitFor();
    await workspace.getByRole("button", { name: "Apply filters" }).waitFor();
    await workspace.waitForFunction(() => document.activeElement?.id === "indicator-evidence");
    assert.equal(new URL(workspace.url()).searchParams.get("area"), "E01011974");
    assert.equal(new URL(workspace.url()).searchParams.get("metric"), "19346");
    assert.ok(!workspace.url().includes("TS24"));
    assert.equal(await workspace.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    console.log("Pilot browser checks passed for retired/current lookup, follow-up and evidence handoff");
  }
  assert.deepEqual(errors, []);
  await interactive.close();
  console.log("Static host browser checks passed for no-JS links, keyboard entry, direct filters, both peer models and mobile reflow");
} finally {
  try {
    await browser?.close();
  } finally {
    if (server.exitCode === null && server.signalCode === null) {
      server.kill();
      await once(server, "exit");
    }
  }
}
