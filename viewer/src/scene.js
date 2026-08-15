import * as THREE from 'three';
import { createBuildings } from './buildings.js';
import { createDistricts } from './districts.js';
import { setupControls } from './controls.js';
import { createArcs } from './arcs.js';
import { updateArcsLegend, updateTrafficLegend, updateSkyLegend } from './ui.js';
import { createTraffic } from './traffic.js';
import { setupPicking } from './picking.js';
import { createSky, SKY_PRESETS } from './sky.js';
import { createTerrain } from './terrain.js';
import { createNature } from './nature.js';
import { createClouds } from './clouds.js';
import { createPostFX } from './postfx.js';
import { playIntro } from './intro.js';
import { createTimeline } from './timeline.js';
import { mountTimeline } from './timelineui.js';
import { OverlayManager, MODES } from './overlays.js';
import { Legend } from './legend.js';
import { Search } from './search.js';
import { Tour } from './tour.js';
import { exportPNG } from './export.js';

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
    camera.position.set(
        world.width * 1.38, world.width * 0.46, world.depth * 1.38);

    const controls = setupControls(camera, renderer, world.width);

    const sky = createSky(scene, renderer, world.width, camera.far);
    const terrain = createTerrain(world.width, SKY_PRESETS[0].fog);
    scene.add(terrain);

    const clouds = createClouds(world.width);
    scene.add(clouds);

    if (cityData.layout.districts) {
        scene.add(createDistricts(cityData.layout.districts));
    }

    // Green cover is inversely proportional to how built-up a district is, so
    // the quiet parts of the repo literally look like parkland.
    const nature = createNature(cityData, world.width);
    scene.add(nature);

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
            // Slow the flow right down. Fast particles across the whole map
            // are peripheral motion the eye cannot stop tracking; at a third
            // of the speed the same information reads as a calm current.
            const tu = trafficData.points.material.uniforms;
            if (tu && tu.uSpeedScale) tu.uSpeedScale.value *= 0.35;
            scene.add(trafficData.points);
            updateTrafficLegend(true, cityData.stats.traffic_source || 'cochange');
        }
    }

    const postfx = createPostFX(renderer, scene, camera);
    updateSkyLegend(SKY_PRESETS[0].label, postfx.enabled);

    // Must read the ORIGINAL query string before constructing anything that
    // rewrites it (OverlayManager does, via setMode's replaceState) - see the
    // comment in overlays.js.
    const urlParams = new URLSearchParams(window.location.search);
    const modeParam = urlParams.get('mode');
    let initialMode = 1;
    if (modeParam) {
        for (const [id, m] of Object.entries(MODES)) {
            if (m.key === modeParam) initialMode = parseInt(id);
        }
    }

    const overlays = new OverlayManager(cityData, buildingsMesh, initialMode);
    const legend = new Legend(document.getElementById('ui2'), cityData);
    legend.render(initialMode);

    // Keep every look-dependent uniform in one place so a sky change updates
    // the buildings and the street in the same frame.
    const facade = buildingsMesh.userData.uniforms;
    const land = terrain.userData.uniforms.land;
    const sea = terrain.userData.uniforms.sea;

    function syncLook(preset) {
        facade.uNight.value = preset.night;
        land.uNight.value = preset.night;
        sea.uNight.value = preset.night;
        land.uHorizon.value.setHex(preset.fog);
        sea.uHorizon.value.setHex(preset.fog);
        clouds.userData.material.opacity = 0.34 * (1 - preset.night * 0.75);
        // Bloom only ever earns its cost at night, and even then gently.
        postfx.bloom.strength = 0.10 + 0.22 * preset.night;
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
        } else if (k === 'p') {
            exportPNG(cityData, renderer, scene, camera, postfx, overlays, timeline);
        }
        
        const modeNum = parseInt(k);
        if (modeNum >= 1 && modeNum <= 6) {
            overlays.setMode(modeNum);
            legend.render(modeNum);
        }
    });

    const picking = setupPicking(camera, renderer, scene, cityData, buildingsMesh, arcsData, controls);

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
        postfx.setSize(window.innerWidth, window.innerHeight);
    });

    window.flyTo = controls.flyTo;

    const search = new Search(cityData, controls, buildingsMesh);
    const tour = new Tour(cityData, controls, buildingsMesh);

    const timeline = createTimeline(cityData, buildingsMesh);
    if (timeline) {
        mountTimeline(timeline);
        window.addEventListener('keydown', (e) => {
            if (e.key.toLowerCase() === 'r' && !e.metaKey && !e.ctrlKey) timeline.toNow();
        });

        // Arcs and traffic must not show relationships for files that do not
        // exist yet on the timeline. Runs once per snapshot change (a few
        // times a second at most while playing), never per frame.
        const importEdges = cityData.edges.import || [];
        timeline.onChange = () => {
            if (arcsData && importEdges.length) {
                const colorAttr = arcsData.mesh.geometry.attributes.color;
                const defAttr = arcsData.mesh.geometry.attributes.defaultColor;
                for (let idx = 0; idx < importEdges.length; idx++) {
                    const start = arcsData.arcSegmentRange[idx * 2];
                    const end = arcsData.arcSegmentRange[idx * 2 + 1];
                    if (start < 0) continue;   // truncated out of the mesh
                    const [a, b] = importEdges[idx];
                    const mult = (timeline.isVisible(a) && timeline.isVisible(b)) ? 1 : 0;
                    for (let v = start; v <= end; v++) {
                        colorAttr.array[v * 3] = defAttr.array[v * 3] * mult;
                        colorAttr.array[v * 3 + 1] = defAttr.array[v * 3 + 1] * mult;
                        colorAttr.array[v * 3 + 2] = defAttr.array[v * 3 + 2] * mult;
                    }
                }
                colorAttr.needsUpdate = true;
            }
            if (trafficData) trafficData.updateAliveMask(timeline.isVisible);
        };
    }

    window.__CHRONOPOLIS__ = {
        city: cityData, scene, camera, renderer,
        buildingsMesh, arcsData, trafficData, controls, sky, postfx, timeline, picking,
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
        if (timeline) timeline.update(now);
        facade.uTime.value = t;
        sea.uTime.value = t;
        clouds.userData.update(t);
        sky.update(t);
        if (trafficData && trafficData.points.visible) trafficData.update(t);

        overlays.update();

        postfx.render();
    }
    animate();
}
