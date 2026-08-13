# Changelog

Append one line per completed task. Newest last.

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
