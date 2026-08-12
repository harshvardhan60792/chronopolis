"""citygen command line interface.

    python -m citygen build <repo> -o out/city.json [options]
    python -m citygen inspect out/city.json
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time

from . import __version__
from .build import build_city
from .walk import WalkOptions


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
    city = build_city(a.repo, opts, verbose=a.verbose)
    dt = time.time() - t0
    city["build_seconds"] = round(dt, 3)

    out = a.out
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
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
    print(f"[citygen] {city['repo']['name']}: {s['files']} files, "
          f"{s['loc']:,} LOC, {s['functions']} fns, "
          f"{s['import_edges']} import edges, {s['parse_errors']} parse errors")
    print(f"[citygen] wrote {out} ({size/1024:.1f} KB) in {dt:.2f}s")
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
    b.set_defaults(func=_cmd_build)

    i = sub.add_parser("inspect", help="print a summary of a city.json")
    i.add_argument("city")
    i.set_defaults(func=_cmd_inspect)

    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
