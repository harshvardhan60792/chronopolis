import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch, MagicMock
from citygen.research.szz import get_deleted_lines, introducers

class TestSZZ(unittest.TestCase):
    @patch("subprocess.check_output")
    def test_get_deleted_lines(self, mock_check_output):
        mock_check_output.return_value = """--- a/src/app.py
+++ b/src/app.py
@@ -10,3 +10,4 @@
@@ -20 +21,2 @@
@@ -30,0 +31,2 @@
--- /dev/null
+++ b/src/new.py
@@ -0,0 +1,5 @@
--- a/src/gone.py
+++ /dev/null
@@ -1,5 +0,0 @@
"""
        deleted = get_deleted_lines("dummy", "abc1234")
        self.assertIn("src/app.py", deleted)
        self.assertEqual(deleted["src/app.py"], [(10, 12), (20, 20)])
        
        self.assertNotIn("src/new.py", deleted)
        
        self.assertIn("src/gone.py", deleted)
        self.assertEqual(deleted["src/gone.py"], [(1, 5)])

    @patch("subprocess.check_output")
    def test_introducers(self, mock_check_output):
        mock_check_output.return_value = """deadbeef00000000000000000000000000000000 10 10
author info
summary info
line content
cafebabe00000000000000000000000000000000 11 11
author info
"""
        shas = introducers("dummy", "fix123", "src/app.py", [(10, 12)])
        self.assertEqual(shas, {"deadbeef00000000000000000000000000000000", "cafebabe00000000000000000000000000000000"})

    @patch("subprocess.check_output")
    def test_introducers_no_ranges(self, mock_check_output):
        shas = introducers("dummy", "fix123", "src/app.py", [])
        self.assertEqual(shas, set())
        mock_check_output.assert_not_called()

if __name__ == "__main__":
    unittest.main()
