# T20 — `citygen risk`: the risk engine every other surface reads

**Blocked by:** T19 · **Effort:** medium · **Phase:** A
**Fills:** nothing new in `city.json`; adds `citygen/risk.py` as a shared library.

## Why this exists
T21 (PR comment) and T22 (pre-commit hook) both need to answer "is this file
dangerous to change, and why". Writing that logic twice guarantees they drift
apart. This task builds it **once**, as a library with a CLI on top, and the
later tasks call the library.

The distinction that makes this task worth doing at all:

- `health` (already in `city.json`, from `calculate_health` in `build.py`) means
  **"how bad is this file"** — churn × complexity, staleness, ownership.
- `risk` means **"how bad is *changing* this file"** — which is a different
  question, dominated by blast radius and by whether anyone still understands
  the code.

Do not reuse `health` as `risk`. A gnarly leaf file with no dependents is
unhealthy and safe to change. A clean file 200 others import is healthy and
dangerous. Collapsing the two would make both useless.

## Files
- new: `citygen/risk.py`
- edit: `citygen/cli.py` (add the `risk` subcommand)
- new: `citygen/tests/test_risk.py`
- edit: `README.md` (CLI Reference)

## The formula
Fixed here, in this file, exactly as ADR-004 fixed the complexity formula.
Change it here first, or the three surfaces disagree.

```python
RISK_WEIGHTS = {
    "blast":      0.35,   # how much of the repo depends on this
    "ownership":  0.25,   # is there anyone left who knows it
    "staleness":  0.15,   # has anyone touched it recently enough to remember
    "complexity": 0.15,   # how hard is it to change correctly
    "churn":      0.10,   # how often does it actually get changed
}
```

Each component is normalised to 0..1 **by within-repo percentile rank**, the
same approach and for the same reason as `calculate_health`: the ramp must stay
meaningful for a 40-file project and a 40,000-file one alike. Reuse the
`bisect`-based `rank()` pattern from `build.py:74` — a linear scan per file is
O(n²) and was already fixed once there.

Component definitions:

| Component | Value | Notes |
|---|---|---|
| `blast` | percentile rank of `len(blast_radius(rev, i)["all"])` | from T19's `impact.py`. **0.0 when `import_resolution == "none"`** — see below |
| `ownership` | `owner_share` if `bus_factor == 1` else `owner_share * 0.5` | a sole author is the risk; a dominant-but-not-sole author is half of it |
| `staleness` | `min(stale_days / 540, 1.0)` | 540 days matches `calculate_health`; do not invent a second constant |
| `complexity` | percentile rank of `complexity` | |
| `churn` | percentile rank of `churn` | |

**The honesty rule, and it is load-bearing.** When a file's language has no
import resolution (anything but python/javascript/typescript/ruby — check the
README Limitations table, and derive it from the same constant, do not hardcode
a second copy), `blast` is not 0 — it is *unknown*. Set `blast` to `None`,
redistribute its 0.35 weight proportionally across the components that do have
data, and set `"blast_known": False` in the output. Every surface must print
`blast radius: unknown (no import resolution for go)` rather than a confident
`0`. Reporting an unmeasured signal as a zero is the difference between a tool
people trust and a tool people stop believing after the first wrong answer.

## API to implement in `citygen/risk.py`

```python
UNKNOWN_BLAST_LANGS: frozenset[str]   # every lang without import resolution

def score_all(city: dict) -> list[dict]:
    """Score every building once. Returns a list parallel to city['buildings'].

    Each entry: {
        "index": int, "path": str, "score": float,      # 0..1, higher = riskier
        "band": "low" | "moderate" | "high",
        "components": {"blast": float|None, "ownership": float, ...},
        "raw": {"dependents": int|None, "bus_factor": int|None,
                "stale_days": int|None, "complexity": int, "churn": int|None},
        "blast_known": bool,
        "reasons": [str, ...],     # human sentences, highest-contribution first
    }
    Computes the reverse index ONCE and reuses it for every file.
    """

def score_paths(city: dict, paths: list[str]) -> list[dict]:
    """score_all filtered to the given paths, preserving the given order.
    Paths not present in the city are returned with score None and
    reasons ["not analysed: <why>"] rather than being silently dropped."""

def staged_paths(repo_root: str) -> list[str]:
    """`git diff --cached --name-only --diff-filter=ACMR`, posix-normalised.
    Returns [] (never raises) when git is absent or nothing is staged."""

def band(score: float) -> str:
    """<0.40 low, <0.70 moderate, else high. Thresholds fixed here."""
```

`reasons` is the part humans actually read. Generate sentences from the
components that contributed most, e.g.:
- `"83 files depend on it (top 2% in this repo)"`
- `"single author @harsh — nobody else has committed to it"`
- `"untouched for 14 months; the context is likely gone"`
- `"complexity 412, the 3rd highest in this repo"`

Emit at most 3, ordered by weighted contribution. A file with no notable
component gets `["nothing notable"]`, not an empty list.

## CLI wiring — exact
```python
    r = sub.add_parser("risk", help="which files are dangerous to change?")
    r.add_argument("paths", nargs="*",
                   help="files to score (default: whole repo, top N)")
    r.add_argument("--city", default="out/city.json")
    r.add_argument("--staged", action="store_true",
                   help="score the files staged in git right now")
    r.add_argument("--top", type=int, default=10,
                   help="how many files to list in whole-repo mode")
    r.add_argument("--json", action="store_true")
    r.add_argument("--fail-over", type=float, default=None, metavar="SCORE",
                   help="exit 1 if any scored file is riskier than SCORE (for CI)")
    r.set_defaults(func=_cmd_risk)
```

`--staged` and positional `paths` are mutually exclusive; if both are given,
error with exit 2 rather than guessing.

## Output format

Whole-repo mode (`citygen risk`):
```
Riskiest files in chronopolis

  0.81  high      citygen/build.py
        83 files depend on it (top 2% in this repo)
        single author @harsh - nobody else has committed to it
        complexity 412, the 3rd highest in this repo

  0.64  moderate  citygen/layout.py
        untouched for 14 months; the context is likely gone
        31 files depend on it

  ...
```

Staged mode (`citygen risk --staged`) prints the same blocks, prefixed with the
count, and prints `Nothing staged.` and exits 0 when the staging area is empty.
An empty staging area is not an error.

Colour: `high` red, `moderate` yellow, `low` default — through the existing
`_style()` helper, gated on `_use_color()`, ASCII only (T18: the Windows console
codepage crashes on non-cp1252 characters, and this CLI must run there
unmodified).

## Acceptance criteria
1. On this repo, `citygen risk` ranks `citygen/build.py` in the top 3. It is the
   most-imported, highest-complexity file here; if it does not surface, the
   formula or the blast wiring is wrong.
2. A file with `bus_factor == 1` and ≥10 dependents always lands in `high`.
   Assert this as a property in the tests, not by eyeballing one repo.
3. On a Go repo (clone `spf13/cobra` into `.testrepos/`), every file reports
   `blast radius: unknown`, **not** `0`, and `blast_known` is `false` in JSON.
4. `--staged` with nothing staged exits 0 and prints `Nothing staged.`
5. `--fail-over 0.7` exits 1 when something scores above 0.7, 0 otherwise, and
   prints which file tripped it.
6. `score_all` on a 1272-building city completes in under 2 seconds. Reverse
   index built once, not per file — a per-file rebuild is O(n·e) and will show
   up here immediately.
7. No `KeyError` on a `--no-git` city: every git-derived field is read with
   `.get()` and its component contributes 0 with a stated reason.

## Verify
```bash
python -m citygen build . -o out/city.json && python -m citygen risk --city out/city.json
```
```bash
python -m citygen risk --staged --city out/city.json
```
```bash
python citygen/tests/test_risk.py
```

## Tests to write in `citygen/tests/test_risk.py`
Bare `test_*` functions, runnable directly (see T18).

- `test_bus_factor_one_with_dependents_is_high` — the property from criterion 2.
- `test_unknown_blast_is_none_not_zero` — a Go-language fixture building;
  assert `components["blast"] is None` and `blast_known is False`.
- `test_weight_redistribution_sums_to_one` — with `blast` unknown, the remaining
  weights must still sum to 1.0 (± 1e-9). This is the bug most likely to ship:
  dropping a component and leaving the divisor at 1.0 silently deflates every
  score for every non-Python repo.
- `test_no_git_city_does_not_raise` — city with `git: null`.
- `test_band_thresholds` — boundary values 0.399/0.40/0.699/0.70.
- `test_score_paths_preserves_order_and_reports_missing`.
- `test_staged_paths_empty_when_no_git` — must return `[]`, not raise.

## Default if ambiguous
- Risk is per-file, never per-directory. Aggregating to districts is a
  presentation concern and does not belong in this library.
- No test-coverage component. The project cannot measure coverage and inventing
  a proxy for it (counting `test_*.py` neighbours) would be a fabricated signal
  in a scoring formula people are meant to trust. If coverage is wanted later it
  arrives as a real ingested `coverage.xml`, not a guess.
