export class Search {
    constructor(city, sceneControls, buildingsMesh) {
        this.city = city;
        this.controls = sceneControls;
        this.mesh = buildingsMesh;
        this.gitMissing = !city.git || city.git.commit_count === 0;

        // Precompute lowercase paths
        this.index = city.buildings.map((b, i) => ({
            b, i,
            pathLower: b.path.toLowerCase(),
            nameLower: b.name.toLowerCase()
        }));

        this.authors = city.git ? city.git.authors.map(a => a.name.toLowerCase()) : [];

        this.setupUI();
        this.bindEvents();
    }

    setupUI() {
        this.container = document.createElement('div');
        this.container.id = 'search-container';
        this.container.innerHTML = `
            <input type="text" id="search-input" placeholder="Search files... (dir: src, lang: js, >complexity: 50)" autocomplete="off">
            <div id="search-results" class="hidden"></div>
            <div id="search-status" class="hidden"></div>
        `;
        document.getElementById('ui2').appendChild(this.container);

        this.input = document.getElementById('search-input');
        this.resultsEl = document.getElementById('search-results');
        this.statusEl = document.getElementById('search-status');
        this.selectedIndex = -1;
        this.matches = [];
        this.isActive = false;
    }

    bindEvents() {
        window.addEventListener('keydown', e => {
            if (e.key === '/' || (e.key === 'k' && (e.ctrlKey || e.metaKey))) {
                e.preventDefault();
                this.input.focus();
            }
        });

        this.input.addEventListener('input', () => this.onInput());
        
        this.input.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                this.input.value = '';
                this.input.blur();
                this.onInput();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, Math.min(7, this.matches.length - 1));
                this.renderResults();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.selectedIndex = Math.max(0, this.selectedIndex - 1);
                this.renderResults();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (this.selectedIndex >= 0 && this.matches[this.selectedIndex]) {
                    this.select(this.matches[this.selectedIndex].i);
                } else if (this.matches.length > 0) {
                    this.select(this.matches[0].i);
                }
            }
        });

        document.addEventListener('click', e => {
            if (!this.container.contains(e.target)) {
                this.resultsEl.classList.add('hidden');
            }
        });
    }

    // Fuzzy subsequence matcher
    isSubsequence(query, text) {
        let qi = 0;
        for (let ti = 0; ti < text.length && qi < query.length; ti++) {
            if (text[ti] === query[qi]) qi++;
        }
        return qi === query.length;
    }

    parseFilters(query) {
        const parts = query.toLowerCase().split(' ');
        let q = '';
        const filters = [];
        
        for (const p of parts) {
            if (p.includes(':')) {
                const [k, v] = p.split(':', 2);
                filters.push({ k, v });
            } else {
                q += p + ' ';
            }
        }
        return { q: q.trim(), filters };
    }

    applyFilters(item, filters) {
        const b = item.b;
        for (const {k, v} of filters) {
            if (k === 'dir' && !item.pathLower.includes(`/${v}`)) return false; // simple substring for dir
            if (k === 'lang' && b.lang !== v) return false;
            if (k === '>complexity') {
                const limit = parseInt(v);
                if (isNaN(limit) || (b.complexity || 0) <= limit) return false;
            }
            if (k === 'owner') {
                if (b.owner == null) return false;
                const author = this.authors[b.owner];
                if (!author || !author.includes(v)) return false;
            }
            if (k === 'stale') {
                const days = v.startsWith('>') ? parseInt(v.slice(1)) : parseInt(v);
                if (isNaN(days) || b.stale_days == null || b.stale_days <= days) return false;
            }
            if (k === 'bus') {
                if (b.bus_factor != parseInt(v)) return false;
            }
        }
        return true;
    }

    onInput() {
        const raw = this.input.value;
        const url = new URL(window.location);
        
        if (!raw.trim()) {
            this.resultsEl.classList.add('hidden');
            this.statusEl.classList.add('hidden');
            this.matches = [];
            this.setDimming(false);
            url.searchParams.delete('q');
            window.history.replaceState({}, '', url);
            return;
        }

        url.searchParams.set('q', raw);
        window.history.replaceState({}, '', url);

        const { q, filters } = this.parseFilters(raw);
        this.matches = [];

        for (const item of this.index) {
            if (item.b.deleted) continue; // don't search ruins by default
            if (!this.applyFilters(item, filters)) continue;
            
            if (!q) {
                // If only filters are active
                item.score = 0;
                this.matches.push(item);
                continue;
            }

            let score = -1;
            if (item.nameLower === q) score = 100;
            else if (item.nameLower.startsWith(q)) score = 80;
            else if (item.pathLower.includes(q)) score = 60;
            else if (this.isSubsequence(q, item.pathLower)) score = 40;

            if (score > 0) {
                item.score = score;
                this.matches.push(item);
            }
        }

        // Sort by score desc, then complexity desc
        this.matches.sort((a, b) => {
            if (a.score !== b.score) return b.score - a.score;
            return (b.b.complexity || 0) - (a.b.complexity || 0);
        });

        this.selectedIndex = 0;
        this.setDimming(true);
        this.renderResults();
        
        this.statusEl.classList.remove('hidden');
        this.statusEl.innerText = `${this.matches.length.toLocaleString()} of ${this.index.length.toLocaleString()} match`;
    }

    renderResults() {
        if (this.matches.length === 0) {
            this.resultsEl.classList.add('hidden');
            return;
        }
        this.resultsEl.classList.remove('hidden');
        
        const top = this.matches.slice(0, 8);
        this.resultsEl.innerHTML = top.map((m, idx) => `
            <div class="search-item ${idx === this.selectedIndex ? 'selected' : ''}" data-idx="${m.i}">
                <div class="search-path">${m.b.path}</div>
                <div class="search-meta">${m.b.loc} loc · cx ${m.b.complexity || 1}</div>
            </div>
        `).join('');

        this.resultsEl.querySelectorAll('.search-item').forEach(el => {
            el.addEventListener('click', () => {
                this.select(parseInt(el.getAttribute('data-idx')));
            });
            el.addEventListener('mouseenter', () => {
                this.selectedIndex = Array.from(this.resultsEl.children).indexOf(el);
                this.renderResults();
            });
        });
    }

    setDimming(active) {
        if (!this.mesh.instanceColor) return;
        this.isActive = active;
        const n = this.mesh.count;
        const color = this.mesh.instanceColor.array;
        const orig = window.__CHRONOPOLIS__.scene.children.find(c => c === this.mesh).userData.origColors || color.slice(); // need to store original colors somehow
        // Actually, Overlays.js controls colors. Let's communicate with Overlays.js or handle dimming in shader?
        // Wait, "Non-matching buildings dim to 20% while a query is active"
        // Let's modify the scale.y instead of color? No, "dim to 20%" means color *= 0.2.
        
        // Simpler: Set a uniform or attributes on the mesh for dimming.
        if (!this.mesh.geometry.attributes.aDim) {
            this.mesh.geometry.setAttribute('aDim', new THREE.InstancedBufferAttribute(new Float32Array(n).fill(1), 1));
        }
        const aDim = this.mesh.geometry.attributes.aDim;
        aDim.array.fill(active ? 0.2 : 1.0);
        
        if (active) {
            for (const m of this.matches) {
                aDim.array[m.i] = 1.0;
            }
        }
        aDim.needsUpdate = true;
    }

    select(index) {
        const plot = this.city.layout.plots[index];
        const b = this.city.buildings[index];
        if (!plot) return;

        this.resultsEl.classList.add('hidden');
        this.input.blur();
        
        // Distance proportional to building height
        const dist = Math.max(30, plot.h * 1.5 + 25);
        
        // Use controls.flyTo
        if (this.controls.flyTo) {
            this.controls.flyTo(plot.x + plot.w/2, plot.h, plot.z + plot.d/2, dist);
        }

        // Highlight
        if (window.__CHRONOPOLIS__.scene) {
             // Let Picking system know to open the panel
             if (window.__CHRONOPOLIS__.picking) {
                 window.__CHRONOPOLIS__.picking.select(index);
             }
        }
    }
}
