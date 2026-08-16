import bisect
import os
import subprocess
from .walk import IMPORT_RESOLVED_LANGS
from .impact import build_reverse_index, blast_radius

HIGH_THRESHOLD = 0.70
MODERATE_THRESHOLD = 0.40

RISK_WEIGHTS = {
    "blast":      0.35,   # how much of the repo depends on this
    "ownership":  0.25,   # is there anyone left who knows it
    "staleness":  0.15,   # has anyone touched it recently enough to remember
    "complexity": 0.15,   # how hard is it to change correctly
    "churn":      0.10,   # how often does it actually get changed
}

def band(score: float) -> str:
    """< MODERATE_THRESHOLD low, < HIGH_THRESHOLD moderate, else high."""
    if score < MODERATE_THRESHOLD:
        return "low"
    if score < HIGH_THRESHOLD:
        return "moderate"
    return "high"

def _rank(val: float, lst: list) -> float:
    return bisect.bisect_left(lst, val) / len(lst) if lst else 0.0

def score_all(city: dict) -> list[dict]:
    buildings = city.get("buildings", [])
    if not buildings:
        return []
    
    n = len(buildings)
    edges = city.get("edges", {}).get("import", [])
    rev = build_reverse_index(edges, n)

    churn_list = sorted(b["churn"] for b in buildings if "churn" in b and b["churn"] is not None)
    cx_list = sorted(b.get("complexity", 0) for b in buildings)
    
    blasts = []
    br_lengths = {}
    for i, b in enumerate(buildings):
        if b["lang"] in IMPORT_RESOLVED_LANGS:
            length = len(blast_radius(rev, i)["all"])
            br_lengths[i] = length
            blasts.append(length)
        else:
            blasts.append(0)
    blasts.sort()

    git_authors = city.get("git", {}).get("authors", []) if city.get("git") else []

    scored = []
    for i, b in enumerate(buildings):
        lang = b["lang"]
        
        has_git = "churn" in b and city.get("git") is not None
        
        churn_val = b.get("churn")
        churn_n = _rank(churn_val, churn_list) if has_git and churn_val is not None else 0.0
        
        cx_val = b.get("complexity", 0)
        cx_n = _rank(cx_val, cx_list)
        
        stale_days = b.get("stale_days")
        staleness = min(stale_days / 540.0, 1.0) if has_git and stale_days is not None else 0.0

        bus_factor = b.get("bus_factor")
        owner_share = b.get("owner_share") or 0.0
        ownership = owner_share if bus_factor == 1 else owner_share * 0.5
        
        if lang in IMPORT_RESOLVED_LANGS:
            br_len = br_lengths[i]
            blast = _rank(br_len, blasts)
            blast_known = True
        else:
            blast = None
            blast_known = False

        components = {
            "blast": blast,
            "ownership": ownership,
            "staleness": staleness,
            "complexity": cx_n,
            "churn": churn_n,
        }

        score = 0.0
        if blast is None:
            remaining_weight = 1.0 - RISK_WEIGHTS["blast"]
            for k, v in components.items():
                if v is not None:
                    score += (v * RISK_WEIGHTS[k]) / remaining_weight
        else:
            for k, v in components.items():
                score += v * RISK_WEIGHTS[k]

        score = round(score, 4)
        
        if bus_factor == 1 and blast_known and br_len >= 10:
            score = max(score, 0.70)

        # Generate reasons
        contribs = []
        w_sum = 1.0 if blast_known else 1.0 - RISK_WEIGHTS["blast"]
        
        if blast is not None:
            contribs.append(("blast", blast * RISK_WEIGHTS["blast"] / w_sum))
        contribs.append(("ownership", ownership * RISK_WEIGHTS["ownership"] / w_sum))
        contribs.append(("staleness", staleness * RISK_WEIGHTS["staleness"] / w_sum))
        contribs.append(("complexity", cx_n * RISK_WEIGHTS["complexity"] / w_sum))
        contribs.append(("churn", churn_n * RISK_WEIGHTS["churn"] / w_sum))
        
        contribs.sort(key=lambda x: x[1], reverse=True)
        
        reasons = []
        if not has_git:
            reasons.append("not tracked in git or missing history")
            if not blast_known:
                reasons.append(f"blast radius: unknown (no import resolution for {lang})")
            elif br_len > 0:
                pct = int((1 - blast) * 100) if blast < 1.0 else 1
                if pct == 0: pct = 1
                reasons.append(f"{br_len} files depend on it (top {pct}% in this repo)")
            reasons.append(f"complexity {cx_val}, the {n - bisect.bisect_left(cx_list, cx_val)}th highest in this repo")
            
        else:
            for k, contrib in contribs[:3]:
                if contrib == 0:
                    continue
                if k == "blast":
                    pct = max(1, int((1 - blast) * 100))
                    reasons.append(f"{br_len} files depend on it (top {pct}% in this repo)")
                elif k == "ownership":
                    owner_name = "unknown"
                    if b.get("owner") is not None and b.get("owner") < len(git_authors):
                        owner_name = git_authors[b["owner"]]["name"]
                    
                    if bus_factor == 1:
                        reasons.append(f"single author @{owner_name} — nobody else has committed to it")
                    else:
                        pct = int(owner_share * 100)
                        reasons.append(f"dominant author @{owner_name} ({pct}% of changes)")
                elif k == "staleness":
                    if stale_days is not None:
                        months = stale_days // 30
                        if months > 0:
                            reasons.append(f"untouched for {months} months; the context is likely gone")
                        else:
                            reasons.append(f"untouched for {stale_days} days")
                elif k == "complexity":
                    rank_idx = n - bisect.bisect_left(cx_list, cx_val)
                    ord_suffix = "th" if 11 <= rank_idx % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(rank_idx % 10, "th")
                    reasons.append(f"complexity {cx_val}, the {rank_idx}{ord_suffix} highest in this repo")
                elif k == "churn":
                    pct = max(1, int((1 - churn_n) * 100))
                    reasons.append(f"high churn: {churn_val} changes (top {pct}% in this repo)")

        if not blast_known and "blast radius: unknown" not in "".join(reasons):
            reasons.insert(0, f"blast radius: unknown (no import resolution for {lang})")
            
        if not reasons:
            reasons = ["nothing notable"]
            
        # Ensure we return at most 3 reasons
        reasons = reasons[:3]

        scored.append({
            "index": i,
            "path": b["path"],
            "score": score,
            "band": band(score),
            "components": components,
            "raw": {
                "dependents": br_len if blast_known else None,
                "bus_factor": bus_factor,
                "stale_days": stale_days,
                "complexity": cx_val,
                "churn": churn_val,
            },
            "blast_known": blast_known,
            "reasons": reasons,
        })
        
    return scored

def score_paths(city: dict, paths: list[str]) -> list[dict]:
    buildings = city.get("buildings", [])
    if not buildings:
        return []

    n = len(buildings)
    edges = city.get("edges", {}).get("import", [])
    rev = build_reverse_index(edges, n)

    churn_list = sorted(b["churn"] for b in buildings if "churn" in b and b["churn"] is not None)
    cx_list = sorted(b.get("complexity", 0) for b in buildings)
    git_authors = city.get("git", {}).get("authors", []) if city.get("git") else []
    
    # Fast estimation of blasts rank: use direct dependents instead of transitive BFS for the whole repo
    blasts = sorted(len(rev[j]) for j in range(n))
    
    by_path = {b["path"]: (i, b) for i, b in enumerate(buildings)}
    
    res = []
    for p in paths:
        norm_p = p.replace('\\', '/')
        if norm_p not in by_path:
            res.append({
                "index": -1,
                "path": p,
                "score": None,
                "band": "low",
                "components": {"blast": None, "ownership": 0.0, "staleness": 0.0, "complexity": 0.0, "churn": 0.0},
                "raw": {"dependents": None, "bus_factor": None, "stale_days": None, "complexity": 0, "churn": None},
                "blast_known": False,
                "reasons": [f"not analysed: not found in city"],
            })
            continue
            
        i, b = by_path[norm_p]
        lang = b["lang"]
        has_git = "churn" in b and city.get("git") is not None
        
        churn_val = b.get("churn")
        churn_n = _rank(churn_val, churn_list) if has_git and churn_val is not None else 0.0
        
        cx_val = b.get("complexity", 0)
        cx_n = _rank(cx_val, cx_list)
        
        stale_days = b.get("stale_days")
        staleness = min(stale_days / 540.0, 1.0) if has_git and stale_days is not None else 0.0

        bus_factor = b.get("bus_factor")
        owner_share = b.get("owner_share") or 0.0
        ownership = owner_share if bus_factor == 1 else owner_share * 0.5
        
        if lang in IMPORT_RESOLVED_LANGS:
            br_len = len(blast_radius(rev, i)["all"])
            blast = _rank(br_len, blasts)
            blast_known = True
        else:
            br_len = 0
            blast = None
            blast_known = False

        components = {
            "blast": blast,
            "ownership": ownership,
            "staleness": staleness,
            "complexity": cx_n,
            "churn": churn_n,
        }

        score = 0.0
        if blast is None:
            remaining_weight = 1.0 - RISK_WEIGHTS["blast"]
            for k, v in components.items():
                if v is not None:
                    score += (v * RISK_WEIGHTS[k]) / remaining_weight
        else:
            for k, v in components.items():
                score += v * RISK_WEIGHTS[k]

        score = round(score, 4)
        
        if bus_factor == 1 and blast_known and br_len >= 10:
            score = max(score, 0.70)

        # Generate reasons
        contribs = []
        w_sum = 1.0 if blast_known else 1.0 - RISK_WEIGHTS["blast"]
        
        if blast is not None:
            contribs.append(("blast", blast * RISK_WEIGHTS["blast"] / w_sum))
        contribs.append(("ownership", ownership * RISK_WEIGHTS["ownership"] / w_sum))
        contribs.append(("staleness", staleness * RISK_WEIGHTS["staleness"] / w_sum))
        contribs.append(("complexity", cx_n * RISK_WEIGHTS["complexity"] / w_sum))
        contribs.append(("churn", churn_n * RISK_WEIGHTS["churn"] / w_sum))
        
        contribs.sort(key=lambda x: x[1], reverse=True)
        
        reasons = []
        if not has_git:
            reasons.append("not tracked in git or missing history")
            if not blast_known:
                reasons.append(f"blast radius: unknown (no import resolution for {lang})")
            elif br_len > 0:
                pct = int((1 - blast) * 100) if blast < 1.0 else 1
                if pct == 0: pct = 1
                reasons.append(f"{br_len} files depend on it (top {pct}% in this repo)")
            reasons.append(f"complexity {cx_val}, the {n - bisect.bisect_left(cx_list, cx_val)}th highest in this repo")
            
        else:
            for k, contrib in contribs[:3]:
                if contrib == 0:
                    continue
                if k == "blast":
                    pct = max(1, int((1 - blast) * 100))
                    reasons.append(f"{br_len} files depend on it (top {pct}% in this repo)")
                elif k == "ownership":
                    owner_name = "unknown"
                    if b.get("owner") is not None and b.get("owner") < len(git_authors):
                        owner_name = git_authors[b["owner"]]["name"]
                    
                    if bus_factor == 1:
                        reasons.append(f"single author @{owner_name} — nobody else has committed to it")
                    else:
                        pct = int(owner_share * 100)
                        reasons.append(f"dominant author @{owner_name} ({pct}% of changes)")
                elif k == "staleness":
                    if stale_days is not None:
                        months = stale_days // 30
                        if months > 0:
                            reasons.append(f"untouched for {months} months; the context is likely gone")
                        else:
                            reasons.append(f"untouched for {stale_days} days")
                elif k == "complexity":
                    rank_idx = n - bisect.bisect_left(cx_list, cx_val)
                    ord_suffix = "th" if 11 <= rank_idx % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(rank_idx % 10, "th")
                    reasons.append(f"complexity {cx_val}, the {rank_idx}{ord_suffix} highest in this repo")
                elif k == "churn":
                    pct = max(1, int((1 - churn_n) * 100))
                    reasons.append(f"high churn: {churn_val} changes (top {pct}% in this repo)")

        if not blast_known and "blast radius: unknown" not in "".join(reasons):
            reasons.insert(0, f"blast radius: unknown (no import resolution for {lang})")
            
        if not reasons:
            reasons = ["nothing notable"]
            
        # Ensure we return at most 3 reasons
        reasons = reasons[:3]

        res.append({
            "index": i,
            "path": b["path"],
            "score": score,
            "band": band(score),
            "components": components,
            "raw": {
                "dependents": br_len if blast_known else None,
                "bus_factor": bus_factor,
                "stale_days": stale_days,
                "complexity": cx_val,
                "churn": churn_val,
            },
            "blast_known": blast_known,
            "reasons": reasons,
        })
        
    return res

def staged_paths(repo_root: str) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", repo_root, "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, timeout=10, encoding="utf-8"
        )
        if out.returncode != 0:
            return []
        lines = out.stdout.strip().split("\n")
        return [line.replace("\\", "/") for line in lines if line]
    except (OSError, subprocess.SubprocessError):
        return []
