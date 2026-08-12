# T14 — Stories + auto city tour (rule-based, no AI)

**Blocked by:** T02, T03, T07 · **Effort:** medium

## Goal
On first load, the city tells you what it found. A cinematic camera path stops
at 5–7 landmarks with one sentence each. This is the ten-second "this tool is
useful" moment, and it is 100% deterministic template text — no LLM, ever.

## Part A — citygen (`citygen/stories.py`)

Compute candidate findings, score them, keep the best per kind, emit to
`city.stories` (schema in `docs/02-DATA-SCHEMA.md`).

| kind | rule | template |
|---|---|---|
| `god_file` | max `in_deg`, require `in_deg >= 5` | `{name} is imported by {in_deg} files and changed in {commits} commits. Everything depends on it.` |
| `hotspot` | max `health`, require churn and complexity both above the 80th percentile | `{name} is the hardest thing here to change safely: complexity {complexity}, {commits} commits, {churn} lines churned.` |
| `hidden_coupling` | top `cochange` strength with **no** import edge either way | `{a} and {b} changed together in {n} commits but never import each other.` |
| `ruin` | largest file with `stale_days > 365` and `in_deg == 0` | `{name} ({loc} lines) has not been touched in {years} years and nothing imports it.` |
| `bus_factor` | largest file with `bus_factor == 1` and `commits >= 10` | `{owner} wrote {share}% of {name}. If they leave, this block goes dark.` |
| `fastest_growing` | biggest LOC delta over the last quarter of history | `{name} grew {delta} lines in the last {days} days — the fastest growth in the repo.` |
| `biggest_district` | district with max complexity share | `{dir} is {pct}% of the repo's complexity in {files} files.` |

Each story carries a camera hint (`target` = plot centre + height, `distance`).
Percentages rounded to integers; no story emitted when its rule is unmet — an
empty stories array is correct output for a trivial repo, never invent filler.

## Part B — viewer (`viewer/src/tour.js`)

- On first load (no `?q=`, no `?city=` deep link), after 1.5 s, show a small
  card: `Take the 40-second tour ▸` / `skip`. Never auto-start without consent —
  hijacking the camera on load is hostile.
- Tour: `flyTo` each story's camera hint, 3.5 s per stop, caption card fading
  in, the subject building pulsing and everything else dimmed to 30%.
- `Space` pauses, `→` next, `Esc` exits to free orbit at the current position.
- The story list is also available any time from a `Findings` button — it is a
  list of 7 clickable insights, which is arguably more useful than the tour
  itself.

## Acceptance criteria
- Stories are correct: verify each one by hand against the repo. A wrong claim
  here destroys trust in the whole tool.
- No story text contains a placeholder, `undefined`, or `NaN`.
- Tour runs end to end without the camera clipping through buildings.
- Works with `git: null` (structure-only stories: `god_file`,
  `biggest_district`; the rest are simply absent).
- Tour is skippable and never replays automatically.

## Default if ambiguous
- Max 7 stories, one per kind, ordered by score desc.
- Text is fixed English templates in `stories.py`. No i18n in v1.
