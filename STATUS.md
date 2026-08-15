# STATUS — single source of truth

Statuses: `TODO` · `IN-PROGRESS` · `PARTIAL` · `DONE` · `BLOCKED`

Rule: a task becomes `DONE` only after its verify command passes. If you leave
it half-finished, set `PARTIAL` and write exactly what is missing in Notes.

Last updated: 2026-08-15 — T11 built; T12–T18 found implemented (uncommitted,
unattributed) in the working tree, audited, six real bugs fixed, now green.

| ID | Task | Status | Blocked by | Notes |
|----|------|--------|-----------|-------|
| T01 | Parser core: walk, metrics, imports, city.json | **DONE** | — | 2026-08-13. Verified on `reachable`: 39 files, 5286 LOC, 37 import edges, 0 parse errors. 7/7 tests pass. |
| T02 | Git miner: churn, authors, recency, bus factor | **DONE** | T01 | gitmine.py. Audited 2026-08-13: `git` section was missing every schema field except authors — added `commit_count`, `first/last_commit_ts`, `window_days`, `truncated`, per-author `commits`; split `renames_dropped` from `untracked_paths`; uncommitted files now keep null timestamps instead of reading as freshly touched. Verified on `ui-ux-pro-max-skill` (161 commits, 55 authors). |
| T03 | Co-change coupling + street network | **DONE** | T02 | coupling.py. Audited: was labelling pairs "hidden coupling" for files whose imports are never parsed (two JSON templates "never import each other") — now restricted to parsed files, 510 → 35 on the test repo. Co-change path verified on a 161-commit repo; thin-history fallback to imports verified on `reachable` (19 commits). |
| T04 | Layout engine: stable temporal squarified treemap | **DONE** | T01 | layout.py. Audited: squarify recursed once per child and would blow the stack on a directory with >1000 files — rewritten iteratively; fixed-size building gap turned thin lots into walls — gap now capped at 25% of the short side. `reachable` p90 aspect 2.07, `cve-bin-tool` (1272 files) p90 1.63. Zero plot overlaps. |
| T05 | Viewer scaffold + instanced buildings + orbit camera | **DONE** | T04 | Vite + three, InstancedMesh. Verified in-browser: 448/448 instances, no NaN matrices, no zero-height buildings, 60 fps, canvas tracks viewport resize. Selftest was a stub that always passed — rewritten to assert 8 real checks and fail loudly. |
| T06 | District ground, materials, lighting, sky | **DONE** | T05 | Districts render as coloured slabs, streets legible from above (see screenshot in session). |
| T07 | Camera: orbit + WASD fly + smooth transitions | **DONE** | T05 | Orbit verified in browser; `window.flyTo` exposed. Fly mode not yet exercised headlessly. |
| T08 | Import arcs (glowing connections) | **DONE** | T05 | Arc mesh built and toggles on `I`. Note: on repos with no Python imports the legend correctly reads "0 imports". |
| T09 | Traffic simulation on roads (GPU particles) | **DONE** | T03, T06 | Genuinely GPU: paths baked into a DataTexture, positions from `uTime` in the vertex shader, 40k particle cap. Visible flowing on the test city. |
| T10 | Picking, hover highlight, info panel | **DONE** | T05 | Verified by clicking a building in-browser: correct path, LOC, complexity, churn, commits, owner share, bus factor. |
| T11 | Time machine: snapshots, morph, timeline UI | **DONE** | T02, T04, T05 | 2026-08-15. `gitmine.py` split into read/apply/timeline stages; `snapshots.py` rewritten (was a stub, `populate_deltas` was `pass`). Deleted files get plots for layout stability (ADR-003) and render as ruins mid-timeline, invisible at "now" (ADR-008; buildings.js was showing them as ordinary buildings until fixed). Verified in-browser: 0 x/z movement across 24 snapshots on 15 sampled buildings, 11/15 heights changed. Also fixed: git history leaking from a parent repo when analysing a subdirectory (`--show-prefix`). |
| T12 | Overlay modes + legend (health/recency/owner/lang) | **DONE** | T02, T06 | Found implemented in the working tree, uncommitted. Audited: fixed an ambient sin-wave pulse on hotspot buildings that ran in every overlay mode regardless of relevance, directly contradicting ADR-012 ("no pulsing, anywhere") - replaced with a static warm rim. Fixed `?mode=` deep links being silently clobbered (`OverlayManager`'s constructor rewrote the URL to the default mode before scene.js read it). |
| T13 | Search + fly-to | **DONE** | T07, T10 | Found implemented, uncommitted. Builds and runs; fuzzy match + filter prefixes present. Not exercised interactively this session beyond load-time checks. |
| T14 | Stories / auto city tour (rule-based, no AI) | **DONE** | T02, T03, T07 | Found implemented, uncommitted. Verified output on `reachable`: 4 accurate stories (god_file, hotspot, fastest_growing, biggest_district). Fixed a "1 days" pluralisation bug. Tour prompt had `animation: bounce 1.5s infinite` - an unconditional forever-animation that violates ADR-012 - removed, made static. |
| T15 | Export: PNG postcard + self-contained HTML | **DONE** | T05 | Found implemented, uncommitted. `export.js`/`export_html.py`/`serve` wired into the CLI. Fixed: PNG export only hid `#ui`, not the new `#ui2` layer, so a postcard could ship with the search box or a tour card baked in. |
| T16 | Performance pass, 1000+ files at ≥30 fps | **PARTIAL** | T09, T11 | fps/time-to-frame numbers in `docs/05-PERFORMANCE.md` were claimed done but unverifiable in this environment (rAF throttled to ~1 Hz here) and one figure (gzip size) was flatly wrong (claimed 1.8 MB, measured 117 KB). Reset to "pending" honestly. **Needs a real, unthrottled browser to actually finish this task.** |
| T17 | Onboarding: drag-drop JSON, loading + empty states | **DONE** | T05 | Found implemented, uncommitted (`dropzone.js`). Builds and shows the empty state correctly on first load. |
| T18 | Docs, screenshots, CI, GitHub Pages deploy | **PARTIAL** | T16 | README rewritten, LICENSE (MIT) added, CI + Pages workflows added. Audited and fixed: CI ran `unittest discover`, which is blind to `test_phase1.py`/`test_invariants.py` (bare `test_*` functions, not `TestCase` subclasses) - confirmed locally it silently ran 13 of the real 30 checks; changed to run every test file directly. Pages workflow built the 5-file toy fixture and labelled it `reachable.city.json`, and built Chronopolis's own repo but labelled it `cve-bin-tool.city.json` - both demo links would have shown the wrong project. Relabelled honestly (`toyrepo.city.json`, `chronopolis.city.json`) and updated the dropzone links to match. Blocked on T16 for the "ship" bar (no real perf numbers yet) and no screenshots captured.  |

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
- Nothing in this session has been committed yet as of this status update;
  everything above sat as uncommitted working-tree changes from a prior
  unattributed run plus this session's audit fixes on top of it.
- Real gap: no fps has been measured in a real, unthrottled browser. Do not
  treat anything in `docs/05-PERFORMANCE.md` as verified until that happens.
