import json
import os
import re
import subprocess
import time
from datetime import datetime

from citygen.walk import is_source_path, EXT_LANG
from citygen.research.labels import FIX_PATTERNS, REVERT_PATTERN, BULK_COMMIT_THRESHOLD

def _is_doc_or_non_source(path: str) -> bool:
    if not is_source_path(path):
        return True
    ext = os.path.splitext(path)[1].lower()
    return EXT_LANG.get(ext) == "docs"

def get_deleted_lines(root: str, sha: str) -> dict[str, list[tuple[int, int]]]:
    """git show <sha> --unified=0 to find deleted line ranges per file."""
    cmd = ["git", "-C", root, "show", sha, "--unified=0", "--no-prefix"]
    try:
        out = None
        for _ in range(3):
            try:
                out = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace", stderr=subprocess.DEVNULL)
                break
            except OSError as e:
                if "paging file" in str(e):
                    time.sleep(1)
                else:
                    raise
        if out is None:
            return {}
    except subprocess.CalledProcessError:
        return {}
    
    result = {}
    current_file = None
    for line in out.splitlines():
        if line.startswith("--- "):
            if line.startswith("--- /dev/null"):
                current_file = None
            else:
                current_file = line[4:].strip()
                if current_file.startswith("a/"):
                    current_file = current_file[2:]
                result[current_file] = []
        elif line.startswith("@@ ") and current_file is not None:
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                if count > 0:
                    result[current_file].append((start, start + count - 1))
    return result

def introducers(root: str, fix_sha: str, path: str,
                deleted_line_ranges: list[tuple[int, int]]) -> set[str]:
    """git blame -w -M -C -L <a>,<b> <fix_sha>^ -- <path>, parsed to commit shas."""
    shas = set()
    if not deleted_line_ranges:
        return shas
        
    cmd = ["git", "-C", root, "blame", "-w", "-M", "-C", "-l", "--line-porcelain", f"{fix_sha}^", "--", path]
    # In order to supply multiple -L, we insert them before the commit sha
    blame_cmd = cmd[:9]
    for start, end in deleted_line_ranges:
        blame_cmd.extend(["-L", f"{start},{end}"])
    blame_cmd.extend(cmd[9:])
    
    try:
        out = None
        for _ in range(3):
            try:
                out = subprocess.check_output(blame_cmd, text=True, encoding="utf-8", errors="replace", stderr=subprocess.DEVNULL)
                break
            except OSError as e:
                if "paging file" in str(e):
                    time.sleep(1)
                else:
                    raise
        if out is None:
            return shas
    except subprocess.CalledProcessError:
        return shas
        
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]{40}) \d+ \d+", line)
        if m:
            shas.add(m.group(1))
    return shas

def run_szz(a):
    repo = a.repo
    max_fixes = a.max_fixes
    out_path = a.out
    
    print(f"Running SZZ on {repo} (max_fixes={max_fixes})")
    
    # 1. Get commit history
    # We need commit sha, message, and files touched
    cmd = ["git", "-C", repo, "log", "--no-merges", "--name-status", "--format=[COMMIT]%x00%H%x00%B%x00"]
    out = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")
    
    fix_regexes = [re.compile(p, re.IGNORECASE) for p in FIX_PATTERNS]
    revert_regex = re.compile(REVERT_PATTERN)
    
    commits_scanned = 0
    fix_commits = []
    revert_commits_count = 0
    excluded_doc_only = 0
    
    parts = out.split("[COMMIT]\x00")
    for part in parts:
        if not part.strip():
            continue
        commits_scanned += 1
        
        try:
            sha, msg, rest = part.split("\x00", 2)
        except ValueError:
            continue
            
        files = []
        for line in rest.splitlines():
            line = line.strip()
            if not line:
                continue
            if re.match(r"^[A-Z]\d*\t", line):
                filename = line.split("\t")[-1]
                files.append(filename)
                
        if len(files) > BULK_COMMIT_THRESHOLD:
            continue
            
        is_fix = any(r.search(msg) for r in fix_regexes)
        is_revert = revert_regex.search(msg)
        
        if is_fix or is_revert:
            if not files or all(_is_doc_or_non_source(f) for f in files):
                excluded_doc_only += 1
                continue
                
            fix_commits.append((sha, files))
            if is_revert:
                revert_commits_count += 1
                
            if len(fix_commits) >= max_fixes:
                break
                
    print(f"Scanned {commits_scanned} commits.")
    print(f"Found {len(fix_commits)} fix commits ({revert_commits_count} reverts).")
    print(f"Excluded {excluded_doc_only} doc-only fix commits.")
    
    labels_files = {}
    labels_commits = {}
    blame_failures = 0
    
    # 2. Process fix commits
    t0 = time.time()
    for i, (fix_sha, files) in enumerate(fix_commits):
        if (i + 1) % 50 == 0:
            print(f"Processing fix commit {i+1}/{len(fix_commits)}...")
            
        deleted = get_deleted_lines(repo, fix_sha)
        
        for path, ranges in deleted.items():
            if _is_doc_or_non_source(path):
                continue
                
            shas = introducers(repo, fix_sha, path, ranges)
            
            if ranges and not shas:
                blame_failures += 1
                
            if shas:
                if path not in labels_files:
                    labels_files[path] = {"introducing_commits": [], "fix_commits": []}
                
                for sha in shas:
                    if sha not in labels_files[path]["introducing_commits"]:
                        labels_files[path]["introducing_commits"].append(sha)
                if fix_sha not in labels_files[path]["fix_commits"]:
                    labels_files[path]["fix_commits"].append(fix_sha)
                    
                for sha in shas:
                    if sha not in labels_commits:
                        labels_commits[sha] = {"introduced": True, "via": []}
                    if fix_sha not in labels_commits[sha]["via"]:
                        labels_commits[sha]["via"].append(fix_sha)
                        
    print(f"Processed in {time.time() - t0:.2f}s")
    
    # Get head sha
    head_sha = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip()
    
    result = {
        "repo": os.path.basename(os.path.abspath(repo)),
        "head": head_sha[:7],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "rule": {
            "fix_patterns": FIX_PATTERNS,
            "max_fixes": max_fixes,
            "excluded_doc_only": True
        },
        "counts": {
            "commits_scanned": commits_scanned,
            "fix_commits": len(fix_commits),
            "revert_commits": revert_commits_count,
            "introducing_commits": len(labels_commits),
            "labelled_files": len(labels_files),
            "blame_failures": blame_failures
        },
        "files": labels_files,
        "commits": labels_commits
    }
    
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        
    print(f"Saved to {out_path}")
    return 0

