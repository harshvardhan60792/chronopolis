# T32 — SZZ-lite: mine the ground truth before claiming anything

**Blocked by:** T20 · **Effort:** medium · **Phase:** E
**Fills:** a dataset, not `city.json`. Output is `out/labels.json`.

## Why this exists
T33 wants to answer "is the risk score any good?". That question is unanswerable
without labelled history: which past changes actually led to defects. This task
mines those labels.

**The literature is unambiguous that this — not the scoring — is the hard part**
(`docs/09-PRIOR-ART.md`). Label quality determines whether T33's numbers mean
anything at all. Budget accordingly: this task is where the intellectual risk
lives, and a sloppy version of it invalidates everything downstream.

## The approach: SZZ, simplified and honest
The standard idea (Śliwerski, Zimmermann, Zeller, 2005 — cite it, do not
re-derive it as if it were new):

```
1. find bug-FIXING commits
2. for each, find the lines it changed
3. git blame those lines at the fix's parent -> the commits that introduced them
4. those are the bug-INTRODUCING commits
5. a file touched by a bug-introducing commit is a positive label
```

## Files
- new: `citygen/research/__init__.py`, `citygen/research/szz.py`
- new: `citygen/research/labels.py`
- edit: `citygen/cli.py` (a `research` subcommand group, or a separate script —
  **do not** put research code on the main CLI path; it is not part of the tool)
- new: `citygen/tests/test_szz.py`
- new: `docs/08-RISK-MODEL.md` (started here, completed in T33)

Keep `citygen/research/` importing nothing from a parser backend and adding no
dependency. It is stdlib + `git`, same as everything else.

## Step 1 — identify fix commits
The rule must be written down verbatim in `docs/08-RISK-MODEL.md` before any
number is produced, because the rule *is* the experiment:

```python
FIX_PATTERNS = [
    r"\bfix(e[sd])?\b", r"\bbug\b", r"\bdefect\b", r"\bissue #?\d+\b",
    r"\bcloses? #\d+\b", r"\bresolves? #\d+\b", r"\bhotfix\b", r"\bregression\b",
]
REVERT_PATTERN = r'^Revert "'
```

Precision notes that must be honoured, not skipped:
- `"fix typo in README"` matches and is not a defect fix. Excluding
  documentation-only commits (all changed paths non-source) removes a chunk of
  this noise. Do it, and report how many were excluded.
- Revert commits are the **highest-precision** signal available: an explicit
  `Revert "X"` says the project itself judged X to be wrong. Label them
  separately and report their count on its own, since a revert-only dataset is
  small but much cleaner. **If the full dataset and the revert-only dataset
  disagree in T33, report both.** That disagreement is a finding.
- Merge commits are skipped (they attribute nothing).
- Commits touching more than 100 files are skipped — same threshold and same
  reasoning as ADR-009's bulk-commit rule. Reuse the constant.

## Step 2 — blame back to introducers
```python
def introducers(root: str, fix_sha: str, path: str,
                deleted_line_ranges: list[tuple[int, int]]) -> set[str]:
    """git blame -w -M -C -L <a>,<b> <fix_sha>^ -- <path>, parsed to commit shas.

    -w  ignore whitespace       -M  detect moved lines within a file
    -C  detect lines copied from other files
    These three flags remove a large class of false attributions (reformatting,
    code motion) and are the difference between a usable dataset and noise.
    """
```

Only the lines a fix **deleted or modified** are evidence (parse the `-` side of
the unified diff). Lines a fix *added* have no prior author and blaming their
surroundings is a known source of false positives.

**Cost warning:** this is one `git blame` subprocess per changed file per fix
commit. On a large repo that is tens of thousands of subprocess spawns and can
take hours. Required mitigations: cap the number of fix commits (`--max-fixes`,
default 500), cache blame results by `(sha, path)`, and print progress. Measure
it on the medium tier before running the large one.

## Step 3 — emit labels
```json
{
  "repo": "flask", "head": "abc1234", "generated_at": "...",
  "rule": {"fix_patterns": [...], "max_fixes": 500, "excluded_doc_only": true},
  "counts": {"commits_scanned": 4211, "fix_commits": 380, "revert_commits": 12,
             "introducing_commits": 502, "labelled_files": 143,
             "blame_failures": 7},
  "files": {"src/flask/app.py": {"introduced_bugs": 9, "fix_commits": [...]}},
  "commits": {"deadbee": {"introduced": true, "via": ["fix_sha", ...]}}
}
```

## The mandatory manual audit
**T33 may not publish any number until this is done.**

Sample 30 labelled (fix commit → introducing commit) pairs at random, with a
recorded seed. Read each pair by hand. Record in `docs/08-RISK-MODEL.md`:

- how many were genuine defect introductions
- how many were refactors, renames, or formatting misattributed by blame
- how many were fix commits that were not really bug fixes
- the resulting estimated label precision, as a fraction with the sample size

The literature reports a meaningful share of SZZ-flagged lines being refactoring
noise. If the audit finds precision below ~0.6, say so plainly and treat every
downstream number as indicative rather than conclusive — in the write-up's
headline, not buried in limitations.

This audit is tedious and is the part most likely to be skipped. Skipping it
converts T33 from a real evaluation into a plausible-looking one, which is worse
than not doing T33 at all.

## Acceptance criteria
1. Runs on `flask` and on this repo, producing `labels.json` with non-zero
   counts and no crash on merge commits, root commits, or binary files.
2. The rule dict in the output fully determines the run — someone else can
   reproduce it from `labels.json` alone.
3. `blame_failures` is reported, not swallowed.
4. Deterministic for a fixed repo state and seed.
5. The 30-pair manual audit is complete and written up **before** T33 starts.
6. Runtime on the medium tier is recorded, and `--max-fixes` demonstrably bounds
   it.

## Verify
```bash
python -m citygen research szz .testrepos/flask --max-fixes 200 -o out/labels.json
```
```bash
python citygen/tests/test_szz.py
```

## Default if ambiguous
- When blame cannot attribute a line, count it in `blame_failures` and drop it.
  Never fall back to "the previous commit" — that fabricates the exact
  relationship being measured.
- Labels are per **file** for T33's purposes, since the risk score is per file.
  Keep per-commit detail in the output anyway; it costs nothing and a later
  commit-level analysis would otherwise need a re-run.
