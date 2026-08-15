import { animate as anime } from 'animejs';

/**
 * Timeline bar: slider, date, play/pause, and a LOC sparkline behind it.
 *
 * The sparkline is the honest part - it shows the shape of the repo's growth
 * so you know where in the history something interesting happened before you
 * drag. Without it, scrubbing is a lucky dip.
 *
 * The bar also states plainly that reconstructed history is approximate. A
 * tool that quietly presents an estimate as fact is worse than one that shows
 * nothing.
 */
export function mountTimeline(timeline) {
    const root = document.createElement('div');
    root.id = 'timeline';
    root.innerHTML = `
      <style>
        #timeline{position:fixed;left:50%;transform:translateX(-50%);bottom:18px;
          width:min(720px,92vw);background:rgba(14,18,24,.82);backdrop-filter:blur(6px);
          border:1px solid rgba(255,255,255,.10);border-radius:10px;padding:9px 13px 7px;
          font:12px/1.4 ui-monospace,Menlo,Consolas,monospace;color:#cfd6df;opacity:0;}
        #timeline .row{display:flex;align-items:center;gap:10px;}
        #timeline button{background:rgba(255,255,255,.07);color:#dfe6ef;border:1px solid rgba(255,255,255,.14);
          border-radius:5px;padding:3px 9px;cursor:pointer;font:inherit;}
        #timeline button:hover{background:rgba(255,255,255,.14);}
        #timeline .date{min-width:64px;font-variant-numeric:tabular-nums;}
        #timeline .facts{min-width:150px;text-align:right;color:#93a0ae;}
        #timeline .track{position:relative;flex:1;height:26px;}
        #timeline canvas{position:absolute;inset:0;width:100%;height:100%;opacity:.5;}
        #timeline input{position:absolute;inset:0;width:100%;margin:0;background:transparent;
          -webkit-appearance:none;appearance:none;cursor:pointer;}
        #timeline input::-webkit-slider-thumb{-webkit-appearance:none;width:11px;height:22px;
          border-radius:3px;background:#e6c992;border:none;cursor:grab;}
        #timeline input::-moz-range-thumb{width:11px;height:22px;border-radius:3px;background:#e6c992;border:none;}
        #timeline .note{margin-top:4px;color:#7d8794;font-size:10.5px;}
      </style>
      <div class="row">
        <button id="tl-play" title="Space">play</button>
        <span class="date" id="tl-date"></span>
        <div class="track">
          <canvas id="tl-spark"></canvas>
          <input id="tl-range" type="range" min="0" max="${timeline.count - 1}"
                 value="${timeline.count - 1}" step="1" aria-label="history position">
        </div>
        <span class="facts" id="tl-facts"></span>
        <button id="tl-now" title="R">now</button>
      </div>
      <div class="note" id="tl-note"></div>`;
    document.body.appendChild(root);

    const range = root.querySelector('#tl-range');
    const dateEl = root.querySelector('#tl-date');
    const factsEl = root.querySelector('#tl-facts');
    const playBtn = root.querySelector('#tl-play');
    const noteEl = root.querySelector('#tl-note');
    const canvas = root.querySelector('#tl-spark');

    noteEl.textContent = timeline.approximate
        ? 'history reconstructed from commit statistics — sizes are approximate'
        : 'history from exact per-commit analysis';

    function drawSpark() {
        const w = canvas.clientWidth || 400;
        const h = canvas.clientHeight || 26;
        const dpr = Math.min(window.devicePixelRatio, 2);
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);
        const locs = timeline.stats.map((s) => s.loc);
        const max = Math.max(1, ...locs);
        ctx.beginPath();
        ctx.moveTo(0, h);
        locs.forEach((v, i) => {
            ctx.lineTo((i / (locs.length - 1)) * w, h - (v / max) * (h - 3));
        });
        ctx.lineTo(w, h);
        ctx.closePath();
        ctx.fillStyle = 'rgba(230,201,146,.30)';
        ctx.fill();
    }
    drawSpark();
    window.addEventListener('resize', drawSpark);

    function render(i) {
        range.value = String(i);
        dateEl.textContent = timeline.labels[i] || '';
        const s = timeline.stats[i];
        factsEl.textContent = s
            ? `${s.files} files · ${s.loc.toLocaleString()} LOC`
            : '';
        playBtn.textContent = timeline.playing ? 'pause' : 'play';
    }
    timeline.onChange = render;
    render(timeline.count - 1);

    range.addEventListener('input', () => {
        timeline.pause();
        timeline.seek(Number(range.value));
    });
    playBtn.addEventListener('click', () => { timeline.togglePlay(); render(timeline.index); });
    root.querySelector('#tl-now').addEventListener('click', () => timeline.toNow());

    window.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' && e.target !== range) return;
        const k = e.key;
        if (k === ' ') { e.preventDefault(); timeline.togglePlay(); render(timeline.index); }
        else if (k === 'ArrowLeft') { timeline.pause(); timeline.seek(timeline.index - 1); }
        else if (k === 'ArrowRight') { timeline.pause(); timeline.seek(timeline.index + 1); }
    });

    // animejs v4's animate() takes (targets, params) - it is NOT the v3
    // anime({targets: ..., easing: ...}) form. Passing the v3 shape here
    // silently makes `params` undefined and JSAnimation crashes reading
    // `.keyframes` off it, which took the whole page down on load.
    anime(root, { opacity: [0, 1], translateY: [10, 0], duration: 700,
                  delay: 900, ease: 'outCubic' });

    return { render };
}
