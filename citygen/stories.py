"""Generates deterministic stories for the cinematic tour (T14)."""

def generate_stories(buildings: list[dict], tree: list[dict], stats: dict, git_stats: dict | None, history: list[dict] | None) -> list[dict]:
    stories = []
    
    def pct(part, total):
        return round(100 * part / total) if total else 0

    active = [b for b in buildings if not b.get("deleted")]
    if not active:
        return []

    # 1. god_file
    god_files = [b for b in active if b.get("in_deg", 0) >= 5]
    if god_files:
        best = max(god_files, key=lambda b: b["in_deg"])
        stories.append({
            "kind": "god_file",
            "building_index": buildings.index(best),
            "score": best["in_deg"],
            "text": f"{best['name']} is imported by {best['in_deg']} files and changed in {best.get('commits', 0)} commits. Everything depends on it."
        })

    # 2. hotspot
    churns = sorted(b.get("churn", 0) for b in active)
    cxs = sorted(b.get("complexity", 0) for b in active)
    c80 = churns[int(len(churns) * 0.8)] if churns else 0
    cx80 = cxs[int(len(cxs) * 0.8)] if cxs else 0
    
    hotspots = [b for b in active if b.get("churn", 0) > c80 and b.get("complexity", 0) > cx80]
    if hotspots:
        best = max(hotspots, key=lambda b: b.get("health", 0))
        stories.append({
            "kind": "hotspot",
            "building_index": buildings.index(best),
            "score": best.get("health", 0),
            "text": f"{best['name']} is the hardest thing here to change safely: complexity {best.get('complexity', 0)}, {best.get('commits', 0)} commits, {best.get('churn', 0)} lines churned."
        })

    # 3. hidden_coupling
    top_hidden = stats.get("top_hidden_coupling", [])
    if top_hidden:
        i, j, strength, n = top_hidden[0]
        a = buildings[i]
        b = buildings[j]
        target_idx = i if a.get("complexity", 0) > b.get("complexity", 0) else j
        stories.append({
            "kind": "hidden_coupling",
            "building_index": target_idx,
            "score": strength,
            "text": f"{a['name']} and {b['name']} changed together in {n} commits but never import each other."
        })

    # 4. ruin
    ruins = [b for b in active if (b.get("stale_days") or 0) > 365 and b.get("in_deg", 0) == 0]
    if ruins:
        best = max(ruins, key=lambda b: b.get("loc", 0))
        years = round(best["stale_days"] / 365.25, 1)
        if years == int(years): years = int(years)
        stories.append({
            "kind": "ruin",
            "building_index": buildings.index(best),
            "score": best.get("loc", 0),
            "text": f"{best['name']} ({best.get('loc', 0)} lines) has not been touched in {years} years and nothing imports it."
        })

    # 5. bus_factor
    bus = [b for b in active if b.get("bus_factor", 0) == 1 and b.get("commits", 0) >= 10]
    if bus and git_stats and "authors" in git_stats:
        best = max(bus, key=lambda b: b.get("loc", 0))
        owner_idx = best.get("owner")
        if owner_idx is not None and 0 <= owner_idx < len(git_stats["authors"]):
            owner_name = git_stats["authors"][owner_idx]["name"]
            share = round(best.get("owner_share", 0) * 100)
            stories.append({
                "kind": "bus_factor",
                "building_index": buildings.index(best),
                "score": best.get("loc", 0),
                "text": f"{owner_name} wrote {share}% of {best['name']}. If they leave, this block goes dark."
            })

    # 6. fastest_growing
    if history and git_stats:
        first = git_stats.get("first_commit_ts")
        last = git_stats.get("last_commit_ts")
        if first and last and last > first:
            window = last - first
            quarter = last - (window / 4)
            growth = {}
            for c in history:
                if c["ts"] >= quarter:
                    for path, adds, dels, _r in c["files"]:
                        growth[path] = growth.get(path, 0) + adds - dels
            
            best_growth = 0
            best_path = None
            for path, delta in growth.items():
                if delta > best_growth:
                    best_growth = delta
                    best_path = path
            
            if best_path:
                try:
                    idx = next(i for i, b in enumerate(buildings) if b["path"] == best_path and not b.get("deleted"))
                    best = buildings[idx]
                    days = max(1, round((window / 4) / 86400))
                    unit = "day" if days == 1 else "days"
                    stories.append({
                        "kind": "fastest_growing",
                        "building_index": idx,
                        "score": best_growth,
                        "text": f"{best['name']} grew {best_growth} lines in the last {days} {unit} — the fastest growth in the repo."
                    })
                except StopIteration:
                    pass

    # 7. biggest_district
    if tree:
        total_cx = stats.get("complexity", 0)
        if total_cx > 0:
            districts = [d for d in tree if d["depth"] == 1 and d["complexity"] > 0]
            if districts:
                best = max(districts, key=lambda d: d["complexity"])
                share = pct(best["complexity"], total_cx)
                
                # find a target building in this district
                in_dist = [b for b in active if b["path"].startswith(best["path"] + "/")]
                if in_dist:
                    target_b = max(in_dist, key=lambda b: b.get("complexity", 0))
                    stories.append({
                        "kind": "biggest_district",
                        "building_index": buildings.index(target_b),
                        "score": best["complexity"],
                        "text": f"{best['name']} is {share}% of the repo's complexity in {best['files']} files."
                    })

    # Order of impact
    return stories
