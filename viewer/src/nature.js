import * as THREE from 'three';

/**
 * Trees and parks.
 *
 * Not decoration - they carry data, which is the only reason they earn their
 * place. A district's green cover is inversely proportional to how built-up it
 * is: quiet corners of the repo look like parkland, dense complex ones look
 * like downtown. You can read "where is this codebase actually busy" from
 * across the map without reading a single label.
 *
 * Nature also does the restorative work the research points at: natural forms
 * hold attention gently, where an unbroken grid of boxes does not. Two draw
 * calls (foliage, trunks) for the whole planting.
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
    const { districts, plots } = city.layout;
    const group = new THREE.Group();
    if (!districts || !districts.length) return group;

    // How built-up is each district? Buildings per unit of ground area.
    const areaByPath = new Map();
    const builtByPath = new Map();
    for (const d of districts) {
        areaByPath.set(d.path, d.w * d.d);
        builtByPath.set(d.path, 0);
    }
    city.buildings.forEach((b, i) => {
        const p = plots[i];
        if (!p) return;
        const key = b.dir || '';
        if (builtByPath.has(key)) builtByPath.set(key, builtByPath.get(key) + p.w * p.d);
    });

    const rnd = makeRandom(0x5eed1a);
    const spots = [];   // {x, z, scale}
    const MAX_TREES = 1800;

    // --- 1. street trees ----------------------------------------------------
    // Geometry that matters: district rectangles TILE - there is no gap
    // between them. The road is the `street_width` margin inside each
    // district, between its boundary and where its buildings start. So a tree
    // belongs at roughly three quarters of the way across that margin: on the
    // kerb, with the middle of the carriageway left clear.
    const sw = city.layout.street_width || 2.0;
    const kerb = sw * 0.78;
    const maxCanopy = sw * 0.30;      // crown radius = 1.5 * scale

    // Plot rectangles per district, so a tree never lands on a building.
    const plotsByDir = new Map();
    city.buildings.forEach((b, i) => {
        const p = plots[i];
        if (!p) return;
        const key = b.dir || '';
        if (!plotsByDir.has(key)) plotsByDir.set(key, []);
        plotsByDir.get(key).push(p);
    });

    const clearOfBuildings = (x, z, list) => {
        if (!list) return true;
        for (const p of list) {
            if (x > p.x - 0.5 && x < p.x + p.w + 0.5 &&
                z > p.z - 0.5 && z < p.z + p.d + 0.5) return false;
        }
        return true;
    };

    for (const d of districts) {
        if (d.w < sw * 3 || d.d < sw * 3) continue;   // too small to have streets
        const step = 7 + rnd() * 3;
        const here = plotsByDir.get(d.path);
        const edges = [
            { x0: d.x, z0: d.z + kerb, dx: 1, dz: 0, len: d.w },
            { x0: d.x, z0: d.z + d.d - kerb, dx: 1, dz: 0, len: d.w },
            { x0: d.x + kerb, z0: d.z, dx: 0, dz: 1, len: d.d },
            { x0: d.x + d.w - kerb, z0: d.z, dx: 0, dz: 1, len: d.d },
        ];
        for (const e of edges) {
            for (let t = step * 0.5; t < e.len; t += step) {
                if (rnd() > 0.55) continue;              // irregular, not a hedge
                const x = e.x0 + e.dx * t;
                const z = e.z0 + e.dz * t;
                if (!clearOfBuildings(x, z, here)) continue;
                spots.push({ x, z, scale: (maxCanopy / 1.5) * (0.75 + rnd() * 0.25) });
            }
        }
    }

    // --- 2. the green belt around the city ----------------------------------
    // Clustered, not scattered: real woodland clumps, and evenly spaced dots
    // read as wallpaper. Density falls off with distance so the city sits in
    // open country rather than a rectangle of forest.
    const beltClusters = 90;
    for (let i = 0; i < beltClusters; i++) {
        const ang = rnd() * Math.PI * 2;
        const radial = 0.62 + Math.pow(rnd(), 0.6) * 1.5;      // 0.62..2.1 x world
        const cx = worldSize / 2 + Math.cos(ang) * worldSize * radial;
        const cz = worldSize / 2 + Math.sin(ang) * worldSize * radial;
        const spread = worldSize * (0.03 + rnd() * 0.07);
        const n = 4 + Math.floor(rnd() * 14);
        for (let k = 0; k < n; k++) {
            const a2 = rnd() * Math.PI * 2;
            const r2 = Math.pow(rnd(), 0.5) * spread;
            const x = cx + Math.cos(a2) * r2;
            const z = cz + Math.sin(a2) * r2;
            // Keep the belt off the built area.
            if (x > -8 && x < worldSize + 8 && z > -8 && z < worldSize + 8) continue;
            spots.push({ x, z, scale: 0.9 + rnd() * 1.1 });
        }
    }

    // --- 3. parkland inside genuinely open districts ------------------------
    // Only leaf districts get planted: nesting means a parent's area is
    // already covered by its children.
    const parents = new Set(districts.map((d) => d.path.split('/').slice(0, -1).join('/')));

    for (const d of districts) {
        if (parents.has(d.path)) continue;
        const area = areaByPath.get(d.path) || 1;
        const built = builtByPath.get(d.path) || 0;
        const open = Math.max(0, 1 - built / area);        // 0 = wall to wall
        if (open < 0.12) continue;                          // downtown: no room

        // A tree every ~40 square units of genuinely open ground, capped so a
        // huge sparse district does not turn into a forest that hides the data.
        const budget = Math.min(90, Math.floor((area * open) / 40));
        for (let i = 0; i < budget; i++) {
            const x = d.x + 1.2 + rnd() * Math.max(0.1, d.w - 2.4);
            const z = d.z + 1.2 + rnd() * Math.max(0.1, d.d - 2.4);
            // Reject anything landing on a building footprint.
            let blocked = false;
            for (let k = 0; k < city.buildings.length; k++) {
                if (city.buildings[k].dir !== d.path) continue;
                const p = plots[k];
                if (!p) continue;
                if (x > p.x - 0.6 && x < p.x + p.w + 0.6 &&
                    z > p.z - 0.6 && z < p.z + p.d + 0.6) { blocked = true; break; }
            }
            if (!blocked) spots.push({ x, z, scale: 0.75 + rnd() * 0.75 });
        }
    }

    if (!spots.length) return group;
    if (spots.length > MAX_TREES) spots.length = MAX_TREES;

    // --- foliage ------------------------------------------------------------
    // Low-poly rounded canopy: an icosahedron reads as a tree crown at this
    // scale and costs 80 triangles.
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
