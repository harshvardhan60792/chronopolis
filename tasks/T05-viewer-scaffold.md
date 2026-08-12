# T05 — Viewer scaffold + instanced buildings + orbit camera

**Blocked by:** T04 · **Effort:** medium · **Milestone: first visual**

## Goal
`npm run dev`, and the repo is a city on screen. One InstancedMesh, orbit
controls, nothing else. Resist adding features here.

## Setup
```bash
cd viewer && npm create vite@latest . -- --template vanilla && npm i three
```
Keep the scaffold minimal: delete the Vite demo CSS/JS. Dependencies must be
exactly `three` (+ `vite` dev). No React, no dat.gui, no stats.js.

## Files
```
viewer/index.html
viewer/package.json
viewer/vite.config.js        # base: './'  (required for file:// and GH Pages)
viewer/src/main.js           # entry, wiring only
viewer/src/data.js           # load + validate city.json
viewer/src/scene.js          # renderer, camera, lights, ground, resize, loop
viewer/src/buildings.js      # InstancedMesh construction + colour helpers
viewer/src/fps.js            # rolling frame-time counter (?stats=1)
viewer/src/selftest.js       # ?selftest=1 harness (see docs/06-TESTING.md)
```

## data.js contract
Load order, first hit wins:
1. `window.__CHRONOPOLIS_CITY__` — base64+gzip inline (self-contained export,
   T15). Decompress with `DecompressionStream('gzip')` — built into browsers,
   no library.
2. `?city=<url>` query parameter.
3. `./city.json` next to index.html.
4. Nothing → show the drop zone (T17 makes it pretty; here a plain message).

Validate: `schema` starts with `chronopolis.city/`, `layout` is non-null,
`layout.plots.length === buildings.length`. On failure show the reason on
screen, do not throw into a blank canvas.

## buildings.js
```js
const geo = new THREE.BoxGeometry(1, 1, 1);
geo.translate(0, 0.5, 0);                 // pivot at base so scale.y grows up
const mat = new THREE.MeshLambertMaterial({ vertexColors: true });
const mesh = new THREE.InstancedMesh(geo, mat, buildings.length);
mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
```
Per building `i`: `dummy.position.set(plot.x + plot.w/2, 0, plot.z + plot.d/2)`,
`dummy.scale.set(plot.w, plot.h, plot.d)`, `dummy.updateMatrix()`,
`mesh.setMatrixAt(i, dummy.matrix)`, `mesh.setColorAt(i, colorFor(i))`.

v1 colour = language palette (python, javascript, docs, data, style, other).
Keep the palette in one exported object; T12 replaces it with overlay modes.

## scene.js
- `WebGLRenderer({ antialias: true })`, `setPixelRatio(min(devicePixelRatio, 2))`
- Perspective camera 55° fov, positioned to frame `layout.world` from ~45°
- `HemisphereLight` + one `DirectionalLight` (shadows OFF for now)
- Ground: large `PlaneGeometry`, dark neutral, plus `Fog` matching background
- `OrbitControls` from `three/examples/jsm/controls/OrbitControls.js`,
  damping on, `maxPolarAngle ≈ 1.5` so the camera cannot go under the ground
- Resize handler; render loop with `requestAnimationFrame`, no per-frame
  allocation

## fps.js
120-frame rolling average, mounted as a fixed-position div when `?stats=1`.
Show `fps` and `frame ms`. ~20 lines. This is the instrument T16 depends on —
do not skip it.

## Acceptance criteria
- `npm run dev` shows the `reachable` city; every building visible, sized and
  positioned per `layout`, no z-fighting with the ground.
- `?stats=1` shows a live fps counter.
- `?selftest=1` prints `SELFTEST OK <fps>` and sets `document.title = "OK"`.
- Loading `out/cve.city.json` (1000+ files) renders and holds ≥ 30 fps on orbit.
- Console is clean: no warnings, no errors.
- `npm run build` produces a dist that also works when opened from `file://`
  (that requires `base: './'`).

## Verify
```bash
cd viewer && npm run build && npm run preview
```
Then open `?city=/out/reachable.city.json&stats=1` and screenshot it into
`docs/img/T05-first-city.png`.

## Default if ambiguous
- Background `#0b0e14`, ground `#141922`, fog matching background.
- Camera starts at `(world.width * 0.9, world.width * 0.55, world.depth * 0.9)`
  looking at the world centre.
- If `layout` is null, refuse to render and tell the user to re-run citygen —
  do not invent a fallback grid layout in the viewer (ADR-001).
