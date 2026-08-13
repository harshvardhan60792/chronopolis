import * as THREE from 'three';
import { Sky } from 'three/examples/jsm/objects/Sky.js';

/**
 * Atmosphere.
 *
 * Uses three's Sky (Preetham analytic scattering) rather than a gradient: real
 * scattering is what makes a horizon look like air instead of a Photoshop
 * ramp, and it costs exactly one draw call on a box that never moves.
 *
 * Everything else in the scene reads its lighting from here - sun colour, fog
 * colour, exposure and how "night" it is - so the whole city stays coherent
 * when the time of day changes.
 *
 * Preset design note: the default is BLUE HOUR, not noon. The most captivating
 * cityscapes are shot in the ~20 minutes after sunset, when the sky still
 * holds a deep saturated blue while the windows have already switched on.
 * Full night loses the sky; full day loses the lights. Blue hour has both.
 */

export const SKY_PRESETS = [
    {
        id: 'blue-hour',
        label: 'blue hour',
        elevation: -1.4,          // sun just under the horizon
        azimuth: 172,
        turbidity: 6.5,
        rayleigh: 2.6,            // high rayleigh = deep saturated blue overhead
        mieCoefficient: 0.006,
        mieDirectionalG: 0.86,
        exposure: 0.55,
        night: 0.88,              // window lights nearly full
        sunColor: 0xffb37a,
        sunIntensity: 0.9,
        hemiSky: 0x4a68a8,
        hemiGround: 0x11151f,
        hemiIntensity: 1.35,      // dusk sky is a huge soft source; without a
                                  // strong hemi the walls read as black voids
        fog: 0x172440,
        fogDensity: 0.0016,
    },
    {
        id: 'golden',
        label: 'golden hour',
        elevation: 3.2,
        azimuth: 168,
        turbidity: 8.5,
        rayleigh: 2.2,
        mieCoefficient: 0.009,
        mieDirectionalG: 0.88,    // strong forward scattering = glow around sun
        exposure: 0.36,
        night: 0.22,
        sunColor: 0xffc08a,
        sunIntensity: 2.1,
        hemiSky: 0x8ab4ff,
        hemiGround: 0x1a1207,
        hemiIntensity: 0.5,
        fog: 0x2e2a33,
        fogDensity: 0.0018,
    },
    {
        id: 'night',
        label: 'night',
        elevation: -8.0,
        azimuth: 190,
        turbidity: 3.0,
        rayleigh: 0.9,
        mieCoefficient: 0.004,
        mieDirectionalG: 0.8,
        exposure: 0.52,
        night: 1.0,
        sunColor: 0x8fa6d8,       // moonlight, not sunlight
        sunIntensity: 0.45,
        hemiSky: 0x2a3a5c,
        hemiGround: 0x07090f,
        hemiIntensity: 0.8,
        fog: 0x070a12,
        fogDensity: 0.0026,
    },
    {
        id: 'day',
        label: 'clear day',
        elevation: 34,
        azimuth: 150,
        turbidity: 4.5,
        rayleigh: 1.4,
        mieCoefficient: 0.005,
        mieDirectionalG: 0.8,
        exposure: 0.30,
        night: 0.0,
        sunColor: 0xfff4e0,
        sunIntensity: 2.6,
        hemiSky: 0xbcd8ff,
        hemiGround: 0x2a2f38,
        hemiIntensity: 0.7,
        fog: 0x9fb4cf,
        fogDensity: 0.0012,
    },
];

const _sunPos = new THREE.Vector3();

function starField(radius) {
    const COUNT = 2200;
    const pos = new Float32Array(COUNT * 3);
    const size = new Float32Array(COUNT);
    // Deterministic PRNG: the same sky every load, so screenshots reproduce.
    let seed = 20260813;
    const rnd = () => {
        seed = (seed * 1664525 + 1013904223) >>> 0;
        return seed / 4294967296;
    };
    for (let i = 0; i < COUNT; i++) {
        // Only the upper hemisphere - stars below the horizon are never seen
        // and would show through the ground on a low camera.
        const u = rnd() * 2 - 1;
        const phi = rnd() * Math.PI * 2;
        const y = Math.abs(u) * 0.9 + 0.06;
        const r = Math.sqrt(1 - y * y);
        pos[i * 3] = Math.cos(phi) * r * radius;
        pos[i * 3 + 1] = y * radius;
        pos[i * 3 + 2] = Math.sin(phi) * r * radius;
        const m = rnd();
        size[i] = (m * m * 2.6 + 0.5) * (radius / 900);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1));

    const mat = new THREE.ShaderMaterial({
        uniforms: {
            uOpacity: { value: 0 },
            uTime: { value: 0 },
            uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
        },
        vertexShader: /* glsl */`
            attribute float aSize;
            uniform float uTime;
            uniform float uPixelRatio;
            varying float vTwinkle;
            void main() {
                vec4 mv = modelViewMatrix * vec4(position, 1.0);
                // slow, per-star desynchronised twinkle
                vTwinkle = 0.75 + 0.25 * sin(uTime * 1.7 + position.x * 0.07 + position.z * 0.11);
                gl_PointSize = aSize * uPixelRatio * 2.2;
                gl_Position = projectionMatrix * mv;
            }
        `,
        fragmentShader: /* glsl */`
            uniform float uOpacity;
            varying float vTwinkle;
            void main() {
                float d = length(gl_PointCoord - 0.5);
                float a = smoothstep(0.5, 0.06, d);
                if (a <= 0.001 || uOpacity <= 0.001) discard;
                gl_FragColor = vec4(vec3(1.0, 0.97, 0.92), a * uOpacity * vTwinkle);
            }
        `,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
    });

    const points = new THREE.Points(geo, mat);
    points.frustumCulled = false;
    points.renderOrder = -1;
    return points;
}

export function createSky(scene, renderer, worldSize, farPlane) {
    const sky = new Sky();
    // The sky is a box: its corners reach scale * 0.87. Scaled past the far
    // plane it is clipped away entirely and the "sky" renders as black - which
    // is exactly what happened the first time this shipped.
    // 0.85 of the far plane: the box corners reach 0.87 of its scale, so this
    // puts them just inside the frustum. Smaller than this and the camera can
    // see the box's own edges as a seam across the sky.
    const skyScale = farPlane ? farPlane * 0.85 : worldSize * 8;
    sky.scale.setScalar(skyScale);
    scene.add(sky);

    const stars = starField(skyScale * 0.42);
    scene.add(stars);

    const sun = new THREE.DirectionalLight(0xffffff, 1);
    sun.position.set(1, 1, 1);
    scene.add(sun);
    scene.add(sun.target);

    const hemi = new THREE.HemisphereLight(0xffffff, 0x000000, 0.5);
    scene.add(hemi);

    // Deep blue ambient fill so unlit faces read as "in shadow at dusk"
    // rather than as black holes.
    const ambient = new THREE.AmbientLight(0x3a4a72, 0.55);
    scene.add(ambient);

    scene.fog = new THREE.FogExp2(0x141d33, 0.0022);

    let index = 0;
    const state = { night: 0, preset: SKY_PRESETS[0] };

    function apply(preset) {
        const u = sky.material.uniforms;
        u.turbidity.value = preset.turbidity;
        u.rayleigh.value = preset.rayleigh;
        u.mieCoefficient.value = preset.mieCoefficient;
        u.mieDirectionalG.value = preset.mieDirectionalG;

        const phi = THREE.MathUtils.degToRad(90 - preset.elevation);
        const theta = THREE.MathUtils.degToRad(preset.azimuth);
        _sunPos.setFromSphericalCoords(1, phi, theta);
        u.sunPosition.value.copy(_sunPos);

        sun.position.copy(_sunPos).multiplyScalar(worldSize * 2);
        sun.color.setHex(preset.sunColor);
        sun.intensity = preset.sunIntensity;
        sun.target.position.set(worldSize / 2, 0, worldSize / 2);
        sun.target.updateMatrixWorld();

        hemi.color.setHex(preset.hemiSky);
        hemi.groundColor.setHex(preset.hemiGround);
        hemi.intensity = preset.hemiIntensity;

        scene.fog.color.setHex(preset.fog);
        scene.fog.density = preset.fogDensity * (400 / worldSize);

        renderer.toneMappingExposure = preset.exposure;
        stars.material.uniforms.uOpacity.value = Math.max(0, preset.night - 0.15);

        state.night = preset.night;
        state.preset = preset;
    }

    apply(SKY_PRESETS[0]);

    return {
        sun,
        state,
        get sunPosition() { return _sunPos; },
        cycle() {
            index = (index + 1) % SKY_PRESETS.length;
            apply(SKY_PRESETS[index]);
            return SKY_PRESETS[index];
        },
        set(id) {
            const i = SKY_PRESETS.findIndex((p) => p.id === id);
            if (i >= 0) { index = i; apply(SKY_PRESETS[i]); }
            return SKY_PRESETS[index];
        },
        update(t) {
            stars.material.uniforms.uTime.value = t;
        },
    };
}
