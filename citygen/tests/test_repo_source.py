import os
import shutil
import subprocess
import tempfile

from citygen.cli import _resolve_repo_source


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_resolve_local_directory_passthrough():
    with tempfile.TemporaryDirectory() as d:
        path, tmp = _resolve_repo_source(d)
        assert path == d
        assert tmp is None


def test_resolve_zip_with_nested_root_dir():
    # e.g. GitHub's own "Download ZIP" nests everything under reponame-branch/
    with tempfile.TemporaryDirectory() as contents, tempfile.TemporaryDirectory() as outdir:
        src = os.path.join(contents, "myrepo-main")
        os.makedirs(src)
        with open(os.path.join(src, "a.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        zip_base = os.path.join(outdir, "archive")
        shutil.make_archive(zip_base, "zip", contents)

        path, tmp = _resolve_repo_source(zip_base + ".zip")
        try:
            assert os.path.isdir(path)
            assert os.path.basename(path) == "myrepo-main"
            assert os.path.isfile(os.path.join(path, "a.py"))
        finally:
            if tmp is not None:
                tmp.cleanup()


def test_resolve_zip_with_flat_root():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "flat")
        os.makedirs(src)
        with open(os.path.join(src, "a.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        zip_base = os.path.join(work, "archive")
        shutil.make_archive(zip_base, "zip", src)

        path, tmp = _resolve_repo_source(zip_base + ".zip")
        try:
            assert os.path.isfile(os.path.join(path, "a.py"))
        finally:
            if tmp is not None:
                tmp.cleanup()


def test_resolve_git_url_clones(tmp_path=None):
    # Clone from a local git repo using an explicit URL scheme so the
    # git-URL branch (not the plain-local-directory branch) is exercised,
    # without depending on network access.
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as work:
        git("init", "-q", cwd=src_dir)
        git("config", "user.email", "t@example.com", cwd=src_dir)
        git("config", "user.name", "T", cwd=src_dir)
        with open(os.path.join(src_dir, "a.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        git("add", "-A", cwd=src_dir)
        git("commit", "-q", "-m", "init", cwd=src_dir)

        url = "file:///" + src_dir.replace(os.sep, "/")
        path, tmp = _resolve_repo_source(url)
        try:
            assert os.path.isdir(os.path.join(path, ".git"))
            assert os.path.isfile(os.path.join(path, "a.py"))
        finally:
            if tmp is not None:
                tmp.cleanup()
