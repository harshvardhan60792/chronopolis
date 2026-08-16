import json
import os
import shutil

CACHE_FORMAT_VERSION = "1"

class Cache:
    def __init__(self, root: str, cache_dir: str | None = None, enabled: bool = True):
        self.root = root
        self.enabled = enabled
        if cache_dir:
            self.base_dir = os.path.abspath(cache_dir)
        else:
            self.base_dir = os.path.join(os.path.abspath(root), ".citygen", "cache")
        self.v_dir = os.path.join(self.base_dir, f"v{CACHE_FORMAT_VERSION}")

        if self.enabled:
            os.makedirs(os.path.join(self.v_dir, "git"), exist_ok=True)
            self._ensure_gitignore()

    def _ensure_gitignore(self) -> None:
        if self.base_dir.endswith(os.path.join(".citygen", "cache")):
            cg_dir = os.path.dirname(self.base_dir)
            gitignore = os.path.join(cg_dir, ".gitignore")
            if not os.path.exists(gitignore):
                try:
                    with open(gitignore, "w", encoding="utf-8") as f:
                        f.write("*\n")
                except OSError:
                    pass
                print("note: created .citygen/ cache directory. You might want to add .citygen/ to your project's .gitignore.")

    def get_git(self, key: str) -> dict | None:
        if not self.enabled:
            return None
        path = os.path.join(self.v_dir, "git", f"{key}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def put_git(self, key: str, record: dict) -> None:
        if not self.enabled:
            return
        path = os.path.join(self.v_dir, "git", f"{key}.json")
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(record, f, separators=(",", ":"))
            os.replace(tmp_path, path)
        except OSError:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except OSError:
                pass

    def git_key(self, head_sha: str, max_commits: int | None, since: str | None, max_commit_files: int) -> str:
        parts = [head_sha]
        if max_commits is not None:
            parts.append(f"mc{max_commits}")
        if since is not None:
            import hashlib
            hashed_since = hashlib.md5(since.encode('utf-8')).hexdigest()[:12]
            parts.append(f"s{hashed_since}")
        parts.append(f"mf{max_commit_files}")
        return "-".join(parts)

    def stats(self) -> dict:
        git_dir = os.path.join(self.v_dir, "git")
        count = 0
        size_bytes = 0
        if os.path.exists(git_dir):
            for name in os.listdir(git_dir):
                if name.endswith(".json"):
                    p = os.path.join(git_dir, name)
                    try:
                        size_bytes += os.path.getsize(p)
                        count += 1
                    except OSError:
                        pass
        return {
            "git_entries": count,
            "git_bytes": size_bytes,
        }

    def clear(self) -> None:
        if os.path.exists(self.v_dir):
            try:
                shutil.rmtree(self.v_dir)
            except OSError:
                pass
