# T21 — PR risk comment: the surface a whole team sees

**Blocked by:** T19, T20 · **Effort:** medium · **Phase:** A
**Fills:** nothing in `city.json`. Adds `citygen pr-report` + a workflow upgrade.

## Why this exists
`.github/workflows/pr-preview.yml` already builds a city per PR and comments a
link to a downloadable HTML file. Almost nobody downloads a file from a CI
comment. This task changes the comment from *"here is an artifact"* to *"here is
the finding"* — so the reviewer gets the answer without clicking anything, and
the 3D city becomes the optional deep dive rather than the price of entry.

This is the highest-retention surface in the plan: it requires no install by
anyone on the team and shows up on its own.

## The failure mode to design against
**A noisy bot is ignored forever, and it only gets one chance.** On a monorepo,
a naive implementation prints "blast radius: 180 files" and a wall of warnings on
every PR, reviewers learn to scroll past it in a week, and no later improvement
wins them back. Every rule below exists to prevent that:

- **Say nothing when there is nothing to say.** If no changed file scores
  `high`, post no comment at all. Silence is the default state of a good bot.
- **Cap hard.** At most 5 flagged files per comment, at most 3 reasons per file.
- **One comment, updated in place**, never a new comment per push. The existing
  workflow already has the marker-based create-or-update logic — keep it.
- **Never fail the build.** Exit 0 always. A risk *warning* that blocks a merge
  becomes a thing to route around, not read.

## Files
- new: `citygen/report.py`
- edit: `citygen/cli.py` (add the `pr-report` subcommand)
- edit: `.github/workflows/pr-preview.yml`
- new: `citygen/tests/test_report.py`
- edit: `README.md` (CI Integration section)

## Design: the CLI produces markdown, the workflow only posts it
Keep all logic in Python where it is testable locally. The workflow must contain
no analysis logic whatsoever — it runs a command, captures stdout, posts it.

```bash
python -m citygen pr-report --city out/city.json \
    --changed-from-stdin < changed_files.txt > comment.md
```

## API to implement in `citygen/report.py`

```python
MAX_FILES_REPORTED = 5
MAX_REASONS_PER_FILE = 3

def changed_files_from_git(repo_root: str, base_ref: str, head_ref: str) -> list[str]:
    """`git diff --name-only --diff-filter=ACMR base...head`, posix-normalised.
    Uses the three-dot form: we want files changed on the PR branch, not files
    that changed on main since the branch started. Two-dot here is a common and
    silent bug that makes every comment wrong on a long-lived branch."""

def build_report(city: dict, changed: list[str]) -> dict:
    """Returns {
        "flagged":   [risk-entry, ...],   # score >= 0.70, capped, sorted desc
        "moderate_count": int,
        "total_changed": int,
        "analysed":  int,                 # changed files present in the city
        "unanalysed": [str, ...],         # changed but not in the city, with why
        "blast_total": int | None,        # union of dependents, None if unknowable
        "blast_known": bool,
        "reviewers": [(str, int), ...],   # suggested, see below
        "silent": bool,                   # True => post nothing
    }"""

def render_markdown(report: dict, city: dict) -> str:
    """The comment body. Returns "" when report['silent'] is True."""
```

**Blast radius must be a union, not a sum.** Two changed files that both feed the
same 50 dependents affect 50 files, not 100. Compute
`set().union(*[blast_radius(rev, i)["all"] for i in changed_idx])` and subtract
the changed files themselves. Summing is the obvious implementation and it
inflates every number the bot prints.

**Reviewer suggestion** comes from `city["buildings"][i]["authors"]` (already
mined by T02) across the flagged files: the top author who is *not* the PR
author, by commit count on those files. Never suggest the PR author. If the only
author is the PR author, say that instead — it is the more interesting finding:
`only @harsh has ever committed to these files`.

## Comment format

```markdown
<!-- chronopolis-risk -->
### Chronopolis — change risk

**2 of 7 changed files are high-risk.** 31 files depend on this change.

| File | Risk | Why |
|---|---|---|
| `auth/session.py` | **0.84 high** | 17 files depend on it · single author @alice, last active 8 months ago |
| `auth/token.py` | **0.72 high** | changes together with `api/login.py` in 80% of commits, with no import between them |

Suggested reviewer: **@alice** (most commits on the flagged files).

<details><summary>3 more files scored moderate</summary>

`api/login.py` 0.61 · `db/pool.py` 0.55 · `util/time.py` 0.44

</details>

<sub>Blast radius counts files reachable through resolved imports. 2 changed files are in languages without import resolution (`.go`) and are not counted. · [How this is computed](../blob/main/tasks/T20-risk-command.md) · [Open the 3D city](ARTIFACT_URL)</sub>
```

Requirements on this format:
- The `<!-- chronopolis-risk -->` marker must be the first line — the existing
  workflow's update logic finds the comment by it.
- The unanalysed-languages caveat in the footer is **mandatory** whenever any
  changed file is in a language without import resolution. Reporting a confident
  blast radius that silently excluded half the diff is exactly how a risk tool
  loses trust permanently.
- The 3D city link is a footnote, not a call to action. That inversion is the
  whole point of this task.

## Workflow changes to `.github/workflows/pr-preview.yml`
Keep the existing build/export/upload steps. Add, before the comment step:

```yaml
      - name: Compute changed files
        run: |
          git fetch --no-tags --depth=50 origin ${{ github.base_ref }}
          git diff --name-only --diff-filter=ACMR \
            origin/${{ github.base_ref }}...HEAD > changed.txt
          echo "changed files:"; cat changed.txt

      - name: Build risk comment
        id: risk
        run: |
          python -m citygen pr-report --city out/pr-preview.city.json \
            --changed-from-stdin < changed.txt > comment.md || true
          if [ -s comment.md ]; then echo "has_comment=true" >> "$GITHUB_OUTPUT";
          else echo "has_comment=false" >> "$GITHUB_OUTPUT"; fi
```

Then gate the existing `actions/github-script` step on
`if: steps.risk.outputs.has_comment == 'true'` and post `comment.md`'s contents
instead of the current link-only body, appending the artifact URL to the footer.

The `|| true` is deliberate: a crash in the report generator must never fail a
contributor's PR.

**`fetch-depth` matters.** The default checkout is shallow (depth 1) and
`git diff base...HEAD` will fail against it. The existing job must set
`fetch-depth: 0` on `actions/checkout` — the git history mining needs it anyway,
so verify it is already there and add it if not.

## Acceptance criteria
1. Run locally against a real branch of this repo with a hand-written
   `changed.txt`; the markdown is valid and the file names are correct.
2. With a changed file list containing only low-risk files, output is empty and
   the exit code is 0. Assert this — the silent path is the one that will be
   broken by a later change and never noticed.
3. Blast radius on two files sharing dependents is the union, not the sum.
   Assert with a fixture where the correct answer differs from the naive one.
4. A changed file not present in the city (new file, vendored, binary) appears
   under `unanalysed` with a reason, and never crashes the report.
5. The comment body is under 65,536 characters (GitHub's limit) even when the
   input is 5,000 changed files. Test with a generated 5,000-path list.
6. Two runs on the same input produce identical markdown.
7. On a fork PR, the workflow does not fail even though `GITHUB_TOKEN` may lack
   comment permission — the post step must tolerate a 403 and log it.

## Verify
```bash
python -m citygen build . -o out/city.json
```
```bash
git diff --name-only --diff-filter=ACMR origin/main...HEAD | python -m citygen pr-report --city out/city.json --changed-from-stdin
```
```bash
python citygen/tests/test_report.py
```

## Default if ambiguous
- Threshold for "flagged" is `high` (≥0.70) only. Moderate files are collapsed
  into the `<details>` block and never listed in the table.
- No emoji beyond none. The existing docs use plain text and ASCII; a bot that
  shouts is a bot that gets muted.
- If `city["git"]` is null (no history), post nothing at all. Every interesting
  signal in this report is history-derived; a comment without them is noise.
