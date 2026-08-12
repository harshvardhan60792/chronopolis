# STATUS — single source of truth

Statuses: `TODO` · `IN-PROGRESS` · `PARTIAL` · `DONE` · `BLOCKED`

Rule: a task becomes `DONE` only after its verify command passes. If you leave
it half-finished, set `PARTIAL` and write exactly what is missing in Notes.

Last updated: 2026-08-13 by initial-architect

| ID | Task | Status | Blocked by | Notes |
|----|------|--------|-----------|-------|
| T01 | Parser core: walk, metrics, imports, city.json | **DONE** | — | 2026-08-13. Verified on `reachable`: 39 files, 5286 LOC, 37 import edges, 0 parse errors. 7/7 tests pass. |
| T02 | Git miner: churn, authors, recency, bus factor | TODO | T01 | Fills `city.git` |
| T03 | Co-change coupling + street network | TODO | T02 | Fills `edges.cochange`, `layout.roads` inputs |
| T04 | Layout engine: stable temporal squarified treemap | TODO | T01 | Fills `city.layout`. Hardest pure-logic task. Read task file fully. |
| T05 | Viewer scaffold + instanced buildings + orbit camera | TODO | T04 | First visual. Milestone. |
| T06 | District ground, materials, lighting, sky | TODO | T05 | |
| T07 | Camera: orbit + WASD fly + smooth transitions | TODO | T05 | |
| T08 | Import arcs (glowing connections) | TODO | T05 | |
| T09 | Traffic simulation on roads (GPU particles) | TODO | T03, T06 | The headline feature. |
| T10 | Picking, hover highlight, info panel | TODO | T05 | |
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
