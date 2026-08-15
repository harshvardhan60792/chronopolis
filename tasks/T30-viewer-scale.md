# T30 — Viewer scaling · CONDITIONAL: do not start without T31's verdict

**Blocked by:** T31 · **Effort:** unknown until T31 reports · **Phase:** D
**Status by default: NOT SCHEDULED.**

## Read this before anything else
This task exists as a placeholder with a gate on it, not as planned work.

`docs/05-PERFORMANCE.md:66` forbids implementing LOD, frustum culling or octrees
without a measurement proving they are needed. `ADR-002` states that one
InstancedMesh makes culling "unnecessary complexity". Both stand until T31
overturns them with evidence.

**If T31's verdict is anything other than "vertex/draw throughput is the binding
constraint", this task is not built.** Mark it in `STATUS.md` as
`WONTFIX: measured, not the bottleneck`, link T31's section, and move on. Closing
a task because the measurement said so is a good outcome and should be recorded
proudly, not quietly.

## If — and only if — T31 schedules it
Then, and only then, this task is **rewritten** to implement the specific fix
T31 named. Do not write that implementation plan now: a plan written before the
measurement would be a guess wearing the costume of a design, and would bias the
measurement it is supposed to follow.

The general shape it would take, recorded only so the gate is understandable:

- Split the single `InstancedMesh` into spatial chunks (a grid over the world
  plane, since the city is essentially 2.5D — an octree is overkill for a
  height-field of boxes).
- Cull per chunk against the camera frustum on the CPU. Draw calls become the
  number of visible chunks — tens, not thousands — which **preserves ADR-002's
  actual intent** (a low, bounded draw-call count) rather than reverting to
  per-object meshes.
- Keep picking working: `instanceId` currently indexes the single mesh, and
  chunking changes that mapping. This is where the bugs would be.
- The timeline, overlays and search all write per-instance colour and would each
  need chunk-aware writes.

That last point is why this is not a small task, and why it must not be started
on speculation: four subsystems currently assume one mesh and one index space.

## Required before any code
Write **ADR-015** in `docs/04-DECISIONS.md`, superseding ADR-002, and **quote
T31's measurement in its Context section**. An ADR that supersedes another
without citing the evidence that forced it is exactly the kind of undocumented
reversal `docs/04-DECISIONS.md`'s own header rules were written to prevent.

## Acceptance criteria (only meaningful once scheduled)
1. ADR-015 written, citing T31's numbers.
2. ≥30 fps at the size T31 identified as failing, on the same machine.
3. Draw-call count reported before and after.
4. Picking, timeline scrubbing, all six overlay modes, and search highlighting
   verified working after chunking — each is a separate check, and each is a
   plausible regression.
5. No visual change at small sizes. A 40-file city must render identically to
   before, verified by screenshot comparison.
6. No new always-on motion. ADR-012 stands regardless of what changes here.

## Default if ambiguous
- If in doubt about whether T31's verdict schedules this: it does not. The
  default is not building it.
