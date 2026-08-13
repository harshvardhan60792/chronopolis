import * as THREE from 'three';
import { langPalette } from './palette.js';

/**
 * Buildings: one InstancedMesh, one draw call, with a procedural facade.
 *
 * The windows are not geometry and not a texture - they are a grid evaluated
 * in the fragment shader from the instance's own world size, with a per-
 * instance hash deciding which panes are lit. That means a 10,000-building
 * city gets a lit skyline for zero extra draw calls, zero texture memory and
 * no vertex cost, which is the only way this stays at 60 fps (ADR-002).
 *
 * Window density is driven by the file's own metrics, so the facade carries
 * information rather than decoration: a busy file is a busy building.
 */

// Narrow cells matter: at 1.7 units a slim building fitted fewer than two
// windows across, so a lit cell became a continuous bar of light spanning the
// whole floor. 1.05 keeps several panes on even the thinnest facade.
const WINDOW_W = 1.05;  // world units per window cell, horizontally
const WINDOW_H = 2.3;   // and vertically (one "floor")

export function createBuildings(buildings, plots) {
    const geo = new THREE.BoxGeometry(1, 1, 1);
    geo.translate(0, 0.5, 0);          // pivot at the base so scale.y grows up

    // Cheap baked AO: darken the bottom ring of vertices so buildings sit in
    // the ground instead of floating on it.
    const pos = geo.attributes.position;
    const colors = new Float32Array(pos.count * 3);
    for (let i = 0; i < pos.count; i++) {
        const shade = pos.getY(i) < 0.1 ? 0.55 : 1.0;
        colors[i * 3] = shade;
        colors[i * 3 + 1] = shade;
        colors[i * 3 + 2] = shade;
    }
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const n = buildings.length;
    const seeds = new Float32Array(n);
    const litness = new Float32Array(n);

    const mat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        vertexColors: true,
        roughness: 0.62,
        metalness: 0.22,
    });

    const uniforms = {
        uTime: { value: 0 },
        uNight: { value: 0.88 },
        uWindowW: { value: WINDOW_W },
        uWindowH: { value: WINDOW_H },
        uWarm: { value: new THREE.Color(0xffd9a0) },
        uCool: { value: new THREE.Color(0x9fd4ff) },
    };
    mat.userData.uniforms = uniforms;

    mat.onBeforeCompile = (shader) => {
        Object.assign(shader.uniforms, uniforms);

        shader.vertexShader = shader.vertexShader
            .replace('#include <common>', /* glsl */`
                #include <common>
                attribute float aSeed;
                attribute float aLit;
                varying vec3 vLocal;
                varying vec3 vSize;
                varying float vSeed;
                varying float vLit;
            `)
            .replace('#include <begin_vertex>', /* glsl */`
                #include <begin_vertex>
                vLocal = position;
                vSeed = aSeed;
                vLit = aLit;
                // Recover this instance's world dimensions from its matrix so
                // the window grid stays a constant real-world size instead of
                // stretching with the building.
                vSize = vec3(
                    length(instanceMatrix[0].xyz),
                    length(instanceMatrix[1].xyz),
                    length(instanceMatrix[2].xyz)
                );
            `);

        shader.fragmentShader = shader.fragmentShader
            .replace('#include <common>', /* glsl */`
                #include <common>
                uniform float uTime;
                uniform float uNight;
                uniform float uWindowW;
                uniform float uWindowH;
                uniform vec3 uWarm;
                uniform vec3 uCool;
                varying vec3 vLocal;
                varying vec3 vSize;
                varying float vSeed;
                varying float vLit;

                float hash21(vec2 p, float s) {
                    p = fract(p * vec2(233.34, 851.73) + s * 17.31);
                    p += dot(p, p + 41.27);
                    return fract(p.x * p.y);
                }
            `)
            .replace('#include <dithering_fragment>', /* glsl */`
                #include <dithering_fragment>

                // Facade only on vertical faces; roofs stay dark like real roofs.
                vec3 nrm = normalize(vNormal);
                float sideness = 1.0 - smoothstep(0.45, 0.75, abs(nrm.y));

                if (sideness > 0.001) {
                    // Horizontal coordinate runs along whichever face we are on.
                    float across = abs(nrm.x) > 0.5
                        ? (vLocal.z + 0.5) * vSize.z
                        : (vLocal.x + 0.5) * vSize.x;
                    float up = vLocal.y * vSize.y;

                    vec2 cell = vec2(floor(across / uWindowW), floor(up / uWindowH));
                    vec2 f = vec2(fract(across / uWindowW), fract(up / uWindowH));

                    // Pane shape: a margin of wall around each window, so the
                    // grid reads as architecture, not as a checkerboard.
                    float pane = smoothstep(0.16, 0.24, f.x) * smoothstep(0.84, 0.76, f.x)
                               * smoothstep(0.20, 0.30, f.y) * smoothstep(0.86, 0.76, f.y);

                    // Ground floor is a lobby: taller, always lit, no grid.
                    float lobby = (1.0 - smoothstep(uWindowH * 0.9, uWindowH * 1.1, up)) * 0.55;

                    float r = hash21(cell + vec2(nrm.x * 3.0, nrm.z * 7.0), vSeed);
                    // Every lit window is STEADY. An earlier version flickered
                    // a few panes for "life"; across hundreds of buildings that
                    // is a field of blinking dots in the periphery and it made
                    // the scene genuinely tiring to look at. Stillness is the
                    // feature.
                    float lit = step(1.0 - vLit, r);

                    vec3 tint = mix(uWarm, uCool, step(0.82, hash21(cell.yx, vSeed + 3.7)));

                    // No two lit rooms are the same brightness. Without this
                    // jitter a lit row reads as one uniform strip of neon.
                    float vary = 0.55 + 0.45 * hash21(cell + 11.3, vSeed + 5.1);
                    float glow = (pane * lit * vary + lobby * 0.85) * sideness * uNight;

                    // Daylight: the windows are glass, not lamps. A slight
                    // darkening where the panes are gives the facade real
                    // structure and keeps the building's own colour - which is
                    // what every overlay mode encodes - fully readable.
                    gl_FragColor.rgb *= 1.0 - 0.22 * pane * sideness * (1.0 - uNight);

                    gl_FragColor.rgb += tint * glow * 1.05;
                    gl_FragColor.rgb *= 1.0 - 0.25 * sideness * uNight * (1.0 - pane) * step(uWindowH, up);
                }
            `);
    };
    // Any change to onBeforeCompile source needs a distinct cache key.
    mat.customProgramCacheKey = () => 'chronopolis-facade-v1';

    const mesh = new THREE.InstancedMesh(geo, mat, n);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    const dummy = new THREE.Object3D();

    for (let i = 0; i < n; i++) {
        const b = buildings[i];
        const plot = plots[i];
        if (!plot) continue;

        dummy.position.set(plot.x + plot.w / 2, 0, plot.z + plot.d / 2);
        dummy.scale.set(plot.w, plot.h, plot.d);
        dummy.updateMatrix();
        mesh.setMatrixAt(i, dummy.matrix);

        const c = langPalette[b.lang] || langPalette.other;
        mesh.setColorAt(i, c);

        // Stable per-building seed: the same repo always lights the same
        // windows, so a screenshot is reproducible.
        seeds[i] = ((i * 2654435761) % 1000) / 1000;

        // Occupancy from activity: a file with functions and recent commits
        // has more lights on than an empty data file.
        // Real towers at dusk run roughly a third to a half of their panes lit.
        // Going higher turns every building into a lantern and the city loses
        // its architecture.
        const density = Math.min(1, (b.functions || 0) / 12);
        const alive = b.stale_days == null ? 0.35
            : 1 - Math.min(1, b.stale_days / 540);
        litness[i] = 0.13 + 0.26 * density + 0.16 * alive;
    }

    geo.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seeds, 1));
    geo.setAttribute('aLit', new THREE.InstancedBufferAttribute(litness, 1));

    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;

    mesh.userData.uniforms = uniforms;
    return mesh;
}
