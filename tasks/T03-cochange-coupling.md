# T03 — Co-change coupling (the traffic signal)

**Blocked by:** T02 · **Effort:** small-medium · **Fills:** `edges.cochange`

## Why this exists
Import graphs show *declared* dependency. Co-change shows *actual* dependency:
files that keep changing in the same commit are coupled whether or not they
reference each other. Rendering that as traffic is the project's core novelty
(ADR-005). Pairs with high co-change and **no import edge** are the money
finding — hidden coupling.

## Files
- new: `citygen/coupling.py`
- edit: `citygen/build.py`, `citygen/cli.py` (`--max-commit-files`, `--min-cochange`)
- new: `citygen/tests/test_coupling.py`

## Algorithm
Reuse the commit → file-list stream from T02 (have `gitmine` yield commits so
this does not need a second `git log` run).

```python
pair_counts = Counter()          # (i, j) with i < j, indices into buildings
for commit in commits:
    files = [idx for idx in commit.files if idx is not None]
    if len(files) > max_commit_files:   # default 60: merges, mass renames
        continue
    for i, j in itertools.combinations(sorted(set(files)), 2):
        pair_counts[(i, j)] += 1
```

Normalise each pair to a 0..1 strength so a busy file does not couple to
everything (Jaccard over commit sets):

```python
strength = c_ij / (commits_i + commits_j - c_ij)
```

Keep a pair if `c_ij >= min_cochange` (default 3) **and** `strength >= 0.12`.
Then cap the output: keep the top `--max-cochange` pairs by
`strength * log(1 + c_ij)` (default 4000) so the JSON stays small.

Emit sorted by `(i, j)`:
```json
"cochange": [[12, 47, 9, 0.31]]     // aIdx, bIdx, commits_together, strength
```

## Also emit (cheap, high value for stories)
In `stats`, add:
- `cochange_pairs`: count kept
- `hidden_coupling`: number of kept pairs with **no** import edge in either
  direction — surface the top 10 in `stats.top_hidden_coupling` as
  `[i, j, strength]`.

## Fallback for thin history
If `git.commit_count < 30` or fewer than 20 pairs survive, set
`stats.traffic_source = "imports"` and leave `cochange` empty. The viewer then
drives traffic from import edges and the legend says so (ADR-005).
Otherwise `stats.traffic_source = "cochange"`.

## Acceptance criteria
- Deterministic ordering, no duplicate unordered pairs, no self-pairs.
- On `../reachable`, the top co-change pairs are ones a human would predict
  (e.g. a module and its test file). **Print them and eyeball this** — if the
  top pairs look random, the parsing is wrong, not the metric.
- `inspect` prints top 10 co-change pairs and top 10 hidden-coupling pairs.
- Time cost < 10 s on a 5000-commit repo.

## Verify
```bash
python -m citygen build ../reachable -o out/reachable.city.json && python -m citygen inspect out/reachable.city.json
```
```bash
python citygen/tests/test_coupling.py
```

## Default if ambiguous
- Normalisation: Jaccard as above. Do not invent a different formula without an
  ADR; the thresholds were chosen to pair with it.
- Directionality: co-change is symmetric. Store `i < j` only.
