# T12 — Overlay modes + legend

**Blocked by:** T02, T06 · **Effort:** small-medium

## Goal
One keystroke re-colours the city to answer a different question. Each mode has
a legend that states exactly what the colour means — an unlabelled heat map is
decoration, not a tool.

## Files
- new: `viewer/src/overlays.js`, `viewer/src/legend.js`
- edit: `viewer/src/buildings.js` (colour write path), `viewer/src/ui.js`

## Modes (number keys 1–6)

| Key | Mode | Colour source |
|---|---|---|
| 1 | **Language** | categorical palette by `lang` (default) |
| 2 | **Health** | composite score, green → amber → red (see below) |
| 3 | **Recency** | `stale_days`: bright warm = touched days ago, cold dark = years |
| 4 | **Ownership** | hue per top author (top 8 authors get hues, rest grey) |
| 5 | **Bus factor** | `bus_factor == 1` red, 2 amber, ≥3 green; size-weighted |
| 6 | **Complexity** | sequential ramp on `complexity` percentile |

### Health score (mode 2) — define it once, here
```
churn_n      = percentile_rank(churn)          # 0..1 within this repo
cx_n         = percentile_rank(complexity)
stale_n      = clamp(stale_days / 540, 0, 1)
owner_risk   = owner_share                      # 0..1
health = 0.40*(churn_n * cx_n)      # hotspot: changes a lot AND hard to change
       + 0.25*cx_n
       + 0.20*owner_risk
       + 0.15*(1 - stale_n)         # abandoned code is a different problem
```
Higher = worse. Compute in **citygen** (T12 may add it to `build.py`) so the
viewer just reads `building.health`, and so the number is available to stories
(T14) and to anyone consuming `city.json`. Percentile ranks are within-repo,
which keeps colours meaningful for both a 40-file and a 4000-file project.

Hotspot rendering: buildings above the 95th percentile of health get an
emissive tint and a slow pulse (a sine on `uTime` in the material's
`onBeforeCompile`, not a per-frame colour write).

## Legend
Bottom-left, always visible, matching the active mode: a gradient or swatch
strip, the metric name, min/max values with units, and one sentence of plain
English. Example for mode 2: `red = changed often and hard to change (churn ×
complexity)`.

Also state global caveats where they apply: complexity is decision-point count
(ADR-004), ownership is commit-count based (ADR-009), history may be
approximate (T11).

## Behaviour
- Switching modes cross-fades colours over 250 ms (lerp in the colour buffer).
- Modes needing git data are disabled with a tooltip when `city.git` is null —
  disabled, not hidden, so the feature is discoverable.
- The current mode persists in the URL (`?mode=health`) so screenshots and links
  reproduce.

## Acceptance criteria
- All six modes render distinctly and correctly on `reachable`.
- Mode switch costs < 1 frame hitch on the 1000-file city.
- No mode produces an all-one-colour city (that means the normalisation is
  broken — percentile ranks prevent it; verify on cve-bin-tool).
- Legend text is accurate for every mode. Read it aloud and check it is true.

## Default if ambiguous
- Colour-blind safety: avoid pure red/green pairs; use the viridis-like ramp
  (dark blue → teal → yellow) for sequential modes and reserve red only for the
  top 5% in health/bus-factor modes.
- Language palette stays the landing mode.
