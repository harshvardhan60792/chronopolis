# T27 — Tree-sitter as an optional parsing backend

**Blocked by:** T25 · **Effort:** large · **Phase:** C
**Fills:** better `functions`/`classes`/`complexity`/`imports` for many languages.

## Why this exists
The regex tiers are the project's most-criticised honest weakness, and the
README already documents why: `// if (x)` inside a comment counts as a decision
point, and eight languages get no function count at all because no regex can
tell a method from an `if` block without guessing. Tree-sitter gives real syntax
trees for all of them.

## The constraint that shapes everything: ADR-006
`citygen` has **zero dependencies**, and "clone and run" is a real part of why
anyone tries it. Tree-sitter is a dependency. The resolution is not to break
ADR-006 but to bound it.

### ADR-014 — write this first, before any code
Add to `docs/04-DECISIONS.md`:

```
## ADR-014 — Tree-sitter is an optional accuracy upgrade, never a requirement
Status: accepted, amends ADR-006 (does not supersede it)
Context: regex heuristics cap analysis quality for every non-Python language,
and 8 languages get no function count at all. Real parsers fix this. ADR-006
forbids dependencies.
Decision: `citygen` core stays stdlib-only and fully functional with zero
dependencies. Tree-sitter enters as an extra (`pip install citygen[parsers]`).
When the extra is present, a tree-sitter backend supplies metrics; when absent,
the existing regex/ast path runs unchanged. CI tests BOTH paths on every commit.
Why: keeps the frictionless install that makes people try it, without capping
accuracy forever for people who want more.
Cost: two parsing paths to keep in agreement, a differential test suite to prove
they agree (T28), and a permanent rule that the zero-dep path is the default.
```

The rule that follows from this and must not be bent: **if the optional path
ever makes the default path slower, less accurate, or harder to install, the
migration is reverted.** The fallback is the product for most users.

## Files
- new: `citygen/parsers/__init__.py` (backend selection)
- new: `citygen/parsers/treesitter.py`
- new: `citygen/parsers/queries/*.scm` (one query file per language)
- edit: `citygen/metrics.py` (dispatch through the backend selector)
- edit: `citygen/build.py` (no logic change — it calls the selector)
- edit: `pyproject.toml` (the `[parsers]` extra)
- edit: `.github/workflows/ci.yml` (a second job with the extra installed)
- new: `citygen/tests/test_parsers.py`

## Backend selection
```python
# citygen/parsers/__init__.py
def available() -> bool:
    """True if tree-sitter and the grammar bundle import cleanly."""

def backend_name() -> str:      # "tree-sitter" | "builtin"
def metrics_for(lang: str, text: str) -> Result | None:
    """None => caller falls back to the builtin regex/ast path."""
```

Selection rules, in order:
1. `CITYGEN_PARSER=builtin` env var forces the stdlib path. **This must exist**
   — it is how the differential test (T28) runs both paths in one CI job, and how
   a user works around a bad grammar.
2. Tree-sitter unavailable, or the grammar for this language is missing ⇒
   builtin.
3. Python always uses `ast`, even when tree-sitter is available. It is stdlib,
   exact, and already correct; swapping it would add risk for zero gain. Python
   instead becomes the **reference implementation** the tree-sitter path is
   validated against in T28.

Print the active backend in `build -v` output and record it in
`city["config"]["parser_backend"]`, so any `city.json` says how it was produced.
A document that does not record which parser made it is unreproducible.

## What to extract per language
Use tree-sitter queries (`.scm` files, one per language, versioned in the repo —
not query strings built in Python, which are unreadable and untestable):

| Metric | How |
|---|---|
| `functions` | count nodes matching the language's function/method declaration query |
| `classes` | class/struct/interface/module declarations |
| `complexity` | `1 + count(decision nodes)` — must match ADR-004's definition, node types instead of keywords |
| `max_fn_complexity` | per-function subtree walk |
| `imports` | language-specific import/require/include nodes, **raw and unresolved** (T24's cache stores these; resolution stays where it is) |

**ADR-004 still governs the complexity formula.** Tree-sitter changes how
decision points are *found*, never what counts as one. If the node-based count
disagrees with the documented formula, the formula wins or ADR-004 gets an
explicit successor — the number must stay comparable to every number already
published.

## Language priority
Ship in this order; each is independently useful and independently testable:
1. **Java, C#, C/C++** — currently complexity-only, no function count. Biggest gain.
2. **Go, Rust** — Go gains real imports (currently none: needs `go.mod`, which
   tree-sitter does not solve on its own — scope it as "resolve within-module
   paths only" and say so).
3. **JS/TS** — replaces the most-used regex path; validate hardest here.
4. **Ruby, PHP, Kotlin, Swift** — round out the set.

Do not attempt all of them in one commit. One language per commit, each with its
query file, its fixtures, and its differential results.

## Acceptance criteria
1. `pip install -e .` with **no extras** still works, all existing tests pass,
   and `citygen build` produces byte-identical output to before this task.
   Assert with a stored `city.json` from before the change.
2. With extras installed, `build -v` reports `parser backend: tree-sitter`.
3. `CITYGEN_PARSER=builtin` with extras installed reproduces the zero-dep output
   byte for byte.
4. CI runs both paths. Add a second job; do not replace the existing one.
5. On a Java repo (`google/gson`), `functions` goes from absent to a count that
   matches hand-inspection on 20 sampled files. Record the 20 files and the
   hand-counts in the test fixture — "matches inspection" with no record is not
   verifiable by anyone else.
6. Per-file parse time with tree-sitter is within 3× of the regex path. If it is
   slower than that, the queries are being recompiled per file — compile once
   and cache per language.
7. A malformed source file produces a partial tree, not an exception.
   Tree-sitter is error-tolerant by design; make sure the wrapper does not
   convert that into a crash.

## Verify
```bash
pip install -e . && python citygen/tests/test_parsers.py
```
```bash
pip install -e ".[parsers]" && python -m citygen build .testrepos/gson -o out/gson.json -v
```
```bash
CITYGEN_PARSER=builtin python -m citygen build . -o out/builtin.json && python -m citygen build . -o out/ts.json
```

## Default if ambiguous
- Grammar distribution: prefer a single maintained bundle package over pinning a
  dozen individual grammar packages. Record which, and its version, in the ADR.
- If a language's grammar is unavailable or unmaintained, that language stays on
  the regex tier. Partial coverage is fine and expected; silently degrading to a
  wrong answer is not.
- Do not remove any regex function in this task. They remain the fallback, and
  T28 needs them to compare against.
