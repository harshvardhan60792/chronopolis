# T11 — Time machine (headline feature)

**Blocked by:** T02, T04, T05 · **Effort:** large · Two halves: citygen + viewer

## Goal
A timeline scrubber that replays the repository's entire history: buildings
rise as files are created, grow with complexity, decay when abandoned, and sink
into ruins when deleted — on a layout that never moves (ADR-003, ADR-008).

---

## Part A — citygen (`citygen/snapshots.py`)

### Choosing snapshots
Default `--snapshots 24`, evenly spaced by **commit date** between the first and
last commit (not evenly by commit count — calendar time reads more naturally).
For each snapshot pick the last commit at or before that date.

### Getting per-file metrics at each snapshot — the cheap way
Do **not** check out 24 working trees. Two accepted strategies:

**A1 (default, fast, approximate):** reconstruct LOC over time from numstat.
Walking commits in order, maintain `loc[path] += adds - dels` (clamped ≥ 0),
`exists[path]` toggled by creation/deletion. Complexity is not available
historically, so scale the present complexity by the LOC ratio:
`complexity_at_t ≈ complexity_now * (loc_at_t / loc_now)`.
Record `snapshots.method = "numstat"` and say "approximate" in the UI legend.
Cost: zero extra git calls (reuses T02's stream).

**A2 (opt-in, exact, slow):** `--snapshots-exact` runs
`git ls-tree -r <sha>` per snapshot plus `git show <sha>:<path>` for changed
Python files, re-running the real AST metrics. Correct, and roughly N×
slower. Implement only after A1 works; gate behind the flag.

### Union layout
`build.py` must compute layout **after** snapshots so the layout tree includes
every path that ever existed, weighted by each file's **maximum** historical
LOC. Files that no longer exist get a plot and are marked
`buildings[i].deleted = true` with `died_ts`.

### Output
Sparse deltas exactly as specified in `docs/02-DATA-SCHEMA.md`
(`snapshots.ts/labels/commits/delta[]`, with `born`, `died`, `h`). Emit a height
entry only when it differs from the previous snapshot by more than 1%.

Also emit `snapshots.stats[]`: per snapshot `{files, loc, authors_active,
commits_since}` — the timeline UI graphs this as a sparkline.

---

## Part B — viewer (`viewer/src/timeline.js`)

### State
- `heights: Float32Array(n)` current, `targets: Float32Array(n)`,
  `alive: Uint8Array(n)` (0 unborn, 1 alive, 2 ruin).
- Scrubbing sets targets from the snapshot deltas: apply deltas cumulatively
  from the last applied index (forward or backward — keep a prefix cache of
  every 8th snapshot as a full state so seeking backwards is cheap).

### Animation
Lerp `heights → targets` over 400 ms with `easeOutCubic`. Each frame, write
instance matrices **only for indices in the dirty set**, then one
`instanceMatrix.needsUpdate = true`. Unborn buildings scale to 0 (invisible);
ruins keep 40% height, desaturate toward grey, and lose their arcs.

### UI
- Bottom bar: a slider across snapshot indices, the date label, a play/pause
  button, and speed (0.5× / 1× / 2×).
- Play advances one snapshot per 700 ms at 1×.
- A sparkline of `snapshots.stats[].loc` behind the slider.
- `←` / `→` step snapshots, `Space` plays/pauses.
- A "now" button jumps to the last snapshot.
- Show the method honestly: `history reconstructed from commit stats
  (approximate)` when `method === "numstat"`.

### Interaction with other layers
- Traffic and arcs must hide edges whose endpoints are not yet born.
- The info panel shows the values **at the current snapshot**, with the present
  value in parentheses when they differ.

## Acceptance criteria
- Scrubbing the full timeline holds ≥ 30 fps on the 1000-file city.
- No building ever changes its x/z position while scrubbing. This is the
  headline property — test it: capture `layout.plots` hashes before and after.
- Playing from first to last snapshot tells a legible story (watch it; if it
  flickers or reshuffles, the delta application is wrong).
- Seeking backwards is as fast as forwards (prefix cache working).
- `snapshots` adds < 1 MB gzipped to a 1000-file city.

## Default if ambiguous
- 24 snapshots, numstat method, ruins visible with a toggle.
- Repos with fewer than 10 commits: emit `snapshots: null` and hide the
  timeline UI entirely rather than showing a two-frame animation.
