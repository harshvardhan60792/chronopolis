import { MODES } from './overlays.js';

export class Legend {
    constructor(container, city) {
        this.el = document.createElement('div');
        this.el.id = 'legend';
        // styling should be in index.css, but we'll set some base classes
        this.el.className = 'legend-panel';
        container.appendChild(this.el);
        this.city = city;
        this.gitMissing = !city.git || city.git.commit_count === 0;
    }

    render(modeId) {
        const mode = MODES[modeId];
        if (!mode) return;

        let content = `<h3>${mode.name}</h3>`;

        if (this.gitMissing && [3, 4, 5].includes(modeId)) {
            content += `<div class="legend-desc">Git history is missing. This mode requires churn/authorship data.</div>`;
            this.el.innerHTML = content;
            return;
        }

        switch (modeId) {
            case 1: // Language
                content += `
                    <div class="legend-desc">Files coloured by primary programming language.</div>
                `;
                // Swatches would ideally be dynamically generated based on city languages, but for now just text is fine
                break;
            case 2: // Health
                content += `
                    <div class="legend-gradient health-gradient"></div>
                    <div class="legend-labels"><span>Healthy</span><span>Hotspot</span></div>
                    <div class="legend-desc">Red = changed often and hard to change (churn × complexity) — the hardest 5% of files in this repo.</div>
                `;
                break;
            case 3: // Recency
                content += `
                    <div class="legend-gradient viridis-gradient"></div>
                    <div class="legend-labels"><span>Just touched</span><span>> 2 years ago</span></div>
                    <div class="legend-desc">Cold dark colours are stale code. Bright warm colours are actively developed.</div>
                `;
                break;
            case 4: // Ownership
                content += `
                    <div class="legend-desc">Coloured by the top 8 authors. Grey = miscellaneous or shared code.</div>
                    <div class="legend-desc">Caveat: Based on commit counts, not lines owned.</div>
                `;
                break;
            case 5: // Bus factor
                content += `
                    <div class="legend-gradient health-gradient"></div>
                    <div class="legend-labels"><span>Many authors (≥3)</span><span>Single author (1)</span></div>
                    <div class="legend-desc">Red = only one person has committed to this file. Size weighted.</div>
                `;
                break;
            case 6: // Complexity
                content += `
                    <div class="legend-gradient viridis-gradient"></div>
                    <div class="legend-labels"><span>Simple</span><span>Complex</span></div>
                    <div class="legend-desc">Sequential ramp based on complexity percentile. Caveat: Complexity is decision-point count (ADR-004).</div>
                `;
                break;
        }

        this.el.innerHTML = content;
    }
}
