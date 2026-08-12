# 02 — Data schema: `city.json` (`chronopolis.city/1`)

This is **the contract**. Additive changes only. Changing the meaning of an
existing field requires an ADR and a schema bump.

Keys marked ✅ are emitted today by T01. Keys marked ⏳ are emitted as
`null`/`[]` today and filled by the task noted.

```jsonc
{
  "schema": "chronopolis.city/1",          // ✅
  "citygen_version": "0.1.0",              // ✅
  "generated_at": "2026-08-13T00:00:00+00:00", // ✅ excluded from determinism
  "build_seconds": 0.14,                   // ✅ excluded from determinism

  "repo": {                                 // ✅
    "name": "reachable",
    "path": "D:/study/claude projects/reachable",
    "has_git": true,
    "head": "58f1852e...",
    "branch": "main"
  },

  "config": { "include_vendor": false, "exclude": [], "include": [],
              "all_languages": true },      // ✅

  "stats": {                                // ✅
    "files": 39, "dirs": 11, "loc": 5286, "sloc": 4300,
    "functions": 222, "classes": 13, "complexity": 920,
    "python_files": 20, "import_edges": 37, "parse_errors": 0,
    "langs": { "python": 20, "docs": 12 }
  },

  "tree": [                                 // ✅ districts, sorted by path
    { "id": "reachable", "path": "reachable", "name": "reachable",
      "parent": "", "depth": 1,
      "files": 9, "loc": 2600, "complexity": 700 }
  ],

  "buildings": [                            // ✅ sorted by path; INDEX IS THE ID
    {
      "id": "reachable/callgraph.py",       // == path; stable across snapshots
      "path": "reachable/callgraph.py",
      "name": "callgraph.py",
      "dir": "reachable",
      "ext": ".py",
      "lang": "python",
      "bytes": 14210,
      "loc": 386,
      "sloc": 320,
      "todo": 2,
      "functions": 14,
      "classes": 1,
      "complexity": 125,                    // 1 + module decisions + Σ function complexity
      "max_fn_complexity": 19,
      "doc_ratio": 0.12,
      "ext_imports": 6,                     // imports that left the repo
      "in_deg": 1,                          // in-repo importers
      "out_deg": 3,
      "parsed": true                        // null for non-Python files

      // ⏳ T02 adds:
      // "commits": 41, "churn": 1820, "adds": 1200, "dels": 620,
      // "first_ts": 1690000000, "last_ts": 1750000000,
      // "authors": [[0, 33], [3, 8]],       // [authorIndex, commitCount], desc
      // "bus_factor": 1, "owner": 0, "owner_share": 0.80,
      // "age_days": 420, "stale_days": 12

      // ⏳ T04 adds nothing here - layout lives in `layout`
      // ⏳ T12 adds: "health": 0.72, "heat": 0.9   (precomputed 0..1 scores)
    }
  ],

  "edges": {                                // ✅ container exists
    "import":   [[12, 4, 2]],               // ✅ [fromIdx, toIdx, weight]
    "call":     [],                         // ⏳ optional, T03 stretch
    "cochange": []                          // ⏳ T03 [aIdx, bIdx, count, strength]
  },

  "git": null,                              // ⏳ T02, see below
  "layout": null,                           // ⏳ T04, see below
  "snapshots": null,                        // ⏳ T11, see below
  "stories": [],                            // ⏳ T14
  "diagnostics": { "parse_errors": [ {"path": "...", "error": "..."} ] } // ✅
}
```

## ⏳ `git` (T02)

```jsonc
"git": {
  "authors": [ { "name": "Ada", "email": "ada@x.dev", "commits": 210 } ],
  "first_commit_ts": 1650000000,
  "last_commit_ts":  1755000000,
  "commit_count": 812,
  "window_days": 1215,
  "truncated": false        // true if --max-commits capped the history
}
```
Author identity: lowercased email is the key; name is the most frequent
spelling. `authors` sorted by commits desc, so index 0 is the top committer.
Buildings reference authors **by index into this array**.

## ⏳ `layout` (T04)

```jsonc
"layout": {
  "world": { "width": 400, "depth": 400 },
  "districts": [
    { "path": "reachable", "x": 12.0, "z": 40.0, "w": 90.0, "d": 60.0,
      "depth": 1, "color": 3 }
  ],
  "plots": [                 // parallel array to `buildings`, same length/order
    { "x": 18.4, "z": 44.2, "w": 6.0, "d": 6.0, "h": 22.5 }
  ],
  "roads": [                 // T03/T04 - centreline polylines for traffic
    { "a": 12, "b": 4, "pts": [[18,44],[30,44],[30,70]], "kind": "import" }
  ]
}
```
`plots[i]` corresponds to `buildings[i]`. `h` is the *final-state* height; the
timeline overrides it per snapshot.

## ⏳ `snapshots` (T11)

```jsonc
"snapshots": {
  "ts": [1650000000, 1655000000, "..."],   // N timestamps, ascending
  "labels": ["2022-04", "2022-06", "..."],
  "commits": ["a1b2c3d", "..."],           // the commit each snapshot samples
  "delta": [                                // one entry per snapshot
    { "born": [4, 9], "died": [], "h": [[4, 3.2], [9, 11.0]] }
  ]
}
```
`h` entries are `[buildingIndex, height]` and appear **only when the value
changed** from the previous snapshot. A building is invisible before its first
`born` and rendered as a ruin after `died`.

Size guard: for a 2000-file repo with 24 snapshots this stays under ~2 MB
uncompressed and ~200 KB gzipped. If it exceeds 8 MB, reduce snapshot count
(`--snapshots`) before inventing a new encoding.

## ⏳ `stories` (T14)

```jsonc
"stories": [
  { "kind": "god_file", "building": 12, "score": 0.94,
    "title": "God building",
    "text": "reachable/models.py is imported by 10 files and changed in 41 commits.",
    "camera": { "target": [18,10,44], "distance": 60 } }
]
```
`text` is produced from fixed templates with numbers substituted. **No AI.**
Kinds: `god_file`, `hotspot`, `ruin`, `bus_factor`, `hidden_coupling`,
`fastest_growing`, `biggest_district`.

## Invariants any consumer may rely on

1. `buildings` is sorted by `path`, and its **index is the stable identifier**
   used by every edge, plot, snapshot delta and story.
2. `tree` is sorted by `path`; `parent` is `""` for top level.
3. All edge indices are valid, `from != to`, and each unordered pair appears
   once in `cochange`, once per direction at most in `import`.
4. No `NaN`, no `Infinity`, no `undefined`. Floats rounded to 3 decimals.
5. Re-running on the same commit changes only `generated_at`/`build_seconds`.
