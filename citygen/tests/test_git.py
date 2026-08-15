"""Tests for history mining, timeline reconstruction and snapshots.

Deliberately no subprocess mocking: the previous version asserted on the exact
order of `subprocess.run` calls, which broke the moment the implementation
added one. These test the pure functions instead, against synthetic commit
records in the shape `read_history` produces.

Run: python citygen/tests/test_git.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from citygen.gitmine import (_clean_rename, apply_history,  # noqa: E402
                             reconstruct_timeline)
from citygen.snapshots import compute_snapshots  # noqa: E402

DAY = 86400


def commit(sha, ts, email, files, bulk=False, name=None):
    return {"sha": sha, "ts": ts, "email": email, "name": name or email,
            "files": files, "bulk": bulk}


def history():
    #                       (path, adds, dels, renamed)
    return [
        commit("a1", 100 * DAY, "ada@x.dev", [("app.py", 100, 0, False),
                                              ("util.py", 40, 0, False)]),
        commit("a2", 110 * DAY, "ada@x.dev", [("app.py", 30, 10, False)]),
        commit("a3", 120 * DAY, "bob@x.dev", [("app.py", 5, 5, False),
                                              ("util.py", 10, 0, False)]),
        commit("a4", 130 * DAY, "bob@x.dev", [("gone.py", 60, 0, False)]),
        commit("a5", 140 * DAY, "bob@x.dev", [("gone.py", 0, 60, False)]),
    ]


def buildings():
    return [
        {"path": "app.py", "loc": 125, "sloc": 125, "complexity": 20},
        {"path": "util.py", "loc": 50, "sloc": 50, "complexity": 6},
        {"path": "new.py", "loc": 10, "sloc": 10, "complexity": 2},   # uncommitted
    ]


class TestRenames(unittest.TestCase):
    def test_brace_form(self):
        p, r = _clean_rename("src/{old => new}/mod.py")
        self.assertEqual(p, "src/new/mod.py")
        self.assertTrue(r)

    def test_plain_form(self):
        p, r = _clean_rename("old.py => new.py")
        self.assertEqual(p, "new.py")
        self.assertTrue(r)

    def test_untouched(self):
        p, r = _clean_rename("src/mod.py")
        self.assertEqual(p, "src/mod.py")
        self.assertFalse(r)


class TestTimeline(unittest.TestCase):
    def test_life_and_death(self):
        t = reconstruct_timeline(history())
        self.assertEqual(t["app.py"]["born"], 100 * DAY)
        self.assertIsNone(t["app.py"]["died"])
        self.assertEqual(t["app.py"]["final_loc"], 100 + 30 - 10 + 5 - 5)
        self.assertEqual(t["app.py"]["max_loc"], 120)
        # A file emptied by a pure deletion is dead, and its peak survives.
        self.assertEqual(t["gone.py"]["died"], 140 * DAY)
        self.assertEqual(t["gone.py"]["max_loc"], 60)
        self.assertEqual(t["gone.py"]["final_loc"], 0)


class TestApplyHistory(unittest.TestCase):
    def setUp(self):
        self.bs = buildings()
        self.git = apply_history(self.bs, history(), 200 * DAY,
                                 {"commit_count": 5})

    def test_churn_and_dates(self):
        app = self.bs[0]
        self.assertEqual(app["commits"], 3)
        self.assertEqual(app["churn"], 100 + 30 + 10 + 5 + 5)
        self.assertEqual(app["first_ts"], 100 * DAY)
        self.assertEqual(app["last_ts"], 120 * DAY)
        self.assertEqual(app["stale_days"], 80)
        self.assertEqual(app["age_days"], 100)

    def test_ownership(self):
        app = self.bs[0]
        # ada has 2 of 3 commits on app.py
        self.assertEqual(self.git["authors"][app["owner"]]["email"], "ada@x.dev")
        self.assertAlmostEqual(app["owner_share"], 0.667, places=2)
        self.assertEqual(app["bus_factor"], 1)

    def test_uncommitted_file_keeps_null_dates(self):
        new = self.bs[2]
        self.assertEqual(new["commits"], 0)
        self.assertIsNone(new["first_ts"])
        self.assertIsNone(new["stale_days"])

    def test_authors_sorted_desc(self):
        counts = [a["commits"] for a in self.git["authors"]]
        self.assertEqual(counts, sorted(counts, reverse=True))


class TestSnapshots(unittest.TestCase):
    def test_too_short_history_returns_none(self):
        self.assertIsNone(compute_snapshots(history(), buildings()))

    def test_deltas_are_sparse_and_ordered(self):
        # Pad to clear the MIN_COMMITS floor.
        h = history()
        for i in range(10):
            h.append(commit(f"p{i}", (150 + i * 5) * DAY, "ada@x.dev",
                            [("app.py", 3, 1, False)]))
        bs = buildings() + [{"path": "gone.py", "loc": 60, "sloc": 60,
                             "complexity": 3, "deleted": True}]
        snap = compute_snapshots(h, bs, 2.6, 12)
        self.assertIsNotNone(snap)
        self.assertEqual(len(snap["delta"]), 12)
        self.assertEqual(snap["ts"], sorted(snap["ts"]))

        born = [i for d in snap["delta"] for i in d["born"]]
        died = [i for d in snap["delta"] for i in d["died"]]
        self.assertEqual(len(born), len(set(born)), "a file is born once")
        gone = next(i for i, b in enumerate(bs) if b["path"] == "gone.py")
        self.assertIn(gone, born)
        self.assertIn(gone, died)

        # Sparse: far fewer height entries than buildings x snapshots.
        entries = sum(len(d["h"]) for d in snap["delta"])
        self.assertLess(entries, len(bs) * 12)

        # File counts never go negative and the last one is sane.
        for st in snap["stats"]:
            self.assertGreaterEqual(st["files"], 0)
            self.assertGreaterEqual(st["loc"], 0)


if __name__ == "__main__":
    unittest.main()
