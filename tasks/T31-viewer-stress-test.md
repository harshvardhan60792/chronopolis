# T31 — Viewer stress test: find the wall before building a ladder

**Blocked by:** T26 · **Effort:** small · **Phase:** D (conditional) · **Runs BEFORE T30**

## Why this exists, and why it has the higher number
`docs/05-PERFORMANCE.md:66` says, in the project's own words: *"do not implement
LOD, frustum culling, or octrees until a measurement proves they are needed."*
This task is that measurement. T30 is numbered lower but runs second, and only
if this task says it should.

Building T30 first would be the project overruling its own architecture doc with
no evidence — the exact pattern a skeptical reviewer is looking for, and it costs
more credibility than the feature could earn back.

## Files
- new: `viewer/scripts/stress-perf.mjs`
- new: `scripts/make_synthetic_city.py`
- edit: `docs/05-PERFORMANCE.md`

## Method
Reuse the existing headful-Puppeteer harness pattern from
`viewer/scripts/measure-perf.mjs` — real Chrome, real GPU. Headless SwiftShader
and this IDE's automation pane both throttle rAF and produce numbers that are
not about the renderer at all; T16 already established this and the reasoning
holds.

`scripts/make_synthetic_city.py` generates valid `city.json` documents at
10k / 50k / 100k / 250k buildings by replicating a real repo's structure, so the
layout, districts and distributions stay realistic rather than uniform. Label
every result as synthetic.

Per size, measure and record:
- time to first frame
- fps: idle orbit, fast orbit, fly-through, timeline scrub, everything-on
- draw calls and triangles (`renderer.info.render`)
- JS heap after load, and after 60 s (leak check)
- `city.json` size raw and gzipped, and **time spent in `JSON.parse`**
- picking latency: time from click to panel populated

## What this task is actually looking for
The four candidate walls, which need four different fixes. Name which one
binds:

| Wall | Symptom | Fix (a different task each) |
|---|---|---|
| Document size | `JSON.parse` dominates, or the tab OOMs before first frame | streaming/chunked format — **not** T30 |
| Per-instance upload | first frame slow, fps fine afterwards | chunked upload, still not culling |
| Fragment shader / overdraw | fps drops as the camera gets closer, not as count rises | simplify the facade shader at distance |
| Vertex/draw throughput | fps falls with instance count regardless of camera | **this is the only one T30's culling addresses** |

A box is 12 triangles. Geometric LOD on a box saves essentially nothing, so if
the wall is anything other than the fourth row, "add LOD and frustum culling" is
the wrong fix and T30 must not be built as written.

## Acceptance criteria
1. Numbers at every size, in real headful Chrome, on one machine with its full
   spec recorded: the GPU/browser `docs/05-PERFORMANCE.md` already names
   (`ANGLE (Intel, Intel(R) UHD Graphics...)`), plus CPU, RAM, and OS, in the
   same format T23 records for the analyser side — that doc has GPU/browser
   only today, not the full machine.
2. The first size that fails is identified, with **what** failed and the
   evidence.
3. The binding constraint is named as one of the four rows above.
4. A conclusion is written in this exact form:

> **At `<N>` buildings the viewer's binding constraint is `<wall>`, measured at
> `<evidence>`. T30 is therefore `<SCHEDULED as <specific fix> | NOT BUILT>`.**

5. If Phase D is not built, `STATUS.md` records T30 as
   `WONTFIX: measured, not the bottleneck`, linking this section. **That is a
   successful outcome for this task, not a failure of it.**

## Verify
```bash
python scripts/make_synthetic_city.py --buildings 100000 -o viewer/public/stress-100k.city.json
```
```bash
cd viewer && node scripts/stress-perf.mjs --city public/stress-100k.city.json
```

## Default if ambiguous
- Synthetic cities are always labelled synthetic. Never let a synthetic number
  be read as a measurement of a real repository.
- If the browser cannot load a size at all, that is the most valuable result in
  the task. Record what happened and at what size.
