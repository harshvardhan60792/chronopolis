import json
import os
import subprocess
import tempfile
import unittest

from citygen.research.evaluate import run_evaluate
from unittest.mock import patch

class TestEvaluate(unittest.TestCase):
    def test_temporal_split(self):
        # Create a tiny git repo
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init"], cwd=d, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=d, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=d, check=True)
            
            with open(os.path.join(d, "file1.py"), "w") as f: f.write("print('1')")
            subprocess.run(["git", "add", "file1.py"], cwd=d, check=True)
            subprocess.run(["git", "commit", "-m", "commit 1"], cwd=d, check=True)
            c1 = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=d, text=True).strip()
            
            with open(os.path.join(d, "file1.py"), "w") as f: f.write("print('2')")
            subprocess.run(["git", "add", "file1.py"], cwd=d, check=True)
            subprocess.run(["git", "commit", "-m", "commit 2"], cwd=d, check=True)
            c2 = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=d, text=True).strip()
            
            # This file only exists in commit 3
            with open(os.path.join(d, "file2.py"), "w") as f: f.write("print('3')")
            subprocess.run(["git", "add", "file2.py"], cwd=d, check=True)
            subprocess.run(["git", "commit", "-m", "commit 3"], cwd=d, check=True)
            c3 = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=d, text=True).strip()
            
            # Labels mock
            labels_json = os.path.join(d, "labels.json")
            with open(labels_json, "w") as f:
                json.dump({
                    "files": {
                        "file1.py": {"introducing_commits": [c3]}
                    }
                }, f)
            
            out_md = os.path.join(d, "out.md")
            
            class Args:
                repo = d
                labels = labels_json
                split = 0.5  # Will pick commit 2 (index 1 out of 3 commits: 0, 1, 2)
                out = out_md
                
            # Intercept build_city to check what it's building
            import citygen.research.evaluate as ev
            orig_build_city = ev.build_city
            
            built_city = None
            def mock_build_city(wt_dir, opts, **kwargs):
                nonlocal built_city
                built_city = orig_build_city(wt_dir, opts, **kwargs)
                return built_city
                
            with patch('citygen.research.evaluate.build_city', side_effect=mock_build_city):
                ev.run_evaluate(Args())
                
            # The city should have been built exactly at commit 2
            # file2.py should NOT exist in the city
            # head should match commit 2
            self.assertIsNotNone(built_city)
            self.assertTrue(built_city["repo"]["head"].startswith(c2[:8]))
            
            files_in_city = [b["path"] for b in built_city["buildings"]]
            self.assertIn("file1.py", files_in_city)
            self.assertNotIn("file2.py", files_in_city)
            
if __name__ == "__main__":
    unittest.main()
