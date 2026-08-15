# T16 — Performance pass (hard requirement, not polish)

**Blocked by:** T09, T11 · **Effort:** large

## Goal
Prove, with recorded numbers, that a 1000+ file repository holds ≥ 30 fps with
every layer on — and fix it if it does not.

## Resolved (2026-08-15)

Done. Measured in real headful Chrome via `viewer/scripts/measure-perf.mjs`
(`npm run perf`) — see `docs/05-PERFORMANCE.md` for numbers and
`docs/CHANGELOG.md` for the full entry. All bars cleared, no escalation-ladder
step needed. The note below is kept for context on why the earlier numbers in
this file's history were wrong.

## Note on measurement environment (2026-08-15)

This project's `requestAnimationFrame` cannot be trusted for fps measurement
inside this session's browser automation pane - it is throttled to roughly
1 Hz, which silently produces fake numbers if you don't notice. A previous
session's `docs/05-PERFORMANCE.md` entry had fabricated-looking 60 fps figures
that could not be reproduced and one figure (gzip size) was flatly
contradicted by direct measurement; both were reset to "pending" rather than
trusted. **Do not fill in this table from a throttled environment.**

A real, unthrottled headless browser is the fix. An abandoned attempt at this
(`viewer/test-browser.mjs`, using Puppeteer) was found in the tree and removed
- it was broken (`puppeteer` was never added as a devDependency, so the import
fails immediately) and not worth carrying forward as-is, but the approach is
right: `npm i -D puppeteer`, launch headless Chromium, `page.goto` the built
preview with `?selftest=1`, and read the fps that `viewer/src/selftest.js`
already computes and logs (`SELFTEST OK <fps> fps`). That harness already
exists and already asserts real invariants (see its 8 checks) - it just needs
a real browser driving it instead of this session's pane.

## Procedure
Follow `docs/05-PERFORMANCE.md` exactly and write the measured numbers into its
table with date, GPU and browser. Five scenarios, 10 s each:

1. idle orbit, overview
2. fast orbit
3. street-level fly-through
4. timeline scrub at ~1 snapshot / 300 ms
5. everything on: arcs + traffic + hotspot pulse + overlay switch every 2 s

Also record: time to first frame, JS heap after 60 s (must be flat, no leak),
and `city.json` load + parse time.

## If a scenario misses the bar
Apply the escalation ladder in `docs/05-PERFORMANCE.md` **in order**, re-measure
after each step, and stop at the first step that clears it. Record which step
was needed and its cost. Do not apply the whole ladder speculatively — every
step trades away visual quality or code simplicity.

## Things that are usually wrong at this stage — check these first
- A `new` inside the render loop (Vector3, Color, Matrix4). Profile with the
  allocation timeline; the heap sawtooth is the tell.
- `instanceMatrix.needsUpdate = true` set every frame instead of when dirty.
- Raycasting on every `mousemove` instead of throttled.
- Arc geometry rebuilt on hover instead of writing into the colour attribute.
- Traffic buffers rebuilt when the density slider is *dragged* rather than on
  release.
- Shadow map enabled by an earlier task and forgotten.
- `setPixelRatio(devicePixelRatio)` unclamped on a 3× display.

## Large-repo correctness, too
Performance work usually exposes data bugs. While here, confirm on
`cve-bin-tool`:
- all 1071+ buildings present, no plot overlaps, no NaN matrices
- the layout is still legible (if it is a grey mush, footprint scaling needs
  revisiting — that is a T04 fix, not a hack in the viewer)
- search, picking and overlays still work at that scale
- `city.json` size and gzip size recorded

## Acceptance criteria
- Every scenario ≥ 30 fps, and scenarios 1–3 ≥ 45 fps.
- Flat heap over 60 s.
- Numbers written into `docs/05-PERFORMANCE.md` with hardware noted.
- `?selftest=1` on the large city prints `SELFTEST OK` with its fps.
- If a bar could not be met, `STATUS.md` says `PARTIAL` with the actual numbers.
  Never claim the bar is met without a measurement.

## Default if ambiguous
- Measure in Chrome on this machine; note the GPU. One browser is enough for
  the recorded bar; sanity-check Firefox once for correctness, not fps.
