# tasks/

One file per task. Pick the first `TODO` in `../STATUS.md` whose dependencies
are `DONE`, open its file here, and follow it.

Every task file has the same sections:

- **Goal** — what exists after this task that did not before
- **Files** — exactly what to create and edit
- **Algorithm / behaviour** — enough detail to implement without redesigning
- **Acceptance criteria** — the bar for calling it done
- **Verify** — the command(s) that must pass
- **Default if ambiguous** — the decision to take instead of asking a human

| File | Task | Depends on |
|---|---|---|
| `T01-parser-core.md` | Parser core ✅ | — |
| `T02-git-miner.md` | Git churn, authors, recency | T01 |
| `T03-cochange-coupling.md` | Co-change coupling (traffic signal) | T02 |
| `T04-layout-engine.md` | Stable temporal treemap | T01 |
| `T05-viewer-scaffold.md` | Viewer + instanced buildings + orbit | T04 |
| `T06-districts-materials.md` | Districts, lighting, sky | T05 |
| `T07-camera-controls.md` | Orbit + fly + flyTo | T05 |
| `T08-import-arcs.md` | Import arcs | T05 |
| `T09-traffic-simulation.md` | GPU traffic | T03, T06 |
| `T10-picking-panel.md` | Picking, hover, info panel | T05 |
| `T11-time-machine.md` | Snapshots + timeline | T02, T04, T05 |
| `T12-overlays-legend.md` | Overlay modes + legend | T02, T06 |
| `T13-search-flyto.md` | Search + filters | T07, T10 |
| `T14-stories-tour.md` | Rule-based findings + tour | T02, T03, T07 |
| `T15-export-share.md` | PNG + self-contained HTML | T05 |
| `T16-performance-pass.md` | 1000+ files ≥ 30 fps | T09, T11 |
| `T17-onboarding-ux.md` | Drop zone, loading, errors | T05 |
| `T18-docs-ci-deploy.md` | README, CI, Pages | T16 |

## Phase 2 — code-intelligence engine

Plan and rationale: `../docs/07-PHASE2-PLAN.md`. Read it before starting any
task below; it fixes the ordering, the ADR changes, and the kill criteria.

| File | Task | Depends on |
|---|---|---|
| `T19-impact-cli.md` | `citygen impact` — blast radius | — |
| `T20-risk-command.md` | `citygen risk` — the shared risk engine | T19 |
| `T21-pr-risk-comment.md` | PR comment with the finding, not a link | T19, T20 |
| `T22-precommit-hook.md` | `citygen hook install` | T20 |
| `T23-profile-harness.md` | **Measure before optimising** | — |
| `T24-cache-layer.md` | Content-addressed parse cache | T23 |
| `T25-incremental-rebuild.md` | Invalidation graph, byte-identical output | T24 |
| `T26-scale-proof.md` | Real numbers on 40k–250k-file repos | T25 |
| `T27-treesitter-backend.md` | Optional real parsers (ADR-0NN — take the next free number, likely not 014, since T25 may already have taken it) | T25 |
| `T28-parser-parity.md` | Differential proof the new parser is better | T27 |
| `T29-call-graph.md` | Fill `edges.call` at last | T27, T28 |
| `T32-szz-ground-truth.md` | Mine bug-introducing commits | T20 |
| `T33-risk-validation.md` | Validate the score; publish either way | T32 |
| `T34-writeup.md` | The engineering write-up | T25, T26, T33 |
| `T31-viewer-stress-test.md` | Find the viewer's wall — **runs before T30** | T26 |
| `T30-viewer-scale.md` | **CONDITIONAL** — only if T31 says so | T31 |

Three rules specific to Phase 2, from the plan:

1. **T23 before T24/T25.** Do not build a cache for a stage nobody measured.
2. **T31 before T30**, and T30 probably never. `docs/05-PERFORMANCE.md:66`
   forbids culling work without a measurement demanding it.
3. **T32's manual audit before T33 publishes anything.** An evaluation with
   unaudited labels is not an evaluation.

If you finish everything: the v2 backlog lives at the bottom of
`../docs/00-VISION.md` non-goals plus `../docs/OPEN-QUESTIONS.md`.
