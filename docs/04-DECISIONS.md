# 04 — Architecture decision records

Append new ADRs at the end. Never edit a decided ADR; supersede it with a new
one and mark the old `SUPERSEDED by ADR-NNN`.

---

## ADR-001 — Layout is computed in Python, not the browser
**Status:** accepted
**Context:** Treemap layout could run in the viewer at load time.
**Decision:** `citygen` computes final plot rectangles and writes them to
`city.json`.
**Why:** determinism across runs, stability across time snapshots, keeps the
render loop free, and makes `city.json` a portable artifact other tools can
consume.
**Cost:** a layout change requires re-running the CLI.

## ADR-002 — Buildings are one InstancedMesh
**Status:** accepted
**Decision:** all file boxes live in a single `THREE.InstancedMesh` with
per-instance colour.
**Why:** the 30 fps @ 1000+ files bar is trivially met at ~6 draw calls. LOD and
frustum culling are unnecessary complexity when the whole city is one call.
**Cost:** highlighting requires per-instance colour writes, and picking needs
`instanceId` handling rather than per-object userData.

## ADR-003 — Stable temporal layout over the union of history
**Status:** accepted
**Context:** Rebuilding a treemap per snapshot makes buildings jump around, and
the animation becomes unreadable.
**Decision:** layout is computed **once**, over the union of every file that
existed at any sampled snapshot, using each file's maximum historical footprint.
Snapshots then only change height, visibility and colour.
**Why:** spatial persistence is the entire reason the time machine is legible.
**Cost:** a repo that deleted a huge subtree leaves empty lots in the present
view. Accepted — the empty lot is informative (it is a ruin).

## ADR-004 — Complexity is a decision-point count, not McCabe from a CFG
**Status:** accepted
**Decision:** `1 + count(If, For, While, ExceptHandler, With, Assert, IfExp,
comprehension, BoolOp extra operands, Match cases - 1)`, per function, summed
per file.
**Why:** stdlib-only, ~2% of McCabe on real code, and building height only needs
a monotonic ranking, not an exact metric.
**Cost:** not comparable to published McCabe numbers. Documented in the UI.

## ADR-005 — Co-change coupling is the traffic signal
**Status:** accepted
**Decision:** traffic volume between two buildings = commits changing both,
normalised (see T03), **not** import weight.
**Why:** the novel and more useful signal. Imports are already drawn as arcs;
duplicating them as traffic would waste the channel.
**Cost:** repos with squashed or shallow history produce a thin traffic layer.
Fall back to import-driven traffic when `commit_count < 30`, and say so in the
legend.

## ADR-006 — No dependencies in citygen, `three` + `vite` only in viewer
**Status:** accepted
**Why:** "clone and run" with no install friction; no supply-chain surface; no
build step required to use the CLI. The whole project must stay free and
frictionless to run.

## ADR-007 — Index-based identifiers in `city.json`
**Status:** accepted
**Decision:** edges, plots, snapshot deltas and stories reference buildings by
array index, never by path string.
**Why:** file size (a 2000-file repo saves megabytes) and O(1) lookups in the
viewer with no map construction.
**Cost:** `buildings` ordering is now load-bearing. It is sorted by path and
that sort is an invariant (see schema doc).

## ADR-008 — Deleted files become ruins, not deletions
**Status:** accepted
**Decision:** during timeline playback a deleted file's building sinks and turns
grey rather than vanishing.
**Why:** it preserves the mental map and makes "this district died" visible,
which is one of the more interesting things history reveals.
**Cost:** a long-lived repo accumulates grey. Provide a toggle to hide ruins.

## ADR-009 — Ownership uses commit-author counts, not `git blame`
**Status:** accepted
**Decision:** per-file authorship comes from `git log --name-only` counts, not
line-level blame.
**Why:** blame over thousands of files takes minutes; log parsing is one
subprocess call for the whole repo. Bus factor from commit counts is close
enough for a visual signal.
**Cost:** a single large refactor commit inflates one author's share. Mitigate
by ignoring commits touching more than 100 files (configurable).

## ADR-010 — anime.js is allowed in the viewer; nothing else joins it
**Status:** accepted
**Context:** ADR-006 froze viewer dependencies at `three` + `vite`. The camera
intro, UI entrance and future timeline/tour motion are ordinary tweening, and
hand-rolled easing loops are exactly the code that rots.
**Decision:** add `animejs` (~7 KB, MIT) as the viewer's animation engine for
**non-3D-specific** motion. 3D look and feel - sky, facades, traffic - stays in
shaders; anime.js never drives a per-frame render uniform.
**Why:** it is the framework-agnostic choice for a vanilla JS project, and the
cost is trivial next to three itself.
**Cost:** one more dependency to keep current. The rule stands otherwise: no
React, no UI framework, no component library.

## ADR-011 — The default look is blue hour, and the sky is physically modelled
**Status:** accepted
**Context:** The first renders used a flat black background. The city read as a
chart on a void.
**Decision:** use three's `Sky` (Preetham analytic scattering) with four
presets - blue hour (default), golden hour, night, clear day - and drive sun
colour, hemisphere light, fog, exposure and window-lit amount from the same
preset table. Buildings get a procedural window grid evaluated in the fragment
shader; the ground fakes wet asphalt with a Fresnel term against the horizon
colour.
**Why:** blue hour is the one time of day where the sky is still saturated and
the windows are already lit, which is why nearly every captivating city
photograph is taken then. Doing it analytically keeps it to one draw call and
zero textures, so it costs almost nothing against the 60 fps bar.
**Cost:** more look-tuning constants to maintain, and the facade shader means
buildings can no longer use a stock three material unmodified.

## ADR-012 — Calm by default: daylight, no flicker, city set in landscape
**Status:** accepted, supersedes the defaults in ADR-011 (the preset machinery
from ADR-011 stands; only which preset leads, and the motion budget, changed)
**Context:** The night-metropolis look was striking and bad at the job. A dark
city hides building colour, and building colour is what every overlay mode
encodes — so the prettier it got, the less it explained. Flickering windows and
twinkling stars made it actively tiring: dozens of small high-frequency motions
in the periphery, which is "hard fascination" and the opposite of restful.
**Decision:** three rules, in priority order.
1. **Comprehension outranks looks.** Default sky is `clear morning`; every
   building's own colour is legible without interaction. Night presets remain
   one keypress away.
2. **Motion is slow, broad and rare.** No flicker anywhere. Stars do not
   twinkle, windows do not blink, water does not sparkle, hotspots do not
   pulse. The only always-on motion is drifting cloud and traffic at a third of
   its old speed. Restorative environments are low-arousal ones (Attention
   Restoration Theory, "soft fascination").
3. **The city sits in a landscape.** Olive-green land with low-frequency
   variation, a sea beyond it, street trees along the avenues and a clustered
   green belt around the built area. Green cover is inversely proportional to
   how built-up a district is, so the calm parts of the picture are also the
   quiet parts of the repo — the nature carries data.
**Why:** the tool's first job is to explain a codebase, its second is to be
pleasant enough that people keep exploring. Anything that trades (1) for (3)
gets cut.
**Cost:** less immediately dramatic than the neon night. Accepted.

## ADR-013 — Colour follows a film grade: cool environment, warm data
**Status:** accepted
**Context:** With a thousand boxes on screen, "what should I look at" has to be
answerable pre-attentively.
**Decision:** adopt two conventions from film colour.
*Complementary separation* — environment (sky, sea, land, pavement) is held in
the cool half of the wheel; buildings are warm-biased. Complementary hues push
the subject forward and the background back, which is why the teal/orange grade
is everywhere; here it means buildings detach from the ground with no outline
or glow. *Desaturate the environment, saturate the focus* — terrain stays under
~0.25 saturation, buildings sit at 0.45–0.60, and only the selected building
and search hits go fully saturated (`emphasise()` / `recede()` in
`palette.js`). Saturation itself becomes the signal.
**Why:** it makes selection and search legible without adding UI, and keeps
overlay ramps readable against a neutral stage.
**Cost:** the language palette can no longer use each language's "official"
brand colour, since several are cool and would sink into the terrain.

---

### Template for new ADRs

```
## ADR-0NN — <decision in one line>
**Status:** accepted | superseded by ADR-0MM
**Context:** what forced a choice
**Decision:** what was chosen
**Why:** the reasoning
**Cost:** what this makes harder later
```

## ADR-014 — Pivot to Git history cache for incremental rebuilds
**Status:** accepted
**Context:** Incremental rebuilding was originally meant to include a parsing cache. However, T23 performance measurements revealed that parsing source files takes 3.2% of the total build time on the large tier (5834 files, 1000 commits), while git_read takes 86.6% (24.49s for git_read vs 0.91s for parse). Caching parsed files would add architectural complexity for negligible gains.
**Decision:** We abandoned the parse cache and pivoted to an incremental git history cache (git log <cached_head>..HEAD).
**Why:** git history mining dominates the build time on large repositories. By only mining new commits and prepending them to a cached history, we drastically speed up the build. We enforce a byte-identical invariant between incremental and cold builds by ensuring that if a force-push or rebase breaks the ancestry path (merge-base --is-ancestor), the incremental step silently falls back to a full mine.
**Cost:** The git cache adds persistent storage (.citygen/cache) and disk IO overhead which can slow down incremental builds on very small repositories where git logs are otherwise instantaneous.

## ADR-015 — Tree-sitter is an optional accuracy upgrade, never a requirement
**Status:** accepted, amends ADR-006 (does not supersede it)
**Context:** regex heuristics cap analysis quality for every non-Python language, and 8 languages get no function count at all. Real parsers fix this. ADR-006 forbids dependencies.
**Decision:** `citygen` core stays stdlib-only and fully functional with zero dependencies. Tree-sitter enters as an extra (`pip install citygen[parsers]`). When the extra is present, a tree-sitter backend supplies metrics; when absent, the existing regex/ast path runs unchanged. CI tests BOTH paths on every commit. We pin the official individual language packages (`tree-sitter-java` etc.) since no single maintained bundle (like `tree-sitter-languages`) is compatible with modern Python environments.
**Why:** keeps the frictionless install that makes people try it, without capping accuracy forever for people who want more.
**Cost:** two parsing paths to keep in agreement, a differential test suite to prove they agree (T28), and a permanent rule that the zero-dep path is the default.
