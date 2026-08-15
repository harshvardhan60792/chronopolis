import * as THREE from 'three';
import { langPalette } from './palette.js';

// Viridis-like ramp (dark blue -> teal -> yellow) for sequential data
function viridis(t) {
    t = Math.max(0, Math.min(1, t));
    const c0 = new THREE.Color(0x3a0d59);
    const c1 = new THREE.Color(0x31648a);
    const c2 = new THREE.Color(0x1fb589);
    const c3 = new THREE.Color(0xf6e846);
    
    if (t < 0.333) return c0.lerp(c1, t * 3.0);
    if (t < 0.666) return c1.lerp(c2, (t - 0.333) * 3.0);
    return c2.lerp(c3, (t - 0.666) * 3.0);
}

// Health/Bus ramp (green -> amber -> red)
function alertRamp(t) {
    t = Math.max(0, Math.min(1, t));
    const green = new THREE.Color(0x3db55c);
    const amber = new THREE.Color(0xf5b231);
    const red = new THREE.Color(0xdf352b);
    
    // Top 5% is red. (t >= 0.95)
    if (t >= 0.95) return red;
    // 0 to 0.95 goes green to amber
    const nt = t / 0.95;
    return green.lerp(amber, nt);
}

const HUE_PALETTE = [
    0x4285F4, 0xEA4335, 0xFBBC05, 0x34A853, 
    0x8AB4F8, 0xF28B82, 0xFDD663, 0x81C995
].map(c => new THREE.Color(c));

export const MODES = {
    1: { name: 'Language', key: 'lang' },
    2: { name: 'Health', key: 'health' },
    3: { name: 'Recency', key: 'recency' },
    4: { name: 'Ownership', key: 'owner' },
    5: { name: 'Bus factor', key: 'bus' },
    6: { name: 'Complexity', key: 'complexity' }
};

export class OverlayManager {
    constructor(city, mesh, initialMode = 1) {
        this.city = city;
        this.mesh = mesh;
        this.n = city.buildings.length;
        this.currentColors = new Float32Array(this.n * 3);
        this.targetColors = new Float32Array(this.n * 3);
        this.modeColors = new Map(); // mode -> Float32Array
        this.activeMode = 1;
        this.transitionStart = 0;
        
        this.gitMissing = !city.git || city.git.commit_count === 0;

        // Initialize base colors directly from the mesh (Language mode)
        const attr = this.mesh.instanceColor || new THREE.InstancedBufferAttribute(new Float32Array(this.n * 3), 3);
        if (this.mesh.instanceColor) {
            this.currentColors.set(this.mesh.instanceColor.array);
        } else {
            this.mesh.instanceColor = attr;
        }
        
        this._precompute();
        // Applying the default mode here rewrites `?mode=` in the URL via
        // setMode()'s history.replaceState call. If a caller wants to honour
        // a deep link, it must pass that mode in - reading the URL again
        // after construction is too late, it has already been overwritten.
        this.setMode(initialMode, true);
    }

    _precompute() {
        // Mode 1: Language
        const mode1 = new Float32Array(this.n * 3);
        for (let i = 0; i < this.n; i++) {
            const b = this.city.buildings[i];
            const c = langPalette[b.lang] || langPalette.other;
            mode1[i * 3] = c.r; mode1[i * 3 + 1] = c.g; mode1[i * 3 + 2] = c.b;
        }
        this.modeColors.set(1, mode1);

        // Mode 2: Health
        const mode2 = new Float32Array(this.n * 3);
        for (let i = 0; i < this.n; i++) {
            const b = this.city.buildings[i];
            const h = b.health || 0; // 0..1 percentile-rank composite
            const c = alertRamp(h);
            mode2[i * 3] = c.r; mode2[i * 3 + 1] = c.g; mode2[i * 3 + 2] = c.b;
        }
        this.modeColors.set(2, mode2);

        // Mode 3: Recency
        const mode3 = new Float32Array(this.n * 3);
        if (!this.gitMissing) {
            for (let i = 0; i < this.n; i++) {
                const b = this.city.buildings[i];
                if (b.stale_days == null) {
                    const c = viridis(1.0); // cold
                    mode3[i * 3] = c.r; mode3[i * 3 + 1] = c.g; mode3[i * 3 + 2] = c.b;
                    continue;
                }
                const t = Math.min(1, b.stale_days / 730);
                const c = viridis(t);
                mode3[i * 3] = c.r; mode3[i * 3 + 1] = c.g; mode3[i * 3 + 2] = c.b;
            }
        }
        this.modeColors.set(3, mode3);

        // Mode 4: Ownership
        const mode4 = new Float32Array(this.n * 3);
        if (!this.gitMissing) {
            for (let i = 0; i < this.n; i++) {
                const b = this.city.buildings[i];
                let c = new THREE.Color(0x777777); 
                if (b.owner != null && b.owner < 8) {
                    c = HUE_PALETTE[b.owner].clone();
                    c.lerp(new THREE.Color(0x777777), 1.0 - (b.owner_share || 1));
                }
                mode4[i * 3] = c.r; mode4[i * 3 + 1] = c.g; mode4[i * 3 + 2] = c.b;
            }
        }
        this.modeColors.set(4, mode4);

        // Mode 5: Bus factor
        const mode5 = new Float32Array(this.n * 3);
        if (!this.gitMissing) {
            const sizes = this.city.buildings.map(b => b.loc || 0);
            for (let i = 0; i < this.n; i++) {
                const b = this.city.buildings[i];
                let c = new THREE.Color(0x555555); // untouched
                if (b.commits > 0) {
                    if (b.bus_factor === 1) c = alertRamp(1.0); // red
                    else if (b.bus_factor === 2) c = alertRamp(0.5); // amber
                    else c = alertRamp(0.0); // green
                    
                    // size-weighted muting (small red files are less red)
                    const s = Math.min(1, Math.log1p(b.loc || 0) / Math.log1p(500));
                    c.lerp(new THREE.Color(0x555555), 1.0 - s);
                }
                mode5[i * 3] = c.r; mode5[i * 3 + 1] = c.g; mode5[i * 3 + 2] = c.b;
            }
        }
        this.modeColors.set(5, mode5);

        // Mode 6: Complexity
        const mode6 = new Float32Array(this.n * 3);
        const cxs = this.city.buildings.map(b => b.complexity || 0).sort((a, b) => a - b);
        function rank(v) {
            if (cxs.length === 0) return 0;
            let low = 0, high = cxs.length;
            while (low < high) {
                const mid = (low + high) >>> 1;
                if (cxs[mid] < v) low = mid + 1;
                else high = mid;
            }
            return low / cxs.length;
        }
        for (let i = 0; i < this.n; i++) {
            const b = this.city.buildings[i];
            const pct = rank(b.complexity || 0);
            const c = viridis(pct);
            mode6[i * 3] = c.r; mode6[i * 3 + 1] = c.g; mode6[i * 3 + 2] = c.b;
        }
        this.modeColors.set(6, mode6);
    }

    setMode(mode, immediate = false) {
        if (!this.modeColors.has(mode)) return;
        if (this.gitMissing && [3, 4, 5].includes(mode)) return; // prevent setting git modes if no git
        
        this.activeMode = mode;
        const target = this.modeColors.get(mode);
        this.targetColors.set(target);

        if (immediate) {
            this.currentColors.set(target);
            this.mesh.instanceColor.array.set(target);
            this.mesh.instanceColor.needsUpdate = true;
            this.transitionStart = 0;
        } else {
            this.transitionStart = performance.now();
        }
        
        // Update URL
        const url = new URL(window.location);
        url.searchParams.set('mode', MODES[mode].key);
        window.history.replaceState({}, '', url);
    }

    update() {
        if (!this.transitionStart) return;

        const now = performance.now();
        const elapsed = now - this.transitionStart;
        const duration = 250; // 250ms cross-fade

        if (elapsed >= duration) {
            this.mesh.instanceColor.array.set(this.targetColors);
            this.currentColors.set(this.targetColors);
            this.mesh.instanceColor.needsUpdate = true;
            this.transitionStart = 0;
            return;
        }

        const t = elapsed / duration;
        const out = this.mesh.instanceColor.array;
        for (let i = 0; i < out.length; i++) {
            out[i] = this.currentColors[i] + (this.targetColors[i] - this.currentColors[i]) * t;
        }
        this.mesh.instanceColor.needsUpdate = true;
    }
}
