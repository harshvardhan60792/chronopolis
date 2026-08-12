# T02 — Git miner

**Blocked by:** T01 · **Effort:** small · **Fills:** `city.git`, per-building git fields

## Goal
One pass over `git log` gives every building: commit count, churn, first/last
touch, author distribution, bus factor. This unlocks heat overlays (T12),
stories (T14) and the time machine (T11).

## Files
- new: `citygen/gitmine.py`
- edit: `citygen/build.py` (call it, merge fields, set `city["git"]`)
- edit: `citygen/cli.py` (`--no-git`, `--max-commits N`, `--since DATE`)
- new: `citygen/tests/test_git.py`

## Algorithm

Single subprocess, streamed — never `read()` the whole output:

```
git -C <root> log --no-merges --date=unix \
    --format=$'\x01%H\x1f%at\x1f%an\x1f%ae' --numstat
```

Parse line by line:
- a line starting with `\x01` opens a new commit: split on `\x1f` into
  sha, unix ts, author name, author email
- other non-empty lines are numstat: `adds \t dels \t path`
  (`-` means binary → treat as 0/0; a path containing ` => ` is a rename,
  take the post-rename side)

Per file accumulate: `commits`, `adds`, `dels`, `churn = adds + dels`,
`first_ts`, `last_ts`, `author_counts[email] += 1`.

Skip a commit's file list entirely for coupling purposes if it touches more
than `--max-commit-files` (default 60) — but still count churn. Record
`skipped_bulk_commits` in `git`.

Only keep files that exist in `buildings` (by path). Renamed-away files are
dropped; that is acceptable in v1 — note it in `git.renames_dropped`.

## Derived per building
```python
authors      = sorted(counts.items(), key=lambda kv: -kv[1])   # [(idx, n)]
owner        = authors[0][0]
owner_share  = authors[0][1] / commits
bus_factor   = smallest k such that sum(top k author commits) > 0.5 * commits
age_days     = (now - first_ts) / 86400
stale_days   = (now - last_ts) / 86400
```
Use the repo's `last_commit_ts` as "now", not wall clock — keeps output
deterministic (ADR-007 spirit).

## Author identity
Key on `email.lower().strip()`. Display name = most frequent spelling for that
email. Build `git.authors` sorted by commit count desc; buildings store author
**indices** into that array.

## Acceptance criteria
- `city["git"]` populated with authors, commit_count, first/last ts, window_days.
- Every building with git history has `commits`, `churn`, `first_ts`, `last_ts`,
  `authors`, `owner`, `owner_share`, `bus_factor`, `age_days`, `stale_days`.
- Files never committed (untracked/new) get `commits: 0` and null timestamps —
  not missing keys.
- `--no-git` and non-git directories still produce a valid city (`git: null`).
- Determinism: two runs identical.
- `python -m citygen inspect` gains sections: top 8 by churn, top 8 by
  commits, count of bus_factor==1 files, 8 stalest files.
- Runs in < 15 s on `../cve-bin-tool` if it has history, else on `../reachable`.

## Verify
```bash
python -m citygen build ../reachable -o out/reachable.city.json && python -m citygen inspect out/reachable.city.json
```
```bash
python citygen/tests/test_git.py
```
Cross-check one file by hand: `git -C ../reachable log --oneline -- reachable/report.py | wc -l` must equal that building's `commits`.

## Default if ambiguous
- Shallow clone / no history → `git: null`, everything else still builds.
- Author email absent → key on name.
- Timestamps are unix seconds, UTC, integers.
