import os
import subprocess

os.makedirs(".testrepos/synthetic_250k", exist_ok=True)
os.chdir(".testrepos/synthetic_250k")

if not os.path.exists(".git"):
    subprocess.run(["git", "init"])

print("Creating files...")
for d in range(250):
    os.makedirs(f'dir_{d}', exist_ok=True)
    for f in range(1000):
        with open(f'dir_{d}/file_{f}.txt', 'w') as out:
            out.write('synthetic')

print("Adding files to git...")
subprocess.run(["git", "add", "."])
print("Committing...")
subprocess.run(["git", "commit", "-m", "Synthetic 250k files"])
print("Done.")
