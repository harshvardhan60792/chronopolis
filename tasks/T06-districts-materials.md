# T06 — District slabs, materials, lighting, sky

**Blocked by:** T05 · **Effort:** small-medium

## Goal
Make it read as a *city* rather than a bar chart: ground plates per folder,
visible streets, a sky, and light that gives the boxes form.

## Files
- new: `viewer/src/districts.js`, `viewer/src/palette.js`
- edit: `viewer/src/scene.js`, `viewer/src/buildings.js`

## District slabs
One `InstancedMesh` of a flat box (`BoxGeometry(1, 1, 1)` scaled to
`w × 0.2 × d`) for `layout.districts`, drawn at `y = 0.01 * depth` so nested
districts sit slightly above their parents and never z-fight.

Colour by top-level district: assign hues by walking depth-1 districts in
sorted order around the colour wheel with fixed saturation/lightness; deeper
districts inherit the parent hue with lightness stepped down. Deterministic —
the same repo always gets the same colours.

## Streets
Streets are the gaps produced by T04's insets. Sell them visually:
- ground plane a shade darker than the district slabs
- optional thin emissive centre-lines later in T09 when traffic exists
Do not model kerbs or road meshes; the negative space is enough.

## Lighting
- `HemisphereLight(skyColor, groundColor, 0.55)`
- one `DirectionalLight` at ~(1, 2, 1) normalised, intensity 1.1
- Shadows: enable `PCFSoftShadowMap` with a tight ortho shadow camera fitted to
  the world bounds, **only if** fps on the 1000-file city stays ≥ 45. Otherwise
  leave off — shadows are the first thing to drop (docs/05-PERFORMANCE.md).
- Fake ambient occlusion cheaply instead: darken the bottom of buildings via
  vertex colours on the box geometry (bottom vertices multiplied by 0.6).

## Sky
Gradient background via a large inverted sphere with a two-colour shader, or
simply a CSS gradient behind a transparent canvas. Prefer the CSS gradient —
zero draw calls, and it composites fine because the ground fills the lower half.

## Building look
Flat-shaded low-poly, no textures (docs/00-VISION.md non-goals). Optional cheap
detail if fps allows: a second InstancedMesh of thin "roof caps" slightly wider
than the building at its top, in a lighter tint. Windows via texture are
explicitly out of scope for v1.

## Acceptance criteria
- Districts are visually obvious without labels; nesting is readable.
- Street grid is visible from above.
- Same repo → same colours every run.
- fps on the 1000-file city unchanged from T05 (± 3 fps), measured with `?stats=1`.
- Screenshot into `docs/img/T06-districts.png`.

## Default if ambiguous
- Hue palette: 12 evenly spaced hues at S 55%, L 42%; skip hues 55°–70°
  (muddy yellow-green) by remapping.
- Shadows off.
- District labels are T12's problem, not this task's.
