import * as THREE from 'three';

/**
 * Colour system.
 *
 * Built on the two rules film colour has settled on, because they solve
 * exactly the problem this tool has - "which of these thousand things should I
 * be looking at":
 *
 * 1. **Complementary separation.** Hollywood's teal/orange grade works because
 *    complementary hues push the subject forward and the surroundings back.
 *    Here the environment - sky, sea, land, pavement - is held in the cool
 *    teal-blue half of the wheel, and the *data* (buildings) lives in the warm
 *    half. Buildings detach from the ground with no outline or glow needed.
 *
 * 2. **Desaturate the environment, saturate the focus.** A colour script keeps
 *    most of the frame muted so that saturation itself becomes a signal. The
 *    terrain never exceeds ~0.25 saturation; buildings sit around 0.45-0.60;
 *    the selected building and search hits are the only fully saturated things
 *    on screen. That is why they read instantly.
 *
 * Practical constraints layered on top:
 * - every building colour keeps a lightness of 0.45-0.68 so it separates from
 *   the dark land in daylight AND stays visible at dusk;
 * - hues avoid the 55-75 deg band (muddy yellow-green) which reads as "dead
 *   grass" against the terrain;
 * - no red/green-only distinctions carry meaning on their own; the overlay
 *   modes pair hue with lightness so the ramps survive colour blindness.
 */

const ENVIRONMENT = {
    // Cool, low saturation. These are deliberately dull - they are the stage.
    // Land leans olive-green and sea leans blue on purpose: at the default
    // camera distance a teal-green land and a teal-blue sea were the same
    // tone, and the city looked like it was floating on open water.
    grass: 0x5f6d4a,
    earth: 0x7d7458,
    sea: 0x2a4761,
    pavement: 0x3b4450,
};

export function generateDistrictColors() {
    // District slabs are pavement, not data. They vary only enough to tell
    // neighbourhoods apart at a glance; the hue spread is wide but the
    // saturation is almost flat, so no district ever out-shouts a building.
    const colors = [];
    for (let i = 0; i < 12; i++) {
        let h = i * 30;
        if (h >= 55 && h <= 75) h += 22;
        const color = new THREE.Color();
        color.setHSL(h / 360, 0.14, 0.30);
        colors.push(color);
    }
    return colors;
}

export const districtHues = generateDistrictColors();

/**
 * Language palette - warm-biased so buildings sit opposite the cool terrain,
 * with lightness carrying as much of the distinction as hue does.
 */
export const langPalette = {
    python: new THREE.Color(0xd9a441),        // warm amber
    javascript: new THREE.Color(0xe8c35a),    // straw
    typescript: new THREE.Color(0x7fa9d8),    // the one cool code colour, kept
    docs: new THREE.Color(0xcfc6b8),          // parchment
    data: new THREE.Color(0x9aa7b4),          // cool grey - data is scaffolding
    style: new THREE.Color(0xb98ac9),         // orchid
    markup: new THREE.Color(0xe0805f),        // terracotta
    shell: new THREE.Color(0x8fbf9f),         // sage
    sql: new THREE.Color(0xc8907a),
    java: new THREE.Color(0xd08a5a),
    go: new THREE.Color(0x86c3c9),
    rust: new THREE.Color(0xc98b6b),
    c: new THREE.Color(0xb0b8c4),
    cpp: new THREE.Color(0xa9b0c8),
    other: new THREE.Color(0xb3aca2),
};

export const environmentColors = ENVIRONMENT;

/**
 * Focus emphasis. Selection and search results get saturation and lightness
 * pushed up; everything else gets pulled down. Same trick a colour script uses
 * to tell you where to look, and it costs one multiply per instance.
 */
export function emphasise(color, target = new THREE.Color()) {
    const hsl = {};
    color.getHSL(hsl);
    target.setHSL(hsl.h, Math.min(1, hsl.s * 1.8 + 0.25), Math.min(0.78, hsl.l * 1.25));
    return target;
}

export function recede(color, target = new THREE.Color()) {
    const hsl = {};
    color.getHSL(hsl);
    target.setHSL(hsl.h, hsl.s * 0.25, hsl.l * 0.55);
    return target;
}
