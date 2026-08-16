import json
import pytest
from citygen.report import build_report, render_markdown

def test_silent_when_no_high_risk():
    city = {
        "git": {"authors": []},
        "buildings": [
            {"path": "a.py", "lang": "python", "complexity": 1},
            {"path": "b.py", "lang": "python", "complexity": 2},
        ],
        "edges": {"import": []}
    }
    # These will have very low scores because they have no dependents, ownership etc.
    report = build_report(city, ["a.py"])
    assert report.get("silent") is True
    assert render_markdown(report, city) == ""

def test_blast_radius_is_union():
    city = {
        "git": {"authors": [{"email": "a@x.com", "name": "A"}]},
        "buildings": [
            {"path": "lib1.py", "lang": "python", "complexity": 100, "bus_factor": 1, "authors": [[0, 10]], "owner_share": 1.0, "churn": 100, "stale_days": 1000},
            {"path": "lib2.py", "lang": "python", "complexity": 100, "bus_factor": 1, "authors": [[0, 10]], "owner_share": 1.0, "churn": 100, "stale_days": 1000},
        ] + [{"path": f"app{i}.py", "lang": "python", "complexity": 10, "churn": 1} for i in range(15)],
        "edges": {
            "import": [[i + 2, 0, 1] for i in range(15)] + [[i + 2, 1, 1] for i in range(15)]
        }
    }
    report = build_report(city, ["lib1.py", "lib2.py"])
    assert not report.get("silent")
    
    # blast radius: lib1 has [2..16], lib2 has [2..16]. Union is 15.
    # The changed files themselves are subtracted from the union, so it's just the 15 app.py files
    assert report["blast_total"] == 15
    assert report["blast_known"] is True

def test_unanalysed_files():
    city = {
        "git": {"authors": []},
        "buildings": [],
        "edges": {"import": []}
    }
    report = build_report(city, ["unknown.py"])
    assert report["unanalysed"] == ["unknown.py (not in city)"]
    assert report.get("silent") is True

def test_author_exclusion():
    city = {
        "git": {"authors": [
            {"email": "pr_author@x.com", "name": "PR Author"},
            {"email": "other@x.com", "name": "Other"}
        ]},
        "buildings": [
            {
                "path": "high_risk.py", 
                "lang": "python", 
                "complexity": 500, 
                "bus_factor": 1, 
                "authors": [[0, 100]], # author 0 is pr_author
                "owner_share": 1.0,
                "stale_days": 1000,
                "churn": 100
            }
        ] + [{"path": f"app{i}.py", "lang": "python", "complexity": 10, "churn": 1} for i in range(15)],
        "edges": {
            "import": [[i + 1, 0, 1] for i in range(15)]
        }
    }
    
    # 1. No exclusion
    report1 = build_report(city, ["high_risk.py"])
    assert not report1["silent"]
    md1 = render_markdown(report1, city)
    assert "Suggested reviewer: **PR Author <pr_author@x.com>**" in md1
    
    # 2. With exclusion
    report2 = build_report(city, ["high_risk.py"], frozenset(["pr_author@x.com"]))
    assert not report2["silent"]
    assert report2["all_authors_excluded"] is True
    md2 = render_markdown(report2, city)
    assert "only the PR's own author has ever committed to these files." in md2

def test_size_limit():
    city = {
        "git": {"authors": [{"email": "a@x.com"}]},
        "buildings": [
            {
                "path": f"f{i}.py", "lang": "python", 
                "complexity": 1000, "bus_factor": 1, 
                "authors": [[0, 1]], "owner_share": 1.0,
                "churn": 100, "stale_days": 1000
            } for i in range(5000)
        ],
        "edges": {"import": [[i, 0, 1] for i in range(1, 15)]}
    }
    
    # 5000 changed files, some will be flagged, some moderate
    # The flag limit is 5, so it should easily fit under 65,536 chars
    report = build_report(city, [f"f{i}.py" for i in range(5000)])
    md = render_markdown(report, city)
    assert len(md) < 65536
    
def test_deterministic_markdown():
    city = {
        "git": {"authors": [{"email": "a@x.com", "name": "A"}]},
        "buildings": [
            {"path": "lib1.py", "lang": "python", "complexity": 100, "bus_factor": 1, "authors": [[0, 10]], "owner_share": 1.0, "churn": 100, "stale_days": 1000},
        ],
        "edges": {"import": []}
    }
    report1 = build_report(city, ["lib1.py"])
    report2 = build_report(city, ["lib1.py"])
    assert render_markdown(report1, city) == render_markdown(report2, city)
