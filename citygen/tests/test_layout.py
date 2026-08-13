"""Tests for layout engine."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from citygen.layout import generate_layout  # noqa: E402

class TestLayout(unittest.TestCase):
    def test_generate_layout(self):
        buildings = [
            {"path": "a/b/c.py", "dir": "a/b", "loc": 100},
            {"path": "a/b/d.py", "dir": "a/b", "loc": 400},
            {"path": "a/e.py", "dir": "a", "loc": 900},
            {"path": "f.py", "dir": "", "loc": 1600},
        ]
        tree = [
            {"path": "a", "depth": 1, "parent": ""},
            {"path": "a/b", "depth": 2, "parent": "a"},
        ]
        
        layout = generate_layout(buildings, tree, world_size=100.0, street_width=2.0)
        
        self.assertIn("world", layout)
        self.assertIn("districts", layout)
        self.assertIn("plots", layout)
        
        self.assertEqual(len(layout["plots"]), len(buildings))
        
        # Check no overlap
        plots = layout["plots"]
        for i in range(len(plots)):
            for j in range(i + 1, len(plots)):
                pi = plots[i]
                pj = plots[j]
                
                # check intersection
                overlap = not (
                    pi["x"] + pi["w"] <= pj["x"] or
                    pj["x"] + pj["w"] <= pi["x"] or
                    pi["z"] + pi["d"] <= pj["z"] or
                    pj["z"] + pj["d"] <= pi["z"]
                )
                self.assertFalse(overlap, f"Overlap between {i} and {j}: {pi} and {pj}")
                
        # Check inside world
        for p in plots:
            self.assertGreaterEqual(p["x"], 0)
            self.assertGreaterEqual(p["z"], 0)
            self.assertLessEqual(p["x"] + p["w"], 100)
            self.assertLessEqual(p["z"] + p["d"], 100)

if __name__ == "__main__":
    unittest.main()
