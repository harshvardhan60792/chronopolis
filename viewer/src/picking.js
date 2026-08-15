import * as THREE from 'three';
import { showPanel, hidePanel } from './panel.js';

export function setupPicking(camera, renderer, scene, cityData, buildingsMesh, arcsData, controls) {
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let hoveredIdx = -1;
    let selectedIdx = -1;
    let lastRaycast = 0;
    
    cityData.buildings.forEach((b, i) => b.idx = i);
    
    const neighbors = new Array(cityData.buildings.length).fill(null).map(() => new Set());
    if (cityData.edges && cityData.edges.import) {
        cityData.edges.import.forEach(e => {
            neighbors[e[0]].add(e[1]);
            neighbors[e[1]].add(e[0]);
        });
    }
    if (cityData.edges && cityData.edges.cochange) {
        cityData.edges.cochange.forEach(e => {
            neighbors[e[0]].add(e[1]);
            neighbors[e[1]].add(e[0]);
        });
    }
    
    const numBuildings = cityData.buildings.length;
    const origColors = new Float32Array(numBuildings * 3);
    const instColor = buildingsMesh.instanceColor;
    if (instColor) {
        origColors.set(instColor.array);
    }
    
    const cHover = new THREE.Color();
    
    function highlight(idx) {
        if (!instColor) return;
        if (idx === -1) {
            instColor.array.set(origColors);
            instColor.needsUpdate = true;
            if (arcsData && arcsData.mesh.geometry.attributes.defaultColor) {
                arcsData.mesh.geometry.attributes.color.array.set(arcsData.mesh.geometry.attributes.defaultColor.array);
                arcsData.mesh.geometry.attributes.color.needsUpdate = true;
            }
            return;
        }
        
        const connected = neighbors[idx];
        
        for (let i = 0; i < numBuildings; i++) {
            cHover.fromArray(origColors, i * 3);
            if (i === idx) {
                cHover.multiplyScalar(1.5); 
            } else if (connected.has(i)) {
                cHover.multiplyScalar(1.1); 
            } else {
                cHover.multiplyScalar(0.35); 
            }
            instColor.setXYZ(i, cHover.r, cHover.g, cHover.b);
        }
        instColor.needsUpdate = true;
        
        if (arcsData && cityData.edges.import) {
            const cAttr = arcsData.mesh.geometry.attributes.color;
            const defC = arcsData.mesh.geometry.attributes.defaultColor;
            if (!cAttr || !defC) return;
            
            for (let i = 0; i < cAttr.count; i++) {
                cAttr.setXYZ(i, defC.getX(i) * 0.15, defC.getY(i) * 0.15, defC.getZ(i) * 0.15);
            }
            
            cityData.edges.import.forEach((e, edgeIdx) => {
                if (e[0] === idx || e[1] === idx) {
                    const startVert = arcsData.arcSegmentRange[edgeIdx * 2];
                    const endVert = arcsData.arcSegmentRange[edgeIdx * 2 + 1];
                    if (startVert !== -1 && endVert !== -1) {
                        for (let v = startVert * 2; v <= endVert * 2 + 1; v++) {
                            cAttr.setXYZ(v, Math.min(1, defC.getX(v)*2), Math.min(1, defC.getY(v)*2), Math.min(1, defC.getZ(v)*2));
                        }
                    }
                }
            });
            cAttr.needsUpdate = true;
        }
    }
    
    function onAction(action, idx) {
        if (action === 'select' || action === 'flyTo') {
            select(idx);
            if (action === 'flyTo' || action === 'select') {
                const plot = cityData.layout.plots[idx];
                if (plot) controls.flyTo({x: plot.x, y: plot.h, z: plot.z}, 50, 900);
            }
        }
    }
    
    function select(idx) {
        selectedIdx = idx;
        if (idx !== -1) {
            showPanel(cityData.buildings[idx], cityData, onAction);
            highlight(idx);
        } else {
            hidePanel();
            highlight(hoveredIdx);
        }
    }
    
    renderer.domElement.addEventListener('mousemove', (e) => {
        if (document.pointerLockElement === renderer.domElement) {
            // fly mode: raycast center of screen
            mouse.x = 0; mouse.y = 0;
        } else {
            mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        }
        
        const now = performance.now();
        if (now - lastRaycast < 33) return; 
        lastRaycast = now;
        
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObject(buildingsMesh);
        
        let newHover = -1;
        if (intersects.length > 0) {
            newHover = intersects[0].instanceId;
        }
        
        if (newHover !== hoveredIdx) {
            hoveredIdx = newHover;
            if (selectedIdx === -1) {
                highlight(hoveredIdx);
            }
        }
    });
    
    renderer.domElement.addEventListener('click', (e) => {
        if (document.pointerLockElement === renderer.domElement) {
            // Do not select on click in fly mode, because click is used to grab pointer lock.
            // Oh, wait, the task says: "click a building". We can do that before fly mode.
            // If already in fly mode, maybe click selects. 
            // "click accuracy: clicking a building always selects"
            // For now, if we are in fly mode, just let it select.
            if (hoveredIdx !== -1) select(hoveredIdx);
            else select(-1);
            return;
        } 
        if (hoveredIdx !== -1) {
            select(hoveredIdx);
        } else {
            select(-1);
        }
    });
    
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            select(-1);
        }
    });
    
    return { select };
}
