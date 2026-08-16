import os
import subprocess
import time
import json
import gzip
import shutil

REPOS = {
    "flask": ".testrepos/flask",
    "cpython": ".testrepos/cpython",
    #"linux": ".testrepos/linux",
    #"synthetic": ".testrepos/synthetic_250k"
}

def get_peak_mem_and_time(cmd):
    start = time.time()
    p = subprocess.Popen(cmd, env={**os.environ, "CITYGEN_PROFILE": "1", "GIT_PAGER": "cat"}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    peak_mem = 0
    while p.poll() is None:
        try:
            out = subprocess.check_output(f'wmic process where processid={p.pid} get WorkingSetSize', shell=True).decode()
            lines = out.strip().split('\n')
            if len(lines) > 1:
                mem = int(lines[1].strip())
                if mem > peak_mem:
                    peak_mem = mem
        except Exception:
            pass
        time.sleep(0.1)
    end = time.time()
    out, _ = p.communicate()
    
    profiling = {}
    for line in out.split('\n'):
        if "PROFILING_RESULTS:" in line:
            profiling = json.loads(line.split("PROFILING_RESULTS:")[1].strip())
    
    return end - start, peak_mem / (1024*1024), profiling, out

for name, path in REPOS.items():
    print(f"--- {name} ---")
    if not os.path.exists(path):
        print("Not cloned yet.")
        continue
    
    out_json = f"{name}.city.json"
    
    print("Cold build...")
    cmd = ["python", "-m", "citygen", "build", path, "-o", out_json]
    wall, mem, prof, out_str = get_peak_mem_and_time(cmd)
    
    size_raw = os.path.getsize(out_json) if os.path.exists(out_json) else 0
    if size_raw > 0:
        with open(out_json, 'rb') as f_in, gzip.open(f"{out_json}.gz", 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        size_gz = os.path.getsize(f"{out_json}.gz")
    else:
        size_gz = 0
        
    print(f"Cold: {wall:.2f}s, Mem: {mem:.2f}MB, JSON: {size_raw/1024/1024:.2f}MB raw, {size_gz/1024/1024:.2f}MB gz")
    
    print("Warm build...")
    wall, mem, prof, out_str = get_peak_mem_and_time(cmd)
    print(f"Warm: {wall:.2f}s, Mem: {mem:.2f}MB")
    
    print("Incremental edit...")
    edit_file = None
    for root, dirs, files in os.walk(path):
        if '.git' in dirs: dirs.remove('.git')
        for f in files:
            if f.endswith('.py') or f.endswith('.c'):
                edit_file = os.path.join(root, f)
                break
        if edit_file: break
    
    if edit_file:
        with open(edit_file, "a") as f:
            f.write("\n# edit\n")
        
        wall, mem, prof, out_str = get_peak_mem_and_time(cmd)
        print(f"Incr-edit: {wall:.2f}s, Mem: {mem:.2f}MB")
        
        subprocess.run(["git", "checkout", "--", edit_file], cwd=path)
        
    print("Incremental git pull...")
    current_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    try:
        old_commit = subprocess.check_output(["git", "rev-parse", "HEAD~20"], cwd=path, text=True).strip()
        subprocess.run(["git", "checkout", old_commit], cwd=path, check=True, capture_output=True)
        get_peak_mem_and_time(cmd)
        subprocess.run(["git", "checkout", current_commit], cwd=path, check=True, capture_output=True)
        wall, mem, prof, out_str = get_peak_mem_and_time(cmd)
        print(f"Incr-pull: {wall:.2f}s, Mem: {mem:.2f}MB")
    except Exception as e:
        print(f"Pull fail: {e}")
