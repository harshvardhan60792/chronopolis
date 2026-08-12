# viewer/

Empty on purpose. **T05 creates it** — see `../tasks/T05-viewer-scaffold.md`.

Do not scaffold it early: the viewer reads `layout` from `city.json`, which T04
produces. Building the renderer before the layout exists means inventing a
throwaway layout in JavaScript, which ADR-001 forbids.

Allowed dependencies, total: `three` (runtime), `vite` (dev). Nothing else.
