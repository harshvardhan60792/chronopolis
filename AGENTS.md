# AGENTS.md — read this before touching anything

You are picking up a project mid-build. This file tells you exactly how to
continue without breaking what exists or duplicating work.

## 60-second orientation

1. Read `STATUS.md` — the task table. It is the truth about what is done.
2. Find the first task whose status is `TODO` and whose `Blocked by` tasks are
   all `DONE`. That is your task. Do not skip ahead.
3. Open `tasks/T<NN>-*.md`. It contains goal, files to touch, algorithm,
   acceptance criteria and the exact verify command.
4. Do the task. Run the verify command. It must pass.
5. Update `STATUS.md`: set the row to `DONE`, fill the date and a one-line note.
6. Append a line to `docs/CHANGELOG.md`.
7. Stop and pick the next task. One task per commit.

## Rules that are not negotiable

- **No dependencies in `citygen/`.** Python standard library only. No
  gitpython, no networkx, no numpy. This keeps `pip install`-free operation.
- **No backend, no network calls, no AI/LLM/ML anywhere.** The viewer must work
  opened from `file://` with the JSON already loaded. If you find yourself
  adding a fetch to a remote host, you have made a mistake.
- **`viewer/` dependencies: `three`, `vite` and `animejs` only** (animejs added
  by ADR-010 for UI/camera tweening). No React, no state library, no UI
  framework, no postprocessing packages beyond what ships inside
  `three/examples/jsm`.
- **The look is a system, not a pile of constants.** Sun colour, fog, exposure,
  window-lit amount and bloom strength all come from the preset table in
  `viewer/src/sky.js`. Add a time of day by adding a row, not by scattering
  values across modules.
- **The data contract is `docs/02-DATA-SCHEMA.md`.** Additive changes only. If
  you must change the meaning of an existing field, write an ADR first
  (`docs/04-DECISIONS.md`) and bump `schema` to `chronopolis.city/2`.
- **Determinism.** Two runs of `citygen` on the same commit must produce
  byte-identical JSON (except `generated_at` and `build_seconds`). Sort
  everything. Never iterate an unsorted set into output.
- **Performance bar is a test, not a hope.** 1000+ file repo must hold ≥30 fps
  in the viewer. `docs/05-PERFORMANCE.md` has the measurement procedure.
- **Never commit `out/*.json`** except the two small demo cities named in T16.

## When you are blocked or the spec is wrong

Do not stall and do not silently improvise a different design.

1. Pick the option the task file lists under **Default if ambiguous** — every
   task has one, precisely so an autonomous agent never needs to ask.
2. If no default covers it, choose the simplest option that satisfies the
   acceptance criteria, and record it in `docs/04-DECISIONS.md` as a new ADR
   with the reasoning. Then continue.
3. Log anything a human should review in `docs/OPEN-QUESTIONS.md`. Keep
   building — do not wait for an answer.

## Working style

- Small commits, one per task, message: `T07: import arcs rendered`.
- Every phase must be independently runnable. Never leave the repo in a state
  where `python -m citygen build` or `npm run dev` is broken.
- Prefer deleting code over adding flags.
- If a task's acceptance criteria cannot be met honestly, mark the row
  `PARTIAL` in `STATUS.md` with a note saying exactly what is missing. Never
  mark `DONE` on unverified work.

## Verify commands you will use constantly

```bash
python citygen/tests/test_phase1.py
```

```bash
python -m citygen build ../reachable -o out/reachable.city.json && python -m citygen inspect out/reachable.city.json
```

```bash
cd viewer && npm run dev
```

## Test repositories on this machine

| Repo | Path | Size | Use for |
|---|---|---|---|
| toyrepo | `fixtures/toyrepo` | 5 files | unit tests, exact assertions |
| reachable | `../reachable` | 39 files, git | correctness sanity, git history features |
| cve-bin-tool | `../cve-bin-tool` | 1071 py files | the 1000+ file performance bar |

If `../reachable` or `../cve-bin-tool` are missing, clone any mid-size Python
project instead and note the substitution in `STATUS.md`.
