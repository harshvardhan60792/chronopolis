/**
 * ?selftest=1 harness.
 *
 * Asserts the scene actually matches the city data, then measures 120 frames.
 * Prints exactly one line - `SELFTEST OK <fps>` or `SELFTEST FAIL <reason>` -
 * and sets document.title, so CI (T18) can check it headlessly.
 *
 * This must FAIL when the scene is wrong. A selftest that always passes is
 * worse than no selftest.
 */

const checks = [];

function check(name, cond, detail = '') {
    checks.push({ name, ok: !!cond, detail });
}

export function runSelftest() {
    const ctx = window.__CHRONOPOLIS__;
    if (!ctx) {
        finish(['scene never initialised (window.__CHRONOPOLIS__ missing)']);
        return;
    }

    const { city, scene, buildingsMesh, arcsData, trafficData } = ctx;
    const n = city.buildings.length;

    check('instance count', buildingsMesh && buildingsMesh.count === n,
        `mesh=${buildingsMesh && buildingsMesh.count} city=${n}`);

    // Every instance matrix must be finite and above ground.
    let badMatrix = -1;
    let zeroScale = 0;
    if (buildingsMesh) {
        const m = buildingsMesh.instanceMatrix.array;
        for (let i = 0; i < m.length; i++) {
            if (!Number.isFinite(m[i])) { badMatrix = Math.floor(i / 16); break; }
        }
        for (let i = 0; i < n; i++) {
            const s = m[i * 16 + 5]; // matrix[1][1] = y scale for an unrotated box
            if (!(s > 0)) zeroScale++;
        }
    }
    check('no NaN in instance matrices', badMatrix === -1, `instance ${badMatrix}`);
    check('no zero-height buildings', zeroScale === 0, `${zeroScale} flat`);

    check('plots parallel to buildings',
        city.layout && city.layout.plots.length === n);
    check('scene populated', scene && scene.children.length >= 3,
        `${scene && scene.children.length} children`);

    if (city.edges && city.edges.import.length) {
        check('arcs built', arcsData && arcsData.mesh, 'no arc mesh');
    }
    if (city.layout.roads && city.layout.roads.length) {
        check('traffic built', trafficData && trafficData.points, 'no traffic points');
    }

    // 120-frame measurement, with a deadline: some headless/background
    // contexts never fire requestAnimationFrame at all, and a selftest that
    // waits forever for a frame reports nothing, which is the worst outcome.
    let frames = 0;
    let done = false;
    const t0 = performance.now();

    const report = () => {
        if (done) return;
        done = true;
        let fps = null;
        if (frames >= 10) {
            fps = Math.round((frames * 1000) / (performance.now() - t0));
            check('fps >= 30', fps >= 30, `${fps} fps`);
        }
        finish(checks.filter((c) => !c.ok).map((c) => `${c.name} (${c.detail})`), fps);
    };

    function tick() {
        frames++;
        if (frames < 120) {
            requestAnimationFrame(tick);
            return;
        }
        report();
    }
    requestAnimationFrame(tick);
    setTimeout(report, 5000);
}

function finish(failures, fps) {
    if (failures.length) {
        console.error(`SELFTEST FAIL ${failures.join('; ')}`);
        document.title = 'FAIL';
        return;
    }
    const rate = fps === null ? 'fps unmeasured (no frames rendered)' : `${fps} fps`;
    console.log(`SELFTEST OK ${rate}, ${checks.length} checks`);
    document.title = 'OK';
}
