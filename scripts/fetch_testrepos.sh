#!/bin/bash
set -e

mkdir -p .testrepos
cd .testrepos

echo "Fetching flask..."
if [ ! -d "flask" ]; then
    git clone --filter=blob:none https://github.com/pallets/flask.git
fi
cd flask
git checkout 2a8a38b051fc248865730bf3511bf2e2ea325e81
cd ..

echo "Fetching cpython..."
if [ ! -d "cpython" ]; then
    git clone --filter=blob:none https://github.com/python/cpython.git
fi
cd cpython
git checkout e3287f631f3c88ed80191aa222e7fc4ba91edd17
cd ..

echo "Fetching linux..."
if [ ! -d "linux" ]; then
    git clone --filter=blob:none https://github.com/torvalds/linux.git
fi
cd linux
git checkout 3eb40771c00a8488fa6ed2cc1fe203477908bf38
cd ..

echo "Setting up synthetic_250k..."
if [ ! -d "synthetic_250k" ]; then
    mkdir -p synthetic_250k
    cd synthetic_250k
    git init
    # Create 250k small files
    # Using python to do it faster
    python3 -c "
import os
for d in range(250):
    os.makedirs(f'dir_{d}', exist_ok=True)
    for f in range(1000):
        with open(f'dir_{d}/file_{f}.txt', 'w') as out:
            out.write('synthetic')
"
    git add .
    git commit -m "Synthetic 250k files"
    cd ..
fi

echo -e ".testrepos/flask flask\n.testrepos/cpython cpython\n.testrepos/linux linux\n.testrepos/synthetic_250k synthetic_250k" > manifest.txt
echo "Done!"
