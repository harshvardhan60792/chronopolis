# T13 — Search + fly-to

**Blocked by:** T07, T10 · **Effort:** small

## Goal
Type part of a filename, hit Enter, the camera flies to it. Also filter the
city down to matches.

## Files
- new: `viewer/src/search.js` · edit: `viewer/src/ui.js`

## Behaviour
- `/` or `Ctrl+K` focuses the search box (top-centre, always visible).
- Fuzzy subsequence match over `path`, ranked by: exact filename match >
  filename prefix > path substring > subsequence, tie-broken by complexity desc.
  ~40 lines, no library.
- Live dropdown of the top 8 with path, LOC and complexity.
- `↑/↓` navigate, `Enter` selects → `flyTo` the building, open the info panel,
  pulse-highlight it for 2 s.
- `Esc` clears; empty query restores the full city.
- Non-matching buildings dim to 20% while a query is active (do not hide them —
  keeping the skyline as context is what makes the match legible).
- Supports filter prefixes, all cheap and useful:
  `dir:citygen` · `lang:python` · `>complexity:50` · `owner:ada` ·
  `stale:>180` · `bus:1`. Combine with space. Document them in the placeholder
  text via a `?` hint popover.

## Acceptance criteria
- Search over a 4000-building city stays responsive (< 16 ms per keystroke) —
  precompute a lowercase path array once.
- `flyTo` frames the building sensibly regardless of city size or building
  height (distance ∝ building height + 25).
- Filters compose and the count is shown: `37 of 1,071 match`.
- URL reflects the query (`?q=parser`) so a search result is linkable.

## Default if ambiguous
- Case-insensitive always. No regex mode in v1.
- Search matches file paths only, never file contents (citygen does not ship
  contents, and it must not start).
