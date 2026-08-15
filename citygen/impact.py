import collections
import os

def build_reverse_index(import_edges: list[list], n: int) -> list[list[int]]:
    """rev[i] = sorted list of building indices that import building i."""
    rev = [[] for _ in range(n)]
    for a, b, w in import_edges:
        rev[b].append(a)
    for i in range(n):
        rev[i].sort()
    return rev

def build_forward_index(import_edges: list[list], n: int) -> list[list[int]]:
    """fwd[i] = sorted list of building indices that building i imports."""
    fwd = [[] for _ in range(n)]
    for a, b, w in import_edges:
        fwd[a].append(b)
    for i in range(n):
        fwd[i].sort()
    return fwd

def blast_radius(rev: list[list[int]], start: int,
                 max_depth: int | None = None) -> dict:
    """Breadth-first over reverse edges from `start`."""
    depths = {}
    visited = {start}
    
    queue = collections.deque([(start, 0)])
    truncated = False
    
    while queue:
        node, current_depth = queue.popleft()
        
        if max_depth is not None and current_depth >= max_depth:
            if rev[node]:
                # There are more dependents we aren't exploring
                truncated = True
            continue
            
        for dependent in rev[node]:
            if dependent not in visited:
                visited.add(dependent)
                next_depth = current_depth + 1
                if next_depth not in depths:
                    depths[next_depth] = []
                depths[next_depth].append(dependent)
                queue.append((dependent, next_depth))

    for d in depths:
        depths[d].sort()
        
    all_deps = []
    for d in depths.values():
        all_deps.extend(d)
    all_deps.sort()
    
    return {
        "depths": depths,
        "all": all_deps,
        "direct": depths.get(1, []),
        "truncated": truncated
    }

def resolve_target(city: dict, query: str) -> int:
    """Map a user-typed path to a building index."""
    buildings = city.get("buildings", [])
    
    # 1. exact match
    for i, b in enumerate(buildings):
        if b["path"] == query:
            return i
            
    # 2. exact match after normalising
    norm_query = query.replace("\\", "/")
    if norm_query.startswith("./"):
        norm_query = norm_query[2:]
        
    for i, b in enumerate(buildings):
        if b["path"] == norm_query:
            return i
            
    # 3. unique suffix match
    suffix_matches = []
    for i, b in enumerate(buildings):
        if b["path"].endswith("/" + norm_query) or b["path"] == norm_query:
            suffix_matches.append(i)
            
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    elif len(suffix_matches) > 1:
        paths = [buildings[i]["path"] for i in suffix_matches[:8]]
        raise LookupError("ambiguous match for '{}':\n  {}".format(
            query, "\n  ".join(paths)))
            
    # 4. unique basename match
    base_query = os.path.basename(norm_query)
    base_matches = []
    for i, b in enumerate(buildings):
        if os.path.basename(b["path"]) == base_query:
            base_matches.append(i)
            
    if len(base_matches) == 1:
        return base_matches[0]
    elif len(base_matches) > 1:
        paths = [buildings[i]["path"] for i in base_matches[:8]]
        raise LookupError("ambiguous match for '{}':\n  {}".format(
            query, "\n  ".join(paths)))
            
    # No matches found, find nearest basename matches
    import difflib
    basenames = {os.path.basename(b["path"]): b["path"] for b in buildings}
    closest = difflib.get_close_matches(base_query, list(basenames.keys()), n=8)
    if closest:
        paths = [basenames[c] for c in closest]
        raise LookupError("no file matches '{}'. nearest matches:\n  {}".format(
            query, "\n  ".join(paths)))
    
    raise LookupError(f"no file matches '{query}'")
