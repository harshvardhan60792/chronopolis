from __future__ import annotations
import subprocess
from .gitmine import read_history

def extend_history(cached: dict, root: str, cached_head: str) -> dict | None:
    """Mine only `<cached_head>..HEAD` and prepend to the cached commit list.

    Returns None (caller falls back to a full mine) when:
      - cached_head is not an ancestor of HEAD (rebase, force-push, amend)
      - `git merge-base --is-ancestor` fails or git errors
      - the cached history was truncated by --max-commits (extending a
        truncated window produces a wrong window)
    """
    meta = cached.get("meta", {})
    if meta.get("truncated", False):
        return None
    
    try:
        proc = subprocess.run(
            ["git", "-C", root, "merge-base", "--is-ancestor", cached_head, "HEAD"],
            capture_output=True, timeout=10
        )
        if proc.returncode != 0:
            return None
    except (OSError, subprocess.SubprocessError):
        return None

    max_commit_files = meta.get("max_commit_files", 60)
    
    rev = f"{cached_head}..HEAD"
    new_history, new_meta = read_history(
        root=root,
        max_commits=None,
        since=None,
        max_commit_files=max_commit_files,
        rev=rev
    )
    
    if new_history is None:
        return None
        
    if not new_history:
        return cached

    old_history = cached.get("history", [])
    merged_history = old_history + new_history
    
    merged_meta = {
        "commit_count": len(merged_history),
        "first_commit_ts": merged_history[0]["ts"] if merged_history else None,
        "last_commit_ts": merged_history[-1]["ts"] if merged_history else None,
        "skipped_bulk_commits": meta.get("skipped_bulk_commits", 0) + new_meta.get("skipped_bulk_commits", 0),
        "truncated": False,
        "max_commit_files": max_commit_files,
    }
    if merged_history and merged_meta["first_commit_ts"] is not None and merged_meta["last_commit_ts"] is not None:
        merged_meta["window_days"] = int((merged_meta["last_commit_ts"] - merged_meta["first_commit_ts"]) / 86400)
    else:
        merged_meta["window_days"] = 0
    
    return {
        "history": merged_history,
        "meta": merged_meta
    }
