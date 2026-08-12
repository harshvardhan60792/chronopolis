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

If you finish everything: the v2 backlog lives at the bottom of
`../docs/00-VISION.md` non-goals plus `../docs/OPEN-QUESTIONS.md`. Do not start
v2 work while any `TODO` above remains.
