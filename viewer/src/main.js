import '../index.css';
import { loadCity } from './data.js';
import { initScene } from './scene.js';
import { mountFps } from './fps.js';
import { runSelftest } from './selftest.js';
import { initUI } from './ui.js';
import { initPanel } from './panel.js';
import { setupDropzone } from './dropzone.js';

async function main() {
    const urlParams = new URLSearchParams(window.location.search);
    
    if (urlParams.has('stats')) {
        mountFps();
    }
    initUI();
    initPanel();
    
    const dzContent = document.getElementById('dz-content');
    const dzLoading = document.getElementById('dz-loading');
    const dzError = document.getElementById('dz-error');

    function showError(msg) {
        dzContent.style.display = 'none';
        dzLoading.style.display = 'none';
        dzError.style.display = 'block';
        dzError.innerText = msg;
    }
    
    function showLoading(msg) {
        dzContent.style.display = 'none';
        dzError.style.display = 'none';
        dzLoading.style.display = 'block';
        dzLoading.innerText = msg;
    }

    async function handleCity(cityData) {
        if (!cityData) {
            showError('No city loaded.');
            return;
        }

        if (!cityData.schema || !cityData.schema.startsWith('chronopolis.city/')) {
            showError('This city was made by citygen (unknown); this viewer expects chronopolis.city/v1.');
            return;
        }
        if (!cityData.layout || !cityData.layout.plots || cityData.layout.plots.length !== cityData.buildings.length) {
            showError('This city has no layout. Re-run: python -m citygen build <repo>');
            return;
        }

        // WebGL check
        try {
            const canvas = document.createElement('canvas');
            if (!canvas.getContext('webgl2')) throw new Error();
        } catch(e) {
            showError('Your browser can\'t run WebGL2. Try Chrome or Firefox.');
            return;
        }

        showLoading(`building ${cityData.buildings.length.toLocaleString()} buildings...`);
        
        // Let UI update
        await new Promise(r => setTimeout(r, 50));
        
        document.getElementById('dropzone').classList.add('hidden');
        document.getElementById('home-btn').classList.remove('hidden');
        document.body.style.opacity = '0';
        document.body.style.transition = 'opacity 0.6s ease-in';
        
        initScene(cityData);
        
        // Give time for first render
        requestAnimationFrame(() => {
            document.body.style.opacity = '1';
        });
        
        if (urlParams.has('selftest')) {
            runSelftest();
        }
    }

    setupDropzone(handleCity, err => showError(err.message));

    // '?dropzone=1' is set by the "load a different city" button - it means
    // skip the auto-load below and go straight to the drop/select screen,
    // even though a city.json is available to auto-load.
    if (urlParams.has('dropzone')) {
        const url = new URL(window.location.href);
        url.searchParams.delete('dropzone');
        window.history.replaceState({}, '', url.toString());
        dzContent.style.display = 'block';
        dzLoading.style.display = 'none';
        dzError.style.display = 'none';
        return;
    }

    showLoading('downloading city.json...');
    let initialCity = null;
    try {
        initialCity = await loadCity();
    } catch (e) {
        showError('Failed to load city: ' + e.message);
        return;
    }

    if (initialCity) {
        handleCity(initialCity);
    } else {
        // No default city found, show the empty state
        dzContent.style.display = 'block';
        dzLoading.style.display = 'none';
        dzError.style.display = 'none';
    }
}

main();
