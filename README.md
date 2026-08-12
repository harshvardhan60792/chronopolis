# Chronopolis

**Your repository as a living city you can rewind.**

Chronopolis reads any git repository and renders it as an explorable 3D city:
every file is a building, every folder a district, imports are roads, and
*traffic flows along those roads based on which files actually change together
in git history*. Drag the timeline and the city rebuilds itself commit by
commit — watch districts rise, hotspots catch fire, and abandoned code decay.

100% local. No AI, no API keys, no backend, no telemetry. A Python CLI produces
one `city.json`; a static three.js page renders it. Free to build, free to host,
free forever.

---

## Why this is not "another CodeCity"

Software-city visualizations exist (Wettel's CodeCity, SoftVis3D, code-city
ports). Every one of them renders **one static snapshot of structure**.
Chronopolis adds four layers nobody has shipped together:

| Layer | What it shows | Why it is new |
|---|---|---|
| **Time machine** | Scrub git history; buildings grow/shrink/appear/vanish with a stable layout so the city never reshuffles | Existing city tools are single-snapshot; Gource shows history but as abstract 2D particles, not a legible city |
| **Traffic simulation** | Animated vehicles on the roads, volume = *temporal coupling* (how often two files change in the same commit) | Static import graphs miss the real coupling. Traffic makes hidden dependencies visible as congestion |
| **Urban decay & fire** | Material state from churn × complexity × age × ownership concentration | Turns four separate metrics into one glanceable "is this neighborhood healthy" read |
| **Postcards** | One self-contained HTML file (city embedded) + PNG export | Shareable with zero hosting — the viral loop |

The result is a comprehension tool that also happens to be the best-looking
thing anyone will see in your repo.

---

## Status

Phase 1 (parser) is **built and verified**. Everything else is specified and
waiting. See [`STATUS.md`](STATUS.md) — it is the single source of truth for
what is done.

## Quick start (what works today)

```bash
python -m citygen build /path/to/repo -o out/city.json
```

```bash
python -m citygen inspect out/city.json
```

Verified output on a real repo (`reachable`, 39 files):

```
files       39   dirs 11   LOC 5,286
python      20 files, 222 fns, 13 classes, complexity 920
edges       import=37  parse_errors=0
```

## Repo map

```
citygen/     Python analyzer + CLI (stdlib only, no dependencies)
viewer/      Vite + three.js static frontend
docs/        vision, architecture, data schema, decisions, perf, testing
tasks/       one file per build task - the executable plan
fixtures/    toyrepo used by tests
out/         generated city.json files (gitignored)
```

## For AI agents / contributors

Read [`AGENTS.md`](AGENTS.md) first. It defines the handoff protocol: how to
find the next task, what "done" means, and what you may not change without
writing an ADR.
