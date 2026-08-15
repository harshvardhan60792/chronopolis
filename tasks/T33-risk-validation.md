# T33 — Validate the risk score, and publish the number either way

**Blocked by:** T32 (including its manual audit) · **Effort:** medium · **Phase:** E
**Fills:** `docs/08-RISK-MODEL.md`.

## Why this exists
T20 ships a risk score built from a hand-written weighting. Right now nobody —
including its author — knows whether it beats "look at whichever file changed
most". This task finds out and publishes the answer.

**No machine learning.** `docs/00-VISION.md` forbids it, and Phase 2 §3.6 keeps
that intact. T20's weights stay exactly as published; this task *measures* the
fixed rule. Nothing is fitted, nothing is trained, no parameters are tuned to
the labels. Tuning the weights against the labels and then reporting the score
would be fitting a model while calling it a rule, which is worse than either.

## The trap that would invalidate everything: temporal leakage
T20's score reads `churn`, `stale_days`, `bus_factor` — all mined from git
history. T32's labels are mined from the same history. Computing both over the
full history and then correlating them **leaks the future into the features**,
and produces a beautiful, meaningless result.

The fix is a temporal split, and it is not optional:

```
                    split point T (default: 70% through the commit history)
   |------------------------------|------------------------------|
   features computed ONLY from     labels computed ONLY from
   commits before T                fix commits after T
```

Concretely:
- Build a `city.json` **as of commit T** — `citygen` can already do this by
  analysing a checkout at that commit, or via `--since`. Verify which mechanism
  gives a clean cutoff and document the exact command used.
- Score every file with T20's `score_all` on that historical city.
- The label for a file is: *did any bug-introducing commit after T touch it?*
- Report the split point, the commit shas on both sides, and the class balance.

If the positive rate is under ~2% the evaluation is dominated by class imbalance
and precision/recall will be unstable — say so, and prefer AUC and lift over raw
precision in the headline.

## The baselines — fixed now, before any number is computed
1. **Churn alone** — rank files by commit count before T.
2. **Complexity alone** — rank by complexity at T.
3. **Random** — at the same positive rate, averaged over 100 seeds.
4. **File size (LOC) alone** — the cheapest possible predictor, and in the
   literature a surprisingly strong one. Include it; if the five-component score
   cannot beat *file size*, that is the most important sentence in the write-up.

## What to report
For the score and every baseline:
- Precision, recall, F1 at top-k for k ∈ {10, 25, 50, 100}
- AUC-ROC and, because of class imbalance, AUC-PR
- Lift at 10%: among the top 10% riskiest files, what share of post-T bug
  introductions was caught, versus the 10% a random pick would give
- A per-component ablation: score with each of the five components removed in
  turn, to show which are carrying the result and which are decoration

The ablation is the most informative output here. If removing `ownership` and
`staleness` changes nothing, T20's formula is really "churn and blast radius
with extra steps", and the honest move is to publish that — and then consider
simplifying the formula in a follow-up rather than defending it.

## Repos
At least 3, of different sizes and languages, named with pinned shas. One repo
is an anecdote. Report each separately **and** pooled; if the result reverses
between repos, that is the finding and it goes in the headline.

## `docs/08-RISK-MODEL.md` structure
1. What is being measured, in two sentences
2. The label-mining rule verbatim, and the T32 manual-audit precision estimate
3. The temporal split, with commit shas and class balance
4. Baselines, fixed in advance (this section is written *before* results exist)
5. Results table
6. Ablation
7. **Threats to validity** — label noise, single-project effects, the fact that
   the score's components and the labels both derive from git history, survivor
   bias in which files still exist
8. Verdict, in one plain sentence at the top of the document as well as the end

## Kill criteria — from the Phase 2 plan §6, restated because they bind here
- The document ships **even if the score loses.** "Churn alone beat my
  five-component score on all three repos" is a publishable, credible result and
  is written as the headline, not a footnote.
- A result far above the literature's documented ceiling means a leak. Do not
  publish it; find the leak. The most likely one is an imperfect temporal split.
- The word "prediction" is avoided. It is a heuristic that ranks files.
- No comparison claim against CodeScene, Commit Guru, or JITBot unless the same
  evaluation was actually run against them, which it will not be. Cite them as
  prior art, not as a beaten benchmark.

## Acceptance criteria
1. The temporal split is verified: assert programmatically that no commit used
   for features is dated after the split point. **Write this assertion as a
   test** — it is the one thing that silently invalidates the whole study.
2. All four baselines are computed and reported.
3. The ablation is complete for all five components.
4. Every number in the doc is reproducible by a command in the doc.
5. The threats-to-validity section is written before the verdict, not after.
6. A reader who disagrees with the conclusion can re-run it from the repo.

## Verify
```bash
python -m citygen research evaluate .testrepos/flask --labels out/labels.json --split 0.7 -o docs/08-RISK-MODEL.md
```
```bash
python citygen/tests/test_evaluate.py
```

## Default if ambiguous
- Split at 70% of commits by date. Report sensitivity at 50% and 85% too — a
  result that only holds at one split point is not a result.
- Files created after T are excluded (no features exist for them).
- Deleted-before-T files are excluded from both sides.
