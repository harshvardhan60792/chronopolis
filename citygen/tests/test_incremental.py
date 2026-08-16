import json
import os
import random
import subprocess
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from citygen.build import build_city
from citygen.cli import _load

import re
from citygen.cli import main as cli_main

def run_cli_build(repo, incremental=False, force_full=False, out="out.json"):
    args = ["build", repo, "-o", out]
    if incremental:
        args.append("--incremental")
    if force_full:
        args.append("--force-full")
    assert cli_main(args) == 0

def assert_byte_identical(file1: str, file2: str):
    with open(file1, "r", encoding="utf-8") as f1, open(file2, "r", encoding="utf-8") as f2:
        s1 = f1.read()
        s2 = f2.read()
    
    # Strip non-deterministic fields using exact regex
    s1 = re.sub(r'"generated_at":\s*"[^"]*",?', '', s1)
    s1 = re.sub(r'"build_seconds":\s*[\d.]+,?', '', s1)
    s2 = re.sub(r'"generated_at":\s*"[^"]*",?', '', s2)
    s2 = re.sub(r'"build_seconds":\s*[\d.]+,?', '', s2)
    
    assert s1 == s2, "incremental output differs from full output!"

def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

def write_file(repo, path, text):
    with open(os.path.join(repo, path), "w", encoding="utf-8") as f:
        f.write(text)

@pytest.fixture
def repo():
    with tempfile.TemporaryDirectory() as d:
        git("init", cwd=d)
        git("config", "user.email", "test@example.com", cwd=d)
        git("config", "user.name", "Test User", cwd=d)
        
        write_file(d, "main.py", "print('hello')\n")
        git("add", "main.py", cwd=d)
        git("commit", "-m", "initial", cwd=d)
        
        yield d

@pytest.fixture
def outdir():
    with tempfile.TemporaryDirectory() as d:
        yield d

def test_incremental_rebase_fallback(repo, outdir):
    # Base build
    run_cli_build(repo, incremental=False, out=os.path.join(outdir, "out_base.json"))
    
    # Amend the commit
    write_file(repo, "main.py", "print('hello2')\n")
    git("add", "main.py", cwd=repo)
    git("commit", "--amend", "--no-edit", cwd=repo)
    
    # Incremental should fallback cleanly
    f_inc = os.path.join(outdir, "out_inc.json")
    run_cli_build(repo, incremental=True, out=f_inc)
    
    # And it should be identical to a cold build
    f_full = os.path.join(outdir, "out_full.json")
    run_cli_build(repo, force_full=True, out=f_full)
    assert_byte_identical(f_inc, f_full)


def test_fuzz_incremental(repo, outdir):
    # Perform random mutations and check invariants
    
    mutations = [
        lambda cwd: write_file(cwd, "file.py", f"x = {random.randint(1,100)}\n"),
        lambda cwd: (git("add", ".", cwd=cwd), git("commit", "-m", "update", cwd=cwd)),
        lambda cwd: (write_file(cwd, "main.py", "print('mutated')\n"), git("add", "main.py", cwd=cwd), git("commit", "--amend", "--no-edit", cwd=cwd)),
        lambda cwd: write_file(cwd, "new.py", "def a(): pass\n"),
        lambda cwd: (git("add", "new.py", cwd=cwd), git("commit", "-m", "new file", cwd=cwd)),
    ]
    
    random.seed(42)
    
    for i in range(10):
        # 1. apply mutation
        mut = random.choice(mutations)
        try:
            mut(repo)
        except subprocess.CalledProcessError:
            pass
            
        # 2. build incremental
        f_inc = os.path.join(outdir, f"out_inc_{i}.json")
        run_cli_build(repo, incremental=True, out=f_inc)
        
        # 3. build full
        f_full = os.path.join(outdir, f"out_full_{i}.json")
        run_cli_build(repo, force_full=True, out=f_full)
        
        # 4. assert identical
        assert_byte_identical(f_inc, f_full)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
