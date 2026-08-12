# T17 — Onboarding: drag-drop, loading, empty and error states

**Blocked by:** T05 · **Effort:** small

## Goal
Someone lands on the page with no city loaded and gets to a rendered city
without reading documentation. Stated requirement: "clean, immediately-obvious
UI on load".

## Files
- new: `viewer/src/dropzone.js` · edit: `viewer/src/ui.js`, `viewer/index.html`

## Empty state (no city found)
Centred card, dark, minimal:

```
        Chronopolis
   your repository as a living city

   ┌─────────────────────────────┐
   │   drop a city.json here     │
   │        or browse            │
   └─────────────────────────────┘

   don't have one?
   $ python -m citygen build /path/to/repo -o city.json     [copy]

   or explore a demo:  [ reachable ]  [ cve-bin-tool ]
```
- Drag anywhere on the page highlights the zone; drop parses (accept `.json`
  and `.json.gz` — decompress with `DecompressionStream`).
- The command line has a one-click copy button.
- Demo buttons load the bundled cities from T18.

## Loading state
- Progress in three explicit stages with real percentages where possible:
  `downloading city.json` → `building 1,071 buildings` → `laying out districts`.
- For large cities, build the scene in chunks with `requestIdleCallback` (or a
  `setTimeout(0)` loop) so the page never white-screens; update the progress
  text between chunks.
- Fade the city in over 600 ms once ready; do not pop.

## Error states — always actionable
| Failure | Message |
|---|---|
| bad JSON | `That file isn't valid JSON. Re-run citygen and try again.` |
| wrong schema | `This city was made by citygen <v>; this viewer expects <v2>.` |
| `layout: null` | `This city has no layout. Re-run: python -m citygen build <repo>` |
| WebGL unavailable | `Your browser can't run WebGL2. Try Chrome or Firefox.` |

Never a blank canvas, never a console-only failure.

## First-run hints
The control hint from T07 plus a single subtle pointer at the first landmark
(`Findings ▸`). Both dismissible and remembered in `localStorage`
(`chronopolis.seen = 1`) — localStorage is local, so it does not violate the no-
backend rule.

## Acceptance criteria
- Opening `index.html` with no query and no `city.json` shows the empty state,
  not an error.
- Drag-drop works for `.json` and `.json.gz`.
- A 1000-file city never blocks the main thread for more than ~200 ms at a
  stretch during load.
- All four error states can be triggered deliberately and read correctly.

## Default if ambiguous
- No settings panel, no theme switcher, no tutorial modal. One card, one hint
  line, done.
