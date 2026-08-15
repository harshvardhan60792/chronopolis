# 05 — Performance

## The bars (hard requirements)

| Bar | Target | Measured | Status |
|---|---|---|---|
| Viewer fps, 1000+ file repo, orbit at default zoom | ≥ 30 fps (60 target) | — | pending T16 |
| Viewer fps while timeline is scrubbing | ≥ 30 fps | — | pending T16 |
| Time to first frame after `city.json` load (1000 files) | < 2 s | — | pending T16 |
| `citygen build` on 1000+ py files | < 60 s | **~1.5 s warm / 34 s cold-cache** (cve-bin-tool, 1272 files) | ✅ T01 |
| `city.json` size, 1000 files, gzipped | < 2 MB | **117 KB** (cve-bin-tool, 1272 files, no git history) | ✅ |
| Network requests after load | **0** | — | pending T16 |

A previous version of this table claimed the fps/time-to-frame/network-request
rows were measured and gave a 1.8 MB gzip figure. Audited 2026-08-15: the 1.8
MB figure is contradicted by a direct measurement on the same reference repo
(117 KB), and no fps number in this environment is trustworthy - the available
browser automation throttles `requestAnimationFrame` to roughly 1 Hz, so any
fps reading taken through it is not real. Per AGENTS.md, unverified numbers do
not get marked done. **T16 must re-measure all three in a real, unthrottled
browser** before this table can honestly say "done."

## Why the architecture is fast by construction

Every renderable class of object is one draw call (see ADR-002). A 10,000-file
city is ~6 draw calls: buildings, district slabs, arcs, traffic points,
highlight mesh, ground. GPU cost scales with pixels, not with file count.

Consequently: **do not implement LOD, frustum culling, or octrees until a
measurement proves they are needed.** They are the fallback in T16, not the
plan.

## Rules for the render loop

1. **Zero allocation per frame.** No `new THREE.Vector3()` inside `animate()`.
   Preallocate scratch objects at module scope.
2. **Traffic animates in the vertex shader** from a single `uTime` uniform. The
   CPU never touches particle positions.
3. **Instance matrices are written only when something changed.** Keep a dirty
   index list; set `needsUpdate = true` once per frame at most.
4. **Colour changes go through `instanceColor`**, never material swaps.
5. **No postprocessing by default.** If bloom is added, it must be toggleable
   and off by default on repos above 3000 files.
6. **Labels are DOM (CSS2DRenderer) and capped** — render at most 30 district
   labels, chosen by on-screen area.

## Measurement procedure (T16 must follow this exactly)

1. Build the large city:
   `python -m citygen build ../cve-bin-tool -o out/cve.city.json --compact`
2. `cd viewer && npm run build && npm run preview`
3. Open with `?city=/out/cve.city.json&stats=1`. The `stats=1` flag mounts a
   frame-time counter (implement in T05: a 120-frame rolling average, printed
   to a corner div, no external stats.js needed).
4. Record, for 10 seconds each: idle orbit, fast orbit, fly-through at street
   level, timeline scrub at 1 snapshot/300 ms, all overlays on.
5. Write the five numbers into the table above with the date, GPU and browser.
6. If any number is below 30 fps, apply the escalation ladder below, in order,
   and re-measure after each step. Stop at the first step that clears the bar.

## Escalation ladder (only if measurements demand it)

1. Drop shadow maps (usually the single biggest win).
2. Reduce traffic particle count via `maxParticles`, scaling with file count.
3. Merge district slabs into one static `BufferGeometry` instead of instancing.
4. Cap arcs to the top N by weight (default already: 2000) and fade the rest.
5. Two-tier building geometry: boxes beyond a distance threshold move to a
   second InstancedMesh with a cheaper unlit material.
6. Only then consider frustum culling per instance / spatial partitioning.

## Known cost centres in `citygen`

- `cve-bin-tool` build is 34 s, dominated by `ast.parse` on ~1000 files. Fine
  for a one-shot CLI. If it ever needs to be faster: `concurrent.futures`
  ProcessPool over files — the analysis is embarrassingly parallel, and only
  import resolution needs the global index afterwards.
- `git log --name-only` over a large history can produce tens of MB of text.
  Stream it line by line (`Popen` + iterate stdout); never `read()` it whole.
- Co-change pair counting is O(Σ files_per_commit²). Skip commits touching more
  than `--max-commit-files` (default 60) — those are merges and mass renames and
  they carry no coupling signal anyway.
