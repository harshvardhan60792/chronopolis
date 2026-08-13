import * as THREE from 'three';

/**
 * The green belt around the city.
 *
 * Scope note, deliberately narrow: nothing is planted *inside* the city.
 *
 * Street trees were tried twice and cut. A treemap leaves no open ground -
 * every square unit inside a district is either a building or roadway - so any
 * in-city planting ends up standing in the street. Worse, it was clutter laid
 * over the exact area the eye needs clear to follow the block structure. The
 * surrounding landscape gives the same "this is a place on Earth, not a bar
 * chart" feeling with none of that cost.
 *
 * Woodland is clustered rather than scattered: evenly spaced dots read as
 * wallpaper, while clumps read as terrain and hold the eye gently - the soft
 * fascination the calm pass is built around (ADR-012).
 *
 * Two draw calls total (crowns, trunks).
 */

// Deterministic PRNG so a repo always grows the same trees.
function makeRandom(seed) {
    let s = seed >>> 0;
    return () => {
        s = (s * 1664525 + 1013904223) >>> 0;
        return s / 4294967296;
    };
}

export function createNature(city, worldSize) {
    const group = new THREE.Group();
    const rnd = makeRandom(0x5eed1a);
    const spots = [];
    const MAX_TREES = 1600;

    const clusters = 110;
    for (let i = 0; i < clusters; i++) {
        const ang = rnd() * Math.PI * 2;
        // Density falls off with distance, so the city sits in open country
        // rather than inside a rectangle of forest.
        const radial = 0.72 + Math.pow(rnd(), 0.6) * 1.6;
        const cx = worldSize / 2 + Math.cos(ang) * worldSize * radial;
        const cz = worldSize / 2 + Math.sin(ang) * worldSize * radial;
        const spread = worldSize * (0.03 + rnd() * 0.08);
        const n = 5 + Math.floor(rnd() * 16);
        for (let k = 0; k < n; k++) {
            const a2 = rnd() * Math.PI * 2;
            const r2 = Math.pow(rnd(), 0.5) * spread;
            const x = cx + Math.cos(a2) * r2;
            const z = cz + Math.sin(a2) * r2;
            // Hard exclusion zone around the built area. Nothing green gets
            // anywhere near the streets.
            const margin = worldSize * 0.06;
            if (x > -margin && x < worldSize + margin &&
                z > -margin && z < worldSize + margin) continue;
            spots.push({ x, z, scale: 0.9 + rnd() * 1.2 });
        }
    }

    if (!spots.length) return group;
    if (spots.length > MAX_TREES) spots.length = MAX_TREES;

    // Low-poly rounded canopy: an icosahedron reads as a tree crown at this
    // distance and costs 80 triangles.
    const crownGeo = new THREE.IcosahedronGeometry(1.5, 0);
    const crownMat = new THREE.MeshStandardMaterial({
        color: 0x5c7f45, roughness: 0.95, metalness: 0.0, flatShading: true,
    });
    const crowns = new THREE.InstancedMesh(crownGeo, crownMat, spots.length);

    const trunkGeo = new THREE.CylinderGeometry(0.22, 0.3, 2.2, 5);
    trunkGeo.translate(0, 1.1, 0);
    const trunkMat = new THREE.MeshStandardMaterial({
        color: 0x4a3b2c, roughness: 1.0, metalness: 0.0, flatShading: true,
    });
    const trunks = new THREE.InstancedMesh(trunkGeo, trunkMat, spots.length);

    const dummy = new THREE.Object3D();
    const tint = new THREE.Color();
    const rnd2 = makeRandom(0xc0ffee);

    spots.forEach((s, i) => {
        dummy.position.set(s.x, 2.4 * s.scale, s.z);
        dummy.scale.setScalar(s.scale);
        dummy.rotation.set(0, rnd2() * Math.PI, 0);
        dummy.updateMatrix();
        crowns.setMatrixAt(i, dummy.matrix);

        dummy.position.set(s.x, 0, s.z);
        dummy.scale.set(s.scale, s.scale * 1.1, s.scale);
        dummy.rotation.set(0, 0, 0);
        dummy.updateMatrix();
        trunks.setMatrixAt(i, dummy.matrix);

        // Foliage is never one flat green in life, and one flat green here
        // reads as plastic.
        const h = 0.22 + rnd2() * 0.06;
        tint.setHSL(h, 0.28 + rnd2() * 0.14, 0.30 + rnd2() * 0.12);
        crowns.setColorAt(i, tint);
    });

    crowns.instanceMatrix.needsUpdate = true;
    trunks.instanceMatrix.needsUpdate = true;
    if (crowns.instanceColor) crowns.instanceColor.needsUpdate = true;

    group.add(crowns);
    group.add(trunks);
    group.userData.count = spots.length;
    return group;
}
