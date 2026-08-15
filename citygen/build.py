"""Assemble a city document from a repository.

Phase 1 scope (implemented): tree, buildings with metrics, intra-repo import
edges, aggregate stats.
Later phases fill: `git` (churn/authors/recency), `coupling` (co-change),
`layout` (treemap plots), `snapshots` (time machine), `stories` (tour).
Those keys are emitted as null/empty here so the viewer contract never changes
shape - only fills in. See docs/02-DATA-SCHEMA.md.
"""

from __future__ import annotations

import bisect
import datetime as _dt
import os
import subprocess

from . import SCHEMA, __version__
from .gitmine import (apply_history, last_commit_ts, read_history,
                      reconstruct_timeline)
from .coupling import calculate_cochange
from .layout import generate_layout
from .metrics import (curly_complexity, generic_metrics, go_metrics,
                      js_metrics, python_metrics, ruby_metrics)
from .resolve import JsModuleIndex, ModuleIndex, RubyModuleIndex
from .snapshots import compute_snapshots
from .stories import generate_stories
from .walk import (EXT_LANG, FileRec, WalkOptions, is_source_path, read_text,
                   walk_repo)


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


def calculate_health(buildings: list[dict]) -> None:
    """Composite 'how worried should I be' score, 0..1, higher is worse.

    Percentile ranks are within-repo so the colour ramp stays meaningful for a
    40-file project and a 4000-file one alike. Formula is fixed in
    tasks/T12-overlays-legend.md - change it there first.
    """
    churn_list = sorted(b["churn"] for b in buildings if "churn" in b)
    cx_list = sorted(b.get("complexity", 0) for b in buildings)

    def rank(val: float, lst: list) -> float:
        # bisect keeps this O(n log n) overall; a linear scan per building made
        # it O(n^2) and showed up on repos with thousands of files
        return bisect.bisect_left(lst, val) / len(lst) if lst else 0.0

    for b in buildings:
        if "churn" not in b:
            b["health"] = 0.0
            continue
        churn_n = rank(b["churn"], churn_list)
        cx_n = rank(b.get("complexity", 0), cx_list)
        stale = b.get("stale_days")
        stale_n = 1.0 if stale is None else max(0.0, min(stale / 540.0, 1.0))
        owner_risk = b.get("owner_share") or 0.0
        b["health"] = round(0.40 * churn_n * cx_n + 0.25 * cx_n
                            + 0.20 * owner_risk + 0.15 * (1 - stale_n), 4)


def build_city(root: str, opts: WalkOptions | None = None,
               verbose: bool = False,
               no_git: bool = False,
               max_commits: int | None = None,
               since: str | None = None,
               max_commit_files: int = 60,
               min_cochange: int = 3,
               world_size: float = 400.0,
               street_width: float = 2.0,
               height_scale: float = 2.6,
               snapshots: int = 24,
               ruins: bool = True) -> dict:
    opts = opts or WalkOptions()
    files: list[FileRec] = walk_repo(root, opts)
    if verbose:
        print(f"[citygen] walked {len(files)} files")

    py_paths = [f.rel for f in files if f.lang == "python"]
    index = ModuleIndex(py_paths)

    JS_LANGS = {"javascript", "typescript"}
    js_paths = [f.rel for f in files if f.lang in JS_LANGS]
    js_index = JsModuleIndex(js_paths)

    rb_paths = [f.rel for f in files if f.lang == "ruby"]
    rb_index = RubyModuleIndex(rb_paths)

    # Complexity/function heuristics only - no import resolution attempted
    # for these (no reserved-word marker to find declarations by, and each
    # language's module system is different enough that faking edges would
    # do more harm than the current honest "0 import edges" does).
    CURLY_LANGS = {"java", "csharp", "cpp", "c", "php", "kotlin", "swift", "rust"}

    buildings: list[dict] = []
    parse_errors: list[dict] = []
    # Keyed by path, not by index: ruins get inserted below and the array is
    # re-sorted, so any index captured during this pass would be wrong.
    pending_imports: list[tuple[str, list]] = []
    pending_imports_js: list[tuple[str, list[str]]] = []
    pending_imports_rb: list[tuple[str, list[tuple[str, bool]]]] = []

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
                pending_imports.append((f.rel, pr.imports))
            else:
                parse_errors.append({"path": f.rel, "error": pr.error})
        elif f.lang in JS_LANGS:
            # Regex heuristic, not a real parser - see metrics.js_metrics.
            # It cannot fail the way ast.parse can, so there is no error path.
            jr = js_metrics(text)
            b["parsed"] = True
            b["functions"] = jr.functions
            b["classes"] = jr.classes
            b["complexity"] = jr.complexity
            pending_imports_js.append((f.rel, jr.imports))
        elif f.lang == "go":
            gr = go_metrics(text)
            b["functions"] = gr.functions
            b["complexity"] = gr.complexity
        elif f.lang in CURLY_LANGS:
            b["complexity"] = curly_complexity(text)
        elif f.lang == "ruby":
            rr = ruby_metrics(text)
            b["parsed"] = True
            b["functions"] = rr.functions
            b["classes"] = rr.classes
            b["complexity"] = rr.complexity
            pending_imports_rb.append((f.rel, rr.imports))
        buildings.append(b)

    # ---- git history, and the ruins it reveals ------------------------------
    history: list[dict] = []
    git_meta: dict = {}
    timeline: dict[str, dict] = {}
    if not no_git:
        h, git_meta = read_history(root, max_commits, since, max_commit_files)
        history = h or []
        if history:
            timeline = reconstruct_timeline(history)

    live = {b["path"] for b in buildings}
    if ruins and timeline:
        # Files that existed once and do not now still shaped this codebase.
        # They get plots so the layout is stable across the whole timeline
        # (ADR-003) and render as ruins at 'now' (ADR-008). Without them the
        # city would reshuffle every time you scrubbed the clock.
        for path, rec in sorted(timeline.items()):
            if path in live or not is_source_path(path):
                continue
            if rec["died"] is None or rec["max_loc"] <= 0:
                continue
            ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
            buildings.append({
                "id": path, "path": path, "name": path.rsplit("/", 1)[-1],
                "dir": path.rsplit("/", 1)[0] if "/" in path else "",
                "ext": ext, "lang": EXT_LANG.get(ext, "other"),
                "bytes": 0, "loc": rec["max_loc"], "sloc": rec["max_loc"],
                "todo": 0, "functions": 0, "classes": 0,
                # No source to parse, so complexity falls back to the same
                # length proxy the height formula uses.
                "complexity": max(1, int(rec["max_loc"] / 18)),
                "max_fn_complexity": 0, "doc_ratio": 0.0, "ext_imports": 0,
                "in_deg": 0, "out_deg": 0, "parsed": None,
                "deleted": True, "died_ts": rec["died"],
            })

    buildings.sort(key=lambda b: b["path"])
    by_path: dict[str, int] = {b["path"]: i for i, b in enumerate(buildings)}
    for b in buildings:
        b.setdefault("deleted", False)

    # ---- intra-repo import edges -------------------------------------------
    edge_w: dict[tuple[int, int], int] = {}
    for rel, imports in pending_imports:
        bi = by_path[rel]
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

    for rel, specs in pending_imports_js:
        bi = by_path[rel]
        seen_ext = 0
        for spec in specs:
            target = js_index.resolve(spec, rel)
            if target is None:
                seen_ext += 1
                continue
            tj = by_path.get(target)
            if tj is None or tj == bi:
                continue
            edge_w[(bi, tj)] = edge_w.get((bi, tj), 0) + 1
        buildings[bi]["ext_imports"] = seen_ext

    for rel, specs in pending_imports_rb:
        bi = by_path[rel]
        seen_ext = 0
        for spec, is_relative in specs:
            target = rb_index.resolve_relative(spec, rel) if is_relative else rb_index.resolve_require(spec)
            if target is None:
                seen_ext += 1
                continue
            tj = by_path.get(target)
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

    git_stats = None
    commits: list[list[int]] = []
    if history:
        git_stats = apply_history(buildings, history, last_commit_ts(root), git_meta)
        for c in history:
            if c["bulk"]:
                continue
            idxs = sorted({by_path[p] for p, _a, _d, _r in c["files"] if p in by_path})
            if idxs:
                commits.append(idxs)

    cochange_edges = []
    cochange_pairs = 0
    hidden_coupling = 0
    top_hidden = []
    
    if git_stats and git_stats["commit_count"] >= 30:
        cochange_edges, cochange_pairs, hidden_coupling, top_hidden = calculate_cochange(
            commits, buildings, import_edges, min_cochange)

    # Thin history produces noise, not signal: fall back to import-driven
    # traffic and say so in the legend (ADR-005).
    traffic_source = "cochange"
    if not git_stats or git_stats["commit_count"] < 30 or cochange_pairs < 20:
        traffic_source = "imports"
        cochange_edges = []
        cochange_pairs = 0
        hidden_coupling = 0
        top_hidden = []

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
        "cochange_pairs": cochange_pairs,
        "hidden_coupling": hidden_coupling,
        "top_hidden_coupling": top_hidden,
        "traffic_source": traffic_source,
    }
    
    calculate_health(buildings)
    # A single repo-level mood cue (viewer/src/weather.js: rain density),
    # not a per-file signal - just the mean of the same composite score the
    # Health overlay colours buildings by.
    stats["avg_health"] = (round(sum(b["health"] for b in buildings) / len(buildings), 4)
                           if buildings else 0.0)

    # Footprints are sized by the largest the file ever was, not by what
    # survives today. That is what keeps a building's plot fixed while the
    # timeline plays (ADR-003) - only its height moves.
    def historical_weight(b: dict) -> float:
        rec = timeline.get(b["path"])
        loc = max(b.get("loc") or 0, rec["max_loc"] if rec else 0)
        return max(1.0, loc ** 0.5)

    layout = generate_layout(
        buildings=buildings,
        tree=tree,
        world_size=world_size,
        street_width=street_width,
        height_scale=height_scale,
        cochange_edges=cochange_edges,
        import_edges=import_edges,
        traffic_source=traffic_source,
        weight_fn=historical_weight,
    )

    snaps = compute_snapshots(history, buildings, height_scale, snapshots) \
        if (history and snapshots >= 2) else None

    stories = generate_stories(buildings, tree, stats, git_stats, history)

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
        "edges": {"import": import_edges, "call": [], "cochange": cochange_edges},
        "git": git_stats,
        "layout": layout,
        "snapshots": snaps,
        "stories": stories,
        "diagnostics": {"parse_errors": parse_errors[:50]},
    }


def _lang_hist(buildings: list[dict]) -> dict:
    hist: dict[str, int] = {}
    for b in buildings:
        hist[b["lang"]] = hist.get(b["lang"], 0) + 1
    return dict(sorted(hist.items(), key=lambda kv: -kv[1]))

