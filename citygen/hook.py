import os
import sys
import subprocess
import time
from typing import Optional

from . import risk

MARKER = "# installed by citygen -- chronopolis risk warning"

def get_git_info(repo: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        root_out = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        root = root_out.stdout.strip()
        
        hooks_path_out = subprocess.run(["git", "-C", repo, "config", "--get", "core.hooksPath"], capture_output=True, text=True)
        hooks_dir = hooks_path_out.stdout.strip()
        
        if not hooks_dir:
            git_dir_out = subprocess.run(["git", "-C", repo, "rev-parse", "--git-dir"], capture_output=True, text=True, check=True)
            git_dir = git_dir_out.stdout.strip()
            # If git_dir is relative, make it absolute or relative to root
            if not os.path.isabs(git_dir):
                git_dir = os.path.join(repo, git_dir)
            hooks_dir = os.path.join(git_dir, "hooks")
        else:
            if not os.path.isabs(hooks_dir):
                hooks_dir = os.path.join(repo, hooks_dir)

        return root, hooks_dir, None
    except subprocess.CalledProcessError:
        return None, None, "Not a git repository"
    except FileNotFoundError:
        return None, None, "git not found"

def install(repo: str, city_path: str, block: bool, threshold: float, force: bool = False) -> int:
    root, hooks_dir, err = get_git_info(repo)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    os.makedirs(hooks_dir, exist_ok=True)
    hook_path = os.path.join(hooks_dir, "pre-commit")

    script = [
        "#!/bin/sh",
        MARKER,
        "# remove with: python -m citygen hook uninstall"
    ]
    
    # We should use relative path or exact city path? The task says:
    # python -m citygen hook run --city "out/city.json" || exit 0
    # and if block, omit || exit 0
    # the arg is city_path.
    city_path = city_path.replace('\\', '/')
    run_cmd = f'python -m citygen hook run --city "{city_path}" --threshold {threshold}'
    if block:
        run_cmd += " --block"
    else:
        run_cmd += " || exit 0"
        
    script.append(run_cmd)
    script_content = "\n".join(script) + "\n"

    if os.path.exists(hook_path):
        with open(hook_path, "r", encoding="utf-8") as f:
            existing = f.read()
        
        if MARKER in existing:
            # ours, overwrite silently
            with open(hook_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            print(f"updated {hook_path}")
            return 0
        else:
            if force:
                backup = f"{hook_path}.bak-{int(time.time())}"
                with open(backup, "w", encoding="utf-8") as f:
                    f.write(existing)
                with open(hook_path, "w", encoding="utf-8") as f:
                    f.write(script_content)
                os.chmod(hook_path, 0o755)
                print(f"backed up existing hook to {backup}")
                print(f"installed {hook_path}")
                return 0
            else:
                first_line = existing.split("\n")[0] if existing else ""
                print(f"error: {hook_path} already exists and is not ours.", file=sys.stderr)
                print(f"First line: {first_line}", file=sys.stderr)
                print("Either append 'python -m citygen hook run' yourself or re-run with --force.", file=sys.stderr)
                return 2

    with open(hook_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    os.chmod(hook_path, 0o755)
    print(f"installed {hook_path}")
    return 0

def uninstall(repo: str) -> int:
    root, hooks_dir, err = get_git_info(repo)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2
        
    hook_path = os.path.join(hooks_dir, "pre-commit")
    if not os.path.exists(hook_path):
        print(f"no hook found at {hook_path}")
        return 0
        
    with open(hook_path, "r", encoding="utf-8") as f:
        existing = f.read()
        
    if MARKER not in existing:
        print(f"error: {hook_path} is not ours, refusing to delete.", file=sys.stderr)
        return 2
        
    os.remove(hook_path)
    print(f"removed {hook_path}")
    
    # check for backups
    import glob
    baks = glob.glob(f"{hook_path}.bak-*")
    if len(baks) == 1:
        os.rename(baks[0], hook_path)
        print(f"restored backup {baks[0]}")
        
    return 0

def run_hook(city_path: str, block: bool, threshold: float) -> int:
    import json
    import subprocess
    import os
    import datetime

    repo_root = "."
    try:
        root_out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        repo_root = root_out.stdout.strip()
    except Exception:
        pass

    if not os.path.isabs(city_path):
        city_path = os.path.join(repo_root, city_path)
    
    # run in under 200ms
    # fast imports etc.
    try:
        with open(city_path, "r", encoding="utf-8") as f:
            city = json.load(f)
    except FileNotFoundError:
        now = datetime.datetime.now()
        git_dir = os.path.join(repo_root, ".git")
        marker_file = os.path.join(git_dir, f"citygen-hint-{now.strftime('%Y%m%d')}")
        if not os.path.exists(git_dir):
            return 0
        if not os.path.exists(marker_file):
            print("city.json is missing - create one with: python -m citygen build . -o out/city.json")
            try:
                open(marker_file, "w").close()
            except Exception:
                pass
        return 0

    # Staleness check
    city_head = city.get("repo", {}).get("head")
    staleness_note = None
    if city_head:
        try:
            head_out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
            current_head = head_out.stdout.strip()
            if current_head != city_head:
                count_out = subprocess.run(["git", "rev-list", "--count", f"{city_head}..HEAD"], capture_output=True, text=True)
                if count_out.returncode == 0:
                    commits_behind = int(count_out.stdout.strip())
                    if commits_behind > 20:
                        staleness_note = f"city data is {commits_behind} commits old - refresh: python -m citygen build . -o out/city.json"
                    elif commits_behind > 0:
                        staleness_note = f"\033[2mcity data is {commits_behind} commits old — refresh: python -m citygen build . -o out/city.json\033[0m"
                else:
                    staleness_note = "city data is from an unknown commit - refresh: python -m citygen build . -o out/city.json"
        except Exception:
            staleness_note = "city data is from an unknown commit - refresh: python -m citygen build . -o out/city.json"
            
    paths = risk.staged_paths(repo_root)
    if not paths:
        return 0

    scored = risk.score_paths(city, paths)
    
    # filter trips
    tripped = []
    for s in scored:
        if s["score"] is None:
            # new file, not yet analysed
            pass
        elif s["score"] >= threshold:
            tripped.append(s)

    if not tripped:
        return 0

    print(f"chronopolis: {len(tripped)} of {len(paths)} staged files is high-risk\n")
    
    for s in tripped:
        score_val = s["score"]
        band = s["band"]
        print(f"  {score_val:.2f}  {band}  {s['path']}")
        for reason in s["reasons"]:
            print(f"        {reason}")
        print()
        
    for s in scored:
        if s["score"] is None and "not found in city" in s["reasons"][0]:
            print(f"  new file, not yet analysed  {s['path']}\n")

    if staleness_note:
        print(f"  {staleness_note}\n")
        
    if not block:
        print("  (warning only; commit proceeding. block with: citygen hook install --block)")
        return 0
    else:
        return 1

