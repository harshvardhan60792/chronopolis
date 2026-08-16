"""Git history mining for Chronopolis.

Split into three pieces on purpose:

  read_history()   one `git log` pass -> a list of commit records
  apply_history()  commit records -> per-building churn/authors/dates
  mine_git_history() the original one-shot convenience wrapper

The split exists because the time machine (T11) needs the raw records *before*
the building list is final: files that were deleted during the repo's history
have to become buildings too (they render as ruins), and that decision can only
be made after reading the log. Running `git log` twice on a large repo is
minutes of wasted work.
"""

from __future__ import annotations

import subprocess

REC = "\x01"
SEP = "\x1f"


def _rev_parse(root: str) -> bool:
    try:
        head = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return head.returncode == 0


def repo_prefix(root: str) -> str:
    """Where `root` sits inside its repository, e.g. 'packages/api/'.

    Analysing a subdirectory of a repo is a normal thing to do (monorepos, or
    a fixture folder inside a tool's own checkout). Without this, `git log`
    happily returns the entire repository's history with repo-root-relative
    paths, which produces wrong churn and phantom deleted files that never
    belonged to the target at all.
    """
    try:
        out = subprocess.run(["git", "-C", root, "rev-parse", "--show-prefix"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def last_commit_ts(root: str) -> int:
    """The repo's own clock. Used instead of wall time so that 'days since'
    figures - and therefore screenshots - are reproducible."""
    try:
        out = subprocess.run(["git", "-C", root, "log", "-1", "--format=%at"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return 0
    s = out.stdout.strip()
    return int(s) if out.returncode == 0 and s.isdigit() else 0


def _clean_rename(path: str) -> tuple[str, bool]:
    """`a/{old => new}/f.py` and `old.py => new.py` both mean: use the new name."""
    if " => " not in path:
        return path, False
    if "{" in path and "}" in path:
        pre, rest = path.split("{", 1)
        mid, post = rest.split("}", 1)
        path = pre + mid.split(" => ")[-1] + post
    else:
        path = path.split(" => ")[-1]
    return path.strip().replace("//", "/"), True


def read_history(root: str, max_commits: int | None = None,
                 since: str | None = None,
                 max_commit_files: int = 60,
                 rev: str | None = None) -> tuple[list[dict] | None, dict]:
    """Stream `git log --numstat` into commit records, oldest first.

    Each record: {sha, ts, name, email, files: [(path, adds, dels, renamed)],
                  bulk: bool}
    `bulk` marks commits touching more than `max_commit_files` files - merges,
    mass renames, vendored drops. Their churn still counts; their file pairs do
    not, because a 400-file commit couples everything to everything.
    """
    if not _rev_parse(root):
        return None, {}

    prefix = repo_prefix(root)
    cmd = ["git", "-C", root, "log", "--no-merges", "--date=unix",
           f"--format={REC}%H{SEP}%at{SEP}%an{SEP}%ae", "--numstat"]
    if rev is not None:
        cmd.append(rev)
    if max_commits is not None:
        cmd += ["-n", str(max_commits)]
    if since is not None:
        cmd += ["--since", since]
    if prefix:
        cmd += ["--", "."]      # only history that touches this subdirectory

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None, {}
    if proc.stdout is None:
        return None, {}

    history: list[dict] = []
    current: dict | None = None
    skipped_bulk = 0

    def close(rec: dict | None) -> None:
        nonlocal skipped_bulk
        if rec is None or not rec["files"]:
            return
        if len(rec["files"]) > max_commit_files:
            rec["bulk"] = True
            skipped_bulk += 1
        history.append(rec)

    for line in proc.stdout:
        line = line.rstrip("\n")
        if not line:
            continue
        if line.startswith(REC):
            close(current)
            parts = line[1:].split(SEP)
            if len(parts) < 4:
                current = None
                continue
            current = {
                "sha": parts[0],
                "ts": int(parts[1]) if parts[1].isdigit() else 0,
                "name": parts[2].strip(),
                "email": parts[3].strip().lower(),
                "files": [],
                "bulk": False,
            }
        elif current is not None:
            cols = line.split("\t", 2)
            if len(cols) != 3:
                continue
            adds_s, dels_s, path = cols
            path, renamed = _clean_rename(path)
            if prefix:
                # numstat paths are always repo-root relative; the rest of
                # citygen works in paths relative to the analysed directory.
                if not path.startswith(prefix):
                    continue
                path = path[len(prefix):]
            adds = 0 if adds_s == "-" else int(adds_s or 0)
            dels = 0 if dels_s == "-" else int(dels_s or 0)
            current["files"].append((path, adds, dels, renamed))

    close(current)
    proc.wait()
    if proc.returncode != 0:
        return None, {}

    history.reverse()   # oldest first: everything downstream replays forward

    meta = {
        "commit_count": len(history),
        "first_commit_ts": history[0]["ts"] if history else None,
        "last_commit_ts": history[-1]["ts"] if history else None,
        "skipped_bulk_commits": skipped_bulk,
        "truncated": max_commits is not None or since is not None,
        "max_commit_files": max_commit_files,
    }
    meta["window_days"] = (
        int((meta["last_commit_ts"] - meta["first_commit_ts"]) / 86400)
        if history else 0
    )
    return history, meta


def reconstruct_timeline(history: list[dict]) -> dict[str, dict]:
    """Replay numstat to recover each path's life story without checkouts.

    Returns {path: {born, died, max_loc, final_loc}}. LOC is approximate by
    construction (adds - dels accumulated); it is the cost of not checking out
    N historical trees, and the UI says so.
    """
    state: dict[str, dict] = {}
    for c in history:
        for path, adds, dels, _renamed in c["files"]:
            rec = state.get(path)
            if rec is None:
                rec = state[path] = {"born": c["ts"], "died": None,
                                     "loc": 0, "max_loc": 0, "final_loc": 0}
            if rec["died"] is not None:
                rec["died"] = None          # resurrected
                rec["loc"] = 0
            rec["loc"] = max(0, rec["loc"] + adds - dels)
            rec["max_loc"] = max(rec["max_loc"], rec["loc"])
            # A pure-deletion edit that empties the file is a deletion.
            if rec["loc"] == 0 and dels > 0 and adds == 0:
                rec["died"] = c["ts"]
    for rec in state.values():
        rec["final_loc"] = rec["loc"]
        rec.pop("loc", None)
    return state


def apply_history(buildings: list[dict], history: list[dict],
                  now_ts: int, meta: dict) -> dict:
    """Write per-building git fields and return the document's `git` section."""
    by_path = {b["path"]: b for b in buildings}
    stats: dict[str, dict] = {}
    author_names: dict[str, dict[str, int]] = {}
    renames_dropped = 0
    untracked_paths = 0

    for c in history:
        email = c["email"]
        names = author_names.setdefault(email, {})
        names[c["name"]] = names.get(c["name"], 0) + 1
        for path, adds, dels, renamed in c["files"]:
            if path not in by_path:
                if renamed:
                    renames_dropped += 1
                else:
                    untracked_paths += 1
                continue
            fs = stats.get(path)
            if fs is None:
                fs = stats[path] = {"commits": 0, "adds": 0, "dels": 0,
                                    "first_ts": None, "last_ts": None,
                                    "authors": {}}
            fs["commits"] += 1
            fs["adds"] += adds
            fs["dels"] += dels
            ts = c["ts"]
            if fs["first_ts"] is None or ts < fs["first_ts"]:
                fs["first_ts"] = ts
            if fs["last_ts"] is None or ts > fs["last_ts"]:
                fs["last_ts"] = ts
            if email:
                fs["authors"][email] = fs["authors"].get(email, 0) + 1

    totals: dict[str, int] = {}
    for fs in stats.values():
        for email, n in fs["authors"].items():
            totals[email] = totals.get(email, 0) + n

    ordered = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    authors = []
    author_idx = {}
    for i, (email, n) in enumerate(ordered):
        names = author_names.get(email, {})
        display = max(names.items(), key=lambda kv: kv[1])[0] if names else email
        authors.append({"name": display, "email": email, "commits": n})
        author_idx[email] = i

    for b in buildings:
        fs = stats.get(b["path"])
        if not fs or fs["commits"] == 0:
            # Never committed (new/untracked). Null timestamps, so overlays can
            # tell "brand new" from "touched today".
            b.update({"commits": 0, "adds": 0, "dels": 0, "churn": 0,
                      "first_ts": None, "last_ts": None, "authors": [],
                      "owner": None, "owner_share": 0.0, "bus_factor": 0,
                      "age_days": None, "stale_days": None})
            continue
        n = fs["commits"]
        ranked = sorted(fs["authors"].items(), key=lambda kv: (-kv[1], kv[0]))
        bus, cum = 0, 0
        for _email, cnt in ranked:
            bus += 1
            cum += cnt
            if cum > 0.5 * n:
                break
        b.update({
            "commits": n,
            "adds": fs["adds"],
            "dels": fs["dels"],
            "churn": fs["adds"] + fs["dels"],
            "first_ts": fs["first_ts"],
            "last_ts": fs["last_ts"],
            "authors": [[author_idx[e], c] for e, c in ranked],
            "owner": author_idx[ranked[0][0]],
            "owner_share": round(ranked[0][1] / n, 3),
            "bus_factor": bus,
            "age_days": int((now_ts - fs["first_ts"]) / 86400) if fs["first_ts"] else 0,
            "stale_days": int((now_ts - fs["last_ts"]) / 86400) if fs["last_ts"] else 0,
        })

    git = dict(meta)
    git["authors"] = authors
    git["renames_dropped"] = renames_dropped
    git["untracked_paths"] = untracked_paths
    return git


def mine_git_history(root: str, buildings: list[dict],
                     max_commits: int | None = None, since: str | None = None,
                     max_commit_files: int = 60) -> tuple[dict | None, list[list[int]]]:
    """One-shot convenience wrapper: read, apply, and return commit index lists
    for the coupling pass. `build.py` uses the granular API instead."""
    history, meta = read_history(root, max_commits, since, max_commit_files)
    if history is None:
        return None, []
    git = apply_history(buildings, history, last_commit_ts(root), meta)
    idx_of = {b["path"]: i for i, b in enumerate(buildings)}
    commits = []
    for c in history:
        if c["bulk"]:
            continue
        idxs = sorted({idx_of[p] for p, _a, _d, _r in c["files"] if p in idx_of})
        if idxs:
            commits.append(idxs)
    return git, commits
