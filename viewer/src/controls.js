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
    // Zoom is handled manually below (dolly-to-cursor, like Google Earth /
    // Cities: Skylines) instead of OrbitControls' default zoom-to-target-line.
    orbit.enableZoom = false;

    const defaultPos = camera.position.clone();
    const defaultTarget = orbit.target.clone();

    let yaw = 0;
    let pitch = 0;
    const velocity = new THREE.Vector3();
    const keys = { w: false, a: false, s: false, d: false, q: false, e: false, ' ': false, shift: false, ctrl: false };

    const baseSpeed = (worldWidth / 200) * 40;

    // Ground-plane raycast, used by dolly-to-cursor zoom and double-click-to-go.
    const raycaster = new THREE.Raycaster();
    const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    const ndc = new THREE.Vector2();
    function groundHit(clientX, clientY) {
        ndc.x = (clientX / window.innerWidth) * 2 - 1;
        ndc.y = -(clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(ndc, camera);
        const pt = new THREE.Vector3();
        return raycaster.ray.intersectPlane(groundPlane, pt) ? pt : null;
    }
    
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
    
    function enterFly() {
        mode = 'fly';
        updateUIForMode(mode);
        orbit.enabled = false;
        const euler = new THREE.Euler().setFromQuaternion(camera.quaternion, 'YXZ');
        yaw = euler.y;
        pitch = euler.x;
        renderer.domElement.requestPointerLock();
    }

    function exitFly() {
        mode = 'orbit';
        updateUIForMode(mode);
        orbit.enabled = true;
        const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
        orbit.target.copy(camera.position).add(dir.multiplyScalar(50));
    }

    function toggleMode() {
        if (mode === 'orbit') {
            enterFly();
        } else {
            document.exitPointerLock();
            exitFly();
        }
    }

    // The browser can drop pointer lock on its own (Escape, alt-tab, a
    // permission prompt) without us calling exitPointerLock() first. If we
    // don't notice, `mode` stays 'fly' forever: WASD goes dead, the hint
    // still reads "fly", and there is no way back in except pressing F blind.
    document.addEventListener('pointerlockchange', () => {
        if (mode === 'fly' && document.pointerLockElement !== renderer.domElement) {
            exitFly();
        }
    });

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

    // Dolly toward whatever is under the cursor, not the orbit target - the
    // zoom behaviour every map/city tool (Google Earth, Cities: Skylines)
    // uses because zooming toward screen-center feels wrong the moment your
    // mouse isn't centered.
    renderer.domElement.addEventListener('wheel', (e) => {
        activeTween = null;
        if (mode !== 'orbit') return;
        e.preventDefault();

        const dist = camera.position.distanceTo(orbit.target);
        const factor = e.deltaY < 0 ? 0.88 : 1 / 0.88;
        let newDist = dist * factor;
        newDist = Math.max(orbit.minDistance, Math.min(orbit.maxDistance, newDist));
        const clampedFactor = newDist / dist;
        if (clampedFactor === 1) return;

        const hit = groundHit(e.clientX, e.clientY) || orbit.target;
        const shift = 1 - clampedFactor;
        camera.position.lerp(hit, shift);
        orbit.target.lerp(hit, shift);
    }, { passive: false });

    // Double-click open ground to fly the camera there - click-to-navigate,
    // the same shortcut RTS/city-builder cameras use.
    renderer.domElement.addEventListener('dblclick', (e) => {
        if (mode !== 'orbit') return;
        const hit = groundHit(e.clientX, e.clientY);
        if (hit) flyTo(hit, camera.position.distanceTo(orbit.target) * 0.55, 650);
    });
    
    let lastTime = performance.now();
    
    function update() {
        const now = performance.now();
        // Clamp dt: a backgrounded tab or a stalled rAF (also how this
        // project's browser-automation pane behaves - see T16 notes) can
        // make the next frame's dt huge, which would otherwise teleport the
        // camera the instant a movement key is held.
        const dt = Math.min((now - lastTime) / 1000, 0.1);
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
            // WASD/QE pan and rotate the orbit camera too, RTS-style, on top
            // of drag-to-orbit - so keyboard-only navigation works without
            // switching into fly mode. Pan speed scales with current zoom
            // distance so it covers ground at a consistent screen-space rate
            // whether zoomed in on one building or looking at the whole city.
            const dir = new THREE.Vector3();
            if (keys.w) dir.z -= 1;
            if (keys.s) dir.z += 1;
            if (keys.a) dir.x -= 1;
            if (keys.d) dir.x += 1;
            if (dir.lengthSq() > 0) {
                dir.normalize();
                dir.applyQuaternion(camera.quaternion);
                dir.y = 0;
                dir.normalize();
                const dist = camera.position.distanceTo(orbit.target);
                dir.multiplyScalar(dist * 1.1 * dt * (keys.shift ? 2.5 : 1));
                camera.position.add(dir);
                orbit.target.add(dir);
            }
            if (keys.q || keys.e) {
                const angle = (keys.q ? 1 : -1) * dt * 1.6;
                const offset = new THREE.Vector3().subVectors(camera.position, orbit.target);
                offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), angle);
                camera.position.copy(orbit.target).add(offset);
            }
            orbit.update();
        } else if (mode === 'fly' && document.pointerLockElement === renderer.domElement) {
            const dir = new THREE.Vector3();
            if (keys.w) dir.z -= 1;
            if (keys.s) dir.z += 1;
            if (keys.a) dir.x -= 1;
            if (keys.d) dir.x += 1;

            // Speed scales with altitude, same as creative-flight in Google
            // Earth/Minecraft: crawl near street level where precision
            // matters, cover ground fast up high where it doesn't.
            const heightFactor = Math.max(0.35, Math.min(5, camera.position.y / 15));
            let speed = baseSpeed * heightFactor * dt * 60;
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
