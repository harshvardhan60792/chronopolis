import * as THREE from 'three';
import { environmentColors } from './palette.js';

/**
 * The land the city stands on: earth, grass and water.
 *
 * Design rule for this whole module: **low spatial frequency, slow or no
 * motion**. Attention Restoration Theory calls the restful kind of attention
 * "soft fascination" - gentle, broad, unhurried stimuli that hold the eye
 * without demanding focus. High-frequency noise, flicker and shimmer are the
 * opposite (hard fascination) and are exactly what made the first night-city
 * version tiring to look at. Everything here varies over tens of world units,
 * never over pixels.
 *
 * It is also the readability floor for the whole tool: buildings are coloured
 * by language, health or ownership, and those colours have to survive against
 * this. So the ground stays desaturated and mid-dark - a muted olive-green
 * earth - and never competes with the data.
 */
export function createTerrain(worldSize, horizonColor) {
    const group = new THREE.Group();

    // --- land ---------------------------------------------------------------
    const landSize = worldSize * 7;
    const landGeo = new THREE.PlaneGeometry(landSize, landSize, 1, 1);
    landGeo.rotateX(-Math.PI / 2);

    const landUniforms = {
        uHorizon: { value: new THREE.Color(horizonColor) },
        uGrass: { value: new THREE.Color(environmentColors.grass) },
        uEarth: { value: new THREE.Color(environmentColors.earth) },
        uCenter: { value: new THREE.Vector2(worldSize / 2, worldSize / 2) },
        uExtent: { value: worldSize },
        uNight: { value: 0.0 },
    };

    const landMat = new THREE.ShaderMaterial({
        uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, landUniforms]),
        fog: true,
        vertexShader: /* glsl */`
            #include <fog_pars_vertex>
            varying vec3 vWorld;
            void main() {
                vec4 wp = modelMatrix * vec4(position, 1.0);
                vWorld = wp.xyz;
                vec4 mvPosition = viewMatrix * wp;
                gl_Position = projectionMatrix * mvPosition;
                #include <fog_vertex>
            }
        `,
        fragmentShader: /* glsl */`
            #include <fog_pars_fragment>
            uniform vec3 uHorizon;
            uniform vec3 uGrass;
            uniform vec3 uEarth;
            uniform vec2 uCenter;
            uniform float uExtent;
            uniform float uNight;
            varying vec3 vWorld;

            float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
            float noise(vec2 p) {
                vec2 i = floor(p), f = fract(p);
                f = f * f * (3.0 - 2.0 * f);
                return mix(mix(hash(i), hash(i + vec2(1,0)), f.x),
                           mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), f.x), f.y);
            }

            void main() {
                // Two very low-frequency octaves only. Meadows read as soft
                // patches of colour at this scale, and nothing shimmers when
                // the camera moves.
                float broad = noise(vWorld.xz * 0.006);
                float mid   = noise(vWorld.xz * 0.021);
                float mix1  = clamp(broad * 0.7 + mid * 0.3, 0.0, 1.0);

                vec3 col = mix(uGrass, uEarth, smoothstep(0.45, 0.85, mix1));
                col *= 0.86 + 0.24 * mid;

                // Aerial perspective: land washes toward the horizon colour
                // with distance. This is what stops the ground reading as a
                // flat cut-out disc floating in space.
                float d = length(vWorld.xz - uCenter) / (uExtent * 4.0);
                col = mix(col, uHorizon, clamp(d * d, 0.0, 0.55));

                col *= mix(1.0, 0.34, uNight);

                gl_FragColor = vec4(col, 1.0);
                #include <fog_fragment>
            }
        `,
    });

    const land = new THREE.Mesh(landGeo, landMat);
    land.position.y = -0.14;
    land.receiveShadow = true;
    group.add(land);

    // --- water --------------------------------------------------------------
    // A calm sea beyond the land, well past the city. Water is the single
    // strongest "this is a real place" cue available for one draw call, and a
    // horizon that ends in water reads as Earth rather than as a diorama.
    const seaGeo = new THREE.PlaneGeometry(landSize * 3.4, landSize * 3.4, 1, 1);
    seaGeo.rotateX(-Math.PI / 2);

    const seaUniforms = {
        uHorizon: { value: new THREE.Color(horizonColor) },
        uDeep: { value: new THREE.Color(environmentColors.sea) },
        uTime: { value: 0 },
        uNight: { value: 0.0 },
    };

    const seaMat = new THREE.ShaderMaterial({
        uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, seaUniforms]),
        fog: true,
        vertexShader: landMat.vertexShader,
        fragmentShader: /* glsl */`
            #include <fog_pars_fragment>
            uniform vec3 uHorizon;
            uniform vec3 uDeep;
            uniform float uTime;
            uniform float uNight;
            varying vec3 vWorld;

            float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
            float noise(vec2 p) {
                vec2 i = floor(p), f = fract(p);
                f = f * f * (3.0 - 2.0 * f);
                return mix(mix(hash(i), hash(i+vec2(1,0)), f.x),
                           mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y);
            }

            void main() {
                // One slow swell. Period is minutes, not seconds: fast water
                // sparkle is hard fascination and the eye cannot ignore it.
                float swell = noise(vWorld.xz * 0.004 + vec2(uTime * 0.006, 0.0));
                vec3 col = mix(uDeep, uHorizon, 0.35 + 0.28 * swell);
                col *= mix(1.0, 0.4, uNight);
                gl_FragColor = vec4(col, 1.0);
                #include <fog_fragment>
            }
        `,
    });

    const sea = new THREE.Mesh(seaGeo, seaMat);
    sea.position.y = -1.6;      // below the land so the coast is a clean edge
    group.add(sea);

    group.userData.uniforms = { land: land.material.uniforms, sea: sea.material.uniforms };
    return group;
}
