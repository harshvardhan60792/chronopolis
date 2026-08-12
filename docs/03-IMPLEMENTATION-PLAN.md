# 03 — Implementation plan

Read with `STATUS.md` (what is done) and `tasks/` (how to do each one).
Phases are ordered by dependency, not by fun. Do not reorder.

## M1 — data is real

| Task | Output | Why now |
|---|---|---|
| **T01 ✅** parser core | `buildings`, `tree`, `edges.import`, `stats` | Everything reads from this |
| **T02** git miner | `git`, per-building churn/authors/dates | Needed by heat, ownership, stories, snapshots |
| **T03** co-change coupling | `edges.cochange` | The traffic data; the project's core novelty |
| **T04** layout engine | `layout.plots`, `layout.districts`, `layout.roads` | Viewer is trivial once this exists |

Exit criteria: `python -m citygen build ../reachable` produces a city with all
four sections populated, deterministic across runs, and `inspect` output that a
human reading the repo agrees with.

## M2 — it is a city

| Task | Output |
|---|---|
| **T05** viewer scaffold + instanced buildings + orbit camera | You can see your repo |
| **T06** district slabs, materials, lighting, sky, fog | It looks intentional |
| **T07** orbit + WASD fly + smooth `flyTo` | It feels like a game |
| **T08** import arcs | Structure becomes visible |

Exit criteria: screenshot of `reachable` that a stranger recognises as a city,
holding 60 fps.

## M3 — it is alive (the differentiators)

| Task | Output |
|---|---|
| **T09** traffic simulation | Roads carry animated flow proportional to co-change |
| **T10** picking + hover + info panel | Click a building, learn the file |
| **T11** time machine | Scrub the repo's whole history |
| **T12** overlay modes + legend | health / recency / ownership / language |

Exit criteria: a 20-second screen recording that makes an engineer say "wait,
go back" — history scrub plus traffic is the moment.

## M4 — it ships

| Task | Output |
|---|---|
| **T13** search + fly-to | Find any file instantly |
| **T14** stories / auto tour | First-load "here is what I found" |
| **T15** PNG postcard + self-contained HTML | Shareable |
| **T16** performance pass | 1000+ files ≥ 30 fps, proven with numbers |
| **T17** onboarding UX | Drag-drop, loading, empty, error states |
| **T18** docs, CI, GitHub Pages | Public |

## Sequencing notes for an autonomous agent

- T05 is the psychological milestone. If time is short, take the shortest path
  to it: T01 → T04 → T05, then backfill T02/T03.
- T09 and T11 both depend on data tasks. If T02/T03 slipped, do T08/T10/T12
  (structure-only features) rather than stalling.
- T16 is not optional polish. It is a stated hard requirement. Budget a full
  session for it and record real fps numbers in `docs/05-PERFORMANCE.md`.
- Every task file ends with **Default if ambiguous** — use it instead of asking.

## Rough effort estimate

| Task | Effort |
|---|---|
| T02, T03, T06, T08, T10, T12, T13, T15, T17 | small (≤1 session each) |
| T05, T07, T14, T18 | medium |
| T04, T09, T11, T16 | large — read the task file completely before coding |
