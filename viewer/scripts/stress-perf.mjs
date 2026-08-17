import puppeteer from 'puppeteer';
import fs from 'fs';
import zlib from 'zlib';

const args = process.argv.slice(2);
let cityArg = 'public/stress.city.json';
const cityIdx = args.indexOf('--city');
if (cityIdx !== -1 && cityIdx + 1 < args.length) {
    cityArg = args[cityIdx + 1];
}

const PREVIEW_URL = process.env.PREVIEW_URL || 'http://localhost:4173';
// we need just the basename for the URL query param, since Vite serves from public
const CITY_BASENAME = cityArg.split('/').pop().split('\\').pop();

const SCENARIOS = [
    { name: 'idle orbit, overview', fn: 'idleOrbit' },
    { name: 'fast orbit', fn: 'fastOrbit' },
    { name: 'street-level fly-through', fn: 'flyThrough' },
    { name: 'timeline scrub ~1 snapshot/300ms', fn: 'timelineScrub' },
    { name: 'everything on (arcs+traffic+overlay cycle)', fn: 'everythingOn' },
];

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

const RUNNERS = {
    idleOrbit: async (page) => measureFor(page, 10000, null),
    fastOrbit: async (page) => {
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
    },
    flyThrough: async (page) => measureFor(page, 10000, async () => {
        await page.evaluate(() => {
            const ctx = window.__CHRONOPOLIS__;
            if (!ctx) return;
            const t = performance.now() / 1000;
            const r = 120;
            ctx.camera.position.set(Math.cos(t * 0.3) * r, 8, Math.sin(t * 0.3) * r);
            ctx.controls.orbit.target.set(0, 6, 0);
        });
    }),
    timelineScrub: async (page) => {
        let i = 0;
        return measureFor(page, 10000, async () => {
            i = (i + 1) % 24;
            await page.evaluate((idx) => {
                const t = window.__CHRONOPOLIS__ && window.__CHRONOPOLIS__.timeline;
                if (t) t.seek(idx);
            }, i);
        });
    },
    everythingOn: async (page) => {
        await page.keyboard.press('i');
        await page.keyboard.press('t');
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
};

async function main() {
    console.log(`Starting stress test for ${cityArg}...`);
    
    // Calculate raw and gz sizes
    let rawSize = 0;
    let gzSize = 0;
    try {
        const buf = fs.readFileSync(cityArg);
        rawSize = buf.length;
        gzSize = zlib.gzipSync(buf).length;
    } catch(e) {
        console.error('Could not read city file for size calculation:', e.message);
    }

    const browser = await puppeteer.launch({
        headless: false,
        args: ['--window-size=1400,900', '--ignore-gpu-blocklist'],
        defaultViewport: { width: 1366, height: 820 },
    });
    
    try {
        const page = await browser.newPage();
        
        // Hook JSON.parse to measure time
        await page.evaluateOnNewDocument(() => {
            window.__jsonParseTime = 0;
            const origParse = JSON.parse;
            JSON.parse = function() {
                const t0 = performance.now();
                const res = origParse.apply(this, arguments);
                window.__jsonParseTime += (performance.now() - t0);
                return res;
            };
            const origJson = Response.prototype.json;
            Response.prototype.json = async function() {
                const t0 = performance.now();
                const res = await origJson.apply(this, arguments);
                window.__jsonParseTime += (performance.now() - t0);
                return res;
            };
        });

        // Hook picking latency
        await page.evaluateOnNewDocument(() => {
            window.__pickLatency = -1;
            let tClick = 0;
            window.addEventListener('mousedown', () => { 
                tClick = performance.now(); 
            }, true);
            
            window.addEventListener('DOMContentLoaded', () => {
                // Poll for info-panel if not immediately there
                const check = setInterval(() => {
                    const panel = document.getElementById('info-panel');
                    if (panel) {
                        clearInterval(check);
                        const observer = new MutationObserver(() => {
                            if (tClick > 0) {
                                window.__pickLatency = performance.now() - tClick;
                                tClick = 0;
                            }
                        });
                        observer.observe(panel, { childList: true, subtree: true, attributes: true, characterData: true });
                    }
                }, 100);
            });
        });

        const gpuInfo = await page.evaluate(() => {
            const gl = document.createElement('canvas').getContext('webgl2');
            if (!gl) return 'no webgl2 context';
            const ext = gl.getExtension('WEBGL_debug_renderer_info');
            if (!ext) return gl.getParameter(gl.RENDERER);
            return gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
        });

        console.log('GPU:', gpuInfo);

        const t0 = Date.now();
        await page.goto(`${PREVIEW_URL}/?city=${CITY_BASENAME}`, { waitUntil: 'networkidle0', timeout: 120000 });
        
        // If it OOMs or fails, we might catch it here
        await page.waitForFunction(() => window.__CHRONOPOLIS__ && window.__CHRONOPOLIS__.buildingsMesh, { timeout: 120000 });
        const timeToFirstFrame = Date.now() - t0;
        console.log(`Time to first frame: ${timeToFirstFrame} ms`);

        await installFrameCounter(page);
        await new Promise((r) => setTimeout(r, 2500));
        
        const jsonParseTime = await page.evaluate(() => window.__jsonParseTime);
        
        // Draw calls & triangles
        const renderInfo = await page.evaluate(() => {
            const ctx = window.__CHRONOPOLIS__;
            if (!ctx || !ctx.renderer) return { calls: 0, triangles: 0 };
            const r = ctx.renderer;
            const old = r.info.autoReset;
            r.info.autoReset = false;
            r.render(ctx.scene, ctx.camera);
            const calls = r.info.render.calls;
            const tris = r.info.render.triangles;
            r.info.autoReset = old;
            return { calls, triangles: tris };
        });

        for (const s of SCENARIOS) {
            const fps = await RUNNERS[s.fn](page);
            console.log(`${s.name}: ${fps} fps`);
        }
        
        // Picking latency
        const box = await page.$eval('canvas', (c) => {
            const r = c.getBoundingClientRect();
            return { x: r.x, y: r.y, w: r.width, h: r.height };
        });
        await page.mouse.click(box.x + box.w / 2, box.y + box.h / 2);
        
        // Wait up to 5s for picking latency
        await page.waitForFunction(() => window.__pickLatency > 0 || window.__pickLatency === -1, { timeout: 5000 }).catch(() => {});
        const pickLatency = await page.evaluate(() => window.__pickLatency);

        // Heap
        const heap0 = await page.evaluate(() => performance.memory ? performance.memory.usedJSHeapSize : null);
        console.log('Waiting 60s to check for memory leaks...');
        await new Promise((r) => setTimeout(r, 60000));
        const heap1 = await page.evaluate(() => performance.memory ? performance.memory.usedJSHeapSize : null);

        console.log('\n--- summary ---');
        console.log(`city.json size: ${(rawSize / 1e6).toFixed(2)} MB raw / ${(gzSize / 1e6).toFixed(2)} MB gz`);
        console.log(`JSON.parse time: ${Math.round(jsonParseTime)} ms`);
        console.log(`Time to first frame: ${timeToFirstFrame} ms`);
        console.log(`Draw calls: ${renderInfo.calls}, Triangles: ${renderInfo.triangles}`);
        console.log(`Picking latency: ${pickLatency > 0 ? Math.round(pickLatency) + ' ms' : 'failed'}`);
        
        if (heap0 !== null) {
            console.log(`JS heap: ${(heap0 / 1e6).toFixed(1)} MB -> ${(heap1 / 1e6).toFixed(1)} MB over 60s idle`);
        } else {
            console.log('JS heap: performance.memory unavailable in this Chrome build');
        }

    } catch (e) {
        console.error('Test failed / browser crashed:', e.message);
    } finally {
        await browser.close();
    }
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
