import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from citygen.risk import score_all, score_paths, staged_paths, band

def test_bus_factor_one_with_dependents_is_high():
    # A file with bus_factor == 1 and >=10 dependents always lands in high.
    city = {
        "buildings": [
            {
                "path": "f1.py", "lang": "python", "bus_factor": 1,
                "owner_share": 1.0, "stale_days": 10, "complexity": 10,
                "churn": 5
            }
        ],
        "edges": {
            "import": [[i, 0, 1] for i in range(1, 12)]
        },
        "git": {"authors": [{"name": "A", "email": "a@a"}]}
    }
    # Add dummy files to ensure it has 10 dependents
    for i in range(1, 12):
        city["buildings"].append({
            "path": f"f{i+1}.py", "lang": "python", "bus_factor": 2,
            "owner_share": 0.5, "stale_days": 0, "complexity": 1,
            "churn": 1
        })
    scored = score_all(city)
    assert scored[0]["band"] == "high"

def test_unknown_blast_is_none_not_zero():
    # a Go-language fixture building; assert components["blast"] is None and blast_known is False.
    city = {
        "buildings": [
            {
                "path": "main.go", "lang": "go", "bus_factor": 1,
                "owner_share": 1.0, "stale_days": 10, "complexity": 10,
                "churn": 5
            }
        ],
        "git": {"authors": [{"name": "A", "email": "a@a"}]}
    }
    scored = score_all(city)
    assert scored[0]["components"]["blast"] is None
    assert scored[0]["blast_known"] is False

def test_weight_redistribution_sums_to_one():
    # with blast unknown, the remaining weights must still sum to 1.0 (± 1e-9).
    # This means if a Go file is the worst in every metric, it scores exactly 1.0
    city = {
        "buildings": [
            {
                "path": "worst.go", "lang": "go", "bus_factor": 1,
                "owner_share": 1.0, "stale_days": 540, "complexity": 100,
                "churn": 100, "owner": 0
            }
        ],
        "git": {"authors": [{"name": "A", "email": "a@a"}]}
    }
    # We need a couple of files so rank can be > 0 (well, if it's the only one, rank is 0.0)
    # Actually rank() logic returns bisect_left / len.
    # So if there's only 1 file, bisect_left(lst, val) is 0, rank is 0.0.
    # Let's add worse files so we can get rank 1.0
    for i in range(1, 10):
        city["buildings"].append({
            "path": f"f{i}.go", "lang": "go", "bus_factor": 2,
            "owner_share": 0.5, "stale_days": 0, "complexity": 1,
            "churn": 1, "owner": 0
        })
    # Since worst.go has strictly higher values, its rank will be 9/10 = 0.9.
    # To get exactly 1.0 we need to adjust, but wait, redistribution test:
    scored = score_all(city)
    s = scored[0]
    
    comp = s["components"]
    assert comp["blast"] is None
    
    # Calculate score manually to verify weights
    c = comp
    weight_sum = sum([0.25, 0.15, 0.15, 0.10])
    expected = (c["ownership"] * 0.25 + c["staleness"] * 0.15 + c["complexity"] * 0.15 + c["churn"] * 0.10) / weight_sum
    assert abs(s["score"] - round(expected, 4)) <= 1e-4

def test_no_git_city_does_not_raise():
    # city with git: null
    city = {
        "buildings": [
            {
                "path": "f1.py", "lang": "python", "complexity": 10
            }
        ],
        "git": None
    }
    scored = score_all(city)
    assert len(scored) == 1
    assert scored[0]["score"] is not None

def test_band_thresholds():
    assert band(0.399) == "low"
    assert band(0.40) == "moderate"
    assert band(0.699) == "moderate"
    assert band(0.70) == "high"

def test_score_paths_preserves_order_and_reports_missing():
    city = {
        "buildings": [
            {"path": "a.py", "lang": "python", "complexity": 1},
            {"path": "b.py", "lang": "python", "complexity": 2}
        ]
    }
    paths = ["b.py", "missing.py", "a.py"]
    res = score_paths(city, paths)
    assert len(res) == 3
    assert res[0]["path"] == "b.py"
    assert res[1]["path"] == "missing.py"
    assert res[1]["score"] is None
    assert "not analysed" in res[1]["reasons"][0]
    assert res[2]["path"] == "a.py"

def test_score_paths_matches_score_all():
    # Regression test: score_paths used to reimplement scoring with a
    # different blast-radius reference distribution (direct dependents,
    # not score_all's transitive BFS count) and silently dropped its own
    # `weights` argument - the same file could score differently
    # depending on which entry point scored it. A 4-file import chain
    # (f0 -> f1 -> f2 -> f3) makes direct-dependents (1) and transitive
    # blast radius (3, for f3) actually diverge, so this would have
    # caught the bug.
    city = {
        "buildings": [
            {"path": f"f{i}.py", "lang": "python", "complexity": i + 1,
             "bus_factor": 2, "owner_share": 0.5, "stale_days": i * 10,
             "churn": i + 1}
            for i in range(4)
        ],
        "edges": {"import": [[0, 1, 1], [1, 2, 1], [2, 3, 1]]},
        "git": {"authors": [{"name": "A", "email": "a@a"}]},
    }
    all_paths = [b["path"] for b in city["buildings"]]

    all_scored = {s["path"]: s for s in score_all(city)}
    paths_scored = {s["path"]: s for s in score_paths(city, all_paths)}

    for path in all_paths:
        assert paths_scored[path]["score"] == all_scored[path]["score"], path
        assert paths_scored[path]["components"] == all_scored[path]["components"], path
        assert paths_scored[path]["reasons"] == all_scored[path]["reasons"], path

    # weights must actually be honoured, not silently dropped
    custom_weights = {"blast": 0.0, "ownership": 0.0, "staleness": 0.0, "complexity": 1.0, "churn": 0.0}
    all_custom = {s["path"]: s for s in score_all(city, custom_weights)}
    paths_custom = {s["path"]: s for s in score_paths(city, all_paths, custom_weights)}
    for path in all_paths:
        assert paths_custom[path]["score"] == all_custom[path]["score"], path

def test_staged_paths_empty_when_no_git():
    # In a non-git dir, it should return []
    # We can mock subprocess or run it in a temp dir
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        assert staged_paths(td) == []

if __name__ == "__main__":
    test_bus_factor_one_with_dependents_is_high()
    test_unknown_blast_is_none_not_zero()
    test_weight_redistribution_sums_to_one()
    test_no_git_city_does_not_raise()
    test_band_thresholds()
    test_score_paths_preserves_order_and_reports_missing()
    test_staged_paths_empty_when_no_git()
    print("All tests passed.")
