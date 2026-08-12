# 06 — Testing

Small, fast, honest. No test framework required: the test file runs standalone
(`python citygen/tests/test_phase1.py`) and also under pytest if present.

## Layers

### 1. Unit — exact numbers against `fixtures/toyrepo`
The fixture is tiny and its expected metrics are written as comments in the
fixture source. If you change the fixture, change the assertions in the same
commit. Current coverage (T01): walk determinism, generic metrics, function
complexity, relative + absolute import resolution, orphan detection, schema
keys, vendor exclusion.

Each later task adds its own file: `test_git.py` (T02), `test_coupling.py`
(T03), `test_layout.py` (T04), etc.

### 2. Property / invariant checks on real repos
Add `citygen/tests/test_invariants.py` in T04. It builds a city from
`fixtures/toyrepo` and, if available, `../reachable`, then asserts the
invariants from `docs/02-DATA-SCHEMA.md`:

- `buildings` sorted by path
- every edge index in range, `from != to`
- `layout.plots` same length as `buildings`
- no plot rectangle overlaps another by more than 1e-6 area
- every plot is inside its district rectangle
- no NaN / Infinity anywhere (walk the JSON)
- two consecutive builds differ only in `generated_at` / `build_seconds`

The determinism check is the highest-value test in the project. Write it as:

```python
a = json.dumps(build_city(path), sort_keys=True)
b = json.dumps(build_city(path), sort_keys=True)
# strip volatile keys before comparing
```

### 3. Golden files
`fixtures/golden/toyrepo.city.json` — regenerate deliberately with
`python scripts/regen_golden.py` and review the diff. A surprising golden diff
is a bug report.

### 4. Viewer smoke test (T05 onward)
No browser test framework. Instead:

- `viewer/src/selftest.js` runs when `?selftest=1`: builds the scene from a
  city, asserts instance counts match `buildings.length`, asserts no NaN in any
  instance matrix, measures 120 frames, prints `SELFTEST OK <fps>` to the
  console, and sets `document.title = "OK"`.
- T16 and CI run it headlessly via the browser tools already available in this
  environment, checking the console line.

## What is deliberately not tested

- Visual appearance. Judged by screenshot, by a human.
- Exact fps values in CI (hardware-dependent). CI only checks the selftest runs
  and no exceptions are thrown; fps numbers are recorded manually in
  `docs/05-PERFORMANCE.md`.

## Before marking any task DONE

1. `python citygen/tests/*.py` all pass.
2. `python -m citygen build ../reachable -o out/reachable.city.json` succeeds and
   `inspect` output still looks sane to a human reading the repo.
3. If the task touched the viewer: `npm run build` succeeds and `?selftest=1`
   prints `SELFTEST OK`.
