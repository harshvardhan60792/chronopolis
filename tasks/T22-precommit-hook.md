# T22 — `citygen hook install`: the pre-commit conscience

**Blocked by:** T20 · **Effort:** small · **Phase:** A
**Fills:** nothing in `city.json`. Adds a hook installer + `risk --staged` glue.

## Why this exists
The tool only becomes habitual if it appears in a path the developer already
walks without deciding to. `git commit` is that path.

## The constraint that determines the entire design
**A slow pre-commit hook is uninstalled by `--no-verify` within a week, and it
never comes back.** The current cold build is ~34 s on 1272 files
(`docs/05-PERFORMANCE.md`). A hook that triggers a build is dead on arrival.

Therefore, and non-negotiably for this task:

1. The hook **reads an existing `city.json`**. It never builds one.
2. It is honest when that data is stale rather than silently wrong.
3. It **warns and exits 0 by default.** Blocking is opt-in (`--block`).
4. Total added latency budget: **under 200 ms**, measured.

Point 3 deserves its own line. A warning that blocks is not a warning, it is a
gate, and gates around soft signals get routed around. The default must be a
thing developers tolerate indefinitely.

## Files
- new: `citygen/hook.py`
- edit: `citygen/cli.py` (add the `hook` subcommand with `install`/`uninstall`/`run`)
- new: `citygen/tests/test_hook.py`
- edit: `README.md`

## CLI shape
```
python -m citygen hook install [--repo .] [--city out/city.json] [--block] [--threshold 0.70]
python -m citygen hook uninstall [--repo .]
python -m citygen hook run [--city out/city.json] [--block] [--threshold 0.70]
```

`install` writes the hook script; `run` is what the hook script actually calls,
so all logic stays in Python and the shell script stays trivial and never needs
regenerating when the logic changes.

## The hook script written to `.git/hooks/pre-commit`

```sh
#!/bin/sh
# installed by citygen -- chronopolis risk warning
# remove with: python -m citygen hook uninstall
python -m citygen hook run --city "out/city.json" || exit 0
```

The trailing `|| exit 0` is deliberate belt-and-braces: even if `hook run` crashes
or citygen is not on PATH in this shell, the developer's commit still goes
through. In `--block` mode the installer omits it and `hook run` returns 1 on a
trip.

## Installer safety — the part most likely to be done carelessly
`.git/hooks/pre-commit` may already exist and may be someone's real work.

| Situation | Required behaviour |
|---|---|
| No existing hook | Write it, `chmod 0755`, print the path |
| Existing hook, already ours (contains the marker comment) | Overwrite silently, report "updated" |
| Existing hook, **not** ours | **Refuse.** Exit 2. Print the existing first line and tell the user to either append `python -m citygen hook run` themselves or re-run with `--force`. Never overwrite someone's hook. |
| `--force` on a foreign hook | Back it up to `.git/hooks/pre-commit.bak-<unix_ts>` first, then write, and print where the backup went |
| Repo has `core.hooksPath` set | Detect via `git config --get core.hooksPath` and install there instead; if it points outside the repo, print the path and ask for confirmation rather than writing into an unexpected directory |
| Not a git repo | Exit 2 with a clear message |

`uninstall` removes the file **only if it contains our marker**, and otherwise
refuses. Restore from a `.bak-*` if exactly one exists, and say so.

## Staleness — the honesty requirement
The hook reads a `city.json` that may be weeks old. It must say so.

Compare `city["repo"]["head"]` against the current `git rev-parse HEAD`. If they
differ, count the commits between them:
`git rev-list --count <city_head>..HEAD` (which fails harmlessly if that sha is
gone — treat failure as "unknown").

| Age | Behaviour |
|---|---|
| Same HEAD | No note |
| 1–20 commits behind | One dim line: `city data is 7 commits old — refresh: python -m citygen build . -o out/city.json` |
| >20 commits behind, or HEAD unknown | Print the warning **and** the staleness note prominently; the numbers may be materially wrong |
| No `city.json` at all | Print one line telling them how to create one, exit 0. **Never nag on every commit** — see below |
| Staged file is not in the city at all (it is new) | Say `new file, not yet analysed` rather than scoring it 0 |

**Do not nag.** When `city.json` is missing, print the hint at most once per day:
touch a marker file at `.git/citygen-hint-<YYYYMMDD>` and stay silent if it
exists. A hook that prints the same setup advice on every commit is a hook that
gets removed.

## Output on a trip
```
chronopolis: 1 of 3 staged files is high-risk

  0.84  high  auth/session.py
        17 files depend on it
        single author @alice - nobody else has committed to it
        untouched for 8 months; the context is likely gone

  city data is 7 commits old - refresh: python -m citygen build . -o out/city.json

  (warning only; commit proceeding. block with: citygen hook install --block)
```

When nothing trips: **print nothing at all** and exit 0. A hook that prints
"all clear" on every commit is noise that trains people to stop reading it.

## Acceptance criteria
1. `hook install` on a clean repo writes an executable hook; `git commit` still
   succeeds when a high-risk file is staged, and prints the warning.
2. `hook install` against a foreign existing hook exits 2 and does **not** modify
   the file. Assert the file's bytes are unchanged.
3. `--force` backs up before overwriting, and the backup content matches the
   original exactly.
4. `hook uninstall` refuses to delete a foreign hook.
5. **Latency:** `hook run` completes in under 200 ms on a 1272-building
   `city.json` with 3 staged files. Measure it and record the number in the
   commit message. If it exceeds 200 ms, the risk scoring is being run over the
   whole repo instead of just the staged paths — use `score_paths`, not
   `score_all`.
6. Nothing staged: exits 0 silently.
7. No `city.json`: exits 0, hint printed at most once per day.
8. `--block` mode: exits 1 on a trip, and `git commit` is actually prevented.
   Verify end-to-end with a real commit attempt, not just the exit code.
9. Works when `git commit` is run from a subdirectory — resolve paths against
   the repo root (`git rev-parse --show-toplevel`), not the current directory.
   This is the most likely real-world break.

## Verify
```bash
python -m citygen build . -o out/city.json
```
```bash
python -m citygen hook install
```
```bash
git add citygen/build.py
```
```bash
python -m citygen hook run --city out/city.json
```
```bash
python citygen/tests/test_hook.py
```

## Tests to write in `citygen/tests/test_hook.py`
Use `tempfile.TemporaryDirectory` plus `git init` for a throwaway repo; bare
`test_*` functions runnable directly (see T18).

- `test_install_creates_executable_hook`
- `test_install_refuses_foreign_hook_and_leaves_bytes_untouched`
- `test_force_backs_up_before_overwrite`
- `test_uninstall_refuses_foreign_hook`
- `test_run_silent_when_nothing_staged`
- `test_run_exit_zero_by_default_on_trip` / `test_run_exit_one_with_block`
- `test_subdirectory_invocation_resolves_repo_root`
- `test_missing_city_hint_is_rate_limited`

## Default if ambiguous
- Default threshold is `risk.HIGH_THRESHOLD` (0.70), imported from `risk.py` —
  do not restate the number 0.70 in `hook.py`.
- The hook considers only `--diff-filter=ACMR` staged paths. Deletions are not
  risky in the sense this tool measures, and flagging them would be noise.
- Never write to `.gitignore`, never create `out/` — the hook only reads.
