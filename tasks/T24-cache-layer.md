# T24 — Content-addressed cache layer

**Blocked by:** T23 · **Effort:** medium · **Phase:** B
**Fills:** nothing in `city.json`. Adds `.citygen/cache/`.

> **Read T23's conclusion first.** If T23 measured that parsing is not the
> dominant cost, the cache target below changes and this task must be rewritten
> before it is started. Do not build this on the assumption that parsing is slow;
> build it on T23's measurement.

## Why this exists
This is the storage half of incrementality. T25 is the invalidation half. They
are split because the storage layer is testable on its own and the invalidation
logic is where the correctness bugs live — mixing them makes both harder to
verify.

## Files
- new: `citygen/cache.py`
- edit: `citygen/build.py` (read-through the cache in the per-file loop)
- edit: `citygen/cli.py` (`--cache-dir`, `--no-cache`, and a `cache` subcommand)
- new: `citygen/tests/test_cache.py`
- edit: `.gitignore` (add `.citygen/`)

## Cache layout
```
.citygen/
  cache/
    v1/
      manifest.json          # path -> {hash, size, mtime_ns, lang}
      objects/
        ab/
          abcdef...json      # one per content hash: the parse result
      git/
        <head_sha>.json      # mined history, keyed by the HEAD it was mined at
```

**Versioned directory (`v1`) is mandatory.** When the metrics formula changes,
every cached result is wrong. The version bumps, the old tree is ignored, and
nothing silently serves stale analysis. This is the single most important
structural decision in this task — a cache that cannot be invalidated wholesale
is worse than no cache.

## Cache key
```python
key = sha256(
    CACHE_FORMAT_VERSION.encode()   # bump when the record shape changes
    + b"\0" + PARSER_VERSION.encode()  # bump when ANY metrics function changes
    + b"\0" + lang.encode()
    + b"\0" + file_bytes
).hexdigest()
```

The key is over **file content**, not path — two identical files share a cache
entry, and a file that moves is a cache hit. `mtime` and `size` live in the
manifest as a *fast pre-check only* (skip hashing when both match a known entry),
never as the key itself; mtime is not a correctness signal and a build that
trusts it will serve wrong results after a checkout.

`PARSER_VERSION` is a constant in `citygen/metrics.py`. **Every change to any
metrics function must bump it.** Add this to the acceptance tests, because it is
the rule that will be forgotten: a test that hashes the source of the metrics
module and fails when it changes without a version bump.

## API to implement in `citygen/cache.py`

```python
CACHE_FORMAT_VERSION = "1"

class Cache:
    def __init__(self, root: str, cache_dir: str | None = None,
                 enabled: bool = True): ...

    def get(self, key: str) -> dict | None:
        """Cached parse record, or None. Never raises on a corrupt file —
        a truncated or unparseable object is a MISS and is deleted."""

    def put(self, key: str, record: dict) -> None:
        """Atomic: write to <name>.tmp then os.replace(). A partially written
        object read by a concurrent process must be impossible."""

    def key_for(self, rel: str, lang: str | None, raw: bytes) -> str: ...

    def stats(self) -> dict:
        """{"hits": n, "misses": n, "writes": n, "bytes": n}"""

    def prune(self, keep_keys: set[str]) -> int:
        """Delete objects not in keep_keys. Returns count removed."""

    def load_manifest(self) -> dict: ...
    def save_manifest(self, m: dict) -> None: ...   # atomic, same as put()
```

## The cached record
Everything the per-file loop derives from file contents, and nothing else:

```json
{
  "v": 1,
  "lang": "python",
  "loc": 159, "sloc": 120, "todo": 0,
  "functions": 6, "classes": 2, "complexity": 34,
  "max_fn_complexity": 9, "doc_ratio": 0.21,
  "parsed": true, "parse_error": null,
  "imports": [["os", 0, []], ["citygen.walk", 1, ["read_text"]]]
}
```

**`imports` is stored raw and unresolved.** Resolution depends on the set of
other files in the repo, which changes between builds — caching a resolved edge
would produce wrong edges the moment a file is added or removed. This is the
subtlest correctness trap in the task; it belongs in a comment in the code, not
only here.

Do **not** cache: anything git-derived (churn, authors, health), anything
layout-derived, anything index-based (ADR-007 indices shift when files are
added). The cache holds per-file, content-derived facts only.

## Git history cache
Keyed by HEAD sha, stored whole. On a build where HEAD is unchanged and the
working tree has no new commits, `read_history` is skipped entirely. This is
likely a large win — T23's numbers decide how large. Invalidate on:
- different HEAD sha
- different `--max-commits` / `--since` / `--max-commit-files` (put them in the
  key, or the flags silently do nothing on the second run — a real and very
  confusing bug)

## `cache` subcommand
```
python -m citygen cache stats [--cache-dir DIR]     # entries, size on disk, hit rate of last build
python -m citygen cache clear [--cache-dir DIR]     # rm -rf the versioned dir, with a printed confirmation
python -m citygen cache prune [--cache-dir DIR]     # drop objects not referenced by the manifest
```

## Acceptance criteria
1. **Byte-identical output.** `build` with an empty cache and `build` with a warm
   cache produce `city.json` files that are identical after removing
   `generated_at` and `build_seconds`. Assert this in a test with a real diff,
   not a spot check of a few fields. This is the acceptance criterion that
   matters; everything else is performance.
2. A corrupt object file (truncate one to 3 bytes) causes a miss and a rebuild,
   not a crash. Test it by actually truncating a file.
3. A concurrent second build against the same cache does not produce a corrupt
   object. Test with two subprocesses building simultaneously.
4. Changing `PARSER_VERSION` invalidates everything.
5. `test_parser_version_bumped_when_metrics_change` fails if `metrics.py`'s
   content hash changes without `PARSER_VERSION` changing.
6. `--no-cache` bypasses entirely, and its output matches the cached path byte
   for byte.
7. Cache size on a 1272-file repo is reported and is under 10 MB. If it is
   larger, the record is storing something it should not.
8. Speedup on a no-change rebuild is reported against T23's warm baseline, on
   the same machine, in the commit message. **No target is asserted here** —
   T23's measurement sets what is achievable, and inventing a number now would
   violate §3.5 of the Phase 2 plan.

## Verify
```bash
python -m citygen cache clear && python -m citygen build . -o out/a.json
```
```bash
python -m citygen build . -o out/b.json && python -m citygen cache stats
```
```bash
python citygen/tests/test_cache.py
```

## Default if ambiguous
- Cache lives in `.citygen/` at the **analysed repo's** root by default, not in
  citygen's own directory and not in a user home directory. It is derived data
  about that repo and belongs with it. `--cache-dir` overrides.
- Add `.citygen/` to the analysed repo's `.gitignore`? **No — never write to a
  user's `.gitignore`.** Print a one-line suggestion on first cache creation
  instead.
- No cache size limit or LRU eviction in this task. `prune` is manual. Automatic
  eviction is a second system and needs its own measurement to justify.
