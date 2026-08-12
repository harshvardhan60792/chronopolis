# T07 — Camera: orbit + fly + smooth transitions

**Blocked by:** T05 · **Effort:** medium

## Goal
Two modes, one key to switch, and a `flyTo(target)` used by search (T13) and
the tour (T14). Navigation must be obvious without reading docs.

## Files
- new: `viewer/src/controls.js`
- edit: `viewer/src/scene.js`, `viewer/src/ui.js`

## Orbit mode (default)
`OrbitControls` with damping 0.08, `minDistance` 8, `maxDistance` world*2,
`maxPolarAngle` 1.52. Left drag rotate, right drag pan, wheel zoom.

## Fly mode (`F` toggles)
Do **not** use `FlyControls`/`PointerLockControls` blindly — write ~80 lines:

- pointer lock on canvas click; `Esc` releases (browser does this for free)
- mouse delta → yaw/pitch, pitch clamped to ±85°
- `WASD` move in camera-forward/right (horizontal plane only for W/S unless
  `look-fly` is on), `Space`/`Shift` up/down, `Ctrl` slow, `Shift+W` boost
- velocity with exponential damping (`v *= 0.86` per frame at 60 fps,
  frame-rate corrected via `dt`), not instant stop
- collision: none against buildings, but clamp `y >= 1.5` so you cannot fall
  through the ground

Base speed scales with world size: `speed = world.width / 200 * 40` units/s.

## flyTo(target, distance, duration)
Tween camera position and controls target together with an ease-in-out cubic,
default 900 ms. Cancel on any user input. Implement as a small tween object
updated in the render loop — do not add a tween library.

```js
flyTo({ x, y, z }, distance = 40, duration = 900)
```
Must work in both modes; in fly mode it also re-derives yaw/pitch at the end so
control does not snap.

## Onboarding (required, this is the "no docs needed" bar)
- A small persistent hint in the corner: `drag orbit · scroll zoom · F fly ·
  click a building`. Fades to 30% opacity after 8 s, returns on hover.
- In fly mode the hint swaps to `WASD move · mouse look · Space/Shift up-down ·
  F exit`.
- `H` toggles all UI (for clean screenshots).
- `R` resets to the default overview camera.

## Acceptance criteria
- Mode switch is instant and never leaves the camera underground or inside a
  building.
- Fly speed feels right on both a 39-file and a 1000-file city (that is what
  the world-relative speed is for).
- `flyTo` used from the console works in both modes.
- No pointer-lock error spam in the console.
- fps unchanged.

## Default if ambiguous
- Orbit is the landing mode. Fly is opt-in; never auto-enter it.
- Invert-Y off. No settings menu in v1.
