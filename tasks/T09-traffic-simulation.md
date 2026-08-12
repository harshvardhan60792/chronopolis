# T09 — Traffic simulation (headline feature)

**Blocked by:** T03, T06 · **Effort:** large

## Goal
Animated flow along `layout.roads`, where volume and speed encode **temporal
coupling** (`edges.cochange`). The city stops being a diagram and becomes alive,
and the animation is carrying real information: congested corridors are pairs of
files that keep changing together.

## Files
- new: `viewer/src/traffic.js`
- edit: `viewer/src/main.js`, `viewer/src/ui.js` (toggle + density slider)

## The one rule
**The CPU must not move particles.** Every particle's position is a function of
`uTime` evaluated in the vertex shader. One `Points` (or one InstancedMesh of a
small quad if you want oriented vehicles) for the entire city, one draw call,
zero per-frame allocation.

## Data preparation (once, at load)
For each road `r` in `layout.roads` (already routed by T04):
- resample its polyline to a fixed `K = 16` points → a per-road path baked into
  a `DataTexture` (`RGBA32F`, width = K, height = roadCount) holding `xyz` +
  cumulative length. Sampling a texture in the vertex shader is the cheapest way
  to give every particle a different path.
- particle count for the road: `round(minP + strength * (maxP - minP))`,
  default `minP = 1`, `maxP = 14`, then scaled by the global density slider.

Build one flat attribute set: for each particle, `aRoad` (row index),
`aOffset` (0..1 phase), `aSpeed` (0.6..1.4 jitter × road speed), `aSide`
(-1/+1 lane offset so two directions do not overlap).

## Vertex shader sketch
```glsl
float t = fract(aOffset + uTime * aSpeed * uSpeedScale);
float fk = t * float(K - 1);
int   k  = int(floor(fk));
vec3  a  = texelFetch(uPaths, ivec2(k,     int(aRoad)), 0).xyz;
vec3  b  = texelFetch(uPaths, ivec2(k + 1, int(aRoad)), 0).xyz;
vec3  pos = mix(a, b, fract(fk));
vec3  dir = normalize(b - a);
pos += vec3(-dir.z, 0.0, dir.x) * aSide * uLaneWidth;   // lane offset
pos.y += uRideHeight;
gl_PointSize = uSize * (300.0 / -mvPosition.z);         // perspective sizing
```
Fragment: soft round sprite (`smoothstep` on `gl_PointCoord` distance), additive
blending, `depthWrite: false`, colour lerped between two palette colours by
road strength (cool = weak coupling, hot = strong).

If `layout.road_style === "arcs"`, the same shader works — the baked path is
just the sampled bezier instead of a street route.

## Controls and legend
- `T` toggles traffic.
- Density slider 0–100% (default 60%) → scales `maxP` and re-issues the buffer
  (rebuild is fine; it is not per-frame).
- Legend states the source honestly: `traffic = files that change together
  (last N commits)` or, in fallback mode, `traffic = imports (history too
  shallow for co-change)`.

## Budget
`maxParticles` default 40 000, hard cap 120 000. Compute the sum first; if it
exceeds the cap, scale every road's count down proportionally rather than
dropping roads (losing whole roads loses information; thinning does not).

## Acceptance criteria
- 40 000 particles at ≥ 55 fps on the `reachable` city and ≥ 30 fps on the
  1000-file city, measured with `?stats=1`.
- Zero per-frame allocations (check with a heap profile: sawtooth should be
  flat).
- Particles visibly follow roads, do not fly through buildings, do not
  disappear at path ends (the `fract` wrap must be seamless).
- Turning traffic off returns fps to the T08 baseline.
- 10-second screen recording into `docs/img/T09-traffic.gif` (or a stills pair).

## Default if ambiguous
- Round glowing dots, not modelled cars. Cars at this scale are invisible and
  cost geometry.
- One-directional flow per road, direction A→B by index order; use `aSide`
  lanes only if the road serves both an import and a co-change relation.
- If `edges.cochange` is empty and `stats.traffic_source === "imports"`, drive
  from import edges with weight in place of strength.
