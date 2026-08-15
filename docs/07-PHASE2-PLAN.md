# 07 — Phase 2 plan: from visualisation to code-intelligence engine

Read with `STATUS.md` (what is done) and `tasks/T19..T34` (how to do each one).
Phase 1 (T01–T18) is complete: a repo becomes a `city.json` and a 3D city.

This document is the plan for Phase 2. It exists because Phase 1 answered
"can this be built" and did not answer **"why would anyone keep it installed"**.

---

## 1. The thesis change

Phase 1 treated the 3D city as the product. Phase 2 demotes it.

```
Phase 1:   repo ──> city.json ──> 3D city          (the city IS the product)
Phase 2:   repo ──> city.json ──> CLI / PR bot / hook   (the answers ARE the product)
                              └─> 3D city              (the deep-dive view)
```

The reasoning: a developer can ignore a 3D city forever and lose nothing. A
developer cannot ignore "this PR touches a file 31 other files depend on, whose
only author left 8 months ago" — that is a fact they needed anyway, delivered
where they already are. Every Phase 2 task is judged against one question:

> Does this put an answer in front of someone who did not open the viewer?

Work that only makes the city prettier is out of scope for Phase 2. That
includes more overlays, more sky presets, more weather, more camera polish.
Phase 1 finished that job; adding to it now trades credibility for surface area.

## 2. What Phase 2 delivers

| # | Deliverable | The one-sentence pitch |
|---|---|---|
| A | `citygen impact <file>` | "What breaks if I touch this?" answered in the terminal, in under a second. |
| B | `citygen risk` | "Which of my staged files are dangerous?" — the pre-commit conscience. |
| C | PR risk comment | Every pull request gets a blast-radius and ownership readout without anyone opening anything. |
| D | Incremental engine | A one-file change re-analyses ~5 files, not 100,000. |
| E | Real parsers (tree-sitter, optional) | Function/import/call data that is actually correct, not regex-approximate. |
| F | Scale proof | Published, measured numbers on repos with 40k–300k files. |
| G | Viewer at 100k buildings | The renderer stops being the reason we can't analyse a monorepo. **Conditional — see §3.6.** |
| H | Risk score, *validated* | The rule-based risk score from (B) measured against mined ground truth, and the numbers published even if they are unimpressive. |

## 3. Non-negotiables

These survive Phase 2 unchanged. A task that violates one is wrong, not bold.

1. **ADR-012 stands.** Comprehension outranks looks. No flicker, no pulse, no
   engagement mechanics. Phase 2 adds no motion to the viewer at all.
2. **ADR-006 stands for the default install.** `pip install` with zero
   dependencies must remain a complete, working tool. Tree-sitter (T27) enters
   as an *optional extra* under a new ADR, never as a hard requirement, and the
   regex tiers stay as the fallback path forever.
3. **ADR-007 stands.** `buildings` stays sorted by path; edges stay index-based.
   The incremental cache (T24) must reproduce that ordering exactly or the
   layout stops being stable and ADR-003 breaks with it.
4. **Determinism.** Two runs on the same commit produce byte-identical
   `city.json` (modulo `generated_at` and `build_seconds`). The incremental
   path must produce the same bytes as a cold build. This is T25's hardest
   acceptance test and the one most likely to be quietly skipped.
5. **No invented numbers.** Every performance or accuracy figure in any
   document, README, or commit message traces to a command in
   `docs/05-PERFORMANCE.md` or `docs/08-RISK-MODEL.md` that reproduces it. If a
   number was not measured on a named machine against a named repo, it does not
   get written down. This rule already caught one round of plausible-looking
   fabricated benchmarks; it is not decorative.
6. **`docs/00-VISION.md`'s "no AI, LLM, or ML anywhere" non-goal stands.** The
   risk score (T20) is a fixed, published, rule-based weighting — no fitting, no
   training, no learned parameters. T33 *validates* that rule against mined
   history, which is measurement, not machine learning. If a future task wants a
   fitted model, it needs ADR-016 to supersede the non-goal explicitly, argued
   on merits, before a line of it is written. **Do not quietly cross this line;**
   the project's credibility rests on doing reversals loudly (ADR-011 → ADR-012
   is the precedent).
7. **`docs/05-PERFORMANCE.md` line 66 stands until it is measured out of the
   way.** It says, in the project's own words: *"do not implement LOD, frustum
   culling, or octrees until a measurement proves they are needed."* Phase D is
   therefore **conditional on Phase B's measurement**, not scheduled. Building it
   without that evidence is the project contradicting its own architecture doc
   to chase an impressive-sounding feature, which costs more credibility than the
   feature earns.

## 4. ADRs this plan changes

Two accepted ADRs block Phase 2 work as written. They are superseded
explicitly, with the new ADR authored as part of the task that needs it —
never silently violated.

| Existing | Blocks | Resolution |
|---|---|---|
| **ADR-006** — no dependencies in citygen | T27 tree-sitter | **ADR-014** (written in T27): core stays stdlib-only; tree-sitter is an optional extra (`pip install citygen[parsers]`) that upgrades accuracy when present. Zero-dep path must stay tested in CI. |
| **ADR-002** — one InstancedMesh, culling deliberately unnecessary | T30 viewer scale | **ADR-015** (written in T30, *only if T31 measures a need*): ADR-002's reasoning was "1000 files ⇒ 6 draw calls, culling is complexity for nothing". That reasoning may expire at ~50k — but "may" is not evidence. The ADR is written **after** the measurement, quoting it, or not at all. |
| **`00-VISION.md` non-goal: no ML** | any fitted risk model | **ADR-016 — not written, and not needed for this plan.** T33 validates a rule-based score; that is measurement. If someone later wants to fit parameters to data, that is a real reversal and needs its own ADR arguing why. Listed here so the boundary is explicit rather than discovered mid-task. |

Note what is **not** in this table: T27's tree-sitter work does not conflict with
`00-VISION.md`'s "no multi-language deep parsing" non-goal, because that non-goal
is scoped **"in v1"** — as is "no live file watching". Phase 2 is exactly where
those v1 scope limits are meant to be revisited. ADR-006's zero-dependency rule
is the real constraint there, and ADR-014 handles it.

## 5. Phases and ordering

Ordering is by dependency and by evidence, not by interest. **Phase B measures
before Phase B optimises**, and Phase E does not start until Phase C gives it
data worth modelling.

```
PHASE A — make it useful         T19 T20 T21 T22      (no new deps, no new data)
    │   ships the daily-use surface on data that already exists
    ▼
PHASE B — make it fast           T23 T24 T25 T26
    │   T23 MEASURES FIRST. T24/T25 optimise only what T23 proved is slow.
    │   T26's numbers are the gate for Phase D below.
    ▼
PHASE C — make it correct        T27 T28 T29
    │   real ASTs; unlocks the call graph the schema has always reserved
    ▼
PHASE E — make it credible       T32 T33 T34
    │   ground truth, honest validation, write-up
    ·
PHASE D — viewer scale           T30 T31    ── CONDITIONAL ──
        Runs ONLY if T26/T31 measures the viewer as the binding constraint.
        Unscheduled by default. See §3.7.
```

**Why D moved and why it is dotted.** The first draft of this plan scheduled
GPU culling and LOD as ordinary work. `docs/05-PERFORMANCE.md:66` forbids exactly
that without a measurement, and no measurement exists. Scheduling it anyway would
have been the plan arguing with the project's own architecture doc. It is now
conditional, and if T26 shows the analyser is the bottleneck rather than the
renderer — which is the likelier outcome, since the current build is already
~34 s cold on 1272 files while the viewer holds 61 fps — then Phase D is
**correctly never built**, and the plan says so up front rather than quietly
dropping it later.

### Phase A — make it useful (T19–T22)

| Task | Output | Why now |
|---|---|---|
| **T19** `citygen impact` | Reverse-dependency blast radius in the terminal | Data already exists (`edges.import`); this is pure exposure, highest value per hour in the whole plan |
| **T20** `citygen risk` | Per-file risk readout + `--staged` mode | The content of every later surface (PR bot, hook) — build the engine once |
| **T21** PR risk comment | `pr-preview.yml` upgraded from "here's a link" to "here's the finding" | The surface a whole team sees without installing anything |
| **T22** `citygen hook install` | Pre-commit warning on high-risk staged files | Puts the tool in the path the developer already walks |

**T22 carries a known hazard, stated here so it is designed for rather than
discovered.** A pre-commit hook that is slow gets `--no-verify`'d out of a
developer's workflow within a week, permanently. The current cold build is ~34 s
(`docs/05-PERFORMANCE.md`), which is fatal for a hook. T22 therefore ships as a
**read-only** consumer of an existing `city.json` — millisecond-fast, and honest
about staleness (it prints how many commits old its data is and how to refresh).
It becomes genuinely live only after T25. Do not let T22 shell out to a full
build. Do not let it block a commit by default.

**Exit criteria:** on this repo and on two cloned real repos, `impact` and
`risk` return answers a human reading the code agrees with, in under 2 seconds
warm; a PR opened against a fork gets a comment with correct file names and a
correct blast-radius count; the installed hook adds under 200 ms to `git commit`.

### Phase B — make it fast (T23–T26)

| Task | Output | Why now |
|---|---|---|
| **T23** profile harness | `scripts/profile_build.py`, a per-stage timing table on 4 repo sizes | You cannot optimise what you have not measured. This step decides what T24/T25 actually build |
| **T24** cache layer | `.citygen/cache/` content-addressed per-file parse results | The reusable half of incrementality |
| **T25** incremental rebuild | Reverse-dep invalidation; `citygen build --incremental` | The FAANG-signal task: a build-system invalidation graph, done properly |
| **T26** scale proof | Real numbers on Linux/Chromium-scale repos in `docs/05-PERFORMANCE.md` | Turns "it works" into evidence |

**Exit criteria:** a one-file edit in a repo of ≥40k files produces a
`city.json` byte-identical to a cold build, in a time T23's baseline shows to be
at least 20× faster than cold. **The speedup target is deliberately not a fixed
millisecond number** — see §6.

### Phase C — make it correct (T27–T29)

| Task | Output | Why now |
|---|---|---|
| **T27** tree-sitter backend | ADR-014, `citygen/parsers/`, optional extra, regex fallback intact | Regex tiers are the project's most-criticised honest weakness |
| **T28** parity + verification | A differential test proving tree-sitter ≥ regex on every fixture | Prevents the migration silently regressing accuracy |
| **T29** call graph | `edges.call` filled at last, viewer renders it as a second arc layer | The schema reserved this in Phase 1 and it has been `[]` ever since |

**Exit criteria:** on a Python repo, tree-sitter output matches the existing
`ast`-based output within a stated tolerance (they should agree almost exactly —
disagreement means a bug in the new path); on a Java repo, function counts go
from *absent* to *correct-by-inspection* on 20 hand-checked files.

### Phase E — make it credible (T32–T34)

| Task | Output | Why now |
|---|---|---|
| **T32** SZZ-lite ground truth | `citygen/research/szz.py` — bug-introducing commits mined from fix/revert commits | The dataset has to exist before any claim can be tested |
| **T33** validation of the T20 score | `docs/08-RISK-MODEL.md`: precision/recall/AUC vs. two fixed baselines | Turns "here is a risk score" into "here is a risk score, and here is how wrong it is" |
| **T34** write-up | A publishable engineering design doc, honest about what failed | The artifact that actually travels; the code alone rarely does |

**This phase fits no ML.** T20's weights stay fixed and published. T33 measures
that fixed rule against mined history. Nothing is trained. That keeps
`00-VISION.md`'s non-goal intact *and* produces the stronger artifact, because
"my transparent hand-written rule scores X against this baseline, here is the
data" is more defensible than an unvalidated model — and it is the exact
framing the established literature invites (see `docs/09-PRIOR-ART.md`).

**Exit criteria:** a reported evaluation with a stated baseline, stated dataset,
stated label-mining rule and stated limitations — **regardless of whether the
score beats the baseline**. See §6.

### Phase D — viewer scale (T30–T31) · CONDITIONAL, NOT SCHEDULED

| Task | Output |
|---|---|
| **T31** stress test *(runs first)* | Measured fps curve at 10k / 50k / 100k / 250k buildings on the machine `docs/05-PERFORMANCE.md` already names |
| **T30** chunked instancing + culling + ADR-015 | **Only if T31 shows the viewer failing before the analyser does** |

Note the deliberate inversion: the measurement task has the lower number and
runs first, because that is the order `docs/05-PERFORMANCE.md:66` requires.

**Gate:** if T26 shows analysis time is the binding constraint on large repos —
the likely outcome — then Phase D is not built, and `STATUS.md` records it as
`WONTFIX: measured, not the bottleneck`. That is a successful outcome for this
phase, not a failure.

**A note on what "LOD" would even mean here, if it is ever needed.** A building
is a box: 12 triangles. Geometric LOD on a box saves nothing, and any plan that
lists "add LOD" as a bullet has not thought about it. If T31 finds a bottleneck
it will be one of: per-instance matrix upload bandwidth, the procedural facade
fragment shader at high overdraw, or CPU-side picking against 100k instances.
Those are three different fixes. T30 must name which one the measurement found
before writing any code.

## 6. Kill criteria and honesty rules

Written before the work starts, so the results cannot be rationalised after.

**T25 (incremental).** No fixed millisecond promise. The claim is a *ratio*
against T23's measured cold baseline on the same machine and repo. If the
achieved speedup is under 10×, the task is not "done with a caveat" — it is
`PARTIAL`, with the bottleneck named in `STATUS.md`. Sub-second targets are
plausible for parsing and almost certainly not for git history mining on a large
repo; T23 exists to find out which stage dominates before anyone claims a number.

**T27 (tree-sitter).** If the optional-extra path makes the zero-dependency path
worse in any way — slower, less accurate, or harder to install — the migration
is reverted. The fallback is the product for most users.

**T33 (validation).** This is the only research-shaped task here, and research
is allowed to fail. The kill criteria, fixed now:

- The evaluation ships **even if the score loses to the baseline.** A negative
  result, honestly reported with its methodology, is a stronger artifact than a
  positive result nobody can reproduce. "Churn alone predicted this as well as
  my five-component score" is a real finding and gets written up as one.
- **Baselines are fixed in advance, before any number is computed:**
  (1) file churn alone, (2) file complexity alone, (3) random, at the same
  positive rate. A score that cannot beat (1) and (2) has added nothing, and the
  write-up must say that in its first paragraph, not its limitations section.
- **Label noise is disclosed, not hidden.** SZZ-style labels are known-noisy —
  the literature reports a substantial fraction of flagged "bug-inducing" lines
  being refactoring noise. The write-up states the mining rule verbatim, reports
  how many commits matched, and hand-checks a random sample of 30 labels with
  the hit rate published.
- **Expect unimpressive numbers, and do not dress them up.** Change-level defect
  prediction has a documented accuracy ceiling; published precision commonly
  lands in a modest range with wide recall variance. Landing there is the
  expected result, not a failure. Landing *far above* it is a signal that the
  evaluation has a leak — most likely the label and the feature both derived
  from the same commits — and must be investigated before publication, not
  celebrated.
- **No novelty claim without a citation.** Just-in-time defect prediction is an
  established field with named prior work, including research bots that already
  did commit-risk-scoring-with-SZZ-validation (`docs/09-PRIOR-ART.md`). The
  contribution here, if any, is *delivery* — free, local, zero-signup, nothing
  uploaded — not the idea. The write-up leads with that and never implies
  otherwise.
- **The word "prediction" is used carefully or not at all.** A fixed rule-based
  score is a *heuristic*, and calling it a prediction invites a direct comparison
  to the literature that it will lose. Say what it is.

**All phases.** Any task whose acceptance check cannot be run by a command
written in its task file is not specified well enough to start.

## 7. What Phase 2 explicitly does not do

- No new overlay modes, sky presets, weather states, or camera features.
- No React/UI framework, no component library (ADR-010's rule stands).
- No SaaS, no account system, no telemetry, no phone-home. The tool analyses
  private source code; it stays local by construction, and that is a feature to
  advertise, not a limitation to apologise for.
- No claim that this is the first tool to do hotspot, ownership or coupling
  analysis. It is not (see `docs/09-PRIOR-ART.md` — `code-maat` has done it
  free and open-source for over a decade, and it is what CodeScene is built on).
  The honest claim is the *composition and delivery*: one free, local,
  zero-dependency tool that puts the same metric set behind a terminal command,
  a PR comment, a commit hook and a 3D city, with no server and no account.
- No ML, no fitted parameters, no training. See §3.6.
- No LOD / culling / octree work without a measurement demanding it. See §3.7.

## 8. What the research said, in one paragraph

Before this plan was written, the landscape was checked (full findings in
`docs/09-PRIOR-ART.md`). The short version: **none of the eight deliverables is
a novel capability.** PR risk bots, hotspot and bus-factor analysis, reverse
dependency queries, content-hash incremental caching, and commit-level risk
scoring validated against mined ground truth all have named prior art, some of
it free and open-source, some of it commercial and expensive, some of it
academic prototypes from 2015 and 2020. This is not a reason to stop; it is a
reason to stop *claiming novelty* and start claiming the thing that is actually
true and actually rare — that all of it is free, local, zero-dependency, and
never uploads a line of source code anywhere. Plans that survive contact with
reality are the ones that knew what reality contained first.
