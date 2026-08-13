export function initUI() {
    const ui = document.getElementById('ui');
    ui.innerHTML = `
        <div id="controls-hint" style="background: rgba(0,0,0,0.7); padding: 8px 12px; border-radius: 4px; transition: opacity 0.3s; font-size: 13px;">
            <span id="hint-orbit">drag orbit · scroll zoom · F fly · K sky · B bloom · I arcs · T traffic</span>
            <span id="hint-fly" class="hidden">WASD move · mouse look · Space/Shift up-down · F exit · K sky · I arcs · T traffic</span>
        </div>
        <div id="sky-legend" class="legend" style="margin-top: 8px; background: rgba(0,0,0,0.7); padding: 4px 8px; border-radius: 4px; font-size: 11px;"></div>
        <div id="arcs-legend" class="legend hidden" style="margin-top: 8px; background: rgba(0,0,0,0.7); padding: 4px 8px; border-radius: 4px; font-size: 11px;"></div>
        <div id="traffic-legend" class="legend hidden" style="margin-top: 8px; background: rgba(0,0,0,0.7); padding: 4px 8px; border-radius: 4px; font-size: 11px;"></div>
    `;
    
    const hint = document.getElementById('controls-hint');
    
    setTimeout(() => {
        hint.style.opacity = '0.3';
    }, 8000);
    
    hint.addEventListener('mouseenter', () => hint.style.opacity = '1');
    hint.addEventListener('mouseleave', () => hint.style.opacity = '0.3');
    
    window.addEventListener('keydown', (e) => {
        if (e.key.toLowerCase() === 'h') {
            ui.classList.toggle('hidden');
        }
    });
}

export function updateUIForMode(mode) {
    const orbit = document.getElementById('hint-orbit');
    const fly = document.getElementById('hint-fly');
    if (!orbit || !fly) return;
    if (mode === 'fly') {
        orbit.classList.add('hidden');
        fly.classList.remove('hidden');
    } else {
        fly.classList.add('hidden');
        orbit.classList.remove('hidden');
    }
}

export function updateSkyLegend(label, bloomOn, autoDropped = false) {
    const el = document.getElementById('sky-legend');
    if (!el) return;
    let bloom = bloomOn ? 'bloom on' : 'bloom off';
    if (autoDropped) bloom = 'bloom off (dropped to hold frame rate)';
    el.innerText = `Sky: ${label} · ${bloom} · K to change`;
}

export function updateArcsLegend(visible, total, truncated) {
    const el = document.getElementById('arcs-legend');
    if (!el) return;
    if (visible) {
        el.classList.remove('hidden');
        if (truncated > 0) {
            el.innerText = `Arcs: top 2000 of ${truncated} imports`;
        } else {
            el.innerText = `Arcs: ${total} imports`;
        }
    } else {
        el.classList.add('hidden');
    }
}

export function updateTrafficLegend(visible, source) {
    const el = document.getElementById('traffic-legend');
    if (!el) return;
    if (visible) {
        el.classList.remove('hidden');
        if (source === 'imports') {
            el.innerText = 'Traffic: imports (history too shallow for co-change)';
        } else {
            el.innerText = 'Traffic: files that change together';
        }
    } else {
        el.classList.add('hidden');
    }
}
