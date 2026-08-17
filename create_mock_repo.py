import os
import subprocess

def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, shell=True, check=True)

repo = ".testrepos/mock_repo"
os.makedirs(repo, exist_ok=True)
run("git init", cwd=repo)
run("git config user.name Test", cwd=repo)
run("git config user.email test@example.com", cwd=repo)

for i in range(5):
    with open(f"{repo}/file_{i}.py", "w") as f:
        f.write(f"print('file {i}')\ndef func{i}():\n    pass\n")
run("git add .", cwd=repo)
run("git commit -m \"initial\"", cwd=repo)

# split point is here (commit 1, 50% split of 2 commits? No, we need more commits)
for j in range(3):
    for i in range(2):
        with open(f"{repo}/file_{i}.py", "a") as f:
            f.write(f"\n# bad feature {j}\n")
    run("git add .", cwd=repo)
    run(f"git commit -m \"feat {j}\"", cwd=repo)

# now the split point will be around here.
# now we introduce a bug
with open(f"{repo}/file_0.py", "a") as f:
    f.write("\n# BUG\nprint(1/0)\n")
run("git add .", cwd=repo)
run("git commit -m \"introduce bug\"", cwd=repo)
bug_sha = subprocess.check_output("git rev-parse HEAD", cwd=repo, shell=True, text=True).strip()

# wait a commit
with open(f"{repo}/file_3.py", "a") as f:
    f.write("\n# harmless\n")
run("git add .", cwd=repo)
run("git commit -m \"harmless\"", cwd=repo)

# now we fix the bug
with open(f"{repo}/file_0.py", "w") as f:
    f.write("print('file 0')\ndef func0():\n    pass\n") # deleted the bug
run("git add .", cwd=repo)
run("git commit -m \"fix: divide by zero\"", cwd=repo)

print("Mock repo created.")
