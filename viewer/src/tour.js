export class Tour {
    constructor(city, controls, buildingsMesh) {
        this.city = city;
        this.controls = controls;
        this.mesh = buildingsMesh;
        this.stories = city.stories || [];
        this.currentIndex = -1;
        this.active = false;
        this.paused = false;
        
        this.setupUI();
        this.bindEvents();

        // Check if we should prompt
        const url = new URL(window.location);
        if (!url.searchParams.has('q') && !url.searchParams.has('mode') && this.stories.length > 0) {
            setTimeout(() => {
                if (!this.active && !this.promptClosed) {
                    this.promptEl.classList.remove('hidden');
                }
            }, 1500);
        }
    }

    setupUI() {
        this.container = document.createElement('div');
        this.container.id = 'tour-container';
        
        this.promptEl = document.createElement('div');
        this.promptEl.id = 'tour-prompt';
        this.promptEl.className = 'tour-card hidden';
        this.promptEl.innerHTML = `
            <div>Chronopolis found ${this.stories.length} insights.</div>
            <div class="tour-actions">
                <button id="tour-start-btn">Take the tour ▸</button>
                <button id="tour-skip-btn">Skip</button>
            </div>
        `;

        this.captionEl = document.createElement('div');
        this.captionEl.id = 'tour-caption';
        this.captionEl.className = 'tour-card hidden';
        
        this.findingsBtn = document.createElement('button');
        this.findingsBtn.id = 'tour-findings-btn';
        this.findingsBtn.innerText = `Findings (${this.stories.length})`;
        
        this.findingsHint = document.createElement('div');
        this.findingsHint.id = 'tour-findings-hint';
        this.findingsHint.className = 'hidden';
        this.findingsHint.innerHTML = 'Start here ▸';
        
        this.findingsList = document.createElement('div');
        this.findingsList.id = 'tour-findings-list';
        this.findingsList.className = 'hidden';
        this.findingsList.innerHTML = this.stories.map((s, i) => `
            <div class="finding-item" data-idx="${i}">
                <strong>${s.kind.replace('_', ' ')}</strong><br>
                ${s.text}
            </div>
        `).join('');

        this.container.appendChild(this.promptEl);
        this.container.appendChild(this.captionEl);
        
        const ui = document.getElementById('ui2');
        ui.appendChild(this.container);
        ui.appendChild(this.findingsBtn);
        ui.appendChild(this.findingsHint);
        ui.appendChild(this.findingsList);
        
        if (!localStorage.getItem('chronopolis.seen') && this.stories.length > 0) {
            this.findingsHint.classList.remove('hidden');
        }
    }

    bindEvents() {
        document.getElementById('tour-start-btn').addEventListener('click', () => {
            this.promptClosed = true;
            this.promptEl.classList.add('hidden');
            this.start();
        });
        
        document.getElementById('tour-skip-btn').addEventListener('click', () => {
            this.promptClosed = true;
            this.promptEl.classList.add('hidden');
        });

        const toggleFindings = () => {
            this.findingsList.classList.toggle('hidden');
            if (!this.findingsHint.classList.contains('hidden')) {
                this.findingsHint.classList.add('hidden');
                localStorage.setItem('chronopolis.seen', '1');
            }
        };
        this.findingsBtn.addEventListener('click', toggleFindings);
        this.findingsHint.addEventListener('click', toggleFindings);

        this.findingsList.querySelectorAll('.finding-item').forEach(el => {
            el.addEventListener('click', () => {
                const idx = parseInt(el.getAttribute('data-idx'));
                this.findingsList.classList.add('hidden');
                this.active = true;
                this.goTo(idx);
            });
        });

        window.addEventListener('keydown', (e) => {
            if (!this.active) return;
            
            if (e.key === 'Escape') {
                this.stop();
            } else if (e.key === 'ArrowRight') {
                this.next();
            } else if (e.key === 'ArrowLeft') {
                this.prev();
            } else if (e.key === ' ') {
                this.paused = !this.paused;
                if (!this.paused) {
                    this.goTo(this.currentIndex); // resume current
                } else {
                    if (this.timer) clearTimeout(this.timer);
                }
            }
        });
    }

    start() {
        if (this.stories.length === 0) return;
        this.active = true;
        this.paused = false;
        this.goTo(0);
    }

    stop() {
        this.active = false;
        if (this.timer) clearTimeout(this.timer);
        this.captionEl.classList.add('hidden');
        this.setDimming(null);
    }

    next() {
        if (this.currentIndex < this.stories.length - 1) {
            this.goTo(this.currentIndex + 1);
        } else {
            this.stop();
        }
    }

    prev() {
        if (this.currentIndex > 0) {
            this.goTo(this.currentIndex - 1);
        }
    }

    goTo(index) {
        this.currentIndex = index;
        const story = this.stories[index];
        const plot = this.city.layout.plots[story.building_index];
        if (!plot) return;

        if (this.timer) clearTimeout(this.timer);

        const dist = Math.max(30, plot.h * 1.8 + 35);
        if (this.controls.flyTo) {
            this.controls.flyTo(plot.x + plot.w/2, plot.h, plot.z + plot.d/2, dist, 1200);
        }

        this.setDimming(story.building_index);
        
        this.captionEl.innerHTML = `
            <div class="tour-progress">${index + 1} of ${this.stories.length} · ${story.kind.replace('_', ' ')}</div>
            <div class="tour-text">${story.text}</div>
            <div class="tour-hints">Space to pause · → next · Esc to exit</div>
        `;
        this.captionEl.classList.remove('hidden');

        if (!this.paused) {
            // 40 second tour for 7 stops = ~5-6s per stop. Wait for flyTo (1.2s) + 4s read time
            this.timer = setTimeout(() => {
                this.next();
            }, 5500);
        }
    }

    setDimming(targetIndex) {
        if (!this.mesh.geometry.attributes.aDim) {
            const n = this.mesh.count;
            this.mesh.geometry.setAttribute('aDim', new THREE.InstancedBufferAttribute(new Float32Array(n).fill(1), 1));
        }
        
        const aDim = this.mesh.geometry.attributes.aDim;
        const n = this.mesh.count;
        
        if (targetIndex === null) {
            aDim.array.fill(1.0);
        } else {
            aDim.array.fill(0.3); // dim to 30%
            aDim.array[targetIndex] = 1.0;
        }
        
        aDim.needsUpdate = true;
    }
}
