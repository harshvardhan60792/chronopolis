# 01 — Architecture

```
  repo (any git checkout)
        │
        ▼
  ┌──────────────────────────────────────────────┐
  │ citygen  (Python 3.10+, stdlib only)         │
  │                                              │
  │  walk.py      file discovery + ignore rules  │
  │  metrics.py   LOC/SLOC/AST/complexity        │
  │  resolve.py   import -> repo path            │
  │  gitmine.py   git log -> churn/authors/dates │  T02
  │  coupling.py  co-change pairs                │  T03
  │  layout.py    stable temporal treemap        │  T04
  │  snapshots.py N historical states            │  T11
  │  stories.py   rule-based findings            │  T14
  │  build.py     orchestration                  │
  │  cli.py       build | inspect | serve        │
  └──────────────────────────────────────────────┘
        │  city.json   (one file, the entire contract)
        ▼
  ┌──────────────────────────────────────────────┐
  │ viewer  (Vite + three.js, static)            │
  │                                              │
  │  data.js      load + validate + derive       │
  │  scene.js     renderer, lights, sky, ground  │
  │  buildings.js one InstancedMesh, all boxes   │
  │  districts.js district slabs + labels        │
  │  arcs.js      import arcs (LineSegments)     │
  │  traffic.js   GPU particle roads             │
  │  controls.js  orbit + fly + fly-to           │
  │  picking.js   raycast -> instanceId -> file  │
  │  timeline.js  snapshot morphing              │
  │  overlays.js  colour modes + legend          │
  │  ui.js        panel, search, legend, export  │
  │  export.js    PNG + single-file HTML         │
  └──────────────────────────────────────────────┘
```

## The one hard rule of the split

**All analysis and all layout happen in Python. The viewer does no graph work
and no layout maths.** The viewer's per-frame job is limited to: update a time
uniform, lerp instance matrices when the timeline moves, raycast on click.

Reasons:
- Layout must be identical across runs and stable across time snapshots. Doing
  it once, offline, in a deterministic language, guarantees that.
- The 60 fps bar is only reachable if the browser is not computing treemaps.
- `city.json` stays a portable artifact: other frontends (or a CLI ASCII
  renderer, or a poster generator) can consume it later.

## Data flow at runtime

1. `index.html` loads `main.js`.
2. `data.js` fetches `city.json` (or reads a dropped file, or reads an inlined
   `window.__CHRONOPOLIS_CITY__` blob in the self-contained export).
3. Derived arrays are computed once: per-building colour per overlay mode,
   per-building height per snapshot, road polylines, arc control points.
4. Scene is built: one `InstancedMesh` for buildings, one for district slabs,
   one `LineSegments` for arcs, one `Points` for traffic.
5. Render loop touches only uniforms and the camera. No allocation per frame.

## Rendering strategy (why it will hit 60 fps)

| Element | Technique | Draw calls |
|---|---|---|
| Buildings (up to ~20k) | single `InstancedMesh` of a unit box, per-instance matrix + colour | 1 |
| Building highlight | second tiny InstancedMesh for the ≤32 highlighted, or per-instance colour swap | 1 |
| District slabs | single `InstancedMesh` of a flat box | 1 |
| Import arcs | one `LineSegments` with all quadratic-bezier points baked, additive blending | 1 |
| Traffic | one `Points` (or instanced quad) with a vertex shader that advances position from a single `uTime` uniform | 1 |
| District labels | CSS2D or a single sprite atlas, only for districts above a screen-size threshold | ≤1 |

Total scene ≈ 6 draw calls regardless of repo size. That is the whole
performance argument. Frustum culling and LOD are fallbacks, not the plan.

## Time machine mechanics

- `citygen` emits `snapshots: [{ts, label, sizes: {buildingIndex: [h, w, d]}}]`
  as *sparse deltas* — only buildings whose metrics changed at that snapshot.
- Viewer keeps a `Float32Array` of current heights, lerps toward the target
  snapshot over ~400 ms with easing, and writes instance matrices only for
  instances that actually changed (dirty set), then sets
  `instanceMatrix.needsUpdate = true` once.
- Buildings not yet born have scale 0 and rise from the ground; deleted
  buildings sink and desaturate to a ruin colour rather than disappearing, so
  the eye can track where things used to be. Toggleable.

## Coordinate system and units

- 1 world unit = 1 metre-ish. A building footprint is 2–14 units square.
- Y is up. Ground plane at y = 0. Districts are slabs of height 0.2 at y ≈ 0.
- The whole city is normalised to fit a 400 × 400 unit square, so camera
  defaults work for any repo size.

## Export: self-contained HTML

`citygen export --html` produces one file: the built viewer bundle (Vite
`build` with `inlineDynamicImports`), plus
`<script>window.__CHRONOPOLIS_CITY__ = "<base64 gzip json>"</script>`. The
viewer checks that global before attempting any fetch. Result opens from
`file://` with zero network activity.
