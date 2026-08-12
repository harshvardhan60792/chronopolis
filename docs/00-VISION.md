# 00 — Vision

## One sentence

Chronopolis turns a git repository into a city you can fly through **and
rewind**, where the traffic on the roads is real coupling mined from commit
history.

## The problem it actually solves

Dropping into an unfamiliar codebase, four questions cost days to answer:

1. Where is the complexity concentrated? (*Which files will hurt me?*)
2. What is actually coupled? (*If I touch this, what breaks?*)
3. What is dead? (*What can I ignore entirely?*)
4. Who knows this code? (*Who do I ask, and what has no owner left?*)

Every one of those has a spatial answer. Chronopolis renders all four in a
single scene, and the time axis answers a fifth question no static tool can:
*how did it get like this?*

## Why "one level above" the existing software-city tools

Prior art and its ceiling:

- **CodeCity (Wettel, 2008)** — the academic origin. Static snapshot, Smalltalk,
  not usable today.
- **SoftVis3D / jscity / code-city ports** — modern renderers, still a single
  static snapshot of structure. Height = LOC, colour = type. That is the whole
  idea, and it is where every implementation stops.
- **Gource** — beautiful history playback, but abstract 2D particle trees with
  no spatial persistence. You cannot learn a codebase's shape from it.
- **GitHub Skyline** — 3D, but only contribution counts. Zero structure.

The gap: **nobody has put structure and history in the same scene.** Structure
tells you what exists; history tells you what matters. Chronopolis is the join.

## The four pillars

### 1. Time machine
The city is built from N snapshots across git history (default 24, evenly
spaced by commit date). A timeline scrubber morphs building heights and
footprints between snapshots and fades buildings in/out as files are born and
deleted. **Layout is computed once over the union of every file that ever
existed**, so a building never moves — only grows, shrinks, appears or vanishes.
That stability is what makes the animation legible instead of a kaleidoscope.

### 2. Traffic from temporal coupling
For every pair of files, count how often they changed in the same commit
(Jaccard-normalised against their individual churn). High coupling becomes a
road with heavy animated traffic. Import edges are the *declared* structure;
co-change is the *actual* structure. Where they disagree is where the bugs live.
No other visual tool renders that disagreement.

### 3. Urban decay, fire, and ownership
A composite health score per building drives its material:

- healthy → clean lit facade
- high complexity + high churn → glowing embers / fire (a hotspot: changed
  often *and* hard to change)
- untouched for years → dark, desaturated, overgrown (a ruin)
- single-author, high-importance → marked with an ownership beacon (bus factor 1)

Four metrics collapse into one glance.

### 4. Postcards
`Export → postcard.png` and `Export → chronopolis-<repo>.html`, a single
self-contained file with the city embedded. Anyone can open it. No server, no
install. This is the sharing loop that makes the project spread.

## Non-goals (say no on purpose)

- No AI, LLM, or ML anywhere. Explanations are rule-based templates.
- No backend, database, accounts, or telemetry.
- No realistic 3D art. Flat-shaded low-poly reads better and runs faster.
- No IDE plugin, no language server, no live file watching in v1.
- No multi-language deep parsing in v1 — Python is the deep target; other files
  still appear as buildings with generic metrics so the city is complete.

## What "done" looks like for v1

A person clones the repo, runs one command against their own project, opens a
page, and within ten seconds says "that's my codebase" — then finds a hotspot
they did not know about, and screenshots it.
