# T08 — Import arcs

**Blocked by:** T05 · **Effort:** small

## Goal
Draw `edges.import` as glowing arcs over the city so declared structure is
visible at a glance. This is the layer that turns a pretty city into a
comprehension tool.

## Files
- new: `viewer/src/arcs.js`
- edit: `viewer/src/main.js`, `viewer/src/ui.js` (toggle)

## Geometry
One `THREE.LineSegments` for everything. For each edge, sample a quadratic
bezier from A's roof to B's roof:

```
p0 = (ax, ah + 0.5, az)
p2 = (bx, bh + 0.5, bz)
p1 = midpoint(p0, p2) + (0, lift, 0)
lift = clamp(distance(p0, p2) * 0.35, 6, 70)
```
16 segments per arc, baked once into a `Float32Array` at load. Per-vertex
colour with alpha fading toward the middle looks better than a flat line: use
`LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.55,
blending: THREE.AdditiveBlending, depthWrite: false })`.

Direction cue without arrowheads: colour-ramp each arc from source colour
(brighter) to target colour (dimmer). Arrowheads on thousands of lines are not
worth the geometry.

## Budget
Cap at `maxArcs` (default 2000), chosen by edge weight then by combined degree.
If `edges.import.length > maxArcs`, show a note in the legend: `showing top
2000 of N imports`.

## Interaction hooks (used by T10)
Keep an index: `arcSegmentRange[edgeIndex] = [startVertex, endVertex]` so
hovering a building can recolour only its arcs by writing into the colour
attribute and setting `needsUpdate`. Also keep `arcsByBuilding[i] = [edgeIdx…]`.

## Toggle
`I` toggles arcs. Default **on** for repos with < 400 edges, **off** above that
(otherwise first impression is spaghetti). State the default in the legend.

## Acceptance criteria
- Arcs connect the correct rooftops (spot-check three edges against
  `city.edges.import` by hand).
- Still one draw call.
- fps drop ≤ 5 on the 1000-file city with arcs on.
- No arcs render for buildings that are hidden.
- Screenshot into `docs/img/T08-arcs.png`.

## Default if ambiguous
- Bidirectional pairs draw as two arcs with slightly different lift so both are
  visible.
- Self-edges do not exist (parser guarantees it); do not add handling.
