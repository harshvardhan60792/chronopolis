import * as THREE from 'three';

/**
 * Procedural "code weather" - rain density reflects the repo's own average
 * health score (churn x complexity x ownership risk x staleness, the same
 * composite the Health overlay uses). A calm, well-maintained repo gets a
 * clear sky; a churny, coupled, single-owner repo gets a steady drizzle.
 *
 * Deliberately GPU-driven (position computed from uTime in the vertex
 * shader, same as traffic.js - see docs/05-PERFORMANCE.md rule 2) and
 * deliberately restrained: intensity is fixed once from a static repo-level
 * score, not animated, and there is no lightning/flash of any kind - a
 * strobing thunderclap would violate ADR-012 ("no strobing, anywhere") for
 * the sake of a gimmick. Rain is capped low even at the worst score; this is
 * mood-setting atmosphere, not a storm.
 */
export function createWeather(worldSize, healthScore) {
    const intensity = Math.max(0, Math.min(1, healthScore || 0));
    if (intensity < 0.06) return null; // clear sky: don't even build the mesh

    const count = Math.round(120 + intensity * 900);
    const spreadSpan = worldSize * 1.6;
    const fallSpan = worldSize * 0.9;
    const topY = worldSize * 0.8;
    const fallSpeed = worldSize * 0.22;

    const xz = new Float32Array(count * 2);
    const phase = new Float32Array(count);
    let seed = 24681357;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    for (let i = 0; i < count; i++) {
        xz[i * 2] = (rnd() - 0.5) * spreadSpan;
        xz[i * 2 + 1] = (rnd() - 0.5) * spreadSpan;
        phase[i] = rnd();
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(count * 3), 3));
    geo.setAttribute('aXZ', new THREE.BufferAttribute(xz, 2));
    geo.setAttribute('aPhase', new THREE.BufferAttribute(phase, 1));
    geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, topY / 2, 0), spreadSpan);

    const mat = new THREE.ShaderMaterial({
        vertexShader: `
            attribute vec2 aXZ;
            attribute float aPhase;
            uniform float uTime;
            uniform float uFallSpeed;
            uniform float uFallSpan;
            uniform float uTopY;
            void main() {
                float y = uTopY - mod(uTime * uFallSpeed + aPhase * uFallSpan, uFallSpan);
                vec4 mv = modelViewMatrix * vec4(aXZ.x, y, aXZ.y, 1.0);
                gl_Position = projectionMatrix * mv;
                gl_PointSize = clamp(600.0 / -mv.z, 1.0, 4.0);
            }
        `,
        fragmentShader: `
            uniform vec3 uColor;
            uniform float uOpacity;
            void main() {
                vec2 p = gl_PointCoord - 0.5;
                float a = 1.0 - smoothstep(0.15, 0.5, length(p));
                if (a < 0.02) discard;
                gl_FragColor = vec4(uColor, a * uOpacity);
            }
        `,
        uniforms: {
            uTime: { value: 0 },
            uFallSpeed: { value: fallSpeed },
            uFallSpan: { value: fallSpan },
            uTopY: { value: topY },
            uColor: { value: new THREE.Color(0xaec4d6) },
            // Capped well under fully opaque - a mood cue, not a downpour.
            uOpacity: { value: 0.10 + intensity * 0.24 },
        },
        transparent: true,
        depthWrite: false,
    });

    const points = new THREE.Points(geo, mat);
    points.frustumCulled = false;
    points.renderOrder = -1;

    function update(t) {
        mat.uniforms.uTime.value = t;
    }
    points.userData.update = update;
    return points;
}
