import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from citygen.impact import build_reverse_index, blast_radius, resolve_target

def test_reverse_index_direction():
    # 2 nodes, edge [0, 1, 1] meaning 0 imports 1. So rev[1] should be [0].
    edges = [[0, 1, 1]]
    rev = build_reverse_index(edges, 2)
    assert rev[1] == [0]
    assert rev[0] == []

def test_blast_radius_depths():
    # 0 imports 1, 1 imports 2, 2 imports 3
    # reverse edges: 3 <- 2, 2 <- 1, 1 <- 0
    # edges format: [dependent, dependency, w]
    edges = [[0, 1, 1], [1, 2, 1], [2, 3, 1]]
    rev = build_reverse_index(edges, 4)
    # blast_radius from 3 (the dependency of all)
    res = blast_radius(rev, 3)
    assert res["depths"][1] == [2]
    assert res["depths"][2] == [1]
    assert res["depths"][3] == [0]
    assert res["direct"] == [2]
    assert res["all"] == [0, 1, 2]
    assert not res["truncated"]

def test_blast_radius_cycle_terminates():
    edges = [[0, 1, 1], [1, 0, 1]]
    rev = build_reverse_index(edges, 2)
    res = blast_radius(rev, 0)
    assert res["all"] == [1]

def test_blast_radius_diamond_first_reach_wins():
    # 0 imports 1, 0 imports 2, 1 imports 3, 2 imports 1
    # Actually diamond: 
    # 3 is imported by 1
    # 1 is imported by 0 and 2
    # 2 is imported by 0
    edges = [
        [1, 3, 1],
        [0, 1, 1],
        [2, 1, 1],
        [0, 2, 1],
    ]
    # start = 3
    # depth 1: 1
    # depth 2: 0, 2 (from 1)
    # depth 3: 0 (from 2) -> should be discarded since 0 was reached at depth 2
    rev = build_reverse_index(edges, 4)
    res = blast_radius(rev, 3)
    assert res["depths"][1] == [1]
    assert sorted(res["depths"][2]) == [0, 2]
    assert 3 not in res["depths"]
    # Check that 0 is not in depth 3
    assert 3 not in res["depths"]
    assert res["all"] == [0, 1, 2]

def test_resolve_target_suffix_and_ambiguity():
    city = {
        "buildings": [
            {"path": "foo/bar.py"},
            {"path": "baz/bar.py"},
            {"path": "unique.py"}
        ]
    }
    
    assert resolve_target(city, "unique.py") == 2
    assert resolve_target(city, "foo/bar.py") == 0
    
    try:
        resolve_target(city, "bar.py")
        assert False, "Should raise LookupError"
    except LookupError as e:
        assert "ambiguous" in str(e)

def test_max_depth_truncation_flag():
    edges = [[0, 1, 1], [1, 2, 1], [2, 3, 1]]
    rev = build_reverse_index(edges, 4)
    
    res_trunc = blast_radius(rev, 3, max_depth=1)
    assert res_trunc["truncated"] is True
    assert res_trunc["all"] == [2]
    
    res_full = blast_radius(rev, 3, max_depth=3)
    assert res_full["truncated"] is False

if __name__ == "__main__":
    test_reverse_index_direction()
    test_blast_radius_depths()
    test_blast_radius_cycle_terminates()
    test_blast_radius_diamond_first_reach_wins()
    test_resolve_target_suffix_and_ambiguity()
    test_max_depth_truncation_flag()
    print("All tests passed!")
