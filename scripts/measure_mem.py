import subprocess
import sys
import time
import os

def run_and_monitor(cmd):
    start = time.time()
    # Popen
    p = subprocess.Popen(cmd)
    
    peak_mem = 0
    while p.poll() is None:
        try:
            # simple wmic call to get WorkingSetSize (not perfect but works on standard Windows without psutil)
            out = subprocess.check_output(f'wmic process where processid={p.pid} get WorkingSetSize', shell=True).decode()
            lines = out.strip().split('\n')
            if len(lines) > 1:
                mem = int(lines[1].strip())
                if mem > peak_mem:
                    peak_mem = mem
        except Exception:
            pass
        time.sleep(0.5)
        
    end = time.time()
    print(f"Wall time: {end - start:.2f}s")
    print(f"Peak memory: {peak_mem / (1024*1024):.2f} MB")
    return p.returncode

if __name__ == "__main__":
    run_and_monitor(sys.argv[1:])
