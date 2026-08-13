import * as THREE from 'three';

/**
 * Slow high cloud.
 *
 * The one piece of continuous motion in the scene that is allowed to be
 * always-on, because it is the right kind: broad, soft-edged, and slow enough
 * that you notice it only if you stop and look. That is the "soft fascination"
 * the restoration research describes - and it is also what keeps a still
 * screenshot from feeling like a dead render.
 *
 * A drifting sky also gives the city scale. Without something moving overhead
 * the whole thing reads as a model on a table.
 */

function cloudTexture() {
    // Generated, not downloaded: the viewer must stay offline-capable.
    const S = 128;
    const cv = document.createElement('canvas');
    cv.width = cv.height = S;
    const ctx = cv.getContext('2d');
    const img = ctx.createImageData(S, S);

    let seed = 987654321;
    const rnd = () => {
        seed = (seed * 1664525 + 1013904223) >>> 0;
        return seed / 4294967296;
    };
    // A handful of overlapping soft blobs makes a more convincing cloud than
    // any single falloff function.
    const blobs = [];
    for (let i = 0; i < 9; i++) {
        blobs.push({
            x: 0.5 + (rnd() - 0.5) * 0.72,
            y: 0.5 + (rnd() - 0.5) * 0.34,
            r: 0.10 + rnd() * 0.20,
        });
    }

    for (let y = 0; y < S; y++) {
        for (let x = 0; x < S; x++) {
            const u = x / S;
            const v = y / S;
            let a = 0;
            for (const b of blobs) {
                const dx = (u - b.x) / b.r;
                const dy = (v - b.y) / (b.r * 0.62);
                a = Math.max(a, 1 - Math.min(1, Math.sqrt(dx * dx + dy * dy)));
            }
            a = Math.pow(a, 1.7);
            // Fade hard at the tile edge so no cloud shows a seam.
            const edge = Math.min(1, Math.min(u, 1 - u, v, 1 - v) * 6);
            const i4 = (y * S + x) * 4;
            img.data[i4] = 255;
            img.data[i4 + 1] = 255;
            img.data[i4 + 2] = 255;
            img.data[i4 + 3] = Math.round(255 * a * edge);
        }
    }
    ctx.putImageData(img, 0, 0);

    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
}

export function createClouds(worldSize) {
    const COUNT = 14;
    const tex = cloudTexture();
    const geo = new THREE.PlaneGeometry(1, 1);
    const mat = new THREE.MeshBasicMaterial({
        map: tex,
        transparent: true,
        opacity: 0.34,
        depthWrite: false,
        fog: false,
        side: THREE.DoubleSide,
    });

    const mesh = new THREE.InstancedMesh(geo, mat, COUNT);
    mesh.renderOrder = -2;
    mesh.frustumCulled = false;

    const span = worldSize * 6;
    const height = worldSize * 1.15;
    const dummy = new THREE.Object3D();
    const drift = [];

    let seed = 424242;
    const rnd = () => {
        seed = (seed * 1664525 + 1013904223) >>> 0;
        return seed / 4294967296;
    };

    for (let i = 0; i < COUNT; i++) {
        drift.push({
            x: (rnd() - 0.5) * span,
            z: (rnd() - 0.5) * span,
            y: height * (0.75 + rnd() * 0.6),
            w: worldSize * (0.9 + rnd() * 1.6),
            speed: worldSize * 0.0009 * (0.6 + rnd() * 0.8),
        });
    }

    function update(t) {
        for (let i = 0; i < COUNT; i++) {
            const c = drift[i];
            let x = c.x + t * c.speed;
            // wrap
            const half = span * 0.5;
            x = ((x + half) % span + span) % span - half;
            dummy.position.set(x, c.y, c.z);
            dummy.rotation.set(-Math.PI / 2, 0, 0);   // lie flat, seen from below
            dummy.scale.set(c.w, c.w * 0.55, 1);
            dummy.updateMatrix();
            mesh.setMatrixAt(i, dummy.matrix);
        }
        mesh.instanceMatrix.needsUpdate = true;
    }

    update(0);
    mesh.userData.update = update;
    mesh.userData.material = mat;
    return mesh;
}
