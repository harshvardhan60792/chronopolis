# T29 — Fill `edges.call`, the slot the schema has reserved since T01

**Blocked by:** T27 · **Effort:** medium · **Phase:** C
**Fills:** `edges.call` in `city.json` (currently hardcoded `[]` at `build.py:406`).

## Why this exists
`docs/02-DATA-SCHEMA.md` has always reserved `edges.call`, and `build.py` has
always emitted `"call": []`. Import edges say *file A references file B*; call
edges say *which function in A calls which in B*, which is what makes blast
radius (T19) precise instead of file-granular.

The payoff is concrete: today `impact` says "17 files depend on this file".
With call edges it can say "17 files depend on it, but only 3 call the function
you actually changed" — a much more useful answer, and the thing that separates
this from `grep -r`.

## Prerequisite reality check
This needs real ASTs. It is blocked on T27 for every language, **including
Python**: `citygen`'s current `ast` path already collects `_callee_name`
(`metrics.py:154`) but resolving a callee name to a *definition in another file*
needs symbol tables that do not exist yet. Do not start this before T27 lands.

## Scope — deliberately narrow
Full inter-procedural call graph resolution is a research problem (dynamic
dispatch, duck typing, higher-order functions, reflection). **This task does not
attempt it.** It resolves the tractable subset and reports the rest as unknown:

| Resolved | Not attempted |
|---|---|
| direct calls to a name imported from a known file | dynamic dispatch on a runtime type |
| direct calls to a module-level function in the same file | calls through a variable holding a function |
| method calls where the receiver's class is unambiguous in the same file | anything reflective (`getattr`, reflection APIs) |
| | duck-typed method calls across files |

Emit a coverage number — `stats.call_resolution_rate` — the fraction of call
sites that resolved. Publishing "we resolved 34% of call sites" is honest and
useful. Silently emitting only the 34% and letting a reader assume it is
complete is the failure mode, and it is why the stat is mandatory rather than
optional.

## Data shape
```json
"call": [[from_building_idx, to_building_idx, count]]
```
Same index-based convention as `edges.import` (ADR-007), same sorted order. Do
**not** introduce function-level nodes into `city.json` in this task — that is a
schema change with layout and viewer consequences. Aggregate to file level for
the edge list, and keep the function-level detail in a side structure only if
T19 needs it:

```json
"call_detail": {"12": {"resolve_symbol": [[47, 3]]}}   // optional, gated behind a flag
```

Gate `call_detail` behind `--call-detail` since it can be large. Measure its
size at the medium tier before enabling it anywhere by default.

## Viewer
Render call edges as a **second, distinct arc layer**, toggled by `C` (import
arcs stay on `I`). Different colour, thinner, and **off by default** — two arc
layers on at once is visual soup, which ADR-012's comprehension-first rule
forbids. Update the legend to name which layer is on.

No new animation. No pulsing on call arcs. ADR-012 stands.

## Acceptance criteria
1. On this repo, `citygen/cli.py` shows call edges into `citygen/build.py`
   (it calls `build_city`) — a fact verifiable by reading the file.
2. `stats.call_resolution_rate` is present, between 0 and 1, and its definition
   is documented in `docs/02-DATA-SCHEMA.md`.
3. Zero call edges to or from a file whose language has no tree-sitter backend —
   and `call_resolution_rate` reflects that rather than reporting 100% of a
   subset.
4. `city.json` size growth at the medium tier is under 15%. If larger, tighten
   the aggregation or gate the layer.
5. Existing import-arc rendering is untouched. Assert with a before/after
   screenshot diff or by checking arc counts are unchanged.
6. A repo built without the tree-sitter extra still emits `"call": []` and does
   not crash. The zero-dependency path stays whole (ADR-014).

## Verify
```bash
pip install -e ".[parsers]" && python -m citygen build . -o out/city.json && python -m citygen inspect out/city.json
```

## Default if ambiguous
- When a call cannot be resolved, count it toward the denominator of
  `call_resolution_rate` and emit nothing. Never guess a target.
- Recursion and self-calls are excluded from the edge list (they are within one
  building), consistent with how import self-edges are already skipped in
  `build.py`.
