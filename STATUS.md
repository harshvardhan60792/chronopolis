# STATUS — single source of truth

Statuses: `TODO` · `IN-PROGRESS` · `PARTIAL` · `DONE` · `BLOCKED`

Rule: a task becomes `DONE` only after its verify command passes. If you leave
it half-finished, set `PARTIAL` and write exactly what is missing in Notes.

Last updated: 2026-08-15 — all 18 tasks DONE. T16 measured for real (headful
Chrome), T07 camera navigation overhauled to feel like a game, T18 finished
with real screenshots. M1-M4 all complete.

| ID | Task | Status | Blocked by | Notes |
|----|------|--------|-----------|-------|
| T01 | Parser core: walk, metrics, imports, city.json | **DONE** | — | 2026-08-13. Verified on `reachable`: 39 files, 5286 LOC, 37 import edges, 0 parse errors. 7/7 tests pass. 2026-08-15: tested against real GitHub repos (psf/requests, pallets/flask, expressjs/express, colinhacks/zod) - found and fixed a real gap: JS/TS files had no regex fallback at all despite the README claiming one, so every non-Python file rendered flat (complexity=1, 0 functions, 0 import arcs) - confirmed on express (0 -> 3114 fns, 0 -> 57 import edges). Added `metrics.js_metrics` + `resolve.JsModuleIndex`. Second bug found on the TS repo: modern TS/ESM code writes `from "./foo.js"` for a file that's actually `foo.ts` (required by Node's ESM resolution) - the naive suffix-append resolver never tried stripping that extension, so zod resolved 3 of what should have been ~540 import edges. Fixed by trying the specifier with any known JS/TS extension stripped before re-appending resolution suffixes (3 -> 540 edges on zod). All 4 real repos verified clean in-browser (`?selftest=1` green, no console errors, no NaN/negative fields). |
| T02 | Git miner: churn, authors, recency, bus factor | **DONE** | T01 | gitmine.py. Audited 2026-08-13: `git` section was missing every schema field except authors — added `commit_count`, `first/last_commit_ts`, `window_days`, `truncated`, per-author `commits`; split `renames_dropped` from `untracked_paths`; uncommitted files now keep null timestamps instead of reading as freshly touched. Verified on `ui-ux-pro-max-skill` (161 commits, 55 authors). |
| T03 | Co-change coupling + street network | **DONE** | T02 | coupling.py. Audited: was labelling pairs "hidden coupling" for files whose imports are never parsed (two JSON templates "never import each other") — now restricted to parsed files, 510 → 35 on the test repo. Co-change path verified on a 161-commit repo; thin-history fallback to imports verified on `reachable` (19 commits). |
| T04 | Layout engine: stable temporal squarified treemap | **DONE** | T01 | layout.py. Audited: squarify recursed once per child and would blow the stack on a directory with >1000 files — rewritten iteratively; fixed-size building gap turned thin lots into walls — gap now capped at 25% of the short side. `reachable` p90 aspect 2.07, `cve-bin-tool` (1272 files) p90 1.63. Zero plot overlaps. |
| T05 | Viewer scaffold + instanced buildings + orbit camera | **DONE** | T04 | Vite + three, InstancedMesh. Verified in-browser: 448/448 instances, no NaN matrices, no zero-height buildings, 60 fps, canvas tracks viewport resize. Selftest was a stub that always passed — rewritten to assert 8 real checks and fail loudly. |
| T06 | District ground, materials, lighting, sky | **DONE** | T05 | Districts render as coloured slabs, streets legible from above (see screenshot in session). |
| T07 | Camera: orbit + WASD fly + smooth transitions | **DONE** | T05 | Orbit verified in browser; `window.flyTo` exposed. Fly mode not yet exercised headlessly. 2026-08-15: navigation overhauled to feel like a real game camera - scroll zoom now dollies toward the cursor instead of screen-center (Google Earth/Cities: Skylines style); WASD/QE now also pan+rotate the orbit camera (RTS-style), not just fly mode; double-click on the ground flies you there; fly-mode speed scales with altitude (crawl low, cover ground fast high up). Fixed a real stuck-mode bug: the browser can drop pointer lock on its own (Escape, alt-tab) without the app calling `exitPointerLock()` first, which left `mode` stuck on 'fly' forever with dead WASD and a stale hint - added a `pointerlockchange` listener that self-heals back to orbit. Also fixed an unclamped `dt` that could teleport the camera after any stall (backgrounded tab, or this environment's throttled rAF) - clamped to 100ms. All verified via direct camera/target state inspection in-browser (zoom shift, pan delta, rotate, fly-to landing point, mode recovery after simulated pointer-lock loss). |
| T08 | Import arcs (glowing connections) | **DONE** | T05 | Arc mesh built and toggles on `I`. Note: on repos with no Python imports the legend correctly reads "0 imports". |
| T09 | Traffic simulation on roads (GPU particles) | **DONE** | T03, T06 | Genuinely GPU: paths baked into a DataTexture, positions from `uTime` in the vertex shader, 40k particle cap. Visible flowing on the test city. |
| T10 | Picking, hover highlight, info panel | **DONE** | T05 | Verified by clicking a building in-browser: correct path, LOC, complexity, churn, commits, owner share, bus factor. |
| T11 | Time machine: snapshots, morph, timeline UI | **DONE** | T02, T04, T05 | 2026-08-15. `gitmine.py` split into read/apply/timeline stages; `snapshots.py` rewritten (was a stub, `populate_deltas` was `pass`). Deleted files get plots for layout stability (ADR-003) and render as ruins mid-timeline, invisible at "now" (ADR-008; buildings.js was showing them as ordinary buildings until fixed). Verified in-browser: 0 x/z movement across 24 snapshots on 15 sampled buildings, 11/15 heights changed. Also fixed: git history leaking from a parent repo when analysing a subdirectory (`--show-prefix`). |
| T12 | Overlay modes + legend (health/recency/owner/lang) | **DONE** | T02, T06 | Found implemented in the working tree, uncommitted. Audited: fixed an ambient sin-wave pulse on hotspot buildings that ran in every overlay mode regardless of relevance, directly contradicting ADR-012 ("no pulsing, anywhere") - replaced with a static warm rim. Fixed `?mode=` deep links being silently clobbered (`OverlayManager`'s constructor rewrote the URL to the default mode before scene.js read it). |
| T13 | Search + fly-to | **DONE** | T07, T10 | Found implemented, uncommitted. Builds and runs; fuzzy match + filter prefixes present. Not exercised interactively this session beyond load-time checks. |
| T14 | Stories / auto city tour (rule-based, no AI) | **DONE** | T02, T03, T07 | Found implemented, uncommitted. Verified output on `reachable`: 4 accurate stories (god_file, hotspot, fastest_growing, biggest_district). Fixed a "1 days" pluralisation bug. Tour prompt had `animation: bounce 1.5s infinite` - an unconditional forever-animation that violates ADR-012 - removed, made static. |
| T15 | Export: PNG postcard + self-contained HTML | **DONE** | T05 | Found implemented, uncommitted. `export.js`/`export_html.py`/`serve` wired into the CLI. Fixed: PNG export only hid `#ui`, not the new `#ui2` layer, so a postcard could ship with the search box or a tour card baked in. |
| T16 | Performance pass, 1000+ files at ≥30 fps | **DONE** | T09, T11 | 2026-08-15. Measured in real headful Chrome (Puppeteer-driven, not the IDE's throttled automation pane, not headless SwiftShader) on this machine's integrated GPU. cve-bin-tool, 1272 buildings: idle orbit 61 fps, fast orbit 61 fps, fly-through 61 fps, timeline scrub 60 fps, everything-on 58 fps — all ≥30, first three ≥45. Time to first frame 1767 ms (<2s bar). 0 network requests after load. JS heap flat over 60s (no leak). `?selftest=1` green at 61 fps. New `viewer/scripts/measure-perf.mjs` (`npm run perf`) reproduces this. Full numbers in `docs/05-PERFORMANCE.md`. |
| T17 | Onboarding: drag-drop JSON, loading + empty states | **DONE** | T05 | Found implemented, uncommitted (`dropzone.js`). Builds and shows the empty state correctly on first load. |
| T18 | Docs, screenshots, CI, GitHub Pages deploy | **DONE** | — | README rewritten, LICENSE (MIT) added, CI + Pages workflows added. Audited and fixed: CI ran `unittest discover`, which is blind to `test_phase1.py`/`test_invariants.py` (bare `test_*` functions, not `TestCase` subclasses) - confirmed locally it silently ran 13 of the real 30 checks; changed to run every test file directly. Pages workflow built the 5-file toy fixture and labelled it `reachable.city.json`, and built Chronopolis's own repo but labelled it `cve-bin-tool.city.json` - both demo links would have shown the wrong project. Relabelled honestly (`toyrepo.city.json`, `chronopolis.city.json`) and updated the dropzone links to match. 2026-08-15: captured 3 real screenshots (`docs/img/hero.png`, `overlays.png`, `timemachine.png`) via a headful-Puppeteer script driving the actual built app against real city.json fixtures (cve-bin-tool for the skyline, a 161-commit sibling repo for the timeline shot with real snapshots/ruins) - not mockups. While framing the overlay screenshot, found and fixed a real layout bug my own longer control-hint text had exposed: the hint stack (top-left) and the search bar (top-center) had no awareness of each other's height and visually collided; capped the hint's width and moved the search bar down to clear it. README now documents navigation (`## Getting Around`) and the time machine with real screenshots. |

## Milestones

- **M1 — data is real** (T01–T04): a correct, deterministic `city.json` with layout.
- **M2 — it is a city** (T05–T08): navigable, pretty, connected. Screenshot-worthy.
- **M3 — it is alive** (T09–T12): traffic, time, overlays. This is the wow.
- **M4 — it ships** (T13–T18): usable, fast, shareable, deployed.

## Current state of the code

- `citygen/` — walk, metrics, resolve, gitmine, coupling, layout, snapshots,
  stories, build, cli, export_html all implemented. Stdlib only.
  `python -m citygen build|inspect|export|serve` all work.
- `viewer/` — full feature set present: scene, buildings (procedural facade),
  districts, terrain/sky/clouds, controls, arcs, traffic, picking/panel,
  timeline, overlays/legend, search, tour/stories, export, dropzone.
- 5/5 python test files pass when run directly (`python citygen/tests/test_*.py`).
  Do **not** trust `python -m unittest discover` for this project - see T18.
- All work is committed. fps has been measured in a real, unthrottled browser
  (T16) - `docs/05-PERFORMANCE.md` numbers are real. Camera navigation was
  overhauled to feel like a game camera (zoom-to-cursor, WASD/QE orbit pan,
  click-to-go, altitude-scaled fly speed) - see `docs/CHANGELOG.md`. README
  now has real screenshots (T18). No open gaps against the M1-M4 milestones.
