import * as THREE from 'three';
import { districtHues } from './palette.js';

export function createDistricts(districts) {
    if (!districts || districts.length === 0) {
        return new THREE.Object3D();
    }
    const geo = new THREE.BoxGeometry(1, 1, 1);
    geo.translate(0, 0.5, 0); 
    const mat = new THREE.MeshLambertMaterial({ vertexColors: false }); 
    
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
        hsl.l = Math.max(0.1, hsl.l - (d.depth - 1) * 0.05);
        color.setHSL(hsl.h, hsl.s, hsl.l);
        
        mesh.setColorAt(i, color);
    }
    
    return mesh;
}
