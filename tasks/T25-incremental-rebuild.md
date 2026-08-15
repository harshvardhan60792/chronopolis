# T25 — Incremental rebuild: the invalidation graph

**Blocked by:** T24 · **Effort:** large · **Phase:** B
**Fills:** nothing new in `city.json`. Adds `--incremental` and must not change
a single byte of the output.

This is the hardest task in Phase 2 and the one with the most engineering
substance in the whole project. It is also the one where a subtle bug produces
*plausible but wrong* output, which is worse than a crash. Read all of it before
writing code.

## Why this exists
Today every build reparses everything. At the medium tier that is tolerable; at
40k+ files it is the reason nobody would run this tool twice. The fix is the
same idea build systems have used for decades: know what changed, know what
depends on what changed, redo only that.

## The one invariant
> **An incremental build must produce output byte-identical to a cold build of
> the same working tree.**

Not "close". Not "equivalent modulo ordering". Identical, after excluding
`generated_at` and `build_seconds`. Every design decision below serves that
invariant, and the acceptance test for it is a differential fuzz test, not a
spot check.

## Files
- new: `citygen/incremental.py`
- edit: `citygen/build.py` (split `build_city` — see below)
- edit: `citygen/cli.py` (`--incremental`, `--force-full`)
- new: `citygen/tests/test_incremental.py`
- edit: `docs/05-PERFORMANCE.md`, `docs/04-DECISIONS.md` (ADR for the split)

## What can and cannot be reused — think this through before coding

| Stage | Reusable? | Why |
|---|---|---|
| `walk` | No | Cheap, and it is how changes are detected in the first place |
| `read` + `parse` | **Yes, per file, by content hash** | The whole point. T24 stores these |
| `resolve` (imports → edges) | **No — always redo** | See the trap below |
| `git_read` | **Yes, incrementally** | `git log <cached_head>..HEAD` appends new commits to the cached history |
| `git_apply`, `health` | No | Cheap, and they read every building anyway |
| `coupling` | No | Depends on the whole commit stream |
| `layout` | No | ADR-003 requires the union of all files; any add/delete changes it |
| `snapshots`, `stories` | No | Derived from the above |

### The resolution trap — read twice
It is tempting to cache resolved import *edges* per file. **Do not.** Import
resolution depends on the set of all files in the repo, not just the importing
file's contents. Adding `foo/bar.py` can make an untouched file's
`import foo.bar` resolve where it previously did not, creating an edge in a file
nobody edited. Caching resolved edges would miss that silently, and the resulting
city would be subtly wrong in a way no test that only edits one file would catch.

Resolution is dict lookups over already-parsed import lists — it is cheap.
**Always re-resolve everything.** Cache the raw parsed import list (T24 already
does), never the resolved target.

Write this reasoning as a comment in `incremental.py`. It is exactly the kind of
thing that gets "optimised" later by someone who did not know.

### The index trap
ADR-007 makes `buildings` array indices load-bearing, and they shift whenever a
file is added or removed. **Never carry an index across builds.** Any cached
structure keyed by index is a bug. Cache by path or by content hash only.

## Required refactor of `build_city`
`build_city` is currently one 320-line function. Incrementality needs the
per-file stage callable on a subset. Split it — mechanically, in its own commit,
with no behaviour change and the existing tests green — into:

```python
def scan_files(root, opts) -> list[FileRec]                  # == walk_repo
def measure_files(files, cache=None) -> tuple[list[dict], list[tuple], ...]
    """The per-file loop: read, parse, build the `b` dicts, collect
    pending_imports*. This is the only stage the cache serves."""
def add_ruins(buildings, timeline, ruins: bool) -> None
def resolve_edges(buildings, by_path, pending*, indices) -> list[list]
def assemble(...) -> dict                                    # everything after
```

`build_city` then becomes a thin orchestration function calling these in order,
and `build_city_incremental` calls the same ones with a warm cache. **Two code
paths that assemble the document differently is how the byte-identical invariant
dies.** There must be exactly one `assemble`.

Commit the refactor separately from the incremental logic. If the refactor
commit changes any output byte, the refactor is wrong and the incremental work
starts on a broken foundation.

## Change detection
```python
def detect_changes(files: list[FileRec], manifest: dict) -> Changes:
    """Returns Changes(added=[rel], modified=[rel], deleted=[rel], unchanged=[rel]).

    Per file: if manifest has the path AND size matches AND mtime_ns matches,
    treat as unchanged WITHOUT hashing (the fast path). Otherwise hash the
    content and compare — a file whose mtime moved but whose content did not is
    still unchanged, which matters after `git checkout` touches everything.
    """
```

Report the counts in verbose mode: `[citygen] 3 modified, 1 added, 0 deleted,
4211 unchanged`. This line is what makes the feature believable to a user, and it
is what you will read constantly while debugging.

## Git history, incrementally
```python
def extend_history(cached: dict, root: str, cached_head: str) -> dict | None:
    """Mine only `<cached_head>..HEAD` and prepend to the cached commit list.

    Returns None (caller falls back to a full mine) when:
      - cached_head is not an ancestor of HEAD (rebase, force-push, amend)
      - `git merge-base --is-ancestor` fails or git errors
      - the cached history was truncated by --max-commits (extending a
        truncated window produces a wrong window)
    """
```

Detecting the rebase case is mandatory. A rebased or amended branch makes the
cached history describe commits that no longer exist, and appending to it yields
a history that never happened. `git merge-base --is-ancestor <cached> HEAD` is
the check; treat any non-zero exit as "fall back to full".

## CLI
```
python -m citygen build . -o out/city.json --incremental
python -m citygen build . -o out/city.json --force-full     # ignore cache, refresh it
```

`--incremental` falls back to a full build **silently and correctly** whenever
the cache is missing, version-mismatched, or unusable, printing one line saying
which. It must never fail because of a cache problem.

## Acceptance criteria

**Correctness (these gate the task; performance does not):**
1. **Differential fuzz test.** In a temp git repo, apply 50 random mutations
   (edit a file, add a file, delete a file, rename a file, add a commit, touch a
   file without changing content, `git checkout` an older commit). After each,
   run a full build and an incremental build and assert the two `city.json`
   documents are identical after stripping `generated_at`/`build_seconds`.
   Seed the RNG and print the seed so a failure is reproducible. This single
   test is worth more than every other test in this task combined.
2. Touching a file's mtime without changing content produces zero reparses.
3. Deleting a file removes its building and shifts every index correctly — assert
   an edge that pointed past the deleted index still points at the same *path*.
4. Adding a file that makes another file's previously-unresolved import resolve
   produces the new edge. **Construct this case explicitly** — it is the
   resolution trap above, and a generic fuzz test may not hit it.
5. A rebase (`git commit --amend`) falls back to a full history mine and produces
   correct output.
6. `--max-commits` differing between runs invalidates the git cache.
7. Cache directory deleted mid-run: falls back, no crash.

**Performance (reported, not asserted at a fixed number):**
8. Report the incremental time for a one-file change against T23's warm cold-build
   baseline, on the same machine and repo, at every tier. Put the table in
   `docs/05-PERFORMANCE.md`.
9. Per the Phase 2 plan §6: if the speedup at the large tier is under 10×, this
   task is `PARTIAL`, not `DONE`, and `STATUS.md` names the stage that now
   dominates. Do not paper over it. "Parsing is now 4% and layout is 71%" is a
   perfectly good result that tells the next task what to do.

## Verify
```bash
python -m citygen build . -o out/city.json --incremental -v
```
```bash
python citygen/tests/test_incremental.py
```
```bash
python scripts/profile_build.py --repos .testrepos/manifest.txt --incremental
```

## Write an ADR
Add **ADR-014** (or the next free number) to `docs/04-DECISIONS.md` recording:
the decision to split `build_city` into stages, that parse results are cached by
content hash while resolution is always redone, and the byte-identical
invariant. Cost: `build_city` is no longer readable top-to-bottom in one
function, and every new stage must decide its cacheability explicitly.

## Default if ambiguous
- `--incremental` is **opt-in** for now. Making it the default is a separate
  decision to take after the fuzz test has run against real repos for a while.
- No file watching, no daemon, no server. `00-VISION.md` ruled those out for v1
  and nothing here needs them.
- When in doubt between "reuse it" and "recompute it", recompute. The invariant
  outranks the speedup, always.
