"""Assemble a city document from a repository.

Phase 1 scope (implemented): tree, buildings with metrics, intra-repo import
edges, aggregate stats.
Later phases fill: `git` (churn/authors/recency), `coupling` (co-change),
`layout` (treemap plots), `snapshots` (time machine), `stories` (tour).
Those keys are emitted as null/empty here so the viewer contract never changes
shape - only fills in. See docs/02-DATA-SCHEMA.md.
"""

from __future__ import annotations

import datetime as _dt
import os
import subprocess

from . import SCHEMA, __version__
from .metrics import generic_metrics, python_metrics
from .resolve import ModuleIndex
from .walk import FileRec, WalkOptions, read_text, walk_repo


def _git(root: str, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", root, *args],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def repo_meta(root: str) -> dict:
    head = _git(root, "rev-parse", "HEAD")
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return {
        "name": os.path.basename(os.path.abspath(root.rstrip("/\\"))),
        "path": os.path.abspath(root),
        "has_git": head is not None,
        "head": head,
        "branch": branch,
    }


def _dir_chain(rel: str) -> list[str]:
    """['a', 'a/b'] for 'a/b/c.py'."""
    parts = rel.split("/")[:-1]
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def build_city(root: str, opts: WalkOptions | None = None,
               verbose: bool = False) -> dict:
    opts = opts or WalkOptions()
    files: list[FileRec] = walk_repo(root, opts)
    if verbose:
        print(f"[citygen] walked {len(files)} files")

    py_paths = [f.rel for f in files if f.lang == "python"]
    index = ModuleIndex(py_paths)

    buildings: list[dict] = []
    by_path: dict[str, int] = {}
    parse_errors: list[dict] = []
    pending_imports: list[tuple[int, list, str]] = []

    for f in files:
        text = read_text(f.abs)
        if text is None:
            continue
        gm = generic_metrics(text)
        b = {
            "id": f.rel,
            "path": f.rel,
            "name": f.rel.rsplit("/", 1)[-1],
            "dir": f.rel.rsplit("/", 1)[0] if "/" in f.rel else "",
            "ext": f.ext,
            "lang": f.lang or "other",
            "bytes": f.size,
            "loc": gm["loc"],
            "sloc": gm["sloc"],
            "todo": gm["todo"],
            "functions": 0,
            "classes": 0,
            "complexity": 1,
            "max_fn_complexity": 0,
            "doc_ratio": 0.0,
            "ext_imports": 0,
            "in_deg": 0,
            "out_deg": 0,
            "parsed": False if f.lang == "python" else None,
        }
        if f.lang == "python":
            pr = python_metrics(text, f.rel)
            b["parsed"] = pr.ok
            if pr.ok:
                b["functions"] = len(pr.functions)
                b["classes"] = len(pr.classes)
                b["complexity"] = pr.complexity
                b["max_fn_complexity"] = pr.max_func_complexity
                b["doc_ratio"] = round(pr.doc_lines / gm["loc"], 3) if gm["loc"] else 0.0
                pending_imports.append((len(buildings), pr.imports, f.rel))
            else:
                parse_errors.append({"path": f.rel, "error": pr.error})
        by_path[f.rel] = len(buildings)
        buildings.append(b)

    # ---- intra-repo import edges -------------------------------------------
    edge_w: dict[tuple[int, int], int] = {}
    for bi, imports, rel in pending_imports:
        seen_ext = 0
        for module, level, symbols in imports:
            # A symbol in `from X import a, b` may itself be a submodule; those
            # are the real dependency, not X's __init__. Try symbols first.
            targets = set()
            for sym in symbols:
                t = index.resolve_symbol(module, level, sym, rel)
                if t:
                    targets.add(t)
            if not targets:
                t = index.resolve(module, level, rel)
                if t:
                    targets.add(t)
            if not targets:
                seen_ext += 1
                continue
            for t in targets:
                tj = by_path.get(t)
                if tj is None or tj == bi:
                    continue
                edge_w[(bi, tj)] = edge_w.get((bi, tj), 0) + 1
        buildings[bi]["ext_imports"] = seen_ext

    import_edges = [[a, b, w] for (a, b), w in sorted(edge_w.items())]
    for a, b, _w in import_edges:
        buildings[a]["out_deg"] += 1
        buildings[b]["in_deg"] += 1

    # ---- directory tree (districts) ----------------------------------------
    dirs: dict[str, dict] = {}
    for b in buildings:
        for d in _dir_chain(b["path"]):
            node = dirs.setdefault(d, {
                "id": d, "path": d, "name": d.rsplit("/", 1)[-1],
                "parent": d.rsplit("/", 1)[0] if "/" in d else "",
                "depth": d.count("/") + 1,
                "files": 0, "loc": 0, "complexity": 0,
            })
            node["files"] += 1
            node["loc"] += b["loc"]
            node["complexity"] += b["complexity"]
    tree = [dirs[k] for k in sorted(dirs)]

    stats = {
        "files": len(buildings),
        "dirs": len(tree),
        "loc": sum(b["loc"] for b in buildings),
        "sloc": sum(b["sloc"] for b in buildings),
        "functions": sum(b["functions"] for b in buildings),
        "classes": sum(b["classes"] for b in buildings),
        "complexity": sum(b["complexity"] for b in buildings),
        "python_files": len(py_paths),
        "import_edges": len(import_edges),
        "parse_errors": len(parse_errors),
        "langs": _lang_hist(buildings),
    }

    return {
        "schema": SCHEMA,
        "citygen_version": __version__,
        "generated_at": _dt.datetime.now(_dt.timezone.utc)
                            .replace(microsecond=0).isoformat(),
        "repo": repo_meta(root),
        "config": {
            "include_vendor": opts.include_vendor,
            "exclude": opts.exclude,
            "include": opts.include,
            "all_languages": opts.all_languages,
        },
        "stats": stats,
        "tree": tree,
        "buildings": buildings,
        "edges": {"import": import_edges, "call": [], "cochange": []},
        "git": None,        # phase 3
        "layout": None,     # phase 4
        "snapshots": None,  # phase 8
        "stories": [],      # phase 10
        "diagnostics": {"parse_errors": parse_errors[:50]},
    }


def _lang_hist(buildings: list[dict]) -> dict:
    hist: dict[str, int] = {}
    for b in buildings:
        hist[b["lang"]] = hist.get(b["lang"], 0) + 1
    return dict(sorted(hist.items(), key=lambda kv: -kv[1]))
