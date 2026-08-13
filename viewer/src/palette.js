import * as THREE from 'three';

export function generateDistrictColors() {
    const colors = [];
    for (let i = 0; i < 12; i++) {
        let h = (i * 30);
        if (h >= 55 && h <= 70) h += 20; 
        const color = new THREE.Color();
        color.setHSL(h / 360, 0.55, 0.42);
        colors.push(color);
    }
    return colors;
}

export const districtHues = generateDistrictColors();

export const langPalette = {
    'python': new THREE.Color(0x3572A5),
    'javascript': new THREE.Color(0xf1e05a),
    'typescript': new THREE.Color(0x3178c6),
    'docs': new THREE.Color(0x888888),
    'data': new THREE.Color(0x999999),
    'style': new THREE.Color(0x563d7c),
    'markup': new THREE.Color(0xe34c26),
    'other': new THREE.Color(0xaaaaaa),
};
