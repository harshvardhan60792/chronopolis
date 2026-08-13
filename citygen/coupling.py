"""Co-change coupling calculation."""

import itertools
from collections import Counter
import math

def calculate_cochange(commits: list[list[int]], buildings: list[dict], import_edges: list[list], min_cochange: int = 3, max_cochange: int = 4000) -> tuple[list[list], int, int, list[list]]:
    pair_counts = Counter()
    for files in commits:
        if len(files) < 2:
            continue
        for i, j in itertools.combinations(sorted(set(files)), 2):
            pair_counts[(i, j)] += 1
            
    cochange_scored = []
    
    for (i, j), c_ij in pair_counts.items():
        if c_ij < min_cochange:
            continue
            
        commits_i = buildings[i].get("commits", 0)
        commits_j = buildings[j].get("commits", 0)
        
        denom = commits_i + commits_j - c_ij
        if denom <= 0:
            continue
            
        strength = c_ij / denom
        if strength >= 0.12:
            score = strength * math.log(1 + c_ij)
            cochange_scored.append((score, i, j, c_ij, round(strength, 3)))
            
    cochange_scored.sort(reverse=True, key=lambda x: x[0])
    cochange_scored = cochange_scored[:max_cochange]
    
    import_pairs = set()
    for a, b, _w in import_edges:
        import_pairs.add((min(a, b), max(a, b)))

    # "Hidden coupling" means: they change together but do NOT import each
    # other. We can only make that claim about files whose imports were
    # actually parsed. Two JSON templates have no import graph at all, so
    # calling them hidden coupling would be a false statement - and T14 turns
    # these into English sentences.
    analyzable = {i for i, b in enumerate(buildings) if b.get("parsed")}

    hidden_candidates = []
    cochange_out = []

    for score, i, j, c_ij, strength in cochange_scored:
        cochange_out.append([i, j, c_ij, strength])
        if i in analyzable and j in analyzable and (i, j) not in import_pairs:
            hidden_candidates.append([i, j, strength])
            
    cochange_out.sort(key=lambda x: (x[0], x[1]))
    
    top_hidden = hidden_candidates[:10]
    
    return cochange_out, len(cochange_out), len(hidden_candidates), top_hidden
