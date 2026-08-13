"""Git history miner for Chronopolis."""

import subprocess

def mine_git_history(root: str, buildings: list[dict], max_commits: int | None = None, since: str | None = None, max_commit_files: int = 60) -> tuple[dict | None, list[list[int]]]:
    head = subprocess.run(
        ["git", "-C", root, "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10
    )
    if head.returncode != 0:
        return None, []

    now_out = subprocess.run(
        ["git", "-C", root, "log", "-1", "--format=%at"],
        capture_output=True, text=True, timeout=10
    )
    now_ts = int(now_out.stdout.strip()) if now_out.returncode == 0 and now_out.stdout.strip().isdigit() else 0

    cmd = ["git", "-C", root, "log", "--no-merges", "--date=unix", "--format=\x01%H\x1f%at\x1f%an\x1f%ae", "--numstat"]
    if max_commits is not None:
        cmd.extend(["-n", str(max_commits)])
    if since is not None:
        cmd.extend(["--since", since])
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None, []

    if proc.stdout is None:
        return None, []

    b_by_path = {b["path"]: b for b in buildings}
    path_to_idx = {b["path"]: i for i, b in enumerate(buildings)}
    file_stats = {}
    author_names = {}
    skipped_bulk_commits = 0
    renames_dropped = 0      # renamed paths whose new name is not in the city
    untracked_paths = 0      # touched paths that are simply not rendered
    commit_count = 0
    first_commit_ts = None
    last_commit_ts = None

    current_commit_ts = None
    current_commit_email = None
    current_commit_files = []

    valid_commits = []

    def process_commit():
        nonlocal skipped_bulk_commits, renames_dropped, untracked_paths
        nonlocal commit_count, first_commit_ts, last_commit_ts
        if not current_commit_files:
            return

        commit_count += 1
        if current_commit_ts:
            if first_commit_ts is None or current_commit_ts < first_commit_ts:
                first_commit_ts = current_commit_ts
            if last_commit_ts is None or current_commit_ts > last_commit_ts:
                last_commit_ts = current_commit_ts

        if len(current_commit_files) > max_commit_files:
            skipped_bulk_commits += 1

        commit_b_idxs = []
        for path, adds, dels in current_commit_files:
            renamed = " => " in path
            if renamed:
                if "{" in path and "}" in path:
                    pre, rest = path.split("{", 1)
                    mid, post = rest.split("}", 1)
                    right = mid.split(" => ")[-1]
                    path = pre + right + post
                else:
                    path = path.split(" => ")[-1]
                path = path.strip().replace("//", "/")

            if path not in b_by_path:
                # A path can be absent for three reasons: it was renamed away,
                # it was deleted, or it is a file the walker never renders
                # (binary, vendored, too big). Only the first is a data loss
                # worth reporting.
                if renamed:
                    renames_dropped += 1
                else:
                    untracked_paths += 1
                continue

            commit_b_idxs.append(path_to_idx[path])
                
            if path not in file_stats:
                file_stats[path] = {"commits": 0, "adds": 0, "dels": 0, "first_ts": None, "last_ts": None, "authors": {}}
                
            fs = file_stats[path]
            fs["commits"] += 1
            fs["adds"] += adds
            fs["dels"] += dels
            
            ts = current_commit_ts
            if ts is not None:
                if fs["last_ts"] is None or ts > fs["last_ts"]:
                    fs["last_ts"] = ts
                if fs["first_ts"] is None or ts < fs["first_ts"]:
                    fs["first_ts"] = ts
                
            if current_commit_email:
                fs["authors"][current_commit_email] = fs["authors"].get(current_commit_email, 0) + 1

        if commit_b_idxs and len(current_commit_files) <= max_commit_files:
            valid_commits.append(commit_b_idxs)

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("\x01"):
            process_commit()
            current_commit_files = []
            
            parts = line[1:].split("\x1f")
            if len(parts) >= 4:
                current_commit_ts = int(parts[1]) if parts[1].isdigit() else 0
                name = parts[2].strip()
                email = parts[3].strip().lower()
                current_commit_email = email
                
                if email not in author_names:
                    author_names[email] = {}
                author_names[email][name] = author_names[email].get(name, 0) + 1
        else:
            parts = line.split("\t", 2)
            if len(parts) == 3:
                adds_str, dels_str, path = parts
                adds = 0 if adds_str == "-" else int(adds_str)
                dels = 0 if dels_str == "-" else int(dels_str)
                current_commit_files.append((path, adds, dels))
                
    process_commit()
    proc.wait()
    
    if proc.returncode != 0:
        return None, []

    global_author_commits = {}
    for fs in file_stats.values():
        for email, count in fs["authors"].items():
            global_author_commits[email] = global_author_commits.get(email, 0) + count

    sorted_authors = sorted(global_author_commits.items(), key=lambda kv: -kv[1])
    git_authors = []
    author_to_idx = {}
    
    for idx, (email, n_commits) in enumerate(sorted_authors):
        names = author_names.get(email, {})
        display_name = max(names.items(), key=lambda kv: kv[1])[0] if names else email
        git_authors.append({"name": display_name, "email": email,
                            "commits": n_commits})
        author_to_idx[email] = idx

    for b in buildings:
        path = b["path"]
        if path in file_stats and file_stats[path]["commits"] > 0:
            fs = file_stats[path]
            commits = fs["commits"]
            b["commits"] = commits
            b["adds"] = fs["adds"]
            b["dels"] = fs["dels"]
            b["churn"] = fs["adds"] + fs["dels"]
            b["first_ts"] = fs["first_ts"]
            b["last_ts"] = fs["last_ts"]
            
            b_authors = sorted(fs["authors"].items(), key=lambda kv: -kv[1])
            b["authors"] = [[author_to_idx[email], count] for email, count in b_authors]
            
            owner_email, owner_count = b_authors[0]
            b["owner"] = author_to_idx[owner_email]
            b["owner_share"] = round(owner_count / commits, 3)
            
            bf = 0
            cumulative = 0
            for email, count in b_authors:
                bf += 1
                cumulative += count
                if cumulative > 0.5 * commits:
                    break
            b["bus_factor"] = bf
            
            b["age_days"] = int((now_ts - fs["first_ts"]) / 86400) if fs["first_ts"] else 0
            b["stale_days"] = int((now_ts - fs["last_ts"]) / 86400) if fs["last_ts"] else 0
        else:
            # Never committed (new/untracked). Timestamps stay null so overlays
            # can tell "brand new" apart from "touched today" - zeroing them
            # would paint untracked files as the freshest in the city.
            b["commits"] = 0
            b["adds"] = 0
            b["dels"] = 0
            b["churn"] = 0
            b["first_ts"] = None
            b["last_ts"] = None
            b["authors"] = []
            b["owner"] = None
            b["owner_share"] = 0.0
            b["bus_factor"] = 0
            b["age_days"] = None
            b["stale_days"] = None

    window_days = 0
    if first_commit_ts and last_commit_ts:
        window_days = int((last_commit_ts - first_commit_ts) / 86400)

    return {
        "authors": git_authors,
        "commit_count": commit_count,
        "first_commit_ts": first_commit_ts,
        "last_commit_ts": last_commit_ts,
        "window_days": window_days,
        "truncated": max_commits is not None or since is not None,
        "skipped_bulk_commits": skipped_bulk_commits,
        "renames_dropped": renames_dropped,
        "untracked_paths": untracked_paths,
    }, valid_commits
