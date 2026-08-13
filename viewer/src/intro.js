import { animate as anime } from 'animejs';

/**
 * Opening move.
 *
 * A city you are dropped into is a screenshot; a city you descend into is a
 * place. This flies the camera down and inward over ~3.4s on load, then hands
 * control back. Any input aborts it immediately - an intro you cannot skip is
 * an intro people resent.
 *
 * anime.js drives it (the project's animation engine for non-3D-specific
 * motion, see ADR-010); the camera is just numbers on an object.
 */
export function playIntro(camera, controls, world) {
    // Ends low and close: a high overview reads as a map, and a map is not
    // what anyone screenshots. Sitting the camera at roughly a third of the
    // world's width above ground puts the skyline against the sky instead of
    // flattening it into a floor plan.
    // Positions are offsets FROM THE CITY CENTRE, not absolute world
    // coordinates. The city spans 0..world.width, so an absolute 0.6 * width
    // lands the camera in the middle of downtown looking at a wall.
    const cx = world.width / 2;
    const cz = world.depth / 2;
    const reach = world.width;

    // The default view has one job: show the whole city and enough of the land
    // around it to place it. Comprehension first - a dramatic low angle that
    // hides two thirds of the repo is a worse default than a clear one.
    const start = {
        x: cx + reach * 1.35,
        y: reach * 0.95,
        z: cz + reach * 1.35,
    };
    const end = {
        x: cx + reach * 0.88,
        y: reach * 0.46,
        z: cz + reach * 0.88,
    };

    camera.position.set(start.x, start.y, start.z);
    if (controls.target) controls.target.set(world.width / 2, 0, world.depth / 2);

    const state = { ...start };
    let cancelled = false;

    const flight = anime(state, {
        x: end.x,
        y: end.y,
        z: end.z,
        duration: 3400,
        ease: 'inOutQuint',
        onUpdate: () => {
            if (cancelled) return;
            camera.position.set(state.x, state.y, state.z);
            // Aim slightly above ground level so the towers, not the tarmac,
            // sit in the middle of the frame.
            camera.lookAt(world.width / 2, world.width * 0.05, world.depth / 2);
            if (controls.target) {
                controls.target.set(world.width / 2, world.width * 0.05, world.depth / 2);
            }
        },
    });

    const abort = () => {
        if (cancelled) return;
        cancelled = true;
        if (flight && typeof flight.pause === 'function') flight.pause();
        window.removeEventListener('pointerdown', abort);
        window.removeEventListener('wheel', abort);
        window.removeEventListener('keydown', abort);
    };

    window.addEventListener('pointerdown', abort, { once: true });
    window.addEventListener('wheel', abort, { once: true, passive: true });
    window.addEventListener('keydown', abort, { once: true });

    // Fade the chrome in behind the flight rather than slapping it on frame 1.
    const panels = document.querySelectorAll('.legend, .hint, #hint, #legend, .overlay-ui');
    if (panels.length) {
        anime(panels, {
            opacity: [0, 1],
            translateY: [-8, 0],
            delay: (_el, i) => 400 + i * 90,
            duration: 700,
            ease: 'outCubic',
        });
    }
}
