import * as THREE from 'three';

/**
 * Streets and the plane the city sits on.
 *
 * Rain-slick asphalt is the single cheapest trick for a cinematic city: a wet
 * road picks up the sky and the window glow and throws it back at grazing
 * angles, which is why night-city photography is almost always shot after
 * rain. Real reflections would cost a second render pass, so this fakes it
 * with a Fresnel term against the horizon colour plus a little procedural
 * puddling - one material, one draw call, no textures.
 */
export function createGround(worldSize, horizonColor) {
    const geo = new THREE.PlaneGeometry(worldSize * 6, worldSize * 6, 1, 1);
    geo.rotateX(-Math.PI / 2);

    const uniforms = {
        uHorizon: { value: new THREE.Color(horizonColor) },
        uAsphalt: { value: new THREE.Color(0x191f2b) },
        uGlow: { value: new THREE.Color(0xffb066) },
        uNight: { value: 0.88 },
        uTime: { value: 0 },
        uCenter: { value: new THREE.Vector2(worldSize / 2, worldSize / 2) },
        uExtent: { value: worldSize },
    };

    // `fog: true` makes three inject the fog chunks, but it does NOT add their
    // uniforms - a ShaderMaterial must supply them itself or the renderer
    // throws while refreshing fog uniforms. merge() deep-clones, so everything
    // downstream must use the merged object, not the literal above.
    const merged = THREE.UniformsUtils.merge([THREE.UniformsLib.fog, uniforms]);

    const mat = new THREE.ShaderMaterial({
        uniforms: merged,
        fog: true,
        vertexShader: /* glsl */`
            #include <fog_pars_vertex>
            varying vec3 vWorld;
            varying vec3 vView;
            void main() {
                vec4 wp = modelMatrix * vec4(position, 1.0);
                vWorld = wp.xyz;
                // Must be called mvPosition: the fog_vertex chunk reads it.
                vec4 mvPosition = viewMatrix * wp;
                vView = -mvPosition.xyz;
                gl_Position = projectionMatrix * mvPosition;
                #include <fog_vertex>
            }
        `,
        fragmentShader: /* glsl */`
            #include <fog_pars_fragment>
            uniform vec3 uHorizon;
            uniform vec3 uAsphalt;
            uniform vec3 uGlow;
            uniform float uNight;
            uniform float uTime;
            uniform vec2 uCenter;
            uniform float uExtent;
            varying vec3 vWorld;
            varying vec3 vView;

            float hash(vec2 p) {
                return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
            }
            float noise(vec2 p) {
                vec2 i = floor(p), f = fract(p);
                f = f * f * (3.0 - 2.0 * f);
                return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x),
                           mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
            }

            void main() {
                vec3 col = uAsphalt;

                // Coarse grain so the tarmac is not a flat fill. Detail fades
                // with distance: at 6x world size the high-frequency octave
                // aliased into visible moire stripes across the horizon.
                float dist = length(vWorld.xz - uCenter);
                float detail = 1.0 - smoothstep(uExtent * 0.6, uExtent * 1.6, dist);
                col += noise(vWorld.xz * 0.9) * 0.05 * detail
                     + noise(vWorld.xz * 5.0) * 0.02 * detail * detail;

                // Wetness pools unevenly, as it does after rain.
                float wet = smoothstep(0.35, 0.85, noise(vWorld.xz * 0.055 + 3.7)) * detail;

                // Fresnel: at grazing angles the wet surface turns into a mirror
                // of the sky; looking straight down it stays dark asphalt.
                vec3 V = normalize(vView);
                float fres = pow(1.0 - clamp(V.y, 0.0, 1.0), 4.0);

                col = mix(col, uHorizon * 1.15, fres * (0.25 + 0.55 * wet));

                // Spill of window light onto the street near the city footprint,
                // fading out past the built area.
                vec2 d = abs(vWorld.xz - uCenter) / (uExtent * 0.62);
                float inCity = 1.0 - smoothstep(0.75, 1.25, max(d.x, d.y));
                float shimmer = 0.55 + 0.45 * noise(vWorld.xz * 0.35 + uTime * 0.03) * detail;
                col += uGlow * inCity * uNight * (0.10 + 0.26 * wet * fres) * shimmer;

                gl_FragColor = vec4(col, 1.0);
                #include <fog_fragment>
            }
        `,
    });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.y = -0.12;
    mesh.receiveShadow = true;
    mesh.userData.uniforms = merged;
    return mesh;
}
