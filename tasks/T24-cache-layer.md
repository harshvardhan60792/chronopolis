# T24 — Git history cache layer

**Blocked by:** T23 · **Effort:** medium · **Phase:** B
**Fills:** nothing in `city.json`. Adds `.citygen/cache/`.

> **T23 measurement applied:** T23 proved `git_read` takes 86.6% of build time on the large tier, while parsing takes only ~3.2%. Therefore, the content-addressed parse cache originally planned has been scrapped. This task and T25 now exclusively target the `git_read` bottleneck.

## Why this exists
This is the storage half of incrementality. T25 is the invalidation half. They are split because the storage layer is testable on its own.

## Files
- new: `citygen/cache.py`
- edit: `citygen/build.py` (read-through the cache in the git stage)
- edit: `citygen/cli.py` (`--cache-dir`, `--no-cache`, and a `cache` subcommand)
- new: `citygen/tests/test_cache.py`
- edit: `.gitignore` (add `.citygen/` to the self-repo's ignore, but never edit a target repo's ignore)

## Cache layout
```
.citygen/
  cache/
    v1/
      git/
        <head_sha>.json      # mined history, keyed by the HEAD it was mined at
```

**Versioned directory (`v1`) is mandatory.** If the cache schema changes, the old tree is ignored.

## Git history cache
Keyed by HEAD sha, stored whole. On a build where HEAD is unchanged and the working tree has no new commits, `read_history` is skipped entirely. Invalidate on:
- different HEAD sha
- different `--max-commits` / `--since` / `--max-commit-files` (put them in the key, or the flags silently do nothing on the second run)

## API to implement in `citygen/cache.py`

```python
CACHE_FORMAT_VERSION = "1"

class Cache:
    def __init__(self, root: str, cache_dir: str | None = None, enabled: bool = True): ...

    def get_git(self, key: str) -> dict | None: ...
    def put_git(self, key: str, record: dict) -> None: ...
    def git_key(self, head_sha: str, max_commits: int|None, since: str|None, max_commit_files: int) -> str: ...

    def stats(self) -> dict: ...
    def clear(self) -> None: ...
```

## `cache` subcommand
```
python -m citygen cache stats [--cache-dir DIR]
python -m citygen cache clear [--cache-dir DIR]
```

## Acceptance criteria
1. **Byte-identical output.** `build` with an empty cache and `build` with a warm cache produce `city.json` files that are identical after removing `generated_at` and `build_seconds`. 
2. A corrupt object file (truncate to 3 bytes) causes a miss and a rebuild, not a crash.
3. A concurrent second build against the same cache does not produce a corrupt object.
4. `--no-cache` bypasses entirely, and its output matches the cached path byte for byte.
5. Cache size and speedup are reported against T23's warm baseline in the commit message.

## Default if ambiguous
- Cache lives in `.citygen/` at the **analysed repo's** root by default. `--cache-dir` overrides.
- Never write to a user's `.gitignore`. Print a one-line suggestion on first cache creation instead.
