# T28 — Differential parity: prove the new parser is better, per language

**Blocked by:** T27 · **Effort:** medium · **Phase:** C

## Why this exists
A parser migration that silently regresses accuracy is the classic failure of
this kind of work, because both paths produce plausible numbers and nobody
compares them file by file. This task makes the comparison mechanical and makes
"tree-sitter is better" a measured claim rather than an assumption.

## Files
- new: `scripts/parser_diff.py`
- new: `citygen/tests/fixtures/parity/<lang>/*.{java,go,rb,ts,...}` + expected JSON
- new: `docs/10-PARSER-PARITY.md`
- edit: `.github/workflows/ci.yml`

## The three comparisons

**1. Against ground truth (`ast`), for Python.** Python is the only language
where an exact answer is available. Run the tree-sitter Python backend against
`citygen`'s own `ast`-based metrics on every Python file in this repo and in
`.testrepos/`. They should agree almost exactly. **Any disagreement is a bug in
the tree-sitter query, not a tie** — Python is the calibration case, and if the
query is wrong here it is wrong everywhere.

**2. Against hand-counted fixtures, per language.** For each supported language,
20–40 small fixture files with hand-verified expected counts committed alongside
them. Hand-counting is tedious and is the actual work of this task; there is no
shortcut and a generated "expected" file is worthless.

Fixtures must include the cases regex provably gets wrong, so the improvement is
demonstrable rather than asserted:
- a decision keyword inside a line comment (`// if (x)`)
- a decision keyword inside a block comment and inside a string literal
- a function-shaped construct inside a string
- nested/anonymous functions, lambdas, arrow functions
- a method with the same name as a keyword in another context
- generics/templates containing `<` `>` that confuse naive matching
- a file with a syntax error in the middle

**3. Regex vs tree-sitter on real repos, reported as a table.** Not pass/fail —
a published comparison per language showing where they diverge and by how much.

## `scripts/parser_diff.py`
```
python scripts/parser_diff.py --repo .testrepos/gson --lang java --out docs/perf/parity-java.md
```
Runs both backends over the same files, emits per-file deltas for `functions`,
`classes`, `complexity`, `imports`, plus summary stats (mean absolute
difference, the 20 files with the largest divergence, and correlation between
the two complexity series).

**Correlation matters more than absolute agreement.** Building *height* only
needs a monotonic ranking (ADR-004 says exactly this). If regex and tree-sitter
correlate at r > 0.95 on complexity, the practical difference for the city is
small — and that is a finding worth publishing honestly, even though it makes
the migration look less impressive than the marketing version would.

## `docs/10-PARSER-PARITY.md` must state, per language
- Fixture pass rate for each backend
- Mean absolute difference and correlation on a real repo
- The specific cases where regex is wrong, with a code snippet from a fixture
- **Where tree-sitter is wrong or worse**, if anywhere. There will be something
  — a grammar quirk, a construct the query misses. Publish it.
- A one-line verdict per language: `tree-sitter: adopt | adopt with caveat | no
  measurable gain`

A language with no measurable gain keeps the regex path as its default, and the
doc says why. Adopting a heavier dependency for a language it does not actually
improve is the outcome this task exists to prevent.

## Acceptance criteria
1. Python: tree-sitter vs `ast` agreement on `functions` and `classes` is exact
   on every file in this repo. Any mismatch is investigated and either fixed or
   documented with a reason.
2. Every language has ≥20 hand-counted fixtures, committed with the counts.
3. CI runs the fixture suite for both backends on every commit.
4. The parity doc exists and contains at least one honest "tree-sitter is worse
   here" or "no measurable gain here" entry, or explicitly states that every
   language improved and shows the numbers backing that.
5. `scripts/parser_diff.py` output is deterministic.

## Verify
```bash
python citygen/tests/test_parsers.py
```
```bash
python scripts/parser_diff.py --repo .testrepos/gson --lang java
```

## Default if ambiguous
- Fixtures are small and hand-written, not copied from real projects — a fixture
  nobody can hand-verify in 30 seconds is not a fixture.
- When the two backends disagree and neither is obviously right, hand-count the
  file and record the answer. That is the whole job.
