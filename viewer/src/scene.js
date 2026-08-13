import * as THREE from 'three';
import { createBuildings } from './buildings.js';
import { createDistricts } from './districts.js';
import { setupControls } from './controls.js';
import { createArcs } from './arcs.js';
import { updateArcsLegend, updateTrafficLegend, updateSkyLegend } from './ui.js';
import { createTraffic } from './traffic.js';
import { setupPicking } from './picking.js';
import { createSky, SKY_PRESETS } from './sky.js';
import { createGround } from './ground.js';
import { createPostFX } from './postfx.js';
import { playIntro } from './intro.js';

export function initScene(cityData) {
    const world = cityData.layout.world;

    const scene = new THREE.Scene();

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    // Filmic tone mapping is what stops bright windows from clipping to white
    // and gives the sky its photographic roll-off. Without it the scattering
    // maths above renders as a flat poster.
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.42;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    document.body.appendChild(renderer.domElement);

    const camera = new THREE.PerspectiveCamera(
        50, window.innerWidth / window.innerHeight, 0.6, world.width * 14);
    camera.position.set(world.width * 0.6, world.width * 0.24, world.depth * 0.6);

    const controls = setupControls(camera, renderer, world.width);

    const sky = createSky(scene, renderer, world.width, camera.far);
    const ground = createGround(world.width, SKY_PRESETS[0].fog);
    scene.add(ground);

    if (cityData.layout.districts) {
        scene.add(createDistricts(cityData.layout.districts));
    }

    const buildingsMesh = createBuildings(cityData.buildings, cityData.layout.plots);
    scene.add(buildingsMesh);

    let arcsData = null;
    if (cityData.edges && cityData.edges.import) {
        arcsData = createArcs(cityData);
        scene.add(arcsData.mesh);
        updateArcsLegend(arcsData.initialVisible, cityData.edges.import.length, arcsData.truncated);
    }

    let trafficData = null;
    if (cityData.layout.roads && cityData.layout.roads.length > 0) {
        trafficData = createTraffic(cityData, 0.6);
        if (trafficData) {
            scene.add(trafficData.points);
            updateTrafficLegend(true, cityData.stats.traffic_source || 'cochange');
        }
    }

    const postfx = createPostFX(renderer, scene, camera);
    updateSkyLegend(SKY_PRESETS[0].label, postfx.enabled);

    // Keep every look-dependent uniform in one place so a sky change updates
    // the buildings and the street in the same frame.
    const facade = buildingsMesh.userData.uniforms;
    const groundU = ground.userData.uniforms;

    function syncLook(preset) {
        facade.uNight.value = preset.night;
        groundU.uNight.value = preset.night;
        groundU.uHorizon.value.setHex(preset.fog);
        postfx.bloom.strength = 0.18 + 0.24 * preset.night;
    }
    syncLook(SKY_PRESETS[0]);

    window.addEventListener('keydown', (e) => {
        const k = e.key.toLowerCase();
        if (k === 'i' && arcsData) {
            arcsData.mesh.visible = !arcsData.mesh.visible;
            updateArcsLegend(arcsData.mesh.visible, cityData.edges.import.length, arcsData.truncated);
        } else if (k === 't' && trafficData) {
            trafficData.points.visible = !trafficData.points.visible;
            updateTrafficLegend(trafficData.points.visible, cityData.stats.traffic_source || 'cochange');
        } else if (k === 'k') {
            const preset = sky.cycle();
            syncLook(preset);
            updateSkyLegend(preset.label, postfx.enabled);
        } else if (k === 'b') {
            updateSkyLegend(sky.state.preset.label, postfx.toggle());
        }
    });

    setupPicking(camera, renderer, scene, cityData, buildingsMesh, arcsData, controls);

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
        postfx.setSize(window.innerWidth, window.innerHeight);
    });

    window.flyTo = controls.flyTo;
    window.__CHRONOPOLIS__ = {
        city: cityData, scene, camera, renderer,
        buildingsMesh, arcsData, trafficData, controls, sky, postfx,
    };

    playIntro(camera, controls, world);

    // --- render loop: no allocation, no branching beyond visibility ---------
    let last = performance.now();
    let acc = 0;
    let frames = 0;
    let fps = 60;

    function animate() {
        requestAnimationFrame(animate);
        const now = performance.now();
        const t = now / 1000;

        acc += now - last;
        last = now;
        frames++;
        if (acc >= 1000) {
            fps = (frames * 1000) / acc;
            acc = 0;
            frames = 0;
            if (postfx.guard(fps)) {
                updateSkyLegend(sky.state.preset.label, false, true);
            }
        }

        controls.update();
        facade.uTime.value = t;
        groundU.uTime.value = t;
        sky.update(t);
        if (trafficData && trafficData.points.visible) trafficData.update(t);

        postfx.render();
    }
    animate();
}
