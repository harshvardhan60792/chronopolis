import * as THREE from 'three';
import { createBuildings } from './buildings.js';
import { createDistricts } from './districts.js';
import { setupControls } from './controls.js';
import { createArcs } from './arcs.js';
import { updateArcsLegend, updateTrafficLegend } from './ui.js';
import { createTraffic } from './traffic.js';
import { setupPicking } from './picking.js';

export function initScene(cityData) {
    const world = cityData.layout.world;
    
    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x0b0e14, world.width * 0.5, world.width * 1.5);
    
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0); 
    document.body.appendChild(renderer.domElement);
    
    const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 1, world.width * 3);
    camera.position.set(world.width * 0.9, world.width * 0.55, world.depth * 0.9);
    
    const controls = setupControls(camera, renderer, world.width);
    
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x141922, 0.55);
    hemiLight.position.set(0, 200, 0);
    scene.add(hemiLight);
    
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.1);
    dirLight.position.set(1, 2, 1).normalize();
    scene.add(dirLight);
    
    const groundGeo = new THREE.PlaneGeometry(world.width * 5, world.depth * 5);
    const groundMat = new THREE.MeshLambertMaterial({ color: 0x141922 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.1;
    scene.add(ground);
    
    if (cityData.layout.districts) {
        const districtsMesh = createDistricts(cityData.layout.districts);
        scene.add(districtsMesh);
    }
    
    const buildingsMesh = createBuildings(cityData.buildings, cityData.layout.plots);
    scene.add(buildingsMesh);
    
    let arcsData = null;
    if (cityData.edges && cityData.edges.import) {
        arcsData = createArcs(cityData);
        scene.add(arcsData.mesh);
        updateArcsLegend(arcsData.initialVisible, cityData.edges.import.length, arcsData.truncated);
    }
    
    window.addEventListener('keydown', (e) => {
        if (e.key.toLowerCase() === 'i' && arcsData) {
            arcsData.mesh.visible = !arcsData.mesh.visible;
            updateArcsLegend(arcsData.mesh.visible, cityData.edges.import.length, arcsData.truncated);
        }
    });
    
    let trafficData = null;
    if (cityData.layout.roads && cityData.layout.roads.length > 0) {
        trafficData = createTraffic(cityData, 0.6);
        if (trafficData) {
            scene.add(trafficData.points);
            updateTrafficLegend(true, cityData.stats.traffic_source || 'cochange');
        }
    }
    
    window.addEventListener('keydown', (e) => {
        if (e.key.toLowerCase() === 't' && trafficData) {
            trafficData.points.visible = !trafficData.points.visible;
            updateTrafficLegend(trafficData.points.visible, cityData.stats.traffic_source || 'cochange');
        }
    });
    
    setupPicking(camera, renderer, scene, cityData, buildingsMesh, arcsData, controls);
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
    
    // Expose flyTo for console use per acceptance criteria
    window.flyTo = controls.flyTo;

    // Handle for the selftest harness (?selftest=1) and for debugging.
    window.__CHRONOPOLIS__ = {
        city: cityData, scene, camera, renderer,
        buildingsMesh, arcsData, trafficData, controls,
    };

    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        if (trafficData && trafficData.points.visible) {
            trafficData.update(performance.now() / 1000);
        }
        renderer.render(scene, camera);
    }
    animate();
}
