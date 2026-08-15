// T16 performance measurement.
//
// Drives a real, headful Chrome (via Puppeteer) against the built preview
// server so `requestAnimationFrame` runs at the display's real rate - the
// in-IDE browser automation pane throttles rAF to ~1 Hz, which produced fake
// numbers in earlier attempts at this task. Headless Chrome was avoided too:
// its default software rasterizer (SwiftShader) does not reflect real GPU
// performance.
//
// Usage: npm run preview (in another terminal, or this script assumes one
// is already serving dist/ at PREVIEW_URL) then `node scripts/measure-perf.mjs`.

import puppeteer from 'puppeteer';

const PREVIEW_URL = process.env.PREVIEW_URL || 'http://localhost:4173';
const CITY = 'perf.city.json';

const SCENARIOS = [
    { name: 'idle orbit, overview', fn: 'idleOrbit' },
    { name: 'fast orbit', fn: 'fastOrbit' },
    { name: 'street-level fly-through', fn: 'flyThrough' },
    { name: 'timeline scrub ~1 snapshot/300ms', fn: 'timelineScrub' },
    { name: 'everything on (arcs+traffic+overlay cycle)', fn: 'everythingOn' },
];

// Runs inside the page. Hooks rAF with an independent counter so the
// measurement does not trust the app's own internal fps display.
async function installFrameCounter(page) {
    await page.evaluate(() => {
        window.__frameCount = 0;
        const raw = window.requestAnimationFrame.bind(window);
        function hook(cb) {
            return raw((t) => {
                window.__frameCount++;
                cb(t);
            });
        }
        window.requestAnimationFrame = hook;
    });
}

async function measureFor(page, ms, driver) {
    await page.evaluate(() => { window.__frameCount = 0; });
    const t0 = Date.now();
    const timer = driver ? setInterval(driver, 50) : null;
    while (Date.now() - t0 < ms) {
        await new Promise((r) => setTimeout(r, 100));
    }
    if (timer) clearInterval(timer);
    const frames = await page.evaluate(() => window.__frameCount);
    return Math.round((frames * 1000) / ms);
}

async function scenarioIdleOrbit(page) {
    return measureFor(page, 10000, null);
}

async function scenarioFastOrbit(page) {
    const box = await page.$eval('canvas', (c) => {
        const r = c.getBoundingClientRect();
        return { x: r.x, y: r.y, w: r.width, h: r.height };
    });
    const cx = box.x + box.w / 2;
    const cy = box.y + box.h / 2;
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    let angle = 0;
    const drive = async () => {
        angle += 0.35;
        await page.mouse.move(cx + Math.cos(angle) * 200, cy + Math.sin(angle) * 120, { steps: 1 });
    };
    await page.evaluate(() => { window.__frameCount = 0; });
    const t0 = Date.now();
    while (Date.now() - t0 < 10000) {
        await drive();
        await new Promise((r) => setTimeout(r, 30));
    }
    await page.mouse.up();
    const frames = await page.evaluate(() => window.__frameCount);
    return Math.round((frames * 1000) / 10000);
}

async function scenarioFlyThrough(page) {
    // Pointer-lock WASD fly mode does not reliably engage under CDP
    // automation, so this drives the camera directly through the exposed
    // debug handle - it exercises the same render path (camera moving
    // through the city at street height) without depending on pointer lock.
    return measureFor(page, 10000, async () => {
        await page.evaluate(() => {
            const ctx = window.__CHRONOPOLIS__;
            if (!ctx) return;
            const t = performance.now() / 1000;
            const r = 120;
            ctx.camera.position.set(Math.cos(t * 0.3) * r, 8, Math.sin(t * 0.3) * r);
            ctx.controls.orbit.target.set(0, 6, 0);
        });
    });
}

async function scenarioTimelineScrub(page) {
    let i = 0;
    return measureFor(page, 10000, async () => {
        i = (i + 1) % 24;
        await page.evaluate((idx) => {
            const t = window.__CHRONOPOLIS__ && window.__CHRONOPOLIS__.timeline;
            if (t) t.seek(idx);
        }, i);
    });
}

async function scenarioEverythingOn(page) {
    await page.keyboard.press('i'); // arcs on
    await page.keyboard.press('t'); // traffic on
    let mode = 1;
    let lastSwitch = Date.now();
    return measureFor(page, 10000, async () => {
        if (Date.now() - lastSwitch > 2000) {
            mode = (mode % 6) + 1;
            await page.keyboard.press(String(mode));
            lastSwitch = Date.now();
        }
    });
}

const RUNNERS = {
    idleOrbit: scenarioIdleOrbit,
    fastOrbit: scenarioFastOrbit,
    flyThrough: scenarioFlyThrough,
    timelineScrub: scenarioTimelineScrub,
    everythingOn: scenarioEverythingOn,
};

async function main() {
    const browser = await puppeteer.launch({
        headless: false,
        args: ['--window-size=1400,900', '--ignore-gpu-blocklist'],
        defaultViewport: { width: 1366, height: 820 },
    });
    const page = await browser.newPage();

    const gpuInfo = await page.evaluate(() => {
        const gl = document.createElement('canvas').getContext('webgl2');
        if (!gl) return 'no webgl2 context';
        const ext = gl.getExtension('WEBGL_debug_renderer_info');
        if (!ext) return gl.getParameter(gl.RENDERER);
        return gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
    });

    const consoleLines = [];
    page.on('console', (msg) => consoleLines.push(msg.text()));

    const t0 = Date.now();
    await page.goto(`${PREVIEW_URL}/?city=${CITY}`, { waitUntil: 'networkidle0' });
    await page.waitForFunction(() => window.__CHRONOPOLIS__ && window.__CHRONOPOLIS__.buildingsMesh, { timeout: 20000 });
    const timeToFirstFrame = Date.now() - t0;

    await installFrameCounter(page);
    // Let the intro camera animation finish before measuring.
    await new Promise((r) => setTimeout(r, 2500));

    const results = {};
    for (const s of SCENARIOS) {
        const fps = await RUNNERS[s.fn](page);
        results[s.name] = fps;
        console.log(`${s.name}: ${fps} fps`);
    }

    // Heap growth over 60s at idle, to catch leaks.
    const heap0 = await page.evaluate(() => performance.memory ? performance.memory.usedJSHeapSize : null);
    await new Promise((r) => setTimeout(r, 60000));
    const heap1 = await page.evaluate(() => performance.memory ? performance.memory.usedJSHeapSize : null);

    // selftest for the invariant checks + its own fps figure.
    await page.goto(`${PREVIEW_URL}/?city=${CITY}&selftest=1`, { waitUntil: 'networkidle0' });
    await page.waitForFunction(() => document.title === 'OK' || document.title === 'FAIL', { timeout: 15000 });
    const selftestTitle = await page.title();
    const selftestLine = consoleLines.reverse().find((l) => l.startsWith('SELFTEST'));

    console.log('\n--- summary ---');
    console.log('GPU:', gpuInfo);
    console.log('time to first frame (ms):', timeToFirstFrame);
    if (heap0 !== null) {
        console.log(`JS heap: ${(heap0 / 1e6).toFixed(1)} MB -> ${(heap1 / 1e6).toFixed(1)} MB over 60s idle`);
    } else {
        console.log('JS heap: performance.memory unavailable in this Chrome build');
    }
    console.log('selftest:', selftestTitle, selftestLine || '(no SELFTEST line seen)');

    await browser.close();
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
