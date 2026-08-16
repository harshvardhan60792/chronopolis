import json
import os
import shutil
import tempfile
import pytest

from citygen.cache import Cache, CACHE_FORMAT_VERSION
from citygen.cli import main

def test_cache_init(tmp_path):
    # default base dir
    c = Cache(str(tmp_path))
    assert c.base_dir == os.path.join(str(tmp_path), ".citygen", "cache")
    assert c.v_dir == os.path.join(c.base_dir, f"v{CACHE_FORMAT_VERSION}")
    assert os.path.exists(os.path.join(c.v_dir, "git"))

    # custom base dir
    c2_dir = tmp_path / "custom"
    c2 = Cache(str(tmp_path), str(c2_dir))
    assert c2.base_dir == str(c2_dir)
    assert c2.v_dir == os.path.join(str(c2_dir), f"v{CACHE_FORMAT_VERSION}")
    assert os.path.exists(os.path.join(c2.v_dir, "git"))

def test_cache_gitignore_created(tmp_path):
    c = Cache(str(tmp_path))
    gi = tmp_path / ".citygen" / ".gitignore"
    assert gi.exists()
    assert gi.read_text() == "*\n"

    # Don't recreate if exists
    gi.write_text("dummy\n")
    c = Cache(str(tmp_path))
    assert gi.read_text() == "dummy\n"

def test_cache_put_get(tmp_path):
    c = Cache(str(tmp_path))
    
    key = c.git_key("abcdef123", 100, None, 60)
    assert key == "abcdef123-mc100-mf60"

    assert c.get_git(key) is None

    data = {"history": [{"id": "abc"}], "meta": {"foo": "bar"}}
    c.put_git(key, data)

    res = c.get_git(key)
    assert res == data

def test_cache_disabled(tmp_path):
    c = Cache(str(tmp_path), enabled=False)
    assert not os.path.exists(c.v_dir)

    key = "test_key"
    c.put_git(key, {"a": 1})
    assert c.get_git(key) is None

def test_cache_stats_and_clear(tmp_path):
    c = Cache(str(tmp_path))
    c.put_git("k1", {"a": 1})
    c.put_git("k2", {"a": 2})

    stats = c.stats()
    assert stats["git_entries"] == 2
    assert stats["git_bytes"] > 0

    c.clear()
    stats2 = c.stats()
    assert stats2["git_entries"] == 0
    assert stats2["git_bytes"] == 0

def test_cache_corrupt_file(tmp_path):
    c = Cache(str(tmp_path))
    key = "corrupt"
    c.put_git(key, {"a": 1})

    # corrupt it manually
    path = os.path.join(c.v_dir, "git", f"{key}.json")
    with open(path, "wb") as f:
        f.write(b"bad")

    assert c.get_git(key) is None
