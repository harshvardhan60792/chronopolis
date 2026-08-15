import * as THREE from 'three';

/**
 * The time machine.
 *
 * Replays the repository's history by moving building heights only. Plots
 * never move: citygen laid the city out over every file that ever existed,
 * weighted by its largest historical size (ADR-003), so scrubbing the clock
 * grows and shrinks the skyline instead of reshuffling it. That spatial
 * persistence is the whole reason the animation is readable.
 *
 * Deleted files sink and grey out rather than vanishing (ADR-008) - an empty
 * lot where a district used to be is information.
 *
 * Performance: heights live in plain Float32Arrays, and each frame writes
 * instance matrices only for the buildings whose height actually changed,
 * setting needsUpdate once.
 */

const EASE_MS = 420;
const PLAY_MS = 700;          // one snapshot per this many ms at 1x
const KEYFRAME_EVERY = 8;     // full-state cache stride for backwards seeking

export function createTimeline(city, buildingsMesh) {
    const snaps = city.snapshots;
    if (!snaps || !snaps.delta || snaps.delta.length < 2) return null;

    const n = city.buildings.length;
    const count = snaps.delta.length;
    const plots = city.layout.plots;

    // state: 0 = not yet born, 1 = alive, 2 = ruin
    const target = new Float32Array(n);
    const current = new Float32Array(n);
    const state = new Uint8Array(n);
    const finalHeight = new Float32Array(n);
    for (let i = 0; i < n; i++) finalHeight[i] = plots[i] ? plots[i].h : 0;

    // Cache a full state every KEYFRAME_EVERY snapshots so seeking backwards
    // is as cheap as seeking forwards; replaying from zero each time made the
    // slider stutter on long histories.
    const keyframes = new Map();

    function applyDelta(k) {
        const d = snaps.delta[k];
        for (const i of d.born) state[i] = 1;
        for (const i of d.died) state[i] = 2;
        for (const [i, h] of d.h) target[i] = h;
    }

    function rebuildTo(index) {
        target.fill(0);
        state.fill(0);
        let start = 0;
        for (let k = Math.floor(index / KEYFRAME_EVERY) * KEYFRAME_EVERY; k >= 0; k -= KEYFRAME_EVERY) {
            const kf = keyframes.get(k);
            if (kf) {
                target.set(kf.target);
                state.set(kf.state);
                start = k + 1;
                break;
            }
        }
        for (let k = start; k <= index; k++) {
            applyDelta(k);
            if (k % KEYFRAME_EVERY === 0 && !keyframes.has(k)) {
                keyframes.set(k, {
                    target: Float32Array.from(target),
                    state: Uint8Array.from(state),
                });
            }
        }
    }

    const dummy = new THREE.Object3D();
    const dirty = new Set();

    function writeInstance(i) {
        const p = plots[i];
        if (!p) return;
        let h = current[i];
        if (state[i] === 0) h = 0;
        else if (state[i] === 2) h = Math.max(0.6, h * 0.4);   // sunken ruin
        dummy.position.set(p.x + p.w / 2, 0, p.z + p.d / 2);
        dummy.scale.set(p.w, Math.max(h, 0.0001), p.d);
        dummy.updateMatrix();
        buildingsMesh.setMatrixAt(i, dummy.matrix);
    }

    let index = count - 1;
    let live = false;           // false = showing 'now', timeline not engaged
    let playing = false;
    let lastPlay = 0;
    let animatingUntil = 0;

    function seek(i, instant = false) {
        index = Math.max(0, Math.min(count - 1, i));
        live = true;
        rebuildTo(index);
        for (let k = 0; k < n; k++) {
            if (state[k] === 0) target[k] = 0;
            if (instant) current[k] = target[k];
            if (current[k] !== target[k] || instant) dirty.add(k);
        }
        animatingUntil = performance.now() + EASE_MS;
        if (instant) flushAll();
        onChange(index);
    }

    function flushAll() {
        for (let i = 0; i < n; i++) writeInstance(i);
        buildingsMesh.instanceMatrix.needsUpdate = true;
        dirty.clear();
    }

    /** Return to the present: heights from the static layout, no ruins sunk. */
    function toNow() {
        live = false;
        playing = false;
        for (let i = 0; i < n; i++) {
            if (city.buildings[i] && city.buildings[i].deleted) {
                state[i] = 0;
                target[i] = 0;
                current[i] = 0;
            } else {
                state[i] = 1;
                target[i] = finalHeight[i];
                current[i] = finalHeight[i];
            }
        }
        flushAll();
        onChange(count - 1);
    }

    // Multiple listeners: the timeline UI redraws the slider, scene.js
    // separately needs to know when to re-check which buildings are alive
    // (for arcs/traffic). `onChange = fn` REPLACES old assignment-style code;
    // keep that ergonomic by having the setter push instead of overwrite.
    const listeners = [];
    function onChange(i) { for (const fn of listeners) fn(i); }

    function update(now) {
        if (!live) return;

        if (playing && now - lastPlay > PLAY_MS) {
            lastPlay = now;
            if (index >= count - 1) playing = false;
            else seek(index + 1);
        }

        if (now > animatingUntil && dirty.size === 0) return;

        // easeOutCubic toward the target height
        let moved = false;
        for (let i = 0; i < n; i++) {
            const t = target[i];
            const c = current[i];
            if (Math.abs(t - c) < 0.01) {
                if (c !== t) { current[i] = t; writeInstance(i); moved = true; }
                continue;
            }
            current[i] = c + (t - c) * 0.18;
            writeInstance(i);
            moved = true;
        }
        if (moved) buildingsMesh.instanceMatrix.needsUpdate = true;
        else dirty.clear();
    }

    return {
        get index() { return index; },
        get count() { return count; },
        get live() { return live; },
        get playing() { return playing; },
        labels: snaps.labels,
        stats: snaps.stats,
        approximate: !!snaps.approximate,
        seek,
        toNow,
        play() { playing = true; lastPlay = performance.now(); if (!live) seek(0); },
        pause() { playing = false; },
        togglePlay() { playing ? this.pause() : this.play(); },
        set onChange(fn) { listeners.push(fn); },
        update,
        /** Which buildings exist at the current position - used to hide arcs
         *  and traffic for files that are not born yet or are deleted. */
        isVisible(i) { return live ? state[i] === 1 : !(city.buildings[i] && city.buildings[i].deleted); },
    };
}
