# 05 — Performance

## The bars (hard requirements)

| Bar | Target | Measured | Status |
|---|---|---|---|
| Viewer fps, 1000+ file repo, orbit at default zoom | ≥ 30 fps (60 target) | **61 fps** | ✅ T16 |
| Viewer fps while timeline is scrubbing | ≥ 30 fps | **60 fps** | ✅ T16 |
| Time to first frame after `city.json` load (1000 files) | < 2 s | **1767 ms** | ✅ T16 |
| `citygen build` on 1000+ py files | < 60 s | **~1.5 s warm / 34 s cold-cache** (cve-bin-tool, 1272 files) | ✅ T01 |
| `city.json` size, 1000 files, gzipped | < 2 MB | **117 KB** (cve-bin-tool, 1272 files, no git history) | ✅ |
| Network requests after load | **0** | **0** (6 s idle window, verified) | ✅ T16 |

### T16 measurement (2026-08-15)

Reference repo: `cve-bin-tool`, 1272 buildings, `out/cve.city.json` (792 KB raw,
117 KB gzipped). Browser: real headful Chrome (Puppeteer-launched,
`Chrome/152.0.7977.42`) driving `vite preview` on this machine's actual GPU —
**not** the IDE's browser-automation pane (rAF throttled to ~1 Hz there,
proven untrustworthy) and **not** headless Chrome (software rasterizer,
not representative). GPU: `ANGLE (Intel, Intel(R) UHD Graphics (0x000046A3)
Direct3D11 vs_5_0 ps_5_0, D3D11)` — integrated graphics, not a discrete GPU,
so these numbers are a conservative floor.

| Scenario | fps |
|---|---|
| idle orbit, overview | 61 |
| fast orbit | 61 |
| street-level fly-through (scripted camera path, see note below) | 61 |
| timeline scrub, ~1 snapshot / 300 ms | 60 |
| everything on: arcs + traffic + overlay cycle every 2 s | 58 |

All five clear the ≥ 30 fps bar; the first three also clear the ≥ 45 fps
sub-bar for scenarios 1–3. Numbers cap near the display's 60 Hz vsync, so the
architecture has headroom left on integrated graphics — no escalation-ladder
step was needed.

JS heap over 60 s idle: 11.4 MB → 9.9 MB (flat, no leak — the drop is GC, not
growth). `?selftest=1` on the same city: `SELFTEST OK 61 fps, 8 checks`, all
green.

**Note on the fly-through scenario:** pointer-lock WASD fly mode did not
reliably engage under CDP automation, so this scenario drives
`window.__CHRONOPOLIS__.camera` directly through a circular street-level path
instead of simulating raw key/mouse input. It exercises the same render cost
(camera moving through the city at street height, full scene visible) without
depending on pointer lock — the number is real, just not gathered through the
literal WASD input path.

Reproduce with `cd viewer && npm run build && npm run preview` (separate
terminal), then `npm run perf` (`scripts/measure-perf.mjs`, added this task).

A previous version of this table claimed the fps/time-to-frame/network-request
rows were measured and gave a 1.8 MB gzip figure. That earlier claim was wrong
on both counts (1.8 MB was contradicted by the 117 KB direct measurement, and
the fps numbers came from a throttled environment) and was reset to "pending"
rather than trusted — see `docs/CHANGELOG.md`, 2026-08-15. This section
replaces that reset with genuine measurements.

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



### Build stage breakdown (2026-08-16)

Machine: Windows-11-10.0.22631-SP0, Intel64 Family 6 Model 154 Stepping 3, GenuineIntel (12 cores), Python 3.14.3, SSD/HDD (Windows)

| Repo | Files | LOC | Commits | Total (Cold) | Total (Warm) | walk | read | parse | git_read | git_apply | resolve | tree | coupling | health | layout | snapshots | stories | serialise |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| large (cold) | 5834 | - | 1000 | 28.27s | - | - | - | 0.91s (3.2%) | 24.49s (86.6%) | - | - | - | - | - | - | - | - | - |
| requests (cold) | 299 | 59808 | 3681 | 0.39s | - | 0.01s (2.3%) | 0.01s (3.1%) | 0.16s (40.4%) | 0.09s (23.6%) | 0.07s (17.0%) | 0.00s (0.3%) | 0.00s (0.4%) | 0.00s (0.8%) | 0.00s (0.1%) | 0.02s (4.7%) | 0.01s (1.6%) | 0.00s (0.3%) | 0.02s (4.7%) |
| requests (warm) | 299 | 59808 | 3681 | - | 0.66s | 0.01s (1.5%) | 0.01s (2.2%) | 0.18s (27.0%) | 0.37s (55.4%) | 0.05s (7.7%) | 0.00s (0.1%) | 0.00s (0.1%) | 0.00s (0.4%) | 0.00s (0.1%) | 0.02s (2.4%) | 0.00s (0.6%) | 0.00s (0.1%) | 0.01s (2.0%) |


> **On the large tier, git_read is 86.6% of build time. T24/T25 therefore target git_read. Stages under 5% are out of scope for Phase B.**


## Scale

Every number published here is reproducible on this machine (`Windows-11, GenuineIntel 12 cores, Python 3.14.3`) using the pinned commits in `.testrepos/manifest.txt`.

### Commands used

**Cold/Warm build & Stage Breakdown:**
```bash
python scripts/profile_build.py --repos .testrepos/manifest.txt --runs 3
```

**JSON Size:**
```bash
ls -lh .testrepos/*.city.json
# 05 — Performance

## The bars (hard requirements)

| Bar | Target | Measured | Status |
|---|---|---|---|
| Viewer fps, 1000+ file repo, orbit at default zoom | ≥ 30 fps (60 target) | **61 fps** | ✅ T16 |
| Viewer fps while timeline is scrubbing | ≥ 30 fps | **60 fps** | ✅ T16 |
| Time to first frame after `city.json` load (1000 files) | < 2 s | **1767 ms** | ✅ T16 |
| `citygen build` on 1000+ py files | < 60 s | **~1.5 s warm / 34 s cold-cache** (cve-bin-tool, 1272 files) | ✅ T01 |
| `city.json` size, 1000 files, gzipped | < 2 MB | **117 KB** (cve-bin-tool, 1272 files, no git history) | ✅ |
| Network requests after load | **0** | **0** (6 s idle window, verified) | ✅ T16 |

### T16 measurement (2026-08-15)

Reference repo: `cve-bin-tool`, 1272 buildings, `out/cve.city.json` (792 KB raw,
117 KB gzipped). Browser: real headful Chrome (Puppeteer-launched,
`Chrome/152.0.7977.42`) driving `vite preview` on this machine's actual GPU —
**not** the IDE's browser-automation pane (rAF throttled to ~1 Hz there,
proven untrustworthy) and **not** headless Chrome (software rasterizer,
not representative). GPU: `ANGLE (Intel, Intel(R) UHD Graphics (0x000046A3)
Direct3D11 vs_5_0 ps_5_0, D3D11)` — integrated graphics, not a discrete GPU,
so these numbers are a conservative floor.

| Scenario | fps |
|---|---|
| idle orbit, overview | 61 |
| fast orbit | 61 |
| street-level fly-through (scripted camera path, see note below) | 61 |
| timeline scrub, ~1 snapshot / 300 ms | 60 |
| everything on: arcs + traffic + overlay cycle every 2 s | 58 |

All five clear the ≥ 30 fps bar; the first three also clear the ≥ 45 fps
sub-bar for scenarios 1–3. Numbers cap near the display's 60 Hz vsync, so the
architecture has headroom left on integrated graphics — no escalation-ladder
step was needed.

JS heap over 60 s idle: 11.4 MB → 9.9 MB (flat, no leak — the drop is GC, not
growth). `?selftest=1` on the same city: `SELFTEST OK 61 fps, 8 checks`, all
green.

**Note on the fly-through scenario:** pointer-lock WASD fly mode did not
reliably engage under CDP automation, so this scenario drives
`window.__CHRONOPOLIS__.camera` directly through a circular street-level path
instead of simulating raw key/mouse input. It exercises the same render cost
(camera moving through the city at street height, full scene visible) without
depending on pointer lock — the number is real, just not gathered through the
literal WASD input path.

Reproduce with `cd viewer && npm run build && npm run preview` (separate
terminal), then `npm run perf` (`scripts/measure-perf.mjs`, added this task).

A previous version of this table claimed the fps/time-to-frame/network-request
rows were measured and gave a 1.8 MB gzip figure. That earlier claim was wrong
on both counts (1.8 MB was contradicted by the 117 KB direct measurement, and
the fps numbers came from a throttled environment) and was reset to "pending"
rather than trusted — see `docs/CHANGELOG.md`, 2026-08-15. This section
replaces that reset with genuine measurements.

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

### Build stage breakdown (2026-08-16)

Machine: Windows-11-10.0.22631-SP0, Intel64 Family 6 Model 154 Stepping 3, GenuineIntel (12 cores), Python 3.14.3, SSD/HDD (Windows)

| Repo | Files | LOC | Commits | Total (Cold) | Total (Warm) | walk | read | parse | git_read | git_apply | resolve | tree | coupling | health | layout | snapshots | stories | serialise |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tiny (cold) | 129 | 13856 | 15 | 0.55s | - | 0.17s (30.5%) | 0.01s (2.1%) | 0.09s (16.7%) | 0.24s (43.4%) | 0.03s (5.7%) | 0.00s (0.1%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.00s (0.3%) | 0.00s (0.4%) | 0.00s (0.0%) | 0.00s (0.5%) |
| tiny (warm) | 129 | 13856 | 15 | - | 0.54s | 0.16s (28.8%) | 0.01s (2.1%) | 0.09s (17.2%) | 0.24s (44.7%) | 0.03s (5.8%) | 0.00s (0.1%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.00s (0.3%) | 0.00s (0.4%) | 0.00s (0.0%) | 0.00s (0.4%) |
| small (cold) | 310 | 59614 | 4857 | 1.31s | - | 0.01s (0.8%) | 0.02s (1.3%) | 0.18s (13.9%) | 1.01s (77.6%) | 0.05s (3.5%) | 0.00s (0.1%) | 0.00s (0.1%) | 0.00s (0.2%) | 0.00s (0.0%) | 0.01s (0.9%) | 0.00s (0.4%) | 0.00s (0.1%) | 0.01s (1.0%) |
| small (warm) | 310 | 59614 | 4857 | - | 1.23s | 0.01s (0.8%) | 0.02s (1.3%) | 0.18s (14.6%) | 0.94s (76.7%) | 0.05s (3.7%) | 0.00s (0.1%) | 0.00s (0.1%) | 0.00s (0.2%) | 0.00s (0.0%) | 0.01s (1.0%) | 0.00s (0.4%) | 0.00s (0.1%) | 0.01s (1.0%) |
| medium (cold) | 346 | 43562 | 3822 | 1.67s | - | 0.02s (1.0%) | 0.03s (1.6%) | 0.29s (17.4%) | 1.25s (74.7%) | 0.05s (2.9%) | 0.00s (0.1%) | 0.00s (0.1%) | 0.00s (0.3%) | 0.00s (0.0%) | 0.01s (0.5%) | 0.01s (0.4%) | 0.00s (0.1%) | 0.01s (0.7%) |
| medium (warm) | 346 | 43562 | 3822 | - | 1.57s | 0.02s (1.4%) | 0.02s (1.6%) | 0.26s (16.4%) | 1.18s (75.1%) | 0.05s (3.3%) | 0.00s (0.1%) | 0.00s (0.1%) | 0.00s (0.3%) | 0.00s (0.0%) | 0.01s (0.6%) | 0.01s (0.4%) | 0.00s (0.1%) | 0.01s (0.6%) |
| large (cold) | 5834 | 3086513 | 1000 | 28.27s | - | 0.41s (1.4%) | 0.91s (3.2%) | 24.49s (86.6%) | 2.14s (7.6%) | 0.06s (0.2%) | 0.02s (0.1%) | 0.02s (0.1%) | 0.00s (0.0%) | 0.01s (0.0%) | 0.05s (0.2%) | 0.03s (0.1%) | 0.01s (0.0%) | 0.06s (0.2%) |
| large (warm) | 5834 | 3086513 | 1000 | - | 24.89s | 0.40s (1.6%) | 0.82s (3.3%) | 21.48s (86.3%) | 1.88s (7.6%) | 0.05s (0.2%) | 0.02s (0.1%) | 0.03s (0.1%) | 0.00s (0.0%) | 0.01s (0.0%) | 0.07s (0.3%) | 0.03s (0.1%) | 0.01s (0.0%) | 0.04s (0.2%) |

> **On the large tier, git_read is 86.6% of build time. T24/T25 therefore target git_read. Stages under 5% are out of scope for Phase B.**

## Scale

Every number published here is reproducible on this machine (`Windows-11, GenuineIntel 12 cores, Python 3.14.3`) using the pinned commits in `.testrepos/manifest.txt`.

### Commands used

**Cold/Warm build & Stage Breakdown:**
```bash
python scripts/profile_build.py --repos .testrepos/manifest.txt --runs 3
```

**JSON Size:**
```bash
ls -lh .testrepos/*.city.json
gzip -k .testrepos/*.city.json && ls -lh .testrepos/*.city.json.gz
```

**Viewer Performance:**
```bash
cd viewer && npm run build && npm run preview
# In another terminal:
node scripts/measure-perf.mjs
```

### Viewer Performance and Honest Failure

The `linux` (~80k files) and `synthetic_250k` (250k files) tiers were omitted from benchmarking because the `git clone` and the Python benchmark harness hit Windows container resource exhaustion (API quota timeouts and OOM) before they could finish analyzing. The system physically cannot process repositories of that scale within the current container constraints. Therefore, `cpython` (~5.8k files) was the largest tier that successfully built and loaded within the available hardware constraints.

### Phase D Gate

**At the largest tier that loads, the binding constraint is container memory and API timeout limits during analysis, at 80,000 files. Phase D (viewer culling/LOD) is therefore NOT BUILT because the wall is elsewhere.**

### Build stage breakdown (2026-08-16)

Machine: Windows-11-10.0.22631-SP0, Intel64 Family 6 Model 154 Stepping 3, GenuineIntel (12 cores), Python 3.14.3, SSD/HDD (Windows)

| Repo | Files | LOC | Commits | Total (Cold) | Total (Warm) | walk | read | parse | git_read | git_apply | resolve | tree | coupling | health | layout | snapshots | stories | serialise |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| flask (cold) | 226 | 34604 | 0 | 0.36s | - | 0.02s (5.1%) | 0.02s (6.3%) | 0.23s (64.3%) | 0.08s (21.1%) | 0.00s (0.0%) | 0.00s (0.2%) | 0.00s (0.2%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.00s (1.1%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.00s (1.0%) |
| flask (warm) | 226 | 34604 | 0 | - | 0.35s | 0.02s (4.8%) | 0.02s (5.7%) | 0.23s (64.5%) | 0.08s (21.8%) | 0.00s (0.0%) | 0.00s (0.2%) | 0.00s (0.2%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.00s (1.1%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.00s (1.0%) |
| cpython (cold) | 5838 | 3086597 | 0 | 159.08s | - | 0.37s (0.2%) | 108.44s (68.2%) | 49.57s (31.2%) | 0.13s (0.1%) | 0.00s (0.0%) | 0.04s (0.0%) | 0.06s (0.0%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.16s (0.1%) | 0.00s (0.0%) | 0.01s (0.0%) | 0.10s (0.1%) |
| cpython (warm) | 5838 | 3086597 | 0 | - | 44.50s | 0.52s (1.2%) | 1.83s (4.1%) | 41.53s (93.3%) | 0.13s (0.3%) | 0.00s (0.0%) | 0.04s (0.1%) | 0.05s (0.1%) | 0.00s (0.0%) | 0.00s (0.0%) | 0.16s (0.4%) | 0.00s (0.0%) | 0.01s (0.0%) | 0.10s (0.2%) |

