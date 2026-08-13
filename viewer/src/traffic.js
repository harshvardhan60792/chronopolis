import * as THREE from 'three';

export function createTraffic(cityData, density = 0.6) {
    const roads = cityData.layout.roads || [];
    if (roads.length === 0) return null;
    
    const K = 16;
    const roadCount = roads.length;
    
    const texData = new Float32Array(K * roadCount * 4);
    
    for (let i = 0; i < roadCount; i++) {
        const road = roads[i];
        const pts = road.pts;
        
        let len = 0;
        const d_pts = [];
        d_pts.push({pt: new THREE.Vector3(...pts[0]), dist: 0});
        for(let j = 1; j < pts.length; j++) {
            const p0 = d_pts[j-1].pt;
            const p1 = new THREE.Vector3(...pts[j]);
            const d = p0.distanceTo(p1);
            len += d;
            d_pts.push({pt: p1, dist: len});
        }
        
        for (let k = 0; k < K; k++) {
            const targetDist = (k / (K - 1)) * len;
            let seg = 0;
            while(seg < d_pts.length - 2 && d_pts[seg+1].dist < targetDist) {
                seg++;
            }
            const start = d_pts[seg];
            const end = d_pts[seg+1] || start;
            
            let t = 0;
            const segDist = end.dist - start.dist;
            if (segDist > 0) t = (targetDist - start.dist) / segDist;
            
            const pt = new THREE.Vector3().lerpVectors(start.pt, end.pt, t);
            
            const idx = (i * K + k) * 4;
            texData[idx] = pt.x;
            texData[idx+1] = pt.y;
            texData[idx+2] = pt.z;
            texData[idx+3] = targetDist;
        }
    }
    
    const dataTexture = new THREE.DataTexture(texData, K, roadCount, THREE.RGBAFormat, THREE.FloatType);
    dataTexture.needsUpdate = true;
    
    const minP = 1;
    const maxP = 14;
    const maxParticles = 40000;
    
    let totalP = 0;
    const roadParticles = [];
    
    for (let i = 0; i < roadCount; i++) {
        let count = Math.round(minP + (maxP - minP) * density);
        roadParticles.push(count);
        totalP += count;
    }
    
    if (totalP > maxParticles) {
        const scale = maxParticles / totalP;
        totalP = 0;
        for (let i = 0; i < roadCount; i++) {
            roadParticles[i] = Math.round(roadParticles[i] * scale);
            totalP += roadParticles[i];
        }
    }
    
    const positions = new Float32Array(totalP * 3);
    const aRoad = new Float32Array(totalP);
    const aOffset = new Float32Array(totalP);
    const aSpeed = new Float32Array(totalP);
    const aSide = new Float32Array(totalP);
    
    let pIdx = 0;
    for (let i = 0; i < roadCount; i++) {
        const count = roadParticles[i];
        for (let p = 0; p < count; p++) {
            aRoad[pIdx] = i;
            aOffset[pIdx] = Math.random();
            aSpeed[pIdx] = 0.6 + Math.random() * 0.8;
            aSide[pIdx] = Math.random() > 0.5 ? 1 : -1;
            pIdx++;
        }
    }
    
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('aRoad', new THREE.BufferAttribute(aRoad, 1));
    geo.setAttribute('aOffset', new THREE.BufferAttribute(aOffset, 1));
    geo.setAttribute('aSpeed', new THREE.BufferAttribute(aSpeed, 1));
    geo.setAttribute('aSide', new THREE.BufferAttribute(aSide, 1));
    
    const vertexShader = `
        uniform sampler2D uPaths;
        uniform float uTime;
        uniform float uSpeedScale;
        uniform float uLaneWidth;
        uniform float uRideHeight;
        uniform float uSize;
        
        attribute float aRoad;
        attribute float aOffset;
        attribute float aSpeed;
        attribute float aSide;
        
        varying float vOffset;
        
        void main() {
            int K = 16;
            float t = fract(aOffset + uTime * aSpeed * uSpeedScale);
            float fk = t * float(K - 1);
            int k = int(floor(fk));
            
            vec3 a = texelFetch(uPaths, ivec2(k, int(aRoad)), 0).xyz;
            vec3 b = texelFetch(uPaths, ivec2(k + 1, int(aRoad)), 0).xyz;
            
            vec3 pos = mix(a, b, fract(fk));
            vec3 dir = normalize(b - a);
            if (length(dir) < 0.001) dir = vec3(1.0, 0.0, 0.0);
            
            pos += vec3(-dir.z, 0.0, dir.x) * aSide * uLaneWidth;
            pos.y += uRideHeight;
            
            vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
            gl_PointSize = uSize * (300.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
            
            vOffset = aOffset;
        }
    `;
    
    const fragmentShader = `
        varying float vOffset;
        uniform vec3 uColorHot;
        uniform vec3 uColorCool;
        
        void main() {
            vec2 p = gl_PointCoord - 0.5;
            float d = length(p);
            float a = 1.0 - smoothstep(0.3, 0.5, d);
            if (a < 0.01) discard;
            
            vec3 color = mix(uColorCool, uColorHot, sin(vOffset * 6.28) * 0.5 + 0.5);
            
            gl_FragColor = vec4(color, a);
        }
    `;
    
    const mat = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms: {
            uPaths: { value: dataTexture },
            uTime: { value: 0 },
            uSpeedScale: { value: 0.05 },
            uLaneWidth: { value: 0.2 },
            uRideHeight: { value: 0.1 }, 
            uSize: { value: 2.0 },
            uColorCool: { value: new THREE.Color(0x3572A5) },
            uColorHot: { value: new THREE.Color(0xe34c26) }
        },
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });
    
    const points = new THREE.Points(geo, mat);
    
    function update(time) {
        mat.uniforms.uTime.value = time;
    }
    
    return { points, update };
}
