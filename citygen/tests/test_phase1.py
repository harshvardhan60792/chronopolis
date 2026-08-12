"""Phase 1 acceptance tests. Run: python -m pytest citygen/tests -q

These assert on fixtures/toyrepo, whose expected numbers are written in the
fixture source as comments. If you change the fixture, change these too.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from citygen.build import build_city                      # noqa: E402
from citygen.metrics import generic_metrics, python_metrics  # noqa: E402
from citygen.walk import WalkOptions, walk_repo           # noqa: E402

TOY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "fixtures", "toyrepo")


def city():
    return build_city(TOY, WalkOptions())


def by_path(c, path):
    return next(b for b in c["buildings"] if b["path"] == path)


def test_walk_is_sorted_and_deterministic():
    a = [f.rel for f in walk_repo(TOY)]
    b = [f.rel for f in walk_repo(TOY)]
    assert a == b == sorted(a)
    assert "pkg/core.py" in a


def test_generic_metrics():
    m = generic_metrics("a\n\n b\n")
    assert m["loc"] == 3 and m["sloc"] == 2


def test_function_complexity():
    src = open(os.path.join(TOY, "pkg", "core.py"), encoding="utf-8").read()
    r = python_metrics(src)
    assert r.ok
    fns = {f.name: f.complexity for f in r.functions}
    assert fns["classify"] == 4      # if + elif + for
    assert fns["run"] == 3           # for + except
    assert r.classes == ["Engine"]


def test_relative_and_absolute_imports_resolve():
    c = city()
    core = by_path(c, "pkg/core.py")
    edges = {(c["buildings"][a]["path"], c["buildings"][b]["path"])
             for a, b, _w in c["edges"]["import"]}
    assert ("pkg/core.py", "pkg/helpers.py") in edges   # from . import helpers
    assert ("pkg/core.py", "pkg/util.py") in edges      # from pkg import util
    assert core["ext_imports"] == 1                     # json


def test_orphan_detected():
    c = city()
    o = by_path(c, "orphan.py")
    assert o["in_deg"] == 0 and o["out_deg"] == 0


def test_schema_keys_present():
    c = city()
    for k in ("schema", "repo", "stats", "tree", "buildings", "edges",
              "git", "layout", "snapshots", "stories", "diagnostics"):
        assert k in c
    assert c["edges"].keys() >= {"import", "call", "cochange"}


def test_no_vendor_dirs():
    files = [f.rel for f in walk_repo(TOY)]
    assert not any("__pycache__" in f or "node_modules" in f for f in files)


if __name__ == "__main__":
    import traceback
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failed += 1
                print(f"FAIL {name}")
                traceback.print_exc()
    raise SystemExit(1 if failed else 0)
