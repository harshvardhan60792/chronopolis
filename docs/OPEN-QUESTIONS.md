# Open questions for the human

Agents: do not block on these. Each has a working default already chosen in the
task files. Add new entries here; do not delete answered ones, mark them.

| # | Question | Default in force | Status |
|---|----------|------------------|--------|
| Q1 | Project license — MIT or Apache-2.0? | MIT (matches three.js, maximises adoption) | open |
| Q2 | Public name confirmed as "Chronopolis"? npm/GitHub availability unchecked. | Keep Chronopolis; fallback `chronopolis-city` | open |
| Q3 | Should the hosted demo ship with a pre-built city of a famous repo (e.g. flask, requests)? Licence-wise fine, just attribution. | Yes — ship `demo/flask.city.json` if a clone is available offline, else `reachable` | open |
| Q4 | Non-Python language support priority after v1: JS/TS via tree-sitter, or Go? | JS/TS first (bigger audience), tree-sitter wheels are pip-only so it must stay an optional extra | open |
| Q5 | Do we want an audio layer (city ambience keyed to activity)? Cheap wow, risk of gimmick. | Skip for v1, note as v2 idea | open |
