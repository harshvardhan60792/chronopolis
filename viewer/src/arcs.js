import * as THREE from 'three';
import { langPalette } from './palette.js';

export function createArcs(cityData) {
    const importEdges = cityData.edges.import || [];
    const maxArcs = 2000;
    
    const buildings = cityData.buildings;
    const plots = cityData.layout.plots;
    
    let edges = importEdges.map((e, idx) => ({ 
        originalIdx: idx, 
        a: e[0], 
        b: e[1], 
        weight: e[2],
        deg: (buildings[e[0]].in_deg + buildings[e[0]].out_deg + buildings[e[1]].in_deg + buildings[e[1]].out_deg)
    }));
    
    edges.sort((a, b) => b.weight - a.weight || b.deg - a.deg);
    
    let truncated = 0;
    if (edges.length > maxArcs) {
        truncated = edges.length;
        edges = edges.slice(0, maxArcs);
    }
    
    const arcSegmentRange = new Int32Array(importEdges.length * 2);
    arcSegmentRange.fill(-1);
    
    const segmentsPerArc = 16;
    const totalVerts = edges.length * segmentsPerArc * 2;
    
    const positions = new Float32Array(totalVerts * 3);
    const colors = new Float32Array(totalVerts * 3);
    const defaultColors = new Float32Array(totalVerts * 3);
    
    let vIdx = 0;
    
    for (const edge of edges) {
        const pa = plots[edge.a];
        const pb = plots[edge.b];
        if (!pa || !pb) continue;
        
        const startVert = vIdx / 3;
        
        const aColor = langPalette[buildings[edge.a].lang] || langPalette.other;
        const bColor = langPalette[buildings[edge.b].lang] || langPalette.other;
        
        const p0 = new THREE.Vector3(pa.x + pa.w/2, pa.h + 0.5, pa.z + pa.d/2);
        const p2 = new THREE.Vector3(pb.x + pb.w/2, pb.h + 0.5, pb.z + pb.d/2);
        
        const dist = p0.distanceTo(p2);
        const lift = Math.max(6, Math.min(70, dist * 0.35));
        const p1 = new THREE.Vector3().addVectors(p0, p2).multiplyScalar(0.5);
        p1.y += lift;
        
        if (edge.a > edge.b) {
            p1.y += 2;
        }
        
        const curve = new THREE.QuadraticBezierCurve3(p0, p1, p2);
        const pts = curve.getPoints(segmentsPerArc);
        
        for (let i = 0; i < segmentsPerArc; i++) {
            const ptA = pts[i];
            const ptB = pts[i+1];
            
            const tA = i / segmentsPerArc;
            const tB = (i+1) / segmentsPerArc;
            
            positions[vIdx] = ptA.x; positions[vIdx+1] = ptA.y; positions[vIdx+2] = ptA.z;
            positions[vIdx+3] = ptB.x; positions[vIdx+4] = ptB.y; positions[vIdx+5] = ptB.z;
            
            const cA = new THREE.Color().copy(aColor).lerp(bColor, tA);
            const cB = new THREE.Color().copy(aColor).lerp(bColor, tB);
            
            const bA = 1.0 - tA * 0.7;
            const bB = 1.0 - tB * 0.7;
            
            colors[vIdx] = cA.r * bA; colors[vIdx+1] = cA.g * bA; colors[vIdx+2] = cA.b * bA;
            colors[vIdx+3] = cB.r * bB; colors[vIdx+4] = cB.g * bB; colors[vIdx+5] = cB.b * bB;
            
            vIdx += 6;
        }
        
        const endVert = (vIdx / 3) - 1;
        arcSegmentRange[edge.originalIdx * 2] = startVert;
        arcSegmentRange[edge.originalIdx * 2 + 1] = endVert;
    }
    
    defaultColors.set(colors);
    
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geo.setAttribute('defaultColor', new THREE.BufferAttribute(defaultColors, 3)); 
    
    const mat = new THREE.LineBasicMaterial({
        vertexColors: true,
        transparent: true,
        opacity: 0.55,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });
    
    const mesh = new THREE.LineSegments(geo, mat);
    
    const initialVisible = importEdges.length < 400;
    mesh.visible = initialVisible;
    
    return {
        mesh,
        arcSegmentRange,
        initialVisible,
        truncated
    };
}
