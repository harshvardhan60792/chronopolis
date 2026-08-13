"""Tests for co-change coupling."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from citygen.coupling import calculate_cochange  # noqa: E402

class TestCoupling(unittest.TestCase):
    def test_calculate_cochange(self):
        buildings = [
            {"path": "a.py", "commits": 10, "parsed": True},
            {"path": "b.py", "commits": 8, "parsed": True},
            {"path": "c.py", "commits": 5, "parsed": True},
        ]
        
        commits = [
            [0, 1], [0, 1], [0, 1], [0, 1], 
            [0, 2],                         
        ]
        
        import_edges = [[0, 1, 1]]
        
        cochange_edges, cochange_pairs, hidden_coupling, top_hidden = calculate_cochange(commits, buildings, import_edges, min_cochange=3)
        
        self.assertEqual(cochange_pairs, 1)
        self.assertEqual(len(cochange_edges), 1)
        self.assertEqual(hidden_coupling, 0)
        self.assertEqual(len(top_hidden), 0)
        
        edge = cochange_edges[0]
        self.assertEqual(edge[0], 0)
        self.assertEqual(edge[1], 1)
        self.assertEqual(edge[2], 4)
        self.assertAlmostEqual(edge[3], 0.286, places=3)
        
        # a<->c co-changed once: strength 1 / (10 + 5 - 1) = 0.071, below the
        # 0.12 floor, so lowering min_cochange must not admit it.
        _e, pairs, _h, _t = calculate_cochange(commits, buildings, import_edges,
                                               min_cochange=1)
        self.assertEqual(pairs, 1)

    def test_hidden_coupling_needs_parsed_files(self):
        buildings = [
            {"path": "a.py", "commits": 4, "parsed": True},
            {"path": "b.py", "commits": 4, "parsed": True},
        ]
        commits = [[0, 1], [0, 1], [0, 1]] # 3 co-changes. strength = 3 / (4 + 4 - 3) = 3/5 = 0.6 > 0.12
        import_edges = []
        
        cochange_edges, cochange_pairs, hidden_coupling, top_hidden = calculate_cochange(commits, buildings, import_edges, min_cochange=2)
        
        self.assertEqual(cochange_pairs, 1)
        self.assertEqual(hidden_coupling, 1)
        self.assertEqual(top_hidden[0][0], 0)
        self.assertEqual(top_hidden[0][1], 1)
        self.assertAlmostEqual(top_hidden[0][2], 0.6, places=3)

        # Same pair, but the files were never parsed for imports (e.g. two
        # JSON templates): co-change still counts, hidden coupling must not.
        unparsed = [dict(b, parsed=None) for b in buildings]
        _e, pairs, hidden, top = calculate_cochange(commits, unparsed,
                                                    import_edges, min_cochange=2)
        self.assertEqual(pairs, 1)
        self.assertEqual(hidden, 0)
        self.assertEqual(top, [])

if __name__ == "__main__":
    unittest.main()
