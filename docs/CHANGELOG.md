# Changelog

Append one line per completed task. Newest last.

- 2026-08-15 — wider language coverage (T01 revisit, continued). Tested 5
  more real GitHub repos: spf13/cobra (Go), sharkdp/fd (Rust), google/gson
  (Java), sinatra/sinatra (Ruby), nlohmann/json (C++). No crashes on any of
  them, but every one rendered with complexity flat at 1 - only the JS/TS
  fix from earlier landed, everything else was still the placeholder tier.
  Added `metrics.go_metrics`: Go's `func` keyword is reserved, so function
  and complexity counting there is nearly as trustworthy as the JS tier (0
  -> 596 functions on cobra). Added `metrics.curly_complexity`: a shared
  decision-point counter (via `if`/`for`/`while`/`switch`/`catch`/`match`,
  all reserved words) for Java, C#, C/C++, PHP, Kotlin, Swift and Rust.
  Deliberately complexity-only - none of these languages marks a function
  or method declaration with a reserved word, so a regex would either miss
  most of them or match every `if (...) {` too; shipping a function count
  that looks precise and isn't would be worse than showing 0. No import
  resolution was attempted for any of these seven - Go's import paths need
  `go.mod` to resolve correctly, and the rest have no relative-specifier
  convention the way JS does, so `import_edges` stays honestly at 0 for
  them. Confirmed real signal: gson's complexity went from uniformly 1 to a
  spread averaging 14.8 (max 422). All 5 repos clean in-browser -
  `?selftest=1` green, zero bad fields, including on the 1189-building C++
  repo with a 4856-complexity outlier. README's Limitations section now
  lists all four tiers (Python AST / JS+Go+TS regex / complexity-only
  regex / LOC-only) instead of a two-tier summary.

- 2026-08-15 — real-repo validation (T01 revisit). Tested against four real
  GitHub repos: psf/requests, pallets/flask (Python, unaffected), and
  expressjs/express, colinhacks/zod (JS/TS, where two real gaps surfaced).
  First: the README claimed a "regex heuristic" fallback for non-Python
  languages, but no such code existed - every JS/TS file rendered flat
  (complexity=1, 0 functions, 0 import arcs) no matter its actual content.
  Added `metrics.js_metrics` (regex-based function/class/complexity/import
  extraction for JS/TS) and `resolve.JsModuleIndex` (relative-specifier
  resolution with the same directory-walk + suffix-append approach as the
  Python resolver), wired into build.py. Confirmed on express: 0 -> 3114
  functions, 0 -> 57 import edges, spot-checked against real files
  (`lib/application.js`: 26 functions/631 lines, matches its actual
  small-method style). Second, found while testing the TS repo: modern
  TypeScript/ESM code writes `from "./foo.js"` even when the real file is
  `foo.ts` (Node's ESM resolution requires the `.js` specifier regardless of
  source extension) - the resolver's naive suffix-append never tried
  stripping that extension first, so zod resolved only 3 of what should be
  ~540 import edges. Fixed by retrying with any known JS/TS extension
  stripped before re-appending resolution suffixes (3 -> 540 edges).
  README's Limitations section corrected to describe what's actually
  implemented (Python AST, JS/TS regex, everything else LOC-only) instead of
  the previous blanket "regex heuristics for imports and complexity" claim
  that wasn't true for any language but JS/TS even now. All four repos
  verified clean in-browser: `?selftest=1` green, zero console errors, zero
  NaN/negative metric fields.

- 2026-08-15 — T18 finished: real README screenshots. Captured
  `docs/img/hero.png`, `overlays.png` and `timemachine.png` by driving the
  actual built app with a headful-Puppeteer script against real city.json
  fixtures - cve-bin-tool (1272 files) for the skyline shots, a 161-commit
  sibling repo for the timeline shot so it would have genuine snapshots and
  ruins to show, not a fabricated example. Found a real layout bug while
  framing the overlay shot: the top-left hint stack and the top-center
  search bar are independently positioned with no awareness of each other's
  height, and my own longer control-hint text (from the camera nav work)
  pushed it into the search bar's territory - capped the hint's width and
  moved the search bar down to clear the stack. README gained a "Getting
  Around" section documenting the new camera controls and a "The Time
  Machine" section with a real screenshot. All 18 tasks are now DONE.

- 2026-08-15 — camera navigation overhaul (T07 revisit). Scroll wheel now
  dollies toward the point under the cursor instead of the screen center
  (the Google Earth / Cities: Skylines convention); WASD/QE pan and rotate
  the orbit camera too, not just fly mode, with pan speed scaled to current
  zoom distance; double-click on open ground flies the camera there;
  fly-mode speed now scales with altitude, crawling near street level and
  covering ground fast up high. Fixed two real bugs found while building
  this: pointer lock can be dropped by the browser itself (Escape, alt-tab)
  without the app calling `exitPointerLock()` first, which left `mode`
  wedged on 'fly' with dead WASD and a stale hint forever - added a
  `pointerlockchange` listener that self-heals back to orbit; and an
  unclamped per-frame `dt` could produce a huge single step (camera
  teleport) after any stall, including a backgrounded tab in a real browser
  - clamped to 100ms.

- 2026-08-15 — T16 (performance pass) measured for real. Added
  `viewer/scripts/measure-perf.mjs` (`npm run perf`): headful Puppeteer Chrome
  driving the built preview, chosen specifically to avoid the two traps that
  produced fake numbers before — the IDE's browser-automation pane throttles
  `requestAnimationFrame` to ~1 Hz, and headless Chrome's default software
  rasterizer isn't representative of real GPU cost. On cve-bin-tool (1272
  buildings) on integrated graphics: 58-61 fps across idle orbit, fast orbit,
  street-level fly-through, timeline scrubbing, and every layer/overlay on at
  once; 1767 ms to first frame; 0 network requests after load; flat JS heap
  over 60 s; `?selftest=1` green. All bars cleared with no escalation-ladder
  step needed. Numbers written into `docs/05-PERFORMANCE.md` with hardware and
  browser version. T16 and its README claim now say DONE instead of pending.

- 2026-08-13 — T01 parser core: repo walk with vendor deny-list, generic + AST
  metrics, decision-point complexity, intra-repo import resolution (absolute,
  relative, `from pkg import submodule`), city.json v1 emitter, `build` and
  `inspect` CLI commands, 7 unit tests, toyrepo fixture. Verified on
  `reachable` and `cve-bin-tool` (1071 py files, 34s build).
- 2026-08-13 — audit of T02–T10 before continuing. Fixed: `git` section missing
  all schema fields; dead `commit_count` check that always passed; O(n²) health
  percentile; hidden-coupling claimed for unparsed files; squarify recursion
  that would overflow the stack on large directories; building gap turning thin
  lots into walls; three test files that could not import their own package;
  a viewer selftest that passed unconditionally and hung when no frames render.
  Added `citygen/tests/test_invariants.py` (10 invariants incl. plot overlap,
  determinism, no-NaN, git schema). Full suite green; viewer verified in
  browser at 60 fps with 448 buildings.
- 2026-08-13 — look pass (ADR-010, ADR-011). Preetham sky with four time-of-day
  presets and a deterministic star field; procedural lit-window facades driven
  by each file's own activity; wet-asphalt ground with Fresnel sky pickup;
  ACES filmic tone mapping; half-res bloom that switches itself off if the
  frame rate cannot afford it; anime.js camera intro. Height formula changed to
  `max(complexity, sloc/18) ** 0.75` because doc-heavy repos were rendering as
  a tiled floor rather than a skyline.
- 2026-08-15 — T11 (time machine) built: history read/apply/reconstruct split
  out of gitmine.py, snapshots.py rewritten from a stub, deleted files get
  stable plots and render as ruins mid-history. Separately, T12-T18 were found
  already implemented in the uncommitted working tree (overlays, search, tour/
  stories, export/serve, onboarding dropzone, CI, GitHub Pages, README/LICENSE)
  from an unattributed prior run. Audited before building on top of it; six
  real bugs fixed: (1) a v3-style animejs call crashed the entire page on load
  against the installed v4 API; (2) an unconditional animated pulse on hotspot
  buildings violated ADR-012 and reintroduced the exact fatigue the calm pass
  removed; (3) `?mode=` deep links were silently discarded by a constructor
  that rewrote the URL before it was read; (4) search/legend/tour all mounted
  into a shrink-wrapped `#ui` box, breaking their viewport-relative CSS -
  fixed with a dedicated full-viewport `#ui2` layer; (5) a permanently
  bouncing CSS animation on the tour hint, another ADR-012 violation; (6) CI's
  `unittest discover` was blind to two of five test files (confirmed: 13 of 30
  real checks ran) - switched to running each file directly. Also fixed a
  subdirectory-analysis bug (git history leaking from a parent repo), a
  pluralisation bug in story text, and corrected `docs/05-PERFORMANCE.md`,
  which claimed measured fps/size numbers that were either unmeasurable in
  this environment or directly contradicted by a real measurement.
- 2026-08-13 — calm pass (ADR-012, ADR-013). Default sky is now daylight, so
  building colour — which every overlay encodes — is readable without
  interaction. All flicker, twinkle and shimmer removed; traffic slowed to a
  third. City now sits in landscape: olive-green land, sea beyond, street trees
  along the avenues and a clustered green belt, with green cover inversely
  proportional to how built-up each district is. Palette regraded on film
  conventions: cool desaturated environment, warm buildings, saturation
  reserved for focus.
- 2026-08-13 — T02 git miner: extracted commits, churn, authorship, bus factor, and age metrics via git log.
- 2026-08-13 — T03 co-change coupling: calculated hidden coupling and co-change traffic edges from git history.
- 2026-08-13 — T04 layout engine: implemented squarified treemap layout assigning plots to buildings.
- 2026-08-13 — T05 viewer scaffold: built Vite+Three.js static frontend with InstancedMesh rendering of the city layout.
- 2026-08-13 — T06 materials: added district ground plates, vertex-color ambient occlusion, and sky gradient.
- 2026-08-13 — T07 camera: implemented orbit mode, pointer-lock fly mode with WASD, and cubic-eased flyTo().
- 2026-08-13 — T08 arcs: rendered import edges as glowing quadratic bezier arcs with color ramping and UI toggles.
- 2026-08-13 — T09 traffic: implemented GPU particle simulation running on baked DataTexture paths.
- 2026-08-13 — T10 picking: added raycast selection, hover dim/highlight logic, and DOM info panel.
