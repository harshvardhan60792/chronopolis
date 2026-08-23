import os
import subprocess
import tempfile

from citygen.build import build_city


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def write_file(repo, path, text):
    with open(os.path.join(repo, path), "w", encoding="utf-8") as f:
        f.write(text)


def test_python_call_edges_resolve_across_files():
    # Regression test: PyResult previously had no def_names field, so
    # build.py's `hasattr(pr, "def_names")` was always False and every
    # Python file contributed zero definitions to the call-graph resolver -
    # cross-file Python calls never resolved to a call edge.
    with tempfile.TemporaryDirectory() as repo:
        git("init", cwd=repo)
        git("config", "user.email", "t@example.com", cwd=repo)
        git("config", "user.name", "T", cwd=repo)
        write_file(repo, "a.py", "def process():\n    pass\n")
        write_file(repo, "b.py", "from a import process\n\ndef main():\n    process()\n")
        git("add", "-A", cwd=repo)
        git("commit", "-m", "init", cwd=repo)

        city = build_city(repo)
        paths = [b["path"] for b in city["buildings"]]
        a_idx = paths.index("a.py")
        b_idx = paths.index("b.py")

        call_edges = city.get("edges", {}).get("call", [])
        assert [b_idx, a_idx] in [[src, dst] for src, dst, *_ in call_edges], (
            f"expected a call edge b.py -> a.py, got {call_edges}"
        )
