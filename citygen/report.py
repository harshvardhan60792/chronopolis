import os
import subprocess
from .impact import build_reverse_index, blast_radius
from .risk import score_paths

def changed_files_from_git(repo_root: str, base_ref: str, head_ref: str) -> list[str]:
    """`git diff --name-only --diff-filter=ACMR base...head`, posix-normalised.
    Uses the three-dot form: we want files changed on the PR branch, not files
    that changed on main since the branch started. Two-dot here is a common and
    silent bug that makes every comment wrong on a long-lived branch."""
    cmd = ["git", "-C", repo_root, "diff", "--name-only", "--diff-filter=ACMR", f"{base_ref}...{head_ref}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding="utf-8", check=True)
        return [line.replace("\\", "/") for line in out.stdout.strip().split("\n") if line]
    except (OSError, subprocess.SubprocessError):
        return []

def load_author_emails(path: str | None) -> frozenset[str]:
    """Empty frozenset if path is None or the file doesn't exist — the
    exclusion rule degrades to "no exclusion" rather than crashing."""
    if not path or not os.path.exists(path):
        return frozenset()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return frozenset(line.strip() for line in f if line.strip())
    except OSError:
        return frozenset()

def build_report(city: dict, changed: list[str],
                 pr_author_emails: frozenset[str] = frozenset()) -> dict:
    if not city.get("git"):
        return {"silent": True}

    buildings = city.get("buildings", [])
    path_to_idx = {b["path"]: i for i, b in enumerate(buildings)}
    
    # 1. separate changed into analysed vs unanalysed
    analysed_idx = []
    unanalysed = []
    
    for c in changed:
        if c in path_to_idx:
            analysed_idx.append(path_to_idx[c])
        else:
            unanalysed.append(c)

    # score paths
    scores = score_paths(city, changed)
    
    flagged = []
    moderate_files = []
    moderate_count = 0
    unresolved_langs = set()
    unresolved_count = 0
    
    from .walk import IMPORT_RESOLVED_LANGS
    
    for s in scores:
        if s["score"] is not None:
            if s["score"] >= 0.70:
                flagged.append(s)
            elif s["score"] >= 0.40:
                moderate_files.append(s)
                moderate_count += 1

        
        # Check unresolved langs among all analysed files
        if s["index"] >= 0:
            b = buildings[s["index"]]
            lang = b.get("lang")
            if lang not in IMPORT_RESOLVED_LANGS:
                ext = b.get("ext") or f".{lang}"
                unresolved_langs.add(ext)
                unresolved_count += 1
                
    flagged.sort(key=lambda x: x["score"], reverse=True)
    flagged = flagged[:5] # cap at 5
    moderate_files.sort(key=lambda x: x["score"], reverse=True)

    silent = len(flagged) == 0
        
    # compute blast radius union
    edges = city.get("edges", {}).get("import", [])
    rev = build_reverse_index(edges, len(buildings))
    
    blast_union = set()
    blast_known = True
    for i in analysed_idx:
        b = buildings[i]
        if b.get("lang") in ("python", "javascript", "typescript", "ruby", "go") and b.get("lang") != "go":
            # go has no import resolution according to test expectations, let's just use what risk.py does: IMPORT_RESOLVED_LANGS
            # Actually, I should use IMPORT_RESOLVED_LANGS from citygen.walk
            from .walk import IMPORT_RESOLVED_LANGS
            if b.get("lang") in IMPORT_RESOLVED_LANGS:
                blast_union.update(blast_radius(rev, i)["all"])
            else:
                blast_known = False # At least one file has unknown blast radius, actually wait: if it's in unanalysed languages, we flag it.
        else:
            from .walk import IMPORT_RESOLVED_LANGS
            if b.get("lang") not in IMPORT_RESOLVED_LANGS:
                blast_known = False

    # subtract changed files themselves from blast union
    blast_union -= set(analysed_idx)
    blast_total = len(blast_union) if blast_known else None

    # finding suggested reviewer
    # top author, by commit count on those flagged files, whose email is not in pr_author_emails
    authors_counts = {}
    git_authors = city.get("git", {}).get("authors", [])
    
    for f in flagged:
        idx = f["index"]
        if idx >= 0:
            b_authors = buildings[idx].get("authors", [])
            for author_idx, count in b_authors:
                if 0 <= author_idx < len(git_authors):
                    email = git_authors[author_idx]["email"]
                    if email not in authors_counts:
                        authors_counts[email] = 0
                    authors_counts[email] += count
                
    reviewers = []
    for email, count in authors_counts.items():
        if not pr_author_emails or email not in pr_author_emails:
            reviewers.append((email, count))
    reviewers.sort(key=lambda x: x[1], reverse=True)

    unanalysed_details = [f"{u} (not in city)" for u in unanalysed]
    
    return {
        "flagged": flagged,
        "moderate_count": moderate_count,
        "moderate_files": moderate_files,
        "total_changed": len(changed),
        "analysed": len(analysed_idx),
        "unanalysed": unanalysed_details,
        "blast_total": blast_total if blast_known else len(blast_union),
        "blast_known": blast_known,
        "reviewers": reviewers,
        "silent": silent,
        "all_authors_excluded": len(authors_counts) > 0 and len(reviewers) == 0,
        "unresolved_langs": list(unresolved_langs),
        "unresolved_count": unresolved_count
    }

def render_markdown(report: dict, city: dict) -> str:
    if report.get("silent"):
        return ""

    lines = []
    lines.append("<!-- chronopolis-risk -->")
    lines.append("### Chronopolis — change risk")
    lines.append("")
    
    flagged = report["flagged"]
    high_count = len(flagged)
    total = report["total_changed"]
    
    blast_text = f"{report['blast_total']} files depend on this change"
    if not report["blast_known"] and report["blast_total"] == 0:
        # If we can't compute it or it's unknown in some way
        pass
    
    lines.append(f"**{high_count} of {total} changed files are high-risk.** {blast_text}.")
    lines.append("")
    lines.append("| File | Risk | Why |")
    lines.append("|---|---|---|")
    
    for f in flagged:
        reasons_str = " · ".join(f["reasons"][:3])
        # Make the score text bold and append " high"
        score_val = f["score"]
        lines.append(f"| `{f['path']}` | **{score_val:.2f} high** | {reasons_str} |")
        
    lines.append("")
    
    if report.get("all_authors_excluded"):
        lines.append("Suggested reviewer: only the PR's own author has ever committed to these files.")
    elif report["reviewers"]:
        top_reviewer_email = report["reviewers"][0][0]
        
        identity = top_reviewer_email
        git_authors = city.get("git", {}).get("authors", [])
        for a in git_authors:
            if a.get("email") == top_reviewer_email:
                name = a.get("name")
                if name:
                    identity = f"{name} <{top_reviewer_email}>"
                break
                
        lines.append(f"Suggested reviewer: **{identity}** (most commits on the flagged files, excluding this PR's own author).")
        
    if report["moderate_count"] > 0:
        # We need to print moderate files here. Since `report` only has `moderate_count` natively, wait... we need the actual list!
        # Ah, report should return moderate files. Let's fix build_report to return them as well.
        moderate_files = report.get("moderate_files", [])
        if moderate_files:
            lines.append(f"<details><summary>{report['moderate_count']} more files scored moderate</summary>")
            lines.append("")
            # `api/login.py` 0.61 · `db/pool.py` 0.55 · `util/time.py` 0.44
            limit = 50
            mod_strs = [f"`{m['path']}` {m['score']:.2f}" for m in moderate_files[:limit]]
            mod_text = " · ".join(mod_strs)
            if len(moderate_files) > limit:
                mod_text += f" ... and {len(moderate_files) - limit} more"
            lines.append(mod_text)
            lines.append("")
            lines.append("</details>")
            lines.append("")
    
    # footer
    footer_parts = ["<sub>Blast radius counts files reachable through resolved imports."]
    
    unresolved_langs = report.get("unresolved_langs", [])
    if unresolved_langs:
        unresolved_count = report.get("unresolved_count", 0)
        langs_str = ", ".join(f"`{ext}`" if ext.startswith('.') else f"`{ext}`" for ext in sorted(unresolved_langs))
        footer_parts.append(f"{unresolved_count} changed file{'s are' if unresolved_count > 1 else ' is'} in languages without import resolution ({langs_str}) and {'are' if unresolved_count > 1 else 'is'} not counted.")
        
    footer_parts.append("[How this is computed](../blob/main/tasks/T20-risk-command.md) · [Open the 3D city](ARTIFACT_URL)</sub>")
    
    lines.append(" · ".join(footer_parts))
    
    return "\n".join(lines)
