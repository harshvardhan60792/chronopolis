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
    --changed-from-stdin --pr-author-emails author_emails.txt < changed_files.txt > comment.md
```

## CLI wiring — exact
In `citygen/cli.py`, register alongside the other Phase A subcommands:

```python
    pr = sub.add_parser("pr-report", help="risk finding for a PR, as markdown")
    pr.add_argument("--city", default="out/city.json")
    pr.add_argument("--changed-from-stdin", action="store_true", required=True,
                    help="read changed file paths, one per line, from stdin")
    pr.add_argument("--pr-author-emails", default=None,
                    help="path to a file of git commit emails (one per line) "
                         "belonging to the PR's author — see 'Identifying the "
                         "PR author' below. Omit to disable the exclusion rule.")
    pr.set_defaults(func=_cmd_pr_report)
```

## Identifying the PR author — required before "never suggest the PR author" can work
A GitHub PR author is identified by **login**; a building's `authors` field
(`docs/02-DATA-SCHEMA.md:66`) is keyed by **git commit email** — two different
identity spaces with no built-in mapping. Resolve it the same way git itself
would: collect every commit email the PR branch itself introduced, and treat
that set as "the PR author" for exclusion purposes.

The workflow computes this (see below) and passes it via `--pr-author-emails`,
a file of emails, one per line. `report.py` never talks to the GitHub API
directly — it stays testable with plain files, consistent with the rest of
this CLI.

```python
def changed_files_from_git(repo_root: str, base_ref: str, head_ref: str) -> list[str]:
    """`git diff --name-only --diff-filter=ACMR base...head`, posix-normalised.
    Uses the three-dot form: we want files changed on the PR branch, not files
    that changed on main since the branch started. Two-dot here is a common and
    silent bug that makes every comment wrong on a long-lived branch."""

def load_author_emails(path: str | None) -> frozenset[str]:
    """Empty frozenset if path is None or the file doesn't exist — the
    exclusion rule degrades to "no exclusion" rather than crashing."""

def build_report(city: dict, changed: list[str],
                 pr_author_emails: frozenset[str] = frozenset()) -> dict:
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
mined by T02) across the flagged files: the top author, by commit count on
those files, whose email is **not** in `pr_author_emails`. If `pr_author_emails`
is empty (the flag was omitted), no exclusion is applied — say so is not
necessary, just pick the top author. If every author on the flagged files is in
`pr_author_emails`, say that instead — it is the more interesting finding:
`only the PR's own author has ever committed to these files`.

Display name: use whatever identity string `authors` already stores (T02's
convention — check `docs/02-DATA-SCHEMA.md` for the exact field, likely an
email or a `Name <email>` string). Do not invent a `@login` handle — nothing in
this pipeline has ever resolved a GitHub login, and fabricating one from an
email's local-part would sometimes be wrong.

## Comment format

```markdown
<!-- chronopolis-risk -->
### Chronopolis — change risk

**2 of 7 changed files are high-risk.** 31 files depend on this change.

| File | Risk | Why |
|---|---|---|
| `auth/session.py` | **0.84 high** | 17 files depend on it · single author alice@example.com, last active 8 months ago |
| `auth/token.py` | **0.72 high** | 22 files depend on it · complexity 380, the 2nd highest in this repo |

Suggested reviewer: **alice@example.com** (most commits on the flagged files, excluding this PR's own author).

*(Every reason shown above comes from `citygen risk`'s five components — blast
radius, ownership, staleness, complexity, churn. Co-change/hidden-coupling is a
real signal this project computes (`edges.cochange`, `stats.top_hidden_coupling`)
but T20 deliberately does not fold it into the risk score — see T20's "why this
task exists" section. If a future task adds it as a sixth component, this
example gets a coupling-based reason back; until then, don't invent one here
that `report.py` cannot actually produce.)*

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
**Do not touch the existing "Comment on PR" step (the one with marker
`&lt;!-- chronopolis-pr-preview --&gt;`).** It is unconditional today and posts the
artifact-download link on every PR — that is a working, already-shipped
feature, and gating it on a risk finding would silently remove it from every
PR that isn't high-risk, which is most of them. This task **adds a second,
separate** comment step; it does not modify the first one.

The current checkout step (`actions/checkout@v4`) has no `fetch-depth` set,
which defaults to a shallow depth-1 clone — `git diff base...HEAD` and the
history mining both need real history. Add `fetch-depth: 0` to the existing
checkout step's `with:` block (it doesn't have one today; add it).

Add these steps after the existing "Upload preview artifact" step, before or
after the existing "Comment on PR" step (order between the two comment steps
doesn't matter — they use different markers and don't interact):

```yaml
    - name: Compute changed files and PR author emails
      run: |
        git diff --name-only --diff-filter=ACMR origin/${{ github.base_ref }}...HEAD > changed.txt
        git log --format=%ae origin/${{ github.base_ref }}...HEAD | sort -u > author_emails.txt
        echo "changed files:"; cat changed.txt

    - name: Build risk comment
      id: risk
      run: |
        python -m citygen pr-report --city out/pr-preview.city.json \
          --changed-from-stdin --pr-author-emails author_emails.txt \
          < changed.txt > comment.md || true
        if [ -s comment.md ]; then echo "has_comment=true" >> "$GITHUB_OUTPUT"
        else echo "has_comment=false" >> "$GITHUB_OUTPUT"; fi

    - name: Comment risk finding on PR
      if: steps.risk.outputs.has_comment == 'true'
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          const body = fs.readFileSync('comment.md', 'utf8');
          const marker = '<!-- chronopolis-risk -->';
          const { data: comments } = await github.rest.issues.listComments({
            owner: context.repo.owner, repo: context.repo.repo,
            issue_number: context.issue.number,
          });
          const existing = comments.find(c => c.body && c.body.includes(marker));
          try {
            if (existing) {
              await github.rest.issues.updateComment({
                owner: context.repo.owner, repo: context.repo.repo,
                comment_id: existing.id, body,
              });
            } else {
              await github.rest.issues.createComment({
                owner: context.repo.owner, repo: context.repo.repo,
                issue_number: context.issue.number, body,
              });
            }
          } catch (e) {
            // Fork PRs commonly run with a read-only GITHUB_TOKEN with no
            // comment permission - a 403 here must not fail the job.
            console.log('could not post risk comment (likely a fork PR): ' + e.message);
          }
```

The `|| true` on "Build risk comment" is deliberate: a crash in the report
generator must never fail a contributor's PR, and must not block the existing
artifact-link comment from posting either — which is exactly why this is a
separate step rather than a modification of the first one.

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
8. **The existing unconditional artifact-link comment (marker
   `&lt;!-- chronopolis-pr-preview --&gt;`) still posts on a low-risk PR.** Open a
   PR that changes nothing risky and confirm both that no risk comment appears
   and that the original preview-link comment still does. This is the criterion
   that catches the regression this task is most likely to introduce.
9. The PR-author exclusion actually excludes: build a fixture where the only
   author on the flagged files is also in `pr_author_emails`, and assert the
   report says so instead of naming them as the suggested reviewer.

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
