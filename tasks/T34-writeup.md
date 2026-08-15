# T34 — The write-up: the artifact that actually travels

**Blocked by:** T25, T26, T33 · **Effort:** medium · **Phase:** E

## Why this exists
Code alone rarely gets read. A well-written engineering document about a hard
problem gets forwarded, and it is the thing that survives contact with someone
who has 15 minutes. This task turns the work into that document.

It is deliberately last: it can only be written once there is a measured result
to write about. Writing it earlier would produce a pitch, which is the opposite
of the point.

## Pick exactly one subject
Not a tour of the project. One problem, in depth. Choose based on which produced
the most interesting *measured* result:

| Candidate | Write this if… |
|---|---|
| **The incremental engine (T25)** | the invalidation design has a non-obvious correctness story — the resolution trap, the rebase fallback, the byte-identical invariant. **Default choice**; it is the strongest systems content and the most transferable. |
| **The scale wall (T26)** | something broke at scale in an instructive way and the diagnosis was non-trivial |
| **The risk-score validation (T33)** | the result was genuinely surprising in either direction |

Write one. A document covering all three is a portfolio page, and portfolio
pages do not get forwarded.

## Structure (engineering design doc, not a blog post)
1. **The problem**, concretely, with the number that made it a problem
2. **Constraints** — zero dependencies, stdlib only, must stay byte-identical,
   one developer. Constraints are what make a solution interesting
3. **Alternatives considered, and why each was rejected** — the section
   experienced readers go to first. It must contain real rejected options with
   real reasons, including at least one that was tried and abandoned
4. **The design**, with the one diagram that carries it
5. **What went wrong** — the resolution trap, the rebase case, the benchmark
   that turned out to be measuring the filesystem. **This section is not
   optional.** A document with no failures in it reads as marketing
6. **Results**, measured, with the machine and the command
7. **What is still broken**, plainly
8. **Prior art**, with citations, and an explicit statement of what is not novel

## Rules
- **Every number traces to `docs/05-PERFORMANCE.md` or `docs/08-RISK-MODEL.md`.**
  No number appears here first.
- No novelty claim contradicting `docs/09-PRIOR-ART.md`. State plainly that PR
  risk bots, hotspot analysis and JIT defect prediction all have prior art, and
  that the contribution is free local delivery.
- No AI-writing tells. Run the `humanizer` skill over the draft: no inflated
  symbolism, no rule-of-three padding, no "it's not just X, it's Y", no em-dash
  overuse, no hollow -ing clauses. This project's docs are written plainly and
  the write-up must match — a document that reads as generated undoes the
  credibility the measurements bought.
- Short. 1500–2500 words. The design doc that gets read is the one that fits in
  a coffee break.

## Also update, in the same pass
- `README.md` — a "How it works" section linking the write-up; the Limitations
  section refreshed against what T27/T28 actually changed
- `docs/03-IMPLEMENTATION-PLAN.md` — mark Phase 2 phases against it
- `STATUS.md` — T19–T34 rows with real notes, in the established style
- `docs/CHANGELOG.md` — dated entries

## Acceptance criteria
1. One subject, 1500–2500 words.
2. The "alternatives considered" section names at least three real options with
   real rejection reasons.
3. The "what went wrong" section is present and specific.
4. Every number is traceable; verify by checking each against its source doc.
5. A reader outside the project can restate the core problem after reading once.
6. No claim contradicts `docs/09-PRIOR-ART.md`.

## Verify
```bash
python -m citygen build . -o out/city.json && python -m citygen inspect out/city.json
```
(the doc's own claims about the tool must still be true of the tool)

## Default if ambiguous
- Publish in-repo as `docs/11-WRITEUP-<topic>.md` first. Cross-posting elsewhere
  is a separate decision, and anything published under the author's name should
  be reviewed by them line by line before it goes out.
- If the honest write-up is "I built an incremental engine and it turned out the
  bottleneck was elsewhere" — write that. It is a better document than a
  triumphant one, and it is the kind that experienced engineers trust.
