import argparse
import datetime
import json
import os
import platform
import subprocess
import sys
import time
from typing import Dict, List, Tuple

STAGES_ORDER = [
    "walk", "read", "parse", "git_read", "git_apply", "resolve",
    "tree", "coupling", "health", "layout", "snapshots", "stories", "serialise"
]

def run_build(repo_path: str, incremental: bool = False) -> Tuple[float, Dict[str, float], Dict, int]:
    env = os.environ.copy()
    env["CITYGEN_PROFILE"] = "1"
    env["GIT_PAGER"] = "cat"
    
    out_file = os.path.join(".testrepos", "dummy_out.json")
    log_file = os.path.join(".testrepos", "dummy_log.txt")
    cmd = [sys.executable, "-m", "citygen", "build", repo_path, "-o", out_file, "--exclude", ".testrepos/*"]
    if incremental:
        cmd.append("--incremental")
    if "cpython" in repo_path or "linux" in repo_path:
        cmd.extend(["--max-commits", "1000"])
    
    with open(log_file, "w", encoding="utf-8") as lf:
        subprocess.run(cmd, env=env, stdout=lf, stderr=subprocess.STDOUT, check=True)
    
    profiling = {}
    with open(log_file, "r", encoding="utf-8") as lf:
        for line in lf:
            if "PROFILING_RESULTS: " in line:
                profiling = json.loads(line.split("PROFILING_RESULTS: ", 1)[1])
                break
            
    with open(out_file, "r", encoding="utf-8") as f:
        city = json.load(f)
        
    wall_time = city.get("build_seconds", 0.0) + profiling.get("serialise", 0.0)
    git_commits = city.get("git", {}).get("commit_count", 0) if city.get("git") else 0
    return wall_time, profiling, city["stats"], git_commits

def format_stage(stages: Dict[str, float], stage: str, total: float) -> str:
    val = stages.get(stage, 0.0)
    pct = (val / total * 100) if total > 0 else 0
    return f"{val:.2f}s ({pct:.1f}%)"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", required=True, help="Manifest file")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per repo")
    parser.add_argument("--out", default="docs/05-PERFORMANCE.md", help="Output markdown file")
    parser.add_argument("--incremental", action="store_true", help="Profile incremental 1-commit changes")
    args = parser.parse_args()

    repos = []
    with open(args.repos, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split()
            path = parts[0]
            label = parts[1] if len(parts) > 1 else path
            repos.append((path, label))

    results = []
    
    plat = platform.platform()
    cpu = platform.processor()
    cpus = os.cpu_count()
    py_ver = platform.python_version()
    # Check if SSD - not easily determinable in a cross-platform way without external dependencies, we will just add a placeholder or what we can.
    drive_type = "unknown drive"
    if os.name == 'nt':
        drive_type = "SSD/HDD (Windows)"

    machine_info = f"Machine: {plat}, {cpu} ({cpus} cores), Python {py_ver}, {drive_type}"
    
    for path, label in repos:
        print(f"Profiling {label} ({path})...")
        if not os.path.exists(path):
            print(f"Skipping {path} (not found)")
            continue

        print(f"  Cold run...")
        try:
            cold_wall, cold_stages, stats, commits = run_build(path)
        except subprocess.CalledProcessError as e:
            print(f"Failed to build {path}:")
            print(e.stderr)
            continue
            
        warm_walls = []
        warm_stages_list = []
        for i in range(args.runs):
            print(f"  Warm run {i+1}/{args.runs}...")
            if args.incremental:
                # Make a dummy 1-file change
                dummy_file = os.path.join(path, f"dummy_{i}.py")
                with open(dummy_file, "w") as df:
                    df.write(f"print('dummy {i}')\n")
                subprocess.run(["git", "-C", path, "add", f"dummy_{i}.py"], check=True, capture_output=True)
                subprocess.run(["git", "-C", path, "commit", "-m", f"dummy {i}"], check=True, capture_output=True)
                
                try:
                    w, s, _, _ = run_build(path, incremental=True)
                finally:
                    pass
            else:
                w, s, _, _ = run_build(path)
                
            warm_walls.append(w)
            warm_stages_list.append(s)
            
        if args.incremental:
            subprocess.run(["git", "-C", path, "reset", "--hard", f"HEAD~{args.runs}"], check=True, capture_output=True)
            
        sorted_indices = sorted(range(len(warm_walls)), key=lambda k: warm_walls[k])
        med_idx = sorted_indices[len(warm_walls) // 2]
        med_wall = warm_walls[med_idx]
        med_stages = warm_stages_list[med_idx]
        
        results.append({
            "label": label,
            "path": path,
            "stats": stats,
            "commits": commits,
            "cold_wall": cold_wall,
            "cold_stages": cold_stages,
            "med_wall": med_wall,
            "med_stages": med_stages,
        })
        
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    out_lines = [
        f"\n### Build stage breakdown ({date_str})",
        "",
        machine_info,
        "",
        "| Repo | Files | LOC | Commits | Total (Cold) | Total (Warm) | " + " | ".join(STAGES_ORDER) + " |",
        "|---|---|---|---|---|---|---" + "|---" * (len(STAGES_ORDER) - 1) + "|"
    ]
    
    for r in results:
        stats = r["stats"]
        files = stats["files"]
        loc = stats["loc"]
        commits = r["commits"]
        
        # We output two lines per repo: one for cold, one for warm
        # Actually, maybe one line with cold and warm total, and warm stages?
        # The prompt says: "reports the **median** of the rest, and separately reports the discarded cold run. Reporting cold and warm separately is mandatory"
        # Let's make it two lines: <label> (cold) and <label> (warm)
        row_cold = [
            f"{r['label']} (cold)",
            str(files),
            str(loc),
            str(commits),
            f"{r['cold_wall']:.2f}s",
            "-",
        ] + [format_stage(r["cold_stages"], st, r["cold_wall"]) for st in STAGES_ORDER]
        
        row_warm = [
            f"{r['label']} (warm)",
            str(files),
            str(loc),
            str(commits),
            "-",
            f"{r['med_wall']:.2f}s",
        ] + [format_stage(r["med_stages"], st, r["med_wall"]) for st in STAGES_ORDER]
        
        out_lines.append("| " + " | ".join(row_cold) + " |")
        out_lines.append("| " + " | ".join(row_warm) + " |")

    # verify 95-105% criteria for warm runs
    for r in results:
        st_sum = sum(r["med_stages"].values())
        pct = (st_sum / r["med_wall"]) * 100
        print(f"{r['label']} warm stages sum to {pct:.1f}% of wall time")
        if not (95 <= pct <= 105):
            print(f"WARNING: {r['label']} warm stages sum to {pct:.1f}% (outside 95-105% range)")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")
        
    print(f"Appended results to {args.out}")

if __name__ == "__main__":
    main()
