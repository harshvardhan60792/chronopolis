export function initPanel() {
    const el = document.createElement('div');
    el.id = 'info-panel';
    el.className = 'hidden';
    el.style.position = 'absolute';
    el.style.top = '10px';
    el.style.right = '10px';
    el.style.width = '320px';
    el.style.background = 'rgba(11, 14, 20, 0.9)';
    el.style.border = '1px solid #333';
    el.style.borderRadius = '6px';
    el.style.padding = '12px';
    el.style.fontFamily = 'monospace';
    el.style.fontSize = '12px';
    el.style.color = '#ddd';
    el.style.pointerEvents = 'auto';
    el.style.maxHeight = '90vh';
    el.style.overflowY = 'auto';
    el.style.zIndex = '100';
    document.body.appendChild(el);
}

export function showPanel(building, cityData, onAction) {
    const el = document.getElementById('info-panel');
    if (!el) return;
    el.classList.remove('hidden');
    
    const inEdges = [];
    const outEdges = [];
    if (cityData.edges && cityData.edges.import) {
        cityData.edges.import.forEach(e => {
            if (e[1] === building.idx) inEdges.push(cityData.buildings[e[0]]);
            if (e[0] === building.idx) outEdges.push(cityData.buildings[e[1]]);
        });
    }
    
    let cochange = [];
    if (cityData.edges && cityData.edges.cochange) {
        cochange = cityData.edges.cochange
            .filter(e => e[0] === building.idx || e[1] === building.idx)
            .map(e => {
                const partnerIdx = e[0] === building.idx ? e[1] : e[0];
                return { partner: cityData.buildings[partnerIdx], strength: e[3] };
            })
            .sort((a, b) => b.strength - a.strength)
            .slice(0, 5);
    }
    
    let html = `
        <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-weight:bold; color:#fff;">
            <div style="word-break:break-all;">${building.path}</div>
            <div style="color:#888;">[${building.lang}]</div>
        </div>
        <hr style="border:0; border-top:1px solid #333; margin:8px 0;" />
        <div>${building.loc} LOC · ${building.functions} functions · ${building.classes} class${building.classes===1?'':'es'}</div>
        <div>complexity ${building.complexity} ${building.max_fn_complexity ? `(worst function ${building.max_fn_complexity})` : ''}</div>
    `;
    
    if (building.commits !== undefined) {
        html += `
            <div>churn ${building.churn} lines over ${building.commits} commits</div>
            <div>last touched ${building.stale_days} days ago · first seen ${building.age_days} days ago</div>
        `;
        if (building.bus_factor !== undefined && cityData.git && cityData.git.authors) {
            const owner = cityData.git.authors[building.owner];
            if (owner) {
                html += `<div>owner: ${owner.name} (${Math.round(building.owner_share * 100)}% of commits) · bus factor ${building.bus_factor}</div>`;
            }
        }
    } else {
        html += `<div>git history not available</div>`;
    }
    
    html += `<hr style="border:0; border-top:1px solid #333; margin:8px 0;" />`;
    
    function renderList(title, items, formatFn) {
        if (!items || items.length === 0) return '';
        let listStr = items.map((x, i) => {
            const f = formatFn(x);
            return `<a href="#" data-idx="${f.idx}" style="color:#4a9eff; text-decoration:none;">${f.label}</a>`;
        }).join(', ');
        return `<div style="display:flex; margin-bottom:4px;"><div style="width:120px; flex-shrink:0;">${title}</div><div style="color:#aaa;">▸ ${listStr}</div></div>`;
    }
    
    html += renderList(`imports (${outEdges.length})`, outEdges, b => ({idx: b.idx, label: b.name}));
    html += renderList(`imported by (${inEdges.length})`, inEdges, b => ({idx: b.idx, label: b.name}));
    html += renderList(`co-change (${cochange.length})`, cochange, c => ({idx: c.partner.idx, label: `${c.partner.name} ${c.strength.toFixed(2)}`}));
    
    html += `
        <hr style="border:0; border-top:1px solid #333; margin:8px 0;" />
        <div style="display:flex; gap:8px;">
            <button id="btn-fly" style="background:#222; border:1px solid #444; color:#fff; cursor:pointer; padding:2px 6px;">[ fly to ]</button>
            <button id="btn-copy" style="background:#222; border:1px solid #444; color:#fff; cursor:pointer; padding:2px 6px;">[ copy path ]</button>
        </div>
    `;
    
    el.innerHTML = html;
    
    el.querySelectorAll('a[data-idx]').forEach(a => {
        a.addEventListener('click', (e) => {
            e.preventDefault();
            onAction('select', parseInt(a.getAttribute('data-idx'), 10));
        });
    });
    
    const flyBtn = document.getElementById('btn-fly');
    if (flyBtn) flyBtn.addEventListener('click', () => onAction('flyTo', building.idx));
    const copyBtn = document.getElementById('btn-copy');
    if (copyBtn) copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(building.path);
        const btn = document.getElementById('btn-copy');
        btn.innerText = '[ copied ]';
        setTimeout(() => btn.innerText = '[ copy path ]', 1000);
    });
}

export function hidePanel() {
    const el = document.getElementById('info-panel');
    if (el) el.classList.add('hidden');
}
