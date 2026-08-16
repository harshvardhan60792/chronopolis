# Parser Parity Diff: python on citygen

## Summary
- **Files**: 34
- **Complexity correlation**: r = 0.9871
- **Mean Absolute Difference (MAD)**:
  - Functions: 0.00
  - Classes: 0.00
  - Complexity: 10.53
  - Imports: 0.32

## Top 20 Largest Divergences
| File | fn (ts-b) | cl (ts-b) | cx (ts-b) | im (ts-b) |
|---|---|---|---|---|
| `build.py` | 8-8 | 0-0 | 103-133 | 17-18 |
| `cli.py` | 14-14 | 0-0 | 85-115 | 27-28 |
| `tests/test_invariants.py` | 13-13 | 0-0 | 49-72 | 7-8 |
| `metrics.py` | 9-9 | 6-6 | 28-50 | 7-8 |
| `risk.py` | 5-5 | 0-0 | 85-107 | 5-5 |
| `tests/test_git.py` | 14-14 | 4-4 | 5-26 | 5-6 |
| `tests/test_phase1.py` | 9-9 | 0-0 | 25-41 | 6-7 |
| `gitmine.py` | 9-9 | 0-0 | 70-84 | 1-2 |
| `layout.py` | 7-7 | 0-0 | 40-55 | 2-2 |
| `tests/test_hook.py` | 14-14 | 0-0 | 51-65 | 10-10 |
| `tests/test_report.py` | 6-6 | 0-0 | 15-29 | 3-3 |
| `resolve.py` | 11-11 | 3-3 | 41-53 | 1-2 |
| `impact.py` | 4-4 | 0-0 | 27-39 | 3-3 |
| `report.py` | 4-4 | 0-0 | 46-58 | 7-7 |
| `stories.py` | 2-2 | 0-0 | 39-51 | 0-0 |
| `cache.py` | 10-10 | 1-1 | 32-42 | 5-5 |
| `snapshots.py` | 1-1 | 0-0 | 24-33 | 2-3 |
| `walk.py` | 4-4 | 2-2 | 26-34 | 3-4 |
| `tests/test_incremental.py` | 8-8 | 0-0 | 12-20 | 11-11 |
| `tests/test_risk.py` | 7-7 | 0-0 | 23-31 | 4-4 |