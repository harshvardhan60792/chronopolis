# T25 — Incremental rebuild: Git history

**Blocked by:** T24 · **Effort:** large · **Phase:** B
**Fills:** nothing new in `city.json`. Adds `--incremental` and must not change a single byte of the output.

> **T23 measurement applied:** The parse cache was scrapped because parsing takes <5% of build time on the large tier. Incremental rebuilds now mean incremental git history mining.

## The one invariant
> **An incremental build must produce output byte-identical to a cold build of the same working tree.**

Not "close". Identical, after excluding `generated_at` and `build_seconds`. 

## Files
- new: `citygen/incremental.py`
- edit: `citygen/build.py`
- edit: `citygen/cli.py` (`--incremental`, `--force-full`)
- new: `citygen/tests/test_incremental.py`
- edit: `docs/05-PERFORMANCE.md`, `docs/04-DECISIONS.md` (ADR for incremental git)

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

Detecting the rebase case is mandatory. A rebased or amended branch makes the cached history describe commits that no longer exist, and appending to it yields a history that never happened. `git merge-base --is-ancestor <cached> HEAD` is the check; treat any non-zero exit as "fall back to full".

## CLI
```
python -m citygen build . -o out/city.json --incremental
python -m citygen build . -o out/city.json --force-full     # ignore cache, refresh it
```

`--incremental` falls back to a full build **silently and correctly** whenever the cache is missing, version-mismatched, or unusable, printing one line saying which. It must never fail because of a cache problem.

## Acceptance criteria

**Correctness (these gate the task; performance does not):**
1. **Fuzz test.** In a temp git repo, apply random git mutations (commit, amend, checkout older commit). After each, assert `--incremental` and full build outputs are byte-identical.
2. A rebase (`git commit --amend`) falls back to a full history mine and produces correct output.
3. `--max-commits` differing between runs invalidates the git cache.
4. Cache directory deleted mid-run: falls back, no crash.

**Performance:**
5. Report the incremental time for a one-file change against T23's warm baseline. Speedup must be substantial for the large tier. Put the table in `docs/05-PERFORMANCE.md`.

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
Add **ADR-014** (or the next free number) to `docs/04-DECISIONS.md` recording the pivot from parse cache to git history cache based on T23's measurement, and how the byte-identical invariant is maintained.

## Default if ambiguous
- `--incremental` is **opt-in** for now. 
- When in doubt between "reuse it" and "recompute it", recompute. The invariant outranks the speedup, always.
