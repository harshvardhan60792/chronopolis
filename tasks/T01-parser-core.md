# T01 — Parser core  ✅ DONE (2026-08-13)

Kept as the reference example of what a completed task record looks like.

## Goal
Walk a repo, compute per-file metrics, resolve intra-repo Python imports, emit
`city.json` v1.

## What was built
- `citygen/walk.py` — deterministic sorted walk, vendor deny-list
  (`node_modules`, `.venv`, `dist`, `site-packages`, …), binary/minified/lock
  file skipping, 2 MB size cap, `--exclude`/`--include` globs.
- `citygen/metrics.py` — `generic_metrics` (LOC/SLOC/TODO/max line) for any text
  file; `python_metrics` via `ast` (functions with qualnames, classes,
  decision-point complexity per function and per file, imports with levels and
  symbols, call names, docstring lines).
- `citygen/resolve.py` — `ModuleIndex` mapping dotted module names to repo
  paths. Handles flat and `src/` layouts, packages via `__init__.py`, relative
  imports at any level, and `from pkg import submodule` (the symbol slot can
  name a module — this was a real bug, fixed).
- `citygen/build.py` — orchestration, district tree, aggregate stats, edge
  weighting, in/out degree.
- `citygen/cli.py` — `build` (with `--compact`, `--gzip`, `--exclude`,
  `--include-vendor`, `--python-only`) and `inspect`.
- `fixtures/toyrepo` + `citygen/tests/test_phase1.py` (7 tests, all pass).

## Verified output
```
$ python -m citygen build ../reachable -o out/reachable.city.json
[citygen] reachable: 39 files, 5,286 LOC, 222 fns, 37 import edges, 0 parse errors
[citygen] wrote out/reachable.city.json (24.2 KB) in 0.14s
```
Top complexity `reachable/callgraph.py` (125) and `entrypoints.py` (120) match
what a human reading that repo would expect. `models.py` has in-degree 10 — the
hub. The repo's deliberate dead-code fixtures (`dead.py`, `registry.py`) come
out isolated, which is the correctness signal that matters most.

Scale check: `cve-bin-tool`, 1071 Python files, built in 34 s.

## Lessons for later tasks
- Symbol-aware import resolution changed edge count 21 → 37 on a 20-file repo.
  Any import heuristic must be checked against a repo you can read by hand.
- `inspect` was worth writing before any rendering existed. Keep extending it —
  it is the cheapest correctness tool in the project.
