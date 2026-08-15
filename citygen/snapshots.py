"""The time machine: N historical states of the city, as sparse deltas.

Method (T11 "numstat", the default): replay `git log --numstat` forward and
track each file's line count as adds minus dels. No historical checkouts, no
re-parsing - one log read covers the whole history. The cost is that LOC is
approximate and complexity at time t is estimated by scaling today's
complexity by the LOC ratio. The viewer says so in the timeline legend; an
exact mode (`--snapshots-exact`) is specified in the task file and not built.

What comes out is deliberately sparse: a height entry is emitted only when a
building's height actually moved. A 2000-file repo over 24 snapshots stays
comfortably inside the size budget in docs/02-DATA-SCHEMA.md.
"""

from __future__ import annotations

import datetime as _dt

from .layout import building_height

MIN_COMMITS = 10        # below this, a timeline is two frames and a lie
HEIGHT_EPSILON = 0.01   # 1% - smaller moves are invisible and cost bytes


def compute_snapshots(history: list[dict], buildings: list[dict],
                      height_scale: float = 2.6,
                      count: int = 24) -> dict | None:
    if not history or len(history) < MIN_COMMITS or count < 2:
        return None

    idx_of = {b["path"]: i for i, b in enumerate(buildings)}
    first_ts = history[0]["ts"]
    last_ts = history[-1]["ts"]
    if last_ts <= first_ts:
        return None

    # Evenly spaced by calendar time, not by commit count: a repo's story reads
    # naturally against dates, and bursty months should look bursty.
    step = (last_ts - first_ts) / (count - 1)
    targets = [int(first_ts + step * i) for i in range(count)]

    # Live state, replayed forward.
    loc: dict[str, int] = {}
    alive: dict[str, bool] = {}
    final_loc = {b["path"]: (b.get("sloc") or b.get("loc") or 0) for b in buildings}
    complexity_now = {b["path"]: b.get("complexity", 1) for b in buildings}

    heights: dict[int, float] = {}      # last emitted height per building index
    born_seen: set[int] = set()
    dead_seen: set[int] = set()

    out_delta = []
    out_stats = []
    out_commits = []

    ci = 0
    n_commits = len(history)
    authors_window: set[str] = set()
    commits_window = 0
    churn_window = 0

    for target in targets:
        while ci < n_commits and history[ci]["ts"] <= target:
            c = history[ci]
            authors_window.add(c["email"])
            commits_window += 1
            for path, adds, dels, _renamed in c["files"]:
                if path not in idx_of:
                    continue
                churn_window += adds + dels
                cur = loc.get(path, 0)
                cur = max(0, cur + adds - dels)
                loc[path] = cur
                if not alive.get(path):
                    alive[path] = True
                if cur == 0 and dels > 0 and adds == 0:
                    alive[path] = False
            ci += 1

        born, died, hs = [], [], []
        for path, is_alive in alive.items():
            i = idx_of[path]
            if is_alive and i not in born_seen:
                born_seen.add(i)
                born.append(i)
                dead_seen.discard(i)
            elif not is_alive and i not in dead_seen:
                dead_seen.add(i)
                died.append(i)

            if not is_alive:
                continue

            l = loc.get(path, 0)
            fl = final_loc.get(path, 0)
            # Complexity is not recoverable from numstat, so scale today's
            # value by how much of the file existed then. Crude, monotonic,
            # and honest about being an estimate.
            ratio = (l / fl) if fl > 0 else 1.0
            h = round(building_height(complexity_now.get(path, 1) * ratio,
                                      l, height_scale), 2)
            prev = heights.get(i)
            if prev is None or abs(h - prev) > max(HEIGHT_EPSILON * max(prev, 1e-6), 0.05):
                heights[i] = h
                hs.append([i, h])

        out_delta.append({"born": sorted(born), "died": sorted(died), "h": hs})
        out_commits.append(history[max(0, ci - 1)]["sha"])
        out_stats.append({
            "files": sum(1 for v in alive.values() if v),
            "loc": sum(v for p, v in loc.items() if alive.get(p)),
            "authors_active": len(authors_window),
            "commits_since": commits_window,
            "churn_since": churn_window,
        })
        authors_window = set()
        commits_window = 0
        churn_window = 0

    return {
        "method": "numstat",
        "approximate": True,
        "count": count,
        "ts": targets,
        "labels": [_dt.datetime.fromtimestamp(t, _dt.timezone.utc).strftime("%Y-%m")
                   for t in targets],
        "commits": out_commits,
        "stats": out_stats,
        "delta": out_delta,
    }
