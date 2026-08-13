import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { updateUIForMode } from './ui.js';

export function setupControls(camera, renderer, worldWidth) {
    let mode = 'orbit'; 
    
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true;
    orbit.dampingFactor = 0.08;
    orbit.minDistance = 8;
    orbit.maxDistance = worldWidth * 2;
    orbit.maxPolarAngle = 1.52;
    orbit.target.set(worldWidth / 2, 0, worldWidth / 2);
    
    const defaultPos = camera.position.clone();
    const defaultTarget = orbit.target.clone();
    
    let yaw = 0;
    let pitch = 0;
    const velocity = new THREE.Vector3();
    const keys = { w: false, a: false, s: false, d: false, ' ': false, shift: false, ctrl: false };
    
    const baseSpeed = (worldWidth / 200) * 40;
    
    function onMouseMove(e) {
        if (mode !== 'fly' || document.pointerLockElement !== renderer.domElement) return;
        const movementX = e.movementX || 0;
        const movementY = e.movementY || 0;
        yaw -= movementX * 0.002;
        pitch -= movementY * 0.002;
        pitch = Math.max(-1.48, Math.min(1.48, pitch)); 
        
        camera.quaternion.setFromEuler(new THREE.Euler(pitch, yaw, 0, 'YXZ'));
    }
    
    function onKeyDown(e) {
        const k = e.key.toLowerCase();
        if (keys.hasOwnProperty(k)) keys[k] = true;
        if (e.key === 'Shift') keys.shift = true;
        if (e.key === 'Control') keys.ctrl = true;
        
        if (k === 'f') {
            toggleMode();
        }
        if (k === 'r') {
            if (mode === 'orbit') {
                flyTo(defaultTarget, defaultPos.distanceTo(defaultTarget), 900);
            }
        }
    }
    
    function onKeyUp(e) {
        const k = e.key.toLowerCase();
        if (keys.hasOwnProperty(k)) keys[k] = false;
        if (e.key === 'Shift') keys.shift = false;
        if (e.key === 'Control') keys.ctrl = false;
    }
    
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);
    
    renderer.domElement.addEventListener('click', () => {
        if (mode === 'fly') {
            renderer.domElement.requestPointerLock();
        }
    });
    
    function toggleMode() {
        mode = mode === 'orbit' ? 'fly' : 'orbit';
        updateUIForMode(mode);
        if (mode === 'fly') {
            orbit.enabled = false;
            const euler = new THREE.Euler().setFromQuaternion(camera.quaternion, 'YXZ');
            yaw = euler.y;
            pitch = euler.x;
            renderer.domElement.requestPointerLock();
        } else {
            document.exitPointerLock();
            orbit.enabled = true;
            const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
            const dist = 50;
            orbit.target.copy(camera.position).add(dir.multiplyScalar(dist));
        }
    }
    
    let activeTween = null;
    
    function easeInOutCubic(x) {
        return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
    }
    
    function flyTo(targetPos, distance = 40, duration = 900) {
        const startPos = camera.position.clone();
        const startTarget = orbit.target.clone();
        
        const offset = new THREE.Vector3().subVectors(startPos, startTarget).normalize();
        if (offset.lengthSq() < 0.1) offset.set(0.5, 1, 0.5).normalize();
        const endPos = new THREE.Vector3(targetPos.x, targetPos.y, targetPos.z).add(offset.multiplyScalar(distance));
        const endTarget = new THREE.Vector3(targetPos.x, targetPos.y, targetPos.z);
        
        activeTween = {
            startPos,
            endPos,
            startTarget,
            endTarget,
            startTime: performance.now(),
            duration
        };
    }
    
    renderer.domElement.addEventListener('pointerdown', () => activeTween = null);
    renderer.domElement.addEventListener('wheel', () => activeTween = null);
    
    let lastTime = performance.now();
    
    function update() {
        const now = performance.now();
        const dt = (now - lastTime) / 1000;
        lastTime = now;
        
        if (activeTween) {
            let t = (now - activeTween.startTime) / activeTween.duration;
            if (t >= 1) {
                t = 1;
                camera.position.copy(activeTween.endPos);
                orbit.target.copy(activeTween.endTarget);
                activeTween = null;
                if (mode === 'fly') {
                    camera.lookAt(orbit.target);
                    const euler = new THREE.Euler().setFromQuaternion(camera.quaternion, 'YXZ');
                    yaw = euler.y;
                    pitch = euler.x;
                }
            } else {
                const f = easeInOutCubic(t);
                camera.position.lerpVectors(activeTween.startPos, activeTween.endPos, f);
                orbit.target.lerpVectors(activeTween.startTarget, activeTween.endTarget, f);
                if (mode === 'fly') {
                    camera.lookAt(orbit.target);
                }
            }
            if (mode === 'orbit') orbit.update();
            return;
        }
        
        if (mode === 'orbit') {
            orbit.update();
        } else if (mode === 'fly' && document.pointerLockElement === renderer.domElement) {
            const dir = new THREE.Vector3();
            if (keys.w) dir.z -= 1;
            if (keys.s) dir.z += 1;
            if (keys.a) dir.x -= 1;
            if (keys.d) dir.x += 1;
            
            let speed = baseSpeed * dt * 60;
            if (keys.shift) speed *= keys.w ? 3 : 1; 
            if (keys.ctrl) speed *= 0.3; 
            
            dir.normalize();
            dir.applyQuaternion(camera.quaternion);
            dir.y = 0;
            dir.normalize();
            
            if (keys[' ']) dir.y += 1;
            if (keys.shift && !keys.w) dir.y -= 1;
            
            velocity.x += dir.x * speed * 0.15;
            velocity.y += dir.y * speed * 0.15;
            velocity.z += dir.z * speed * 0.15;
            
            camera.position.add(velocity);
            
            const damping = Math.pow(0.86, dt * 60);
            velocity.multiplyScalar(damping);
            
            if (camera.position.y < 1.5) {
                camera.position.y = 1.5;
                velocity.y = Math.max(0, velocity.y);
            }
        }
    }
    
    return { update, flyTo, orbit };
}
