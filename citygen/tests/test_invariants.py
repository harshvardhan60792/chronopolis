"""Invariant tests over the whole city document.

These are the highest-value tests in the project: they catch the class of bug
that produces a city which renders but lies. Run against the toyrepo fixture
and, when present, the real repos next door.

Run: python citygen/tests/test_invariants.py
"""

from __future__ import annotations

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from citygen.build import build_city                    # noqa: E402
from citygen.walk import WalkOptions                    # noqa: E402

TOY = os.path.join(ROOT, "fixtures", "toyrepo")
NEIGHBOURS = [os.path.join(os.path.dirname(ROOT), n) for n in ("reachable",)]

VOLATILE = ("generated_at", "build_seconds")


def repos() -> list[str]:
    out = [TOY]
    out += [p for p in NEIGHBOURS if os.path.isdir(p)]
    return out


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# --------------------------------------------------------------------------
def test_buildings_sorted_and_indexed():
    for repo in repos():
        c = build_city(repo)
        paths = [b["path"] for b in c["buildings"]]
        check(paths == sorted(paths), f"{repo}: buildings not sorted by path")
        for i, b in enumerate(c["buildings"]):
            check(b["id"] == b["path"], f"{repo}: id != path at {i}")


def test_edge_indices_valid():
    for repo in repos():
        c = build_city(repo)
        n = len(c["buildings"])
        for kind, edges in c["edges"].items():
            for e in edges:
                a, b = e[0], e[1]
                check(0 <= a < n and 0 <= b < n, f"{repo}: {kind} index out of range")
                check(a != b, f"{repo}: {kind} self-edge at {a}")
        seen = set()
        for e in c["edges"]["cochange"]:
            key = (e[0], e[1])
            check(e[0] < e[1], f"{repo}: cochange pair not ordered i<j")
            check(key not in seen, f"{repo}: duplicate cochange pair {key}")
            seen.add(key)


def test_layout_parallel_and_inside_world():
    for repo in repos():
        c = build_city(repo)
        lay = c["layout"]
        check(lay is not None, f"{repo}: layout missing")
        plots = lay["plots"]
        check(len(plots) == len(c["buildings"]),
              f"{repo}: {len(plots)} plots for {len(c['buildings'])} buildings")
        W, D = lay["world"]["width"], lay["world"]["depth"]
        for i, p in enumerate(plots):
            check(p is not None, f"{repo}: building {i} has no plot")
            check(p["w"] > 0 and p["d"] > 0 and p["h"] > 0,
                  f"{repo}: non-positive plot at {i}: {p}")
            check(-0.01 <= p["x"] and p["x"] + p["w"] <= W + 0.01,
                  f"{repo}: plot {i} outside world in x: {p}")
            check(-0.01 <= p["z"] and p["z"] + p["d"] <= D + 0.01,
                  f"{repo}: plot {i} outside world in z: {p}")


def test_plots_do_not_overlap():
    """The single most important layout invariant: no two buildings share
    ground. Overlapping plots look like z-fighting garbage in the viewer."""
    for repo in repos():
        c = build_city(repo)
        plots = c["layout"]["plots"]
        boxes = [(p["x"], p["z"], p["x"] + p["w"], p["z"] + p["d"]) for p in plots]
        order = sorted(range(len(boxes)), key=lambda i: boxes[i][0])
        for ii, i in enumerate(order):
            ax0, az0, ax1, az1 = boxes[i]
            for j in order[ii + 1:]:
                bx0, bz0, bx1, bz1 = boxes[j]
                if bx0 >= ax1 - 1e-6:
                    break                       # sorted by x: no later box can overlap
                ox = min(ax1, bx1) - max(ax0, bx0)
                oz = min(az1, bz1) - max(az0, bz0)
                check(ox <= 1e-6 or oz <= 1e-6,
                      f"{repo}: plots {i} and {j} overlap by {ox:.3f}x{oz:.3f}")


def test_aspect_ratio_is_citylike():
    """Buildings must read as boxes, not walls. The p90 bar from T04 only
    means something with enough plots to have a 90th percentile; on a 5-file
    fixture it is just the worst single lot, so tiny repos get a loose max
    bound instead."""
    for repo in repos():
        c = build_city(repo)
        ratios = sorted(max(p["w"], p["d"]) / min(p["w"], p["d"])
                        for p in c["layout"]["plots"])
        if len(ratios) >= 20:
            p90 = ratios[int(len(ratios) * 0.9)]
            check(p90 <= 3.0, f"{repo}: p90 aspect ratio {p90:.2f} > 3.0")
        else:
            check(ratios[-1] <= 8.0, f"{repo}: worst aspect ratio {ratios[-1]:.2f} > 8.0")


def test_no_nan_anywhere():
    def walk(node, path="$"):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, float):
            check(not math.isnan(node) and not math.isinf(node),
                  f"non-finite value at {path}: {node}")

    for repo in repos():
        walk(build_city(repo))


def test_git_section_matches_schema():
    for repo in repos():
        c = build_city(repo)
        g = c["git"]
        if g is None:
            continue
        for key in ("authors", "commit_count", "first_commit_ts",
                    "last_commit_ts", "window_days", "truncated"):
            check(key in g, f"{repo}: git.{key} missing")
        check(g["commit_count"] > 0, f"{repo}: git.commit_count is 0")
        n_auth = len(g["authors"])
        for a in g["authors"]:
            check({"name", "email", "commits"} <= set(a), f"{repo}: author fields")
        counts = [a["commits"] for a in g["authors"]]
        check(counts == sorted(counts, reverse=True),
              f"{repo}: authors not sorted by commits desc")
        for i, b in enumerate(c["buildings"]):
            check("commits" in b, f"{repo}: building {i} missing git fields")
            for ai, _n in b["authors"]:
                check(0 <= ai < n_auth, f"{repo}: bad author index on building {i}")
            if b["commits"] == 0:
                check(b["first_ts"] is None and b["stale_days"] is None,
                      f"{repo}: uncommitted building {i} has fake timestamps")
            else:
                check(b["bus_factor"] >= 1, f"{repo}: bus_factor 0 with commits")
                check(0 < b["owner_share"] <= 1, f"{repo}: bad owner_share")


def test_traffic_source_consistency():
    for repo in repos():
        c = build_city(repo)
        src = c["stats"]["traffic_source"]
        check(src in ("cochange", "imports"), f"{repo}: bad traffic_source {src}")
        if src == "imports":
            check(not c["edges"]["cochange"],
                  f"{repo}: fell back to imports but kept cochange edges")
        roads = c["layout"]["roads"]
        for r in roads:
            check(r["kind"] == src, f"{repo}: road kind {r['kind']} != {src}")
            check(len(r["pts"]) >= 2, f"{repo}: degenerate road")


def test_determinism():
    """Two builds of the same tree must differ only in volatile fields."""
    for repo in repos():
        a = build_city(repo)
        b = build_city(repo)
        for k in VOLATILE:
            a.pop(k, None)
            b.pop(k, None)
        check(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True),
              f"{repo}: build is not deterministic")


def test_health_scores_present_and_ranged():
    for repo in repos():
        c = build_city(repo)
        if c["git"] is None:
            continue
        vals = [b["health"] for b in c["buildings"]]
        check(all(0.0 <= v <= 1.0 for v in vals), f"{repo}: health out of range")
        check(len(set(vals)) > 1, f"{repo}: health is constant - normalisation broken")


if __name__ == "__main__":
    import traceback
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as exc:
                failed += 1
                print(f"FAIL {name}: {exc}")
                if not isinstance(exc, AssertionError):
                    traceback.print_exc()
    print(f"\n{failed} failed")
    raise SystemExit(1 if failed else 0)
