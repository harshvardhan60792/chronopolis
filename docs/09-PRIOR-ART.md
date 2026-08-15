# 09 — Prior art

Written before Phase 2 started, so no claim in this project rests on not having
looked. Every capability Phase 2 proposes was checked against what already
exists. **None of it is a novel capability.** That is fine, and knowing it is
worth more than not knowing it.

Maintenance rule: when a claim in the README or a write-up implies novelty,
check it against this file first. If this file contradicts it, this file wins.

---

## 1. The honest summary

| Phase 2 deliverable | Prior art | Verdict |
|---|---|---|
| PR risk comments (T21) | CodeScene PR/MR integration; SonarQube PR decoration; academic **Commit Guru** (2015) and **JITBot** (2020) | Solved commercially and academically. Not novel. |
| Blast-radius CLI (T19) | `pydeps --reverse`, `grimp` (Python); `madge`, `rev-dep` (JS/TS); NDepend CQLinq coupling queries; SciTools Understand dependency graphs | Solved per-language and in paid GUI tools. Not novel; the cross-language + terminal-native + risk-fused combination is uncommon. |
| Pre-commit risk hook (T22) | `husky` + `lint-staged`, the `pre-commit` framework — universal for lint/format | The mechanism is ubiquitous; feeding it *risk* rather than lint is less common but obvious. Not novel. |
| Incremental analysis (T24/T25) | Bazel, Turborepo, `rust-analyzer`'s Salsa framework | A settled build-systems pattern. Zero novelty in the technique; the engineering is still real work. |
| Hotspot / bus-factor / coupling (already shipped, T01–T03) | **code-maat** — Adam Tornhill's free, open-source CLI, which is what CodeScene itself is built on. Over a decade old. | Fully solved, **free and open source**. Claiming this would be embarrassing. |
| Risk score validated against mined ground truth (T32/T33) | Just-in-time defect prediction: a large literature. SZZ (2005) for linking fixes to bug-introducing changes; Nagappan & Ball (2005) on churn-based defect prediction; Kamei et al. on JIT-SDP; **Commit Guru** (Rosen, Grawi, Shihab — FSE 2015) and **JITBot** (ASE 2020) shipped this as working bots | Established field with a documented accuracy ceiling. Not novel. |
| Software cities (already shipped) | CodeCity (Wettel, 2008), SoftVis3D, jscity, Gource, GitHub Skyline, CodeCharta | The metaphor is old. See §4 for the part that is genuinely less common. |

## 2. What the incumbents cost

Relevant because "free" is this project's actual differentiator, so it needs to
be true and specific rather than asserted.

- **CodeScene** — does automated PR risk commentary today, and does it well:
  hotspots, bus factor, code-health delta, a risk profile blending technical and
  social signals. Priced per active author (Standard ~€18, Pro ~€27 per author
  per month at time of writing); free for open source.
- **SonarQube** — PR decoration is free on SonarCloud only up to a LOC cap;
  self-hosted PR decoration requires Developer Edition (four figures annually).
  Community Build has no PR decoration at all.
- **GitHub, free and native** — the dependency graph gives package-level
  transitive dependencies; CODEOWNERS gives reviewer-by-ownership routing.
  Neither gives *file-level* blast radius inside a repo, which is the gap T19
  fills.
- **NDepend, SciTools Understand** — real impact analysis, real dependency
  graphs, paid, GUI/IDE-first, no PR-bot or pre-commit story.
- **code-maat** — free, open source, and already computes the hotspot and
  ownership analysis this project computes. The differentiator against it is
  delivery and presentation, not analysis.

## 3. The known traps in the T32/T33 research

Recorded here so the work is designed around them rather than discovering them
in the results.

1. **Labelling is the hard part, not modelling.** SZZ-style mining links a
   bug-fix commit back to the commit that introduced the fixed lines. The
   literature reports a meaningful fraction of flagged "bug-inducing" lines
   being refactoring noise rather than real defect introduction. Any evaluation
   that does not report its label quality is not an evaluation.
2. **The accuracy ceiling is low and well documented.** Published precision for
   change-level defect prediction commonly sits in a modest range with wide
   recall variance. Landing there is the expected outcome.
3. **A suspiciously good result means a leak.** If the score massively beats the
   baselines, the most likely explanation is that the label and the feature were
   derived from overlapping commits. Investigate before publishing.
4. **The no-ML non-goal is a constraint, and arguably an advantage.**
   `docs/00-VISION.md` forbids ML. That rules out the techniques the literature
   uses to reach even its modest ceiling — so a hand-written rule should not be
   expected to beat them, and must not be presented as if it did. What it *can*
   be is transparent, inspectable, and honest about its own accuracy, which
   published models in this space frequently are not.

## 4. What is actually unclaimed

Not a capability — a composition and a delivery model:

> One free, local-first, zero-dependency, zero-account, zero-server tool that
> computes a single metric set from git history and structure, then exposes it
> through a terminal command, a PR comment, a commit hook, **and** an explorable
> 3D city — with no source code leaving the machine.

Each half of that exists elsewhere. The combination at this price (free) and
this delivery model (single local install, no backend) does not appear to.
Additionally, from `docs/00-VISION.md`'s own survey: existing software-city
tools render structure *or* history; rendering both in one spatially-stable
scene remains uncommon.

That is the claim. It is a claim about **packaging and access**, not invention,
and every public description of this project should say so in those terms.

## 5. Could not verify

Listed rather than quietly omitted.

- Whether GitLab's "Blast Radius Reviewer" (walks a call graph ~3 hops, weights
  by distance, posts to the MR) is an official GitLab product or a community /
  hackathon contribution to its agent catalogue — found via a third-party blog,
  not a primary GitLab source.
- Whether **Commit Guru** and **JITBot** are still running services today; both
  are research artifacts from 2015 and 2020 respectively.
- CodeScene's internal precision/recall figures — described qualitatively in
  their material, not published as numbers.
- Third-party blog claims about other commercial "blast radius" products, which
  rested on a single secondhand source and were not cross-checked against each
  vendor's own documentation.
- Exact current pricing for all commercial tools listed in §2; treat those
  figures as approximate and re-check before quoting them anywhere public.
