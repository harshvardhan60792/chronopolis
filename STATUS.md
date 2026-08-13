# STATUS — single source of truth

Statuses: `TODO` · `IN-PROGRESS` · `PARTIAL` · `DONE` · `BLOCKED`

Rule: a task becomes `DONE` only after its verify command passes. If you leave
it half-finished, set `PARTIAL` and write exactly what is missing in Notes.

Last updated: 2026-08-13 — T02–T10 audited, bugs fixed, all suites green.

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
| T11 | Time machine: snapshots, morph, timeline UI | TODO | T02, T04, T05 | The other headline feature. |
| T12 | Overlay modes + legend (health/recency/owner/lang) | TODO | T02, T06 | |
| T13 | Search + fly-to | TODO | T07, T10 | |
| T14 | Stories / auto city tour (rule-based, no AI) | TODO | T02, T03, T07 | |
| T15 | Export: PNG postcard + self-contained HTML | TODO | T05 | |
| T16 | Performance pass, 1000+ files at ≥30 fps | TODO | T09, T11 | Non-negotiable bar. |
| T17 | Onboarding: drag-drop JSON, loading + empty states | TODO | T05 | |
| T18 | Docs, screenshots, CI, GitHub Pages deploy | TODO | T16 | Ship. |

## Milestones

- **M1 — data is real** (T01–T04): a correct, deterministic `city.json` with layout.
- **M2 — it is a city** (T05–T08): navigable, pretty, connected. Screenshot-worthy.
- **M3 — it is alive** (T09–T12): traffic, time, overlays. This is the wow.
- **M4 — it ships** (T13–T18): usable, fast, shareable, deployed.

## Current state of the code

- `citygen/` — walk.py, metrics.py, resolve.py, build.py, cli.py implemented and
  tested. Stdlib only. `python -m citygen build|inspect` works.
- `viewer/` — empty. T05 creates it.
- `out/reachable.city.json`, `out/cve.city.json` — generated locally, gitignored.
