import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';

/**
 * Bloom.
 *
 * Lit windows and traffic are small bright points; without bloom they read as
 * flat coloured pixels, with it they read as light. It is the difference
 * between a diagram and a photograph.
 *
 * The cost is real (a downsampled blur chain), so: bloom runs at half
 * resolution, and `guard()` switches it off automatically if the frame rate
 * cannot afford it. The 30 fps bar wins over prettiness, always.
 */
export function createPostFX(renderer, scene, camera) {
    const size = renderer.getSize(new THREE.Vector2());

    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));

    const bloom = new UnrealBloomPass(
        new THREE.Vector2(size.x / 2, size.y / 2),
        0.34,   // strength - enough to halo the windows, not to wash out the city
        0.55,   // radius
        0.48,   // threshold: only genuinely bright things bloom. At 0.22 the
                // lit facades all crossed it and the city rendered as one
                // white blob with no architecture in it.
    );
    composer.addPass(bloom);
    composer.addPass(new OutputPass());

    let enabled = true;
    let autoDisabled = false;
    let samples = 0;
    let strikes = 0;
    const WARMUP_SAMPLES = 4;   // fps is sampled once a second

    return {
        composer,
        bloom,
        get enabled() { return enabled; },
        toggle() {
            enabled = !enabled;
            autoDisabled = false;
            return enabled;
        },
        setSize(w, h) {
            composer.setSize(w, h);
            bloom.setSize(w / 2, h / 2);
        },
        render() {
            if (enabled) composer.render();
            else renderer.render(scene, camera);
        },
        /**
         * Called with a rolling fps sample. One-way: once bloom has been
         * dropped for performance it stays off until the user asks for it
         * back, so the scene never oscillates between looks.
         */
        guard(fps) {
            // The first seconds are shader compilation and texture upload, not
            // steady-state cost. Judging bloom on those samples switched it off
            // on machines that could easily afford it, so: ignore the warm-up,
            // then require three consecutive bad samples before dropping.
            samples++;
            if (samples <= WARMUP_SAMPLES || !enabled || autoDisabled) return false;
            if (fps > 0 && fps < 32) strikes++;
            else strikes = 0;
            if (strikes >= 3) {
                enabled = false;
                autoDisabled = true;
                return true;
            }
            return false;
        },
    };
}
