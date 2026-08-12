# T10 — Picking, hover highlight, info panel

**Blocked by:** T05 · **Effort:** small-medium

## Goal
Click a building → know everything about that file. Hover → see what it is
connected to. This is where the city becomes usable rather than decorative.

## Files
- new: `viewer/src/picking.js`, `viewer/src/panel.js`
- edit: `viewer/src/ui.js`, `viewer/src/arcs.js` (highlight API)

## Picking
`THREE.Raycaster` against the buildings `InstancedMesh` — three.js populates
`intersection.instanceId`, which is the building index directly (ADR-007).
Throttle hover raycasts to ~30 Hz and skip while the camera is moving fast.

## Hover
- Building under cursor: brighten via `setColorAt` (keep the original colour in
  a `Float32Array` to restore).
- Its connected buildings (imports in + out, and top co-change partners) get a
  secondary tint; everything else dims to 35% — the "spotlight" effect is what
  makes coupling legible.
- Its arcs recolour to full-bright; other arcs drop to 15% opacity.
- Restore on mouse-out. All of this is colour-attribute writes, no material
  swaps, no new objects.

## Click → panel
Fixed panel, top-right, ~320 px, plain DOM (no framework):

```
reachable/callgraph.py                      [python]
────────────────────────────────────────────
386 LOC · 14 functions · 1 class
complexity 125  (worst function 19)
churn 1,820 lines over 41 commits
last touched 12 days ago · first seen 420 days ago
owner: Ada (80% of commits) · bus factor 1
────────────────────────────────────────────
imports (3)          ▸ models.py, util.py, …
imported by (1)      ▸ cli.py
changes with (top 5) ▸ tests/test_callgraph.py  0.42
                       report.py               0.31
────────────────────────────────────────────
[ fly to ]  [ isolate ]  [ copy path ]
```
- Every listed file is clickable → selects that building and flies to it.
- `isolate` hides everything except this building and its neighbours (a scene
  filter, implemented as scale-0 instances + arc alpha 0).
- Numbers come straight from the building record; show `—` for fields the city
  does not have (e.g. no git data) rather than hiding rows inconsistently.
- `Esc` closes; clicking empty ground closes.

## Keyboard
`Tab` cycles selection through the current search/filter result set (T13 wires
that; here just support next/prev over all buildings sorted by complexity).

## Acceptance criteria
- Click accuracy: clicking a building always selects that exact file — verify by
  cross-checking the panel path against a manual raycast of 5 buildings.
- Hover at 60 fps on the 1000-file city (throttling working).
- Panel never shows `undefined`, `NaN`, or an empty section header.
- Selection survives an overlay-mode change (T12) and a timeline scrub (T11).

## Default if ambiguous
- Single selection only; no multi-select in v1.
- Panel is DOM, not in-scene text.
- Relative dates ("12 days ago") computed against `git.last_commit_ts`, not
  wall clock, so screenshots stay reproducible.
