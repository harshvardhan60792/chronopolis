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

def strip_volatile(city: dict) -> dict:
    c = dict(city)
    c.pop("generated_at", None)
    c.pop("build_seconds", None)
    return c

def assert_byte_identical(c1: dict, c2: dict):
    sc1 = strip_volatile(c1)
    sc2 = strip_volatile(c2)
    # Use json dumps to check byte-identical, ignoring dict key order variations by sorting keys
    s1 = json.dumps(sc1, sort_keys=True)
    s2 = json.dumps(sc2, sort_keys=True)
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

def test_incremental_rebase_fallback(repo):
    # Base build
    c_full = build_city(repo, incremental=False)
    
    # Amend the commit
    write_file(repo, "main.py", "print('hello2')\n")
    git("add", "main.py", cwd=repo)
    git("commit", "--amend", "--no-edit", cwd=repo)
    
    # Incremental should fallback cleanly
    c_inc = build_city(repo, incremental=True)
    
    # And it should be identical to a cold build
    c_new_full = build_city(repo, force_full=True)
    assert_byte_identical(c_inc, c_new_full)


def test_fuzz_incremental(repo):
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
        c_inc = build_city(repo, incremental=True)
        
        # 3. build full
        c_full = build_city(repo, force_full=True)
        
        # 4. assert identical
        assert_byte_identical(c_inc, c_full)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
