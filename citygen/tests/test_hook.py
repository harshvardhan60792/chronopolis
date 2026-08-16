import os
import json
import subprocess
import stat
import time
from tempfile import TemporaryDirectory
import pytest

from citygen.hook import install, uninstall, run_hook, MARKER
from citygen import risk

def setup_git_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    
def write_file(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def get_hook_path(repo):
    return os.path.join(repo, ".git", "hooks", "pre-commit")

def test_install_creates_executable_hook():
    with TemporaryDirectory() as d:
        setup_git_repo(d)
        res = install(d, "out/city.json", False, risk.HIGH_THRESHOLD)
        assert res == 0
        
        hook = get_hook_path(d)
        assert os.path.exists(hook)
        
        # Check executable (skip on Windows)
        if os.name != "nt":
            st = os.stat(hook)
            assert bool(st.st_mode & stat.S_IEXEC)
        
        with open(hook, "r") as f:
            content = f.read()
        assert MARKER in content
        assert "python -m citygen hook run --city" in content
        assert "|| exit 0" in content

def test_install_refuses_foreign_hook_and_leaves_bytes_untouched():
    with TemporaryDirectory() as d:
        setup_git_repo(d)
        hook = get_hook_path(d)
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        foreign = "#!/bin/sh\necho 'foreign'\n"
        with open(hook, "wb") as f:
            f.write(foreign.encode("utf-8"))
            
        res = install(d, "out/city.json", False, risk.HIGH_THRESHOLD)
        assert res == 2
        
        with open(hook, "rb") as f:
            assert f.read() == foreign.encode("utf-8")

def test_force_backs_up_before_overwrite():
    with TemporaryDirectory() as d:
        setup_git_repo(d)
        hook = get_hook_path(d)
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        foreign = "#!/bin/sh\necho 'foreign'\n"
        with open(hook, "w") as f:
            f.write(foreign)
            
        res = install(d, "out/city.json", False, risk.HIGH_THRESHOLD, force=True)
        assert res == 0
        
        with open(hook, "r") as f:
            content = f.read()
            assert MARKER in content
            
        import glob
        baks = glob.glob(f"{hook}.bak-*")
        assert len(baks) == 1
        with open(baks[0], "r") as f:
            assert f.read() == foreign

def test_uninstall_refuses_foreign_hook():
    with TemporaryDirectory() as d:
        setup_git_repo(d)
        hook = get_hook_path(d)
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        foreign = "#!/bin/sh\necho 'foreign'\n"
        with open(hook, "w") as f:
            f.write(foreign)
            
        res = uninstall(d)
        assert res == 2
        
        with open(hook, "r") as f:
            assert f.read() == foreign

def test_run_silent_when_nothing_staged(capsys):
    with TemporaryDirectory() as d:
        setup_git_repo(d)
        city_path = os.path.join(d, "city.json")
        write_file(city_path, json.dumps({
            "repo": {"path": d, "head": "abc"},
            "buildings": [], "edges": {"import": []}, "git": {}
        }))
        
        res = run_hook(city_path, False, risk.HIGH_THRESHOLD)
        assert res == 0
        captured = capsys.readouterr()
        assert captured.out == ""

def test_run_exit_zero_by_default_on_trip(capsys, monkeypatch):
    with TemporaryDirectory() as d:
        setup_git_repo(d)
        city_path = os.path.join(d, "city.json")
        write_file(city_path, json.dumps({
            "repo": {"path": d, "head": "abc"},
            "buildings": [
                {
                    "path": "high_risk.py",
                    "lang": "python",
                    "churn": 100,
                    "complexity": 50,
                    "bus_factor": 1,
                    "owner_share": 1.0
                }
            ],
            "edges": {"import": []}, 
            "git": {"authors": [{"name": "Test", "email": "test@example.com"}]}
        }))
        
        write_file(os.path.join(d, "high_risk.py"), "print('hello')")
        subprocess.run(["git", "add", "high_risk.py"], cwd=d, check=True)
        
        # Mock subprocess to avoid real rev-parse head failing since we don't have commits
        original_run = subprocess.run
        def mock_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and "HEAD" in cmd:
                return subprocess.CompletedProcess(cmd, 0, "abc\n", "")
            return original_run(cmd, *args, **kwargs)
        monkeypatch.setattr(subprocess, "run", mock_run)
        
        cwd = os.getcwd()
        try:
            os.chdir(d)
            res = run_hook(city_path, False, 0.0)
        finally:
            os.chdir(cwd)
            
        assert res == 0
        captured = capsys.readouterr()
        assert "high-risk" in captured.out
        assert "warning only" in captured.out

def test_run_exit_one_with_block(capsys, monkeypatch):
    with TemporaryDirectory() as d:
        setup_git_repo(d)
        city_path = os.path.join(d, "city.json")
        write_file(city_path, json.dumps({
            "repo": {"path": d, "head": "abc"},
            "buildings": [
                {
                    "path": "high_risk.py",
                    "lang": "python",
                    "churn": 100,
                    "complexity": 50,
                    "bus_factor": 1,
                    "owner_share": 1.0,
                    "stale_days": 100,
                }
            ],
            "edges": {"import": []}, 
            "git": {"authors": [{"name": "Test", "email": "test@example.com"}]}
        }))
        
        write_file(os.path.join(d, "high_risk.py"), "print('hello')")
        subprocess.run(["git", "add", "high_risk.py"], cwd=d, check=True)
        
        # Monkeypatch HEAD check so it doesn't fail on empty repo
        original_run = subprocess.run
        def mock_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and "HEAD" in cmd:
                return subprocess.CompletedProcess(cmd, 0, "abc\n", "")
            return original_run(cmd, *args, **kwargs)
        monkeypatch.setattr(subprocess, "run", mock_run)
        
        cwd = os.getcwd()
        try:
            os.chdir(d)
            res = run_hook(city_path, True, 0.0) # threshold 0.0 to guarantee trip
        finally:
            os.chdir(cwd)
            
        assert res == 1
        captured = capsys.readouterr()
        assert "high-risk" in captured.out
        assert "warning only" not in captured.out

def test_subdirectory_invocation_resolves_repo_root(capsys):
    with TemporaryDirectory() as d:
        setup_git_repo(d)
        subdir = os.path.join(d, "sub", "dir")
        os.makedirs(subdir)
        
        os.makedirs(os.path.join(d, "out"), exist_ok=True)
        city_path = "out/city.json"
        write_file(os.path.join(d, "out", "city.json"), json.dumps({
            "repo": {"path": d, "head": "abc"},
            "buildings": [],
            "edges": {"import": []}, 
            "git": {}
        }))
        
        # Run from subdir
        cwd = os.getcwd()
        try:
            os.chdir(subdir)
            res = run_hook(city_path, False, risk.HIGH_THRESHOLD)
            assert res == 0
        finally:
            os.chdir(cwd)

def test_missing_city_hint_is_rate_limited(capsys, monkeypatch):
    with TemporaryDirectory() as d:
        setup_git_repo(d)
        cwd = os.getcwd()
        try:
            os.chdir(d)
            
            # First run: should print hint
            res = run_hook("does_not_exist.json", False, risk.HIGH_THRESHOLD)
            assert res == 0
            captured = capsys.readouterr()
            assert "city.json is missing" in captured.out
            
            # Second run: should be silent
            res = run_hook("does_not_exist.json", False, risk.HIGH_THRESHOLD)
            assert res == 0
            captured = capsys.readouterr()
            assert captured.out == ""
        finally:
            os.chdir(cwd)
