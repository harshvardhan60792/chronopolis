import { loadCity } from './data.js';
import { initScene } from './scene.js';
import { mountFps } from './fps.js';
import { runSelftest } from './selftest.js';
import { initUI } from './ui.js';
import { initPanel } from './panel.js';

async function main() {
    const urlParams = new URLSearchParams(window.location.search);
    
    if (urlParams.has('stats')) {
        mountFps();
    }
    initUI();
    initPanel();

    let cityData = null;
    try {
        cityData = await loadCity();
    } catch (e) {
        document.getElementById('dropzone').innerText = 'Failed to load city: ' + e.message;
        return;
    }

    if (!cityData) {
        document.getElementById('dropzone').innerText = 'No city loaded. Please run citygen or drag a city.json here.';
        return;
    }

    if (!cityData.schema || !cityData.schema.startsWith('chronopolis.city/')) {
        document.getElementById('dropzone').innerText = 'Invalid schema. Must be chronopolis.city/';
        return;
    }
    if (!cityData.layout || !cityData.layout.plots || cityData.layout.plots.length !== cityData.buildings.length) {
        document.getElementById('dropzone').innerText = 'Invalid or missing layout. Please re-run citygen.';
        return;
    }

    document.getElementById('dropzone').classList.add('hidden');
    initScene(cityData);
    
    if (urlParams.has('selftest')) {
        runSelftest();
    }
}

main();
