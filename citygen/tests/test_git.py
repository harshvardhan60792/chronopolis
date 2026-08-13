"""Tests for git history mining."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from citygen.gitmine import mine_git_history  # noqa: E402

class TestGitMine(unittest.TestCase):
    @patch('subprocess.Popen')
    @patch('subprocess.run')
    def test_mine_git_history(self, mock_run, mock_popen):
        mock_run.side_effect = [
            MagicMock(returncode=0), # rev-parse HEAD
            MagicMock(returncode=0, stdout="1600000000\n") # log -1
        ]
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = [
            "\x01abcdef123\x1f1500000000\x1fAlice\x1falice@example.com",
            "10\t5\tfile1.py",
            "-\t-\tfile2.py", # binary or no churn
            "\x01abcdef124\x1f1400000000\x1fBob\x1fbob@example.com",
            "5\t5\tfile3.py => file1.py", # rename
        ]
        mock_popen.return_value = mock_proc
        
        buildings = [
            {"path": "file1.py"},
            {"path": "file2.py"}
        ]
        
        res, commits = mine_git_history("dummy", buildings)
        
        self.assertIsNotNone(res)
        self.assertEqual(len(res["authors"]), 2)
        
        b1 = buildings[0]
        self.assertEqual(b1["commits"], 2)
        self.assertEqual(b1["adds"], 15)
        self.assertEqual(b1["dels"], 10)
        self.assertEqual(b1["churn"], 25)
        
        b2 = buildings[1]
        self.assertEqual(b2["commits"], 1)

if __name__ == "__main__":
    unittest.main()
