# T23 — Profile harness: measure before optimising

**Blocked by:** — · **Effort:** small · **Phase:** B
**Fills:** nothing. Produces `docs/05-PERFORMANCE.md` stage tables.

## Why this exists
T24 and T25 are a caching and invalidation system, which is a week of work and
a real source of correctness bugs. Building them to speed up a stage that turns
out to be 8% of runtime would be the single most embarrassing outcome in this
plan. **This task decides what T24/T25 actually build.**

There is already a hint in `docs/05-PERFORMANCE.md`: the `cve-bin-tool` build is
34 s cold, "dominated by `ast.parse` on ~1000 files", but **~1.5 s warm**. That
20× gap between cold and warm is suspicious and important — it suggests much of
the 34 s is filesystem I/O, not parsing. If that is true, a parse cache buys far
less than expected on a warm machine and the real win at scale is elsewhere.
Nobody knows yet. That is the point of this task.

## Files
- new: `scripts/profile_build.py`
- edit: `docs/05-PERFORMANCE.md` (a new "Build stage breakdown" section)
- edit: `.gitignore` (`.testrepos/` is already there; confirm)

## What to measure
Instrument `build_city` **without permanently changing its signature**. Use a
module-level stage timer that is a no-op unless enabled, so production builds
pay nothing:

```python
# citygen/_profile.py  (new, tiny, stdlib only)
import contextlib, os, time
_ENABLED = os.environ.get("CITYGEN_PROFILE") == "1"
_STAGES: dict[str, float] = {}

@contextlib.contextmanager
def stage(name: str):
    if not _ENABLED:
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        _STAGES[name] = _STAGES.get(name, 0.0) + (time.perf_counter() - t0)

def results() -> dict[str, float]:
    return dict(_STAGES)

def reset() -> None:
    _STAGES.clear()
```

Then wrap each stage in `citygen/build.py`. These are the real stage boundaries
in the current code — use exactly these names so the tables stay comparable
across runs:

| Stage name | Covers |
|---|---|
| `walk` | `walk_repo(root, opts)` |
| `read` | `read_text(f.abs)` calls, summed |
| `parse` | `python_metrics` / `js_metrics` / `go_metrics` / `curly_complexity` / `ruby_metrics` / `generic_metrics` |
| `git_read` | `read_history(...)` |
| `git_apply` | `apply_history(...)` + `reconstruct_timeline(...)` |
| `resolve` | the three `pending_imports*` resolution loops |
| `tree` | the directory-tree accumulation loop |
| `coupling` | `calculate_cochange(...)` |
| `health` | `calculate_health(...)` |
| `layout` | `generate_layout(...)` |
| `snapshots` | `compute_snapshots(...)` |
| `stories` | `generate_stories(...)` |
| `serialise` | `json.dumps` + file write (this happens in `cli.py`, time it there) |

`read` and `parse` are separated deliberately — that split is the whole reason
this task exists. They currently sit in the same loop; time them individually
inside it.

## The harness: `scripts/profile_build.py`

```
python scripts/profile_build.py --repos .testrepos/manifest.txt --runs 3 --out docs/perf/stages.md
python scripts/profile_build.py --repos .testrepos/manifest.txt --incremental
```

`--incremental` is accepted now (before T24/T25 exist) as a forward-compatible
flag: if the `citygen build` invocation it shells out to doesn't understand
`--incremental` yet, the harness catches that specific failure, reports
"incremental not yet implemented" per repo instead of crashing, and exits 0.
T25 turns this into a real measurement later without needing to touch this
script's CLI surface again.

Behaviour:
- Reads a manifest of local repo paths, one per line, with an optional label.
- For each repo, runs the build `--runs` times **in a fresh subprocess** with
  `CITYGEN_PROFILE=1`, discards the first run (cold FS cache), reports the
  **median** of the rest, and separately reports the discarded cold run.
  Reporting cold and warm separately is mandatory: the existing 34 s / 1.5 s
  figure is meaningless without that distinction, and repeating that mistake
  would waste this whole task.
- Records, per repo: file count, LOC, commit count, total wall time, and every
  stage's seconds + percentage of total.
- Records the machine: `platform.platform()`, `platform.processor()`, CPU count,
  Python version, and whether the repo lives on an SSD or network drive if
  determinable. A benchmark without a machine is not a benchmark.
- Writes a markdown table. Never overwrite previous results — append a dated
  section, so regressions are visible over time.

## Repos to profile
Fetch into `.testrepos/` (gitignored). Four size tiers so the scaling curve is
visible, not a single point:

| Tier | Repo | Rough scale |
|---|---|---|
| tiny | this repo (`chronopolis`) | ~40 files |
| small | `psf/requests` | ~100 files |
| medium | `pallets/flask` or `cve-bin-tool` | ~1.2k files |
| large | `python/cpython` or `torvalds/linux` (shallow-cloned, see below) | 10k–70k files |

For the large tier, clone with `--filter=blob:none` rather than a full clone, and
note in the results that history depth affects `git_read` timing. If a full
history clone is impractical, record what was used — an honest "measured on a
1000-commit truncation" beats an unlabelled number.

## Acceptance criteria
1. `CITYGEN_PROFILE` unset ⇒ zero measurable overhead. Verify by timing a build
   with and without the instrumentation merged; the difference must be within
   run-to-run noise. If the context manager costs anything measurable in the
   per-file loop, hoist the enabled-check outside the loop.
2. Stage percentages sum to 95–105% of measured wall time. A large gap means a
   stage is unwrapped — find it before publishing anything.
3. The `read` vs `parse` split is reported separately for at least the medium
   and large tiers. **This is the finding the rest of Phase B depends on.**
4. Results are reproducible: two harness runs on the same repo give medians
   within 15% of each other. If not, increase `--runs` and say so.
5. `docs/05-PERFORMANCE.md` gains a dated stage table for every tier, with the
   machine recorded.

## The decision this task must produce
Write the conclusion explicitly at the bottom of the results section, in this
form, before T24 starts:

> **On the large tier, `<stage>` is `<N>`% of build time. T24/T25 therefore
> target `<that stage>`. Stages under 5% are out of scope for Phase B.**

If that conclusion says the dominant cost is `git_read` rather than `parse`,
then T24's design changes from a parse cache to a history cache — and it is far
better to learn that here than after writing the wrong cache.

## Verify
```bash
python scripts/profile_build.py --repos .testrepos/manifest.txt --runs 3
```
```bash
CITYGEN_PROFILE=1 python -m citygen build . -o out/city.json -v
```

## Default if ambiguous
- Median, not mean. One GC pause should not move the headline number.
- Wall time, not CPU time. The user waits on wall time.
- No `cProfile` in the reported numbers — its overhead distorts exactly the
  tight per-file loop being measured. Use it separately for exploration if
  useful, but publish only `perf_counter` numbers.
