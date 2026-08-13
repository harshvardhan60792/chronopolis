import * as THREE from 'three';
import { districtHues } from './palette.js';

export function createDistricts(districts) {
    if (!districts || districts.length === 0) {
        return new THREE.Object3D();
    }
    const geo = new THREE.BoxGeometry(1, 1, 1);
    geo.translate(0, 0.5, 0);
    // Slabs are pavement, not signage: rough, unlit-looking, and dark enough
    // that the buildings and their windows stay the brightest thing in frame.
    // District hue survives, saturation does not (see the desaturation below).
    const mat = new THREE.MeshStandardMaterial({
        vertexColors: false,
        roughness: 1.0,     // fully rough: any gloss here reads as wet tile and
        metalness: 0.0,     // fights the actual wet-street effect on the ground
    });
    
    const mesh = new THREE.InstancedMesh(geo, mat, districts.length);
    mesh.instanceMatrix.setUsage(THREE.StaticDrawUsage);
    
    const dummy = new THREE.Object3D();
    const color = new THREE.Color();
    
    let topLevelCount = 0;
    const pathHueMap = {};
    
    for (let i = 0; i < districts.length; i++) {
        const d = districts[i];
        if (d.depth === 1) {
            pathHueMap[d.path] = topLevelCount++;
        }
    }
    
    for (let i = 0; i < districts.length; i++) {
        const d = districts[i];
        
        dummy.position.set(d.x + d.w/2, d.depth * 0.01, d.z + d.d/2);
        dummy.scale.set(d.w, 0.2, d.d);
        dummy.updateMatrix();
        mesh.setMatrixAt(i, dummy.matrix);
        
        let parts = d.path.split('/');
        let topPath = parts[0];
        let hueIdx = pathHueMap[topPath] || 0;
        
        const baseC = districtHues[hueIdx % districtHues.length];
        color.copy(baseC);
        
        const hsl = {};
        color.getHSL(hsl);
        // Keep the hue as the district's identity, drop it to city-block
        // darkness. Fully saturated plates made the city look like a chart.
        color.setHSL(
            hsl.h,
            hsl.s * 0.42,
            Math.max(0.055, 0.135 - (d.depth - 1) * 0.022),
        );
        
        mesh.setColorAt(i, color);
    }
    
    return mesh;
}
