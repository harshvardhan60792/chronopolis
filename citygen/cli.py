"""citygen command line interface.

    python -m citygen build <repo> -o out/city.json [options]
    python -m citygen inspect out/city.json
"""

from __future__ import annotations

import argparse
import gzip
import http.server
import json
import os
import socketserver
import sys
import time

from . import __version__
from .build import build_city
from .export_html import export_html
from .walk import WalkOptions


def _use_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

def _style(code: str, text: str, enabled: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if enabled else text



def _cmd_build(a: argparse.Namespace) -> int:
    if not os.path.isdir(a.repo):
        print(f"error: not a directory: {a.repo}", file=sys.stderr)
        return 2
    t0 = time.time()
    opts = WalkOptions(
        include_vendor=a.include_vendor,
        exclude=a.exclude or [],
        include=a.include or [],
        all_languages=not a.python_only,
    )
    city = build_city(
        a.repo, opts, verbose=a.verbose,
        no_git=a.no_git, max_commits=a.max_commits, since=a.since,
        max_commit_files=a.max_commit_files, min_cochange=a.min_cochange,
        world_size=a.world_size, street_width=a.street_width,
        height_scale=a.height_scale,
        snapshots=a.snapshots, ruins=not a.no_ruins,
    )
    dt = time.time() - t0
    city["build_seconds"] = round(dt, 3)

    out = a.out
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    
    from ._profile import stage
    with stage("serialise"):
        text = json.dumps(city, separators=(",", ":") if a.compact else None,
                          indent=None if a.compact else 2)
        if a.gzip:
            out = out if out.endswith(".gz") else out + ".gz"
            with gzip.open(out, "wt", encoding="utf-8") as fh:
                fh.write(text)
        else:
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(text)

    s = city["stats"]
    size = os.path.getsize(out)
    color = _use_color()
    bold = lambda t: _style("1", t, color)
    green = lambda t: _style("32;1", t, color)
    dim = lambda t: _style("2", t, color)

    print(f"[citygen] {bold(city['repo']['name'])}: {s['files']} files, "
          f"{s['loc']:,} LOC, {s['functions']} fns, "
          f"{s['import_edges']} import edges, {s['parse_errors']} parse errors")
    snaps = city.get("snapshots")
    if snaps:
        ruins = sum(1 for b in city["buildings"] if b.get("deleted"))
        print(f"[citygen] timeline: {snaps['count']} snapshots "
              f"{snaps['labels'][0]} -> {snaps['labels'][-1]}, {ruins} ruins")
    # Plain ASCII, not a unicode checkmark: Windows' default console codepage
    # (cp1252/cp437) crashes on print() for characters outside it, and this
    # is a stdlib-only, no-dependency CLI that has to work in that terminal
    # unmodified (ADR-006).
    building_count = f"{len(city['buildings']):,} buildings"
    print(f"{green('OK')} built {bold(building_count)} "
          f"in {dt:.2f}s -> {dim(out)} ({size/1024:.1f} KB)")
    print(f"  {dim('next:')} python -m citygen serve {out}")
    
    from ._profile import results
    st = results()
    if st:
        print(f"PROFILING_RESULTS: {json.dumps(st)}")
    
    return 0


def _load(path: str) -> dict:
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _cmd_inspect(a: argparse.Namespace) -> int:
    """Human sanity-check of a city document - the Phase 1 acceptance tool."""
    city = _load(a.city)
    s, bs = city["stats"], city["buildings"]
    print(f"schema      {city['schema']}  (citygen {city['citygen_version']})")
    print(f"repo        {city['repo']['name']}  git={city['repo']['has_git']} "
          f"head={(city['repo']['head'] or '-')[:8]}")
    print(f"files       {s['files']}   dirs {s['dirs']}   LOC {s['loc']:,}")
    print(f"python      {s['python_files']} files, {s['functions']} fns, "
          f"{s['classes']} classes, complexity {s['complexity']:,}")
    print(f"edges       import={s['import_edges']}  parse_errors={s['parse_errors']}")
    print(f"langs       {s['langs']}")

    def top(key: str, n: int = 8) -> None:
        print(f"\n-- top {n} by {key}")
        for b in sorted(bs, key=lambda x: -x.get(key, 0))[:n]:
            print(f"   {b[key]:>7}  {b['path']}")

    top("complexity")
    top("loc")
    top("in_deg")
    orphans = [b for b in bs if b["lang"] == "python"
               and not b["in_deg"] and not b["out_deg"]]
    print(f"\n-- isolated python files: {len(orphans)}")
    for b in orphans[:8]:
        print(f"   {b['path']}")
    if city["diagnostics"]["parse_errors"]:
        print("\n-- parse errors")
        for e in city["diagnostics"]["parse_errors"][:5]:
            print(f"   {e['path']}: {e['error'][:70]}")

    if city.get("git"):
        top("churn")
        top("commits")
        bf1 = sum(1 for b in bs if b.get("bus_factor") == 1)
        print(f"\n-- files with bus_factor == 1: {bf1}")
        print("\n-- top 8 stalest files")
        for b in sorted([b for b in bs if b.get("stale_days")], key=lambda x: -x["stale_days"])[:8]:
            print(f"   {b['stale_days']:>7} days  {b['path']}")
            
        print(f"\n-- top 10 co-change pairs ({s.get('cochange_pairs')} pairs total)")
        for edge in city["edges"]["cochange"][:10]:
            print(f"   {edge[3]:>6.3f} strength  {bs[edge[0]]['path']} <-> {bs[edge[1]]['path']} ({edge[2]} commits)")

        print(f"\n-- top 10 hidden coupling pairs ({s.get('hidden_coupling')} total)")
        for h in s.get("top_hidden_coupling", [])[:10]:
            print(f"   {h[2]:>6.3f} strength  {bs[h[0]]['path']} <-> {bs[h[1]]['path']}")
            
    return 0


def _cmd_impact(a: argparse.Namespace) -> int:
    import os
    if not os.path.exists(a.city):
        print(f"no city at {a.city} — run: python -m citygen build . -o {a.city}", file=sys.stderr)
        return 2

    city = _load(a.city)
    
    from .impact import build_reverse_index, blast_radius, resolve_target
    
    try:
        start_idx = resolve_target(city, a.file)
    except LookupError as e:
        if os.path.exists(a.file):
            print("citygen skipped this file during build (vendored/oversized/binary)", file=sys.stderr)
            return 2
        print(f"error: {e}", file=sys.stderr)
        return 2

    b = city["buildings"][start_idx]
    import_edges = city.get("edges", {}).get("import", [])
    n = len(city["buildings"])
    
    rev = build_reverse_index(import_edges, n)
    result = blast_radius(rev, start_idx, a.depth)
    
    color = _use_color()
    bold = lambda t: _style("1", t, color)
    
    direct_count = len(result["direct"])
    trans_count = len(result["all"])
    
    resolution = "full" if b.get("lang") in ("python", "javascript", "typescript", "ruby") else "none"
    
    if a.json:
        out = {
            "file": b["path"],
            "index": start_idx,
            "direct": [city["buildings"][i]["path"] for i in result["direct"]],
            "transitive": [city["buildings"][i]["path"] for i in result["all"]],
            "depths": {str(d): [city["buildings"][i]["path"] for i in sorted(deps)] for d, deps in result["depths"].items()},
            "counts": {
                "direct": direct_count,
                "transitive": trans_count,
                "max_depth": max(result["depths"].keys()) if result["depths"] else 0
            },
            "signals": {},
            "import_resolution": resolution,
            "truncated": result["truncated"]
        }
        for k in ["bus_factor", "owner_share", "stale_days", "complexity", "loc"]:
            if k in b:
                out["signals"][k] = b[k]
        
        print(json.dumps(out, indent=2))
        return 0

    print(bold(b["path"]))
    print()
    print(f"  Direct dependents        {direct_count}")
    print(f"  Transitive dependents    {trans_count}")
    if result["depths"]:
        max_d = max(result["depths"].keys())
        print(f"  Depth                    {max_d} level{'s' if max_d > 1 else ''}")
    else:
        print("  Depth                    0 levels")
    print()

    has_git = city.get("repo", {}).get("has_git", True)
    
    if not has_git:
        print("  Risk signals (no git history in this city)")
        if "complexity" in b:
            print(f"    complexity             {b['complexity']}")
        print()
    else:
        if any(k in b for k in ("bus_factor", "stale_days", "complexity")):
            print("  Risk signals")
            if "bus_factor" in b:
                commits = b.get("commits", 0)
                share = b.get("owner_share", 0.0) * 100
                print(f"    bus factor             {b['bus_factor']}  (harsh, {share:.0f}% of {commits} commits)")
            if "stale_days" in b:
                print(f"    last touched           {b['stale_days']} days ago")
            if "complexity" in b:
                print(f"    complexity             {b['complexity']}")
            print()

    if trans_count == 0:
        print(f"No file in this repo imports {b['path']}.")
        if resolution == "none":
            lang_val = b.get('lang', 'unknown')
            print(f"Note: import arcs are not resolved for {lang_val} — this is \"no data\", not \"no dependents\".")
        return 0

    for d in sorted(result["depths"].keys()):
        deps = result["depths"][d]
        print(f"  Depth {d}  ({len(deps)} file{'s' if len(deps) > 1 else ''})")
        
        show = deps if a.tree else deps[:15]
        for i in show:
            print(f"    {city['buildings'][i]['path']}")
        
        if not a.tree and len(deps) > 15:
            print(f"    ... and {len(deps) - 15} more")

    return 0

def _cmd_risk(a: argparse.Namespace) -> int:
    import sys
    from .risk import score_all, score_paths, staged_paths

    if not os.path.exists(a.city):
        print(f"no city at {a.city} — run: python -m citygen build . -o {a.city}", file=sys.stderr)
        return 2

    city = _load(a.city)

    if a.staged and a.paths:
        print("error: --staged and paths are mutually exclusive", file=sys.stderr)
        return 2

    if a.staged:
        repo_path = city.get("repo", {}).get("path", ".")
        paths = staged_paths(repo_path)
        if not paths:
            print("Nothing staged.")
            return 0
        scored = score_paths(city, paths)
    elif a.paths:
        scored = score_paths(city, a.paths)
    else:
        scored = score_all(city)
        scored.sort(key=lambda s: s["score"] if s["score"] is not None else -1.0, reverse=True)
        scored = scored[:a.top]

    if a.json:
        import json
        print(json.dumps(scored, indent=2))
        return 0

    if not a.staged and not a.paths:
        print(f"Riskiest files in {city.get('repo', {}).get('name', 'repo')}\n")

    color = _use_color()
    bold = lambda t: _style("1", t, color)
    red = lambda t: _style("31", t, color)
    yellow = lambda t: _style("33", t, color)

    for i, s in enumerate(scored):
        prefix = f"{i+1}. " if a.staged else "  "
        score = s["score"]
        band = s["band"]
        
        if score is None:
            score_str = "None"
            band_styled = band
        else:
            score_str = f"{score:.2f}"
            if band == "high":
                band_styled = red(band)
            elif band == "moderate":
                band_styled = yellow(band)
            else:
                band_styled = band

        band_padded = band_styled + " " * max(0, 8 - len(band))
        
        if a.staged:
            print(f"{i+1}. {score_str:>4}  {band_padded}  {s['path']}")
        else:
            print(f"  {score_str:>4}  {band_padded}  {s['path']}")
            
        for reason in s["reasons"]:
            print(f"        {reason}")
        print()

    if a.fail_over is not None:
        failed = [s for s in scored if s["score"] is not None and s["score"] > a.fail_over]
        if failed:
            print(f"error: {len(failed)} files exceed risk threshold {a.fail_over}", file=sys.stderr)
            return 1

    return 0

def _cmd_pr_report(a: argparse.Namespace) -> int:
    import sys
    from .report import build_report, render_markdown, load_author_emails

    if not os.path.exists(a.city):
        print(f"no city at {a.city} — run: python -m citygen build . -o {a.city}", file=sys.stderr)
        return 2

    city = _load(a.city)

    if getattr(a, "changed_from_stdin", False):
        changed = [line.strip() for line in sys.stdin if line.strip()]
    else:
        changed = []

    pr_author_emails = load_author_emails(a.pr_author_emails)
    report = build_report(city, changed, pr_author_emails)

    if report.get("silent"):
        return 0

    markdown = render_markdown(report, city)
    if markdown:
        print(markdown)

    return 0


def _cmd_export(a: argparse.Namespace) -> int:
    from .export_html import export_html
    try:
        export_html(a.json_path, a.output)
        return 0
    except Exception as e:
        print(f"Error exporting HTML: {e}", file=sys.stderr)
        return 1


def _cmd_serve(a: argparse.Namespace) -> int:
    viewer_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'viewer', 'dist')
    if not os.path.exists(viewer_dist):
        print("Error: viewer/dist not found. Did you run 'npm run build'?", file=sys.stderr)
        return 1

    import shutil
    if a.json_path and os.path.exists(a.json_path):
        shutil.copy(a.json_path, os.path.join(viewer_dist, 'city.json'))
        print(f"Copied {a.json_path} to viewer/dist/city.json")

    os.chdir(viewer_dist)
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", a.port), Handler) as httpd:
        print(f"Serving at http://localhost:{a.port}")
        try:
            import webbrowser
            webbrowser.open(f"http://localhost:{a.port}")
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="citygen",
                                description="Chronopolis repository analyzer")
    p.add_argument("--version", action="version", version=f"citygen {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="analyze a repo -> city.json")
    b.add_argument("repo")
    b.add_argument("-o", "--out", default="out/city.json")
    b.add_argument("--exclude", action="append", metavar="GLOB")
    b.add_argument("--include", action="append", metavar="GLOB")
    b.add_argument("--include-vendor", action="store_true",
                   help="do not skip node_modules/.venv/dist/...")
    b.add_argument("--python-only", action="store_true",
                   help="only files with a known language extension")
    b.add_argument("--compact", action="store_true", help="minified JSON")
    b.add_argument("--gzip", action="store_true", help="write .json.gz")
    b.add_argument("-v", "--verbose", action="store_true")
    b.add_argument("--no-git", action="store_true", help="skip git history")
    b.add_argument("--max-commits", type=int, help="limit git commits")
    b.add_argument("--since", help="limit git commits since DATE")
    b.add_argument("--max-commit-files", type=int, default=60, help="max files per commit to count for coupling")
    b.add_argument("--min-cochange", type=int, default=3, help="min commits together to count for coupling")
    b.add_argument("--world-size", type=float, default=400.0, help="layout world size")
    b.add_argument("--street-width", type=float, default=2.0, help="district street width")
    b.add_argument("--height-scale", type=float, default=2.6, help="building height scale multiplier")
    b.add_argument("--snapshots", type=int, default=24,
                   help="history snapshots for the timeline (0 disables)")
    b.add_argument("--no-ruins", action="store_true",
                   help="omit deleted files instead of rendering them as ruins")
    b.set_defaults(func=_cmd_build)

    i = sub.add_parser("inspect", help="print a summary of a city.json")
    i.add_argument("city")
    i.set_defaults(func=_cmd_inspect)

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

    e = sub.add_parser("export", help="Export city JSON as a self-contained HTML file")
    e.add_argument("json_path", help="Path to the input city.json")
    e.add_argument("-o", "--output", required=True, help="Path for the output HTML file")
    e.set_defaults(func=_cmd_export)

    s = sub.add_parser("serve", help="Serve the viewer locally")
    s.add_argument("json_path", nargs="?", help="Path to city.json to serve")
    s.add_argument("--port", type=int, default=8000, help="Port to serve on")
    s.set_defaults(func=_cmd_serve)

    r = sub.add_parser("risk", help="which files are dangerous to change?")
    r.add_argument("paths", nargs="*",
                   help="files to score (default: whole repo, top N)")
    r.add_argument("--city", default="out/city.json")
    r.add_argument("--staged", action="store_true",
                   help="score the files staged in git right now")
    r.add_argument("--top", type=int, default=10,
                   help="how many files to list in whole-repo mode")
    r.add_argument("--json", action="store_true")
    r.add_argument("--fail-over", type=float, default=None, metavar="SCORE",
                   help="exit 1 if any scored file is riskier than SCORE (for CI)")
    r.set_defaults(func=_cmd_risk)
    
    pr = sub.add_parser("pr-report", help="risk finding for a PR, as markdown")
    pr.add_argument("--city", default="out/city.json")
    pr.add_argument("--changed-from-stdin", action="store_true", required=True,
                    help="read changed file paths, one per line, from stdin")
    pr.add_argument("--pr-author-emails", default=None,
                    help="path to a file of git commit emails (one per line) "
                         "belonging to the PR's author — see 'Identifying the "
                         "PR author' below. Omit to disable the exclusion rule.")
    pr.set_defaults(func=_cmd_pr_report)

    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())

