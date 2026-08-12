# T04 — Layout engine: stable temporal squarified treemap

**Blocked by:** T01 · **Effort:** large · **Fills:** `city.layout`

This is the hardest pure-logic task and everything visual depends on it. Read
the whole file before writing code.

## Goal
Assign every building a non-overlapping rectangular plot on a 400 × 400 ground
plane, grouped so that folders read as districts, with streets between them and
a layout that never changes when the timeline moves (ADR-003).

## Files
- new: `citygen/layout.py`
- edit: `citygen/build.py` (call after metrics, before emit), `citygen/cli.py`
  (`--world-size`, `--street-width`, `--height-scale`)
- new: `citygen/tests/test_layout.py`

## Step 1 — build the nesting tree
From `buildings[].dir` and `tree`, construct a node tree:
`root → dirs → files`. Every node needs a **weight**:

```
weight(file) = max(1.0, sqrt(loc))       # sqrt keeps a 5000-line file from
                                          # eating the map
weight(dir)  = sum(weight(children)) 
```
Use `sqrt(loc)` for area so footprint stays proportional-ish to size without
enormous outliers. Height is a separate metric (step 4).

**Stability rule:** if `snapshots` will exist (T11), weight uses each file's
**maximum LOC across history**, and the tree includes every file that ever
existed. In T04, current state is fine — but write the function to take a
`weight_fn` so T11 can swap it without restructuring.

## Step 2 — squarified treemap, recursive
Classic Bruls/Huizing/van Wijk squarified algorithm. Per node:

```python
def squarify(children, rect):
    # children sorted by weight desc (ties broken by path -> deterministic)
    # place a "row" along the shorter side, greedily adding children while
    # the worst aspect ratio improves; then recurse on the remaining rect
```
Aspect ratio target 1.0; the standard `worst()` function:
`max(rowMax*w²/s², s²/(rowMin*w²))` where `s` is row sum and `w` the side
length. Pseudocode is in any squarified-treemap reference; implement it
directly, do not approximate with a slice-and-dice — slice-and-dice produces
long thin slivers that look nothing like a city.

## Step 3 — streets and padding
When a district rectangle is subdivided:
- inset the district rect by `street_width` (default 2.0 units) on all sides
  before laying out its children — this creates the road grid for free
- inset every leaf plot by `building_gap` (default 0.6) so buildings do not
  touch
- district slab = the un-inset rectangle, drawn at y ≈ 0 with height 0.2 and a
  colour keyed to `depth` (depth 1 districts get distinct hues, deeper ones
  get shaded variants of the parent hue)

Minimum plot size: 1.2 × 1.2. If a district cannot fit its children at minimum
size, grow the district rectangle proportionally at the parent level rather
than shrinking below the minimum (a city with invisible buildings is useless).

## Step 4 — heights
```
h = height_scale * (complexity ** 0.65)
clamp to [1.5, 90]
```
`height_scale` default 1.6. Exponent < 1 keeps one monster file from becoming a
2 km spike that hides the city. Record the chosen scale in
`layout.height_formula` as a string so the UI legend can state it.

## Step 5 — roads for traffic (needed by T09)
For each co-change pair (or import edge in the fallback case) in the top N by
strength, compute a polyline between the two plot centres that runs along
street space rather than through buildings:

Simplest correct approach — **L-shaped Manhattan route with a mid corridor**:
1. from A's centre, go to the nearest street centreline of A's district
2. travel along district-boundary streets to B's district (route on the coarse
   grid of district rectangle edges)
3. enter B

If routing on district boundaries proves fiddly, the accepted fallback is a
**quadratic bezier lifted above the rooftops** (control point at
`max(h_a, h_b) * 1.4`) — arcs instead of streets. Do that rather than shipping
routes that clip through buildings. Record which you used in `layout.road_style`
(`"streets"` | `"arcs"`).

## Output
Fill `layout` exactly as specified in `docs/02-DATA-SCHEMA.md`:
`world`, `districts[]`, `plots[]` (parallel to `buildings`), `roads[]`,
plus `height_formula` and `road_style`.

## Acceptance criteria
- `len(plots) == len(buildings)`, same order.
- **No two plots overlap** (assert in tests, area-intersection check).
- Every plot lies inside its district rectangle.
- Every district lies inside its parent, and inside the world rect.
- Aspect ratio: 90th percentile of `max(w,d)/min(w,d)` across plots ≤ 3.0.
- Deterministic across runs.
- `python scripts/preview_layout.py out/reachable.city.json` writes an SVG
  top-down preview to `out/layout.svg` — **write this script, it is how you
  check the layout without a browser.** Look at it before declaring done.

## Verify
```bash
python citygen/tests/test_layout.py
```
```bash
python -m citygen build ../reachable -o out/reachable.city.json && python scripts/preview_layout.py out/reachable.city.json
```

## Default if ambiguous
- World size 400 × 400, street width 2.0, gap 0.6, height scale 1.6.
- Root-level files (no directory) go in a district called `"/"` placed last.
- Empty directories are skipped entirely.
- If a repo has one giant directory, that is correct output, not a bug.
