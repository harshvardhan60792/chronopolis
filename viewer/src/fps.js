export function mountFps() {
    const el = document.createElement('div');
    el.style.position = 'fixed';
    el.style.bottom = '10px';
    el.style.right = '10px';
    el.style.background = 'rgba(0,0,0,0.8)';
    el.style.padding = '5px 10px';
    el.style.fontFamily = 'monospace';
    el.style.fontSize = '12px';
    el.style.color = '#0f0';
    el.style.zIndex = '100';
    el.id = 'fps-counter';
    document.body.appendChild(el);
    
    let frames = 0;
    let lastTime = performance.now();
    let frameTimes = [];
    
    function tick() {
        frames++;
        const now = performance.now();
        const elapsed = now - lastTime;
        frameTimes.push(elapsed);
        if (frameTimes.length > 120) {
            frameTimes.shift();
        }
        if (frames % 30 === 0) {
            const avg = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
            const fps = 1000 / avg;
            el.innerText = `${Math.round(fps)} fps | ${avg.toFixed(1)} ms`;
        }
        lastTime = now;
        requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}
