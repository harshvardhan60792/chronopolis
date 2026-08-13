import * as THREE from 'three';
import { langPalette } from './palette.js';

export function createBuildings(buildings, plots) {
    const geo = new THREE.BoxGeometry(1, 1, 1);
    geo.translate(0, 0.5, 0);
    
    const pos = geo.attributes.position;
    const colors = new Float32Array(pos.count * 3);
    for (let i = 0; i < pos.count; i++) {
        const y = pos.getY(i);
        const shade = y < 0.1 ? 0.6 : 1.0;
        colors[i*3] = shade;
        colors[i*3+1] = shade;
        colors[i*3+2] = shade;
    }
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    
    const mat = new THREE.MeshLambertMaterial({ 
        color: 0xffffff,
        vertexColors: true 
    });
    
    const mesh = new THREE.InstancedMesh(geo, mat, buildings.length);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    
    const dummy = new THREE.Object3D();
    
    for (let i = 0; i < buildings.length; i++) {
        const b = buildings[i];
        const plot = plots[i];
        if (!plot) continue;
        
        dummy.position.set(plot.x + plot.w/2, 0, plot.z + plot.d/2);
        dummy.scale.set(plot.w, plot.h, plot.d);
        dummy.updateMatrix();
        
        mesh.setMatrixAt(i, dummy.matrix);
        
        let c = langPalette[b.lang];
        if (!c) c = langPalette['other'];
        mesh.setColorAt(i, c);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    
    return mesh;
}
