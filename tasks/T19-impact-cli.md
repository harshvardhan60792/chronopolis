# T19 — `citygen impact <file>`: blast radius in the terminal

**Blocked by:** — (all data already exists) · **Effort:** small · **Phase:** A
**Fills:** nothing in `city.json` — this is a *read* command over existing data.

## Why this exists
`edges.import` has been computed since T01 and is only ever visible as glowing
arcs in a 3D viewer nobody has open. The question it answers — *"what breaks if
I change this file?"* — is one developers ask before every risky edit, and today
they answer it by grepping. This task turns existing data into the single
highest-value-per-hour output in the whole project.

## Files
- new: `citygen/impact.py`
- edit: `citygen/cli.py` (add the `impact` subcommand)
- new: `citygen/tests/test_impact.py`
- edit: `README.md` (CLI Reference section)

## Data contract (already true — do not change it)
`city["edges"]["import"]` is a list of `[importer_idx, imported_idx, weight]`.
Read `docs/02-DATA-SCHEMA.md` before writing code. Direction matters and is the
single easiest thing to get backwards in this task:

```
edge [a, b, w]   means   buildings[a]  imports  buildings[b]
                          (the dependent)        (the dependency)
```

So the *dependents* of a file are the `a`s of every edge whose `b` is that file.
That is the **reverse** of the stored direction. Getting this backwards produces
a plausible-looking answer that is exactly wrong, and no test that only checks
"returns a non-empty list" will catch it — which is why the acceptance test
below names specific files.

## API to implement in `citygen/impact.py`

```python
def build_reverse_index(import_edges: list[list], n: int) -> list[list[int]]:
    """rev[i] = sorted list of building indices that import building i."""

def build_forward_index(import_edges: list[list], n: int) -> list[list[int]]:
    """fwd[i] = sorted list of building indices that building i imports."""

def blast_radius(rev: list[list[int]], start: int,
                 max_depth: int | None = None) -> dict:
    """Breadth-first over reverse edges from `start`.

    Returns {
        "depths": {1: [idx, ...], 2: [idx, ...], ...},  # first-reached depth only
        "all": [idx, ...],          # every reachable dependent, sorted, excl. start
        "direct": [idx, ...],       # == depths.get(1, [])
        "truncated": bool,          # True if max_depth cut the search short
    }
    """

def resolve_target(city: dict, query: str) -> int:
    """Map a user-typed path to a building index.

    Match order, first non-ambiguous wins:
      1. exact match on b["path"]
      2. exact match after normalising backslashes to "/" and stripping "./"
      3. unique suffix match  (query "walk.py" -> "citygen/walk.py")
      4. unique basename match
    Raise LookupError with a helpful message listing up to 8 candidates when
    the match is ambiguous, and a different message when there are none.
    """
```

**Cycle safety:** import graphs contain cycles. BFS must carry a `visited` set
and a node's recorded depth is its *first* (shortest) reach. A recursive
implementation will blow the stack on a large repo — use an explicit
`collections.deque`, matching the reason T04's squarify was rewritten iteratively.

## CLI wiring — exact
In `citygen/cli.py`, add after `_cmd_inspect`:

```python
def _cmd_impact(a: argparse.Namespace) -> int:
```

and register in `main()` next to the other subparsers:

```python
    im = sub.add_parser("impact", help="what breaks if I change this file?")
    im.add_argument("file", help="path to a file in the analysed repo")
    im.add_argument("--city", default="out/city.json",
                    help="path to city.json (default: out/city.json)")
    im.add_argument("--depth", type=int, default=None,
                    help="stop after N levels of dependents")
    im.add_argument("--json", action="store_true", help="machine-readable output")
    im.add_argument("--tree", action="store_true",
                    help="print the dependency tree, not just counts")
    im.set_defaults(func=_cmd_impact)
```

Reuse the existing `_load(path)` helper for reading `city.json` (it already
handles `.gz`). Reuse `_use_color()` / `_style()` for colour — do not add a new
styling mechanism, and do not add `rich` (ADR-006).

## Output format (default, no flags)

```
citygen/walk.py

  Direct dependents        1
  Transitive dependents    3
  Depth                    3 levels

  Risk signals
    bus factor             1  (harsh, 100% of 12 commits)
    last touched           2 days ago
    complexity             34

  Depth 1  (1 file)
    citygen/build.py
  Depth 2  (1 file)
    citygen/cli.py
  Depth 3  (1 file)
    citygen/__main__.py
```

Rules for this output:
- Cap each depth listing at 15 paths, then `... and N more` — a hub file in a
  large repo has hundreds of dependents and a wall of text is not an answer.
  `--tree` prints all of them.
- The "Risk signals" block is printed **only** when the fields exist
  (`b.get("bus_factor")`, `b.get("stale_days")`). A `--no-git` city has none of
  them; print the block header with `(no git history in this city)` rather than
  silently omitting it, so the user knows why.
- With zero dependents, say so plainly and usefully:
  `No file in this repo imports citygen/cli.py.` followed by, when
  `b["lang"]` is one of the languages without import resolution (see the README
  Limitations table), the honest caveat:
  `Note: import arcs are not resolved for <lang> — this is "no data", not "no dependents".`
  **This caveat is required.** Reporting "0 dependents" for a Go file when the
  analyser never resolves Go imports is the single most misleading thing this
  command could do.

## `--json` output
```json
{
  "file": "citygen/walk.py",
  "index": 12,
  "direct": ["citygen/build.py"],
  "transitive": ["citygen/build.py", "citygen/cli.py", "citygen/__main__.py"],
  "depths": {"1": ["citygen/build.py"], "2": ["citygen/cli.py"], "3": ["citygen/__main__.py"]},
  "counts": {"direct": 1, "transitive": 3, "max_depth": 3},
  "signals": {"bus_factor": 1, "owner_share": 1.0, "stale_days": 2, "complexity": 34, "loc": 159},
  "import_resolution": "full",
  "truncated": false
}
```
`import_resolution` is `"full"` for python/javascript/typescript/ruby,
`"none"` for every other language. The PR bot (T21) reads this field to decide
whether to report a blast radius at all.

## Error paths — all of them must be handled
| Condition | Behaviour |
|---|---|
| `--city` file missing | exit 2, message: `no city at out/city.json — run: python -m citygen build . -o out/city.json` |
| file not found in city | exit 2, message with up to 8 nearest basename matches |
| ambiguous suffix match | exit 2, list the candidates, do not guess |
| file exists on disk but was excluded from the build (vendored, too large, binary) | exit 2, and say which: `citygen skipped this file during build (vendored/oversized/binary)` |

## Acceptance criteria
Run against **this repo**, whose dependency chain is known and short:

1. `impact citygen/walk.py` reports `citygen/build.py` at depth 1, and
   `citygen/cli.py` at depth 2. If it reports zero dependents, the edge
   direction is reversed — fix that before anything else.
2. `impact citygen/cli.py` reports `citygen/__main__.py` as a dependent and does
   **not** report `citygen/walk.py` (that is a dependency, not a dependent).
3. `impact citygen/__main__.py` reports zero dependents and does not crash.
4. Deterministic: two runs produce byte-identical output.
5. Completes in under 1 second on a `city.json` with ≥1000 buildings.
6. A cyclic import graph terminates. Test this with a hand-built fixture in
   `test_impact.py` — do not rely on a real repo happening to have a cycle.

## Verify
```bash
python -m citygen build . -o out/city.json
```
```bash
python -m citygen impact citygen/walk.py --city out/city.json
```
```bash
python citygen/tests/test_impact.py
```

## Tests to write in `citygen/tests/test_impact.py`
Follow the existing style in `citygen/tests/test_coupling.py` — bare `test_*`
functions with `assert`, run directly as a script, **not** `unittest.TestCase`
(see T18: `unittest discover` is blind to this project's tests, and CI runs each
file directly).

- `test_reverse_index_direction` — a two-node fixture, assert `rev[1] == [0]` for
  edge `[0, 1, 1]`.
- `test_blast_radius_depths` — a 4-node chain, assert depth assignment.
- `test_blast_radius_cycle_terminates` — edges `[[0,1,1],[1,0,1]]`, assert it
  returns rather than hanging.
- `test_blast_radius_diamond_first_reach_wins` — a node reachable at depth 2 and
  depth 3 is reported at 2 only.
- `test_resolve_target_suffix_and_ambiguity` — assert `LookupError` on ambiguous.
- `test_max_depth_truncation_flag` — `truncated` is `True` only when cut short.

## Default if ambiguous
- Weight (`w`) is **ignored** in this command. Blast radius is a reachability
  question, not a strength question.
- External imports (`ext_imports`) are not dependents and are never counted.
- Depth is unlimited by default. A hub file legitimately reaches most of a repo,
  and truncating by default would hide exactly the finding that matters.
