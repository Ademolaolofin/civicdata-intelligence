# CivicData Explorer v0.3 proof of concept

Atlas — Lead Development Agent, CivicData Intelligence

This local build demonstrates the public portal and workspace using one
Hartlepool profile, two DfE EYFS indicators across four academic years,
a small deprivation summary and the published MHCLG and DfE comparator
sets. The homepage limits authority selection to Hartlepool.

## Build and run

Build from `feature/lof-integration` at `141ebc4` or a later revision that
contains both the v0.2 comparator and v0.3 prototype.

Use Python 3 with the repository requirements installed and the four
local snapshots from the [Explorer guide](../../docs/explorer.md).
Use Node.js 22.12 or newer and pnpm 11.25.0. This build was verified
with Node.js 24.22.3, Python 3.13.15, React 19.2.4, TypeScript 5.9.3,
and Vite 7.3.1. The package lockfile fixes the dependency graph.

From the repository root in PowerShell:

```powershell
Set-Location prototypes/explorer-v03
pnpm install --frozen-lockfile --store-dir .build/pnpm-store
..\..\.venv\Scripts\python.exe export_release.py
pnpm run build
pnpm run check
..\..\.venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1 --directory dist
```

Use [home](http://127.0.0.1:8765/),
[Hartlepool](http://127.0.0.1:8765/authorities/E06000001/), and
[workspace](http://127.0.0.1:8765/workspace/). Stop the server with Ctrl+C.
On this workstation, the Codex-bundled Node and pnpm were used because
neither was on the system PATH.

To reproduce the optional browser smoke check from the same directory,
run `node check-browser.mjs <python.exe> <playwright-package-path> <chromium-browser.exe>`
with Playwright and an installed Chromium-compatible browser. It starts
and stops its own loopback static server and writes screenshots to
`.build/`. This is test tooling and is outside the application lockfile.

## Static generation and shared data

1. The Python exporter calls the existing Explorer snapshot validators
   and comparison function. It copies selected values, definitions,
   provenance, published ranks and source geography into
   `.build/release.json`, including input checksums. The browser does
   not recalculate EYFS values or compare geography.
2. TypeScript checks both entries. Vite bundles the interactive
   workspace as `dist/workspace.js` and compiles the build-time renderer
   separately under `.build/renderer`.
3. The renderer uses React's `renderToStaticMarkup` to emit real
   `index.html` files at each of the three routes and copies the same
   release JSON into `dist/data`. Each route uses relative links.
4. Home and profile use ordinary HTML navigation without JavaScript.
   The workspace has an HTML fallback with the default broad comparison.
   With JavaScript, its React entry fetches the same release JSON, mounts
   the interactive controls and reflects the selection in the URL.
   Static hosting requires only the contents of `dist/` and support for
   directory index files. There is no runtime Node or Python application.

## Review boundaries

This proof of concept covers one authority and a limited deprivation
summary. The workspace uses a selectable year list and ranked tables.
Full search, indicator catalogue, advanced charting, accessibility audit,
licensing review and public hosting are outside this build. The local
DfE option uses the scoped v0.2 review branch and retains its geography
safeguards. The build includes no raw workbooks or CSVs. Generated output
and installed packages are ignored by Git.

This review shares source code only. Before a public preview, confirm
the application code licence, inventory third-party notices for bundled
dependencies, and verify redistribution terms and attribution for every
field in the generated release.

## Optional local postcode and evidence pilot

The original authority profile remains available. To enable the postcode
route, fetch the fixed public-venue fixtures once and export with the pilot
flag from this directory:

```powershell
..\..\.venv\Scripts\python.exe pilot_release.py --fetch
..\..\.venv\Scripts\python.exe export_release.py --pilot
pnpm run build
pnpm run check
pnpm run check:pilot
..\..\.venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1 --directory dist
```

Open `/explore/` and try the Civic Centre postcode `TS24 8AY`.
The fixed lookup and question matching run in the browser. The workspace
link carries the statistical area and selected evidence. See the
[pilot evaluation and source notes](../../docs/hartlepool-pilot-evaluation.md).
