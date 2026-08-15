"""Repository walking and ignore rules.

Deliberately dependency-free: no gitpython, no pathspec. A default deny-list
of directory names covers ~99% of real repositories; `--exclude` adds globs.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field

# Directories never worth rendering as districts. Vendored/generated code
# would otherwise dominate the skyline and lie about the repo's real shape.
DEFAULT_DENY_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    ".venv", "venv", "env", ".env", "virtualenv", "site-packages", ".eggs",
    "node_modules", "bower_components", "vendor", "third_party",
    "dist", "build", "out", ".next", ".nuxt", ".output", "target",
    ".terraform", ".gradle", ".dart_tool", "Pods",
    "graphify-out", "chronopolis-out",
}

DEFAULT_DENY_FILE_GLOBS = (
    "*.min.js", "*.min.css", "*_pb2.py", "*_pb2_grpc.py", "*.pyc",
    "*.lock", "package-lock.json", "yarn.lock", "poetry.lock",
)

# Language table. v1 analyzes Python deeply; other extensions are still walked
# so the city shows the whole repo, but they get metrics-only buildings.
EXT_LANG = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".java": "java", ".go": "go", ".rs": "rust", ".rb": "ruby",
    ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".php": "php", ".kt": "kotlin", ".swift": "swift",
    ".sh": "shell", ".ps1": "powershell",
    ".html": "markup", ".css": "style", ".scss": "style",
    ".json": "data", ".yml": "data", ".yaml": "data", ".toml": "data",
    ".md": "docs", ".rst": "docs", ".txt": "docs",
    ".sql": "sql",
}

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf",
    ".zip", ".gz", ".tar", ".whl", ".exe", ".dll", ".so", ".dylib",
    ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".db", ".sqlite",
}

MAX_FILE_BYTES = 2_000_000  # skip generated monsters; they are not architecture


@dataclass
class WalkOptions:
    include_vendor: bool = False
    exclude: list[str] = field(default_factory=list)   # extra globs (posix paths)
    include: list[str] = field(default_factory=list)   # if set, keep only matches
    max_bytes: int = MAX_FILE_BYTES
    all_languages: bool = True  # False => only files with a known EXT_LANG entry


@dataclass
class FileRec:
    rel: str          # posix-style path relative to repo root
    abs: str
    ext: str
    lang: str | None
    size: int


def _denied(rel: str, opts: WalkOptions) -> bool:
    base = rel.rsplit("/", 1)[-1]
    for pat in DEFAULT_DENY_FILE_GLOBS:
        if fnmatch.fnmatch(base, pat):
            return True
    for pat in opts.exclude:
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(base, pat):
            return True
    if opts.include:
        return not any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(base, p)
                       for p in opts.include)
    return False


def walk_repo(root: str, opts: WalkOptions | None = None) -> list[FileRec]:
    """Return every renderable file under `root`, sorted by path.

    Sorted output matters: the city layout must be deterministic so that two
    runs of citygen on the same commit produce byte-identical geometry.
    """
    opts = opts or WalkOptions()
    root = os.path.abspath(root)
    files: list[FileRec] = []

    for dirpath, dirnames, filenames in os.walk(root):
        if not opts.include_vendor:
            dirnames[:] = [d for d in dirnames if d not in DEFAULT_DENY_DIRS]
        else:
            dirnames[:] = [d for d in dirnames if d != ".git"]
        dirnames.sort()
        for name in sorted(filenames):
            ap = os.path.join(dirpath, name)
            rel = os.path.relpath(ap, root).replace(os.sep, "/")
            ext = os.path.splitext(name)[1].lower()
            if ext in BINARY_EXTS:
                continue
            lang = EXT_LANG.get(ext)
            if lang is None and not opts.all_languages:
                continue
            if _denied(rel, opts):
                continue
            try:
                size = os.path.getsize(ap)
            except OSError:
                continue
            if size > opts.max_bytes or size == 0:
                continue
            files.append(FileRec(rel=rel, abs=ap, ext=ext, lang=lang, size=size))

    files.sort(key=lambda f: f.rel)
    return files


def is_source_path(rel: str) -> bool:
    """Would `walk_repo` have rendered this path, judged from the path alone?

    Used for paths that no longer exist on disk (deleted files recovered from
    git history), where stat and content are unavailable.
    """
    parts = rel.split("/")
    if any(p in DEFAULT_DENY_DIRS for p in parts[:-1]):
        return False
    name = parts[-1]
    for pat in DEFAULT_DENY_FILE_GLOBS:
        if fnmatch.fnmatch(name, pat):
            return False
    ext = os.path.splitext(name)[1].lower()
    if ext in BINARY_EXTS:
        return False
    return ext in EXT_LANG


def read_text(path: str) -> str | None:
    """Read source as text; None if it is not decodable (treat as binary)."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        if b"\x00" in raw[:4096]:
            return None
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return None
