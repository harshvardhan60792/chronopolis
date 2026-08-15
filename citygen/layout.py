"""Layout engine for Chronopolis: stable temporal squarified treemap."""

import math
from typing import Callable, Any

MIN_HEIGHT = 4.0
MAX_HEIGHT = 95.0


def building_height(complexity: float, sloc: float,
                    height_scale: float = 2.6) -> float:
    """Height is complexity, but a file with no branching is not a flat plate -
    a 400-line config or document is still a building. Taking the larger of
    complexity and a floors-from-length proxy keeps non-code files honest and
    stops the skyline collapsing into a tiled floor on doc-heavy repos.

    Exponent 0.75 rather than 0.65: the flatter curve buried the median
    building at ~4 units against an ~8 unit footprint, which renders as tiled
    floor rather than a skyline.

    Shared with the snapshot builder so a building's height at 'now' on the
    timeline is identical to its height in the static layout.
    """
    floors = (sloc or 0) / 18.0
    metric = max(complexity or 1, floors, 1.0)
    return max(MIN_HEIGHT, min(MAX_HEIGHT, height_scale * (metric ** 0.75)))

def generate_layout(buildings: list[dict], tree: list[dict], 
                    world_size: float = 400.0, 
                    street_width: float = 2.0, 
                    building_gap: float = 0.6, 
                    height_scale: float = 2.6,
                    cochange_edges: list = None,
                    import_edges: list = None,
                    traffic_source: str = "cochange",
                    weight_fn: Callable[[dict], float] = None) -> dict:
    
    if weight_fn is None:
        weight_fn = lambda b: max(1.0, math.sqrt(b.get("loc", 0) if b.get("loc") is not None else 0))
        
    nodes = {}
    
    for i, b in enumerate(buildings):
        path = b["path"]
        nodes[path] = {
            "type": "file",
            "path": path,
            "idx": i,
            "weight": weight_fn(b),
            "children": [],
            "parent": b["dir"] if b["dir"] else "/",
        }
        
    for d in tree:
        path = d["path"]
        nodes[path] = {
            "type": "dir",
            "path": path,
            "depth": d["depth"],
            "weight": 0.0,
            "children": [],
            "parent": d["parent"] if d["parent"] else "/",
        }
        
    nodes["/"] = {
        "type": "dir",
        "path": "/",
        "depth": 0,
        "weight": 0.0,
        "children": [],
        "parent": None,
    }
    
    for p, node in nodes.items():
        if p == "/":
            continue
        parent = node["parent"]
        if parent not in nodes:
            parent = "/"
        nodes[parent]["children"].append(node)
        
    def calc_weight(node):
        if node["type"] == "dir":
            w = sum(calc_weight(c) for c in node["children"])
            node["weight"] = w
            return w
        return node["weight"]
        
    calc_weight(nodes["/"])
    
    districts = []
    plots = [None] * len(buildings)
    
    def layout_node(node, x, z, w, d):
        if node["type"] == "file":
            b = buildings[node["idx"]]
            h = building_height(b.get("complexity", 1),
                                b.get("sloc") or b.get("loc") or 0,
                                height_scale)

            # Inset for the gap between neighbours, but never take more than a
            # quarter of the smaller side: a fixed inset on a thin cell turns a
            # 3.0 x 1.4 lot into 1.8 x 0.2, which renders as a wall, not a
            # building.
            gap = min(building_gap, 0.25 * min(w, d))
            ix = x + gap
            iz = z + gap
            iw = max(0.1, w - 2 * gap)
            id_ = max(0.1, d - 2 * gap)
            
            plots[node["idx"]] = {
                "x": round(ix, 3),
                "z": round(iz, 3),
                "w": round(iw, 3),
                "d": round(id_, 3),
                "h": round(h, 3),
            }
            return

        if node["path"] != "/":
            districts.append({
                "path": node["path"],
                "x": round(x, 3),
                "z": round(z, 3),
                "w": round(w, 3),
                "d": round(d, 3),
                "depth": node.get("depth", 0),
                "color": node.get("depth", 0)
            })
            
            x += street_width
            z += street_width
            w = max(1.2, w - 2 * street_width)
            d = max(1.2, d - 2 * street_width)
            
        children = [c for c in node["children"] if c["weight"] > 0]
        children.sort(key=lambda c: (-c["weight"], c["path"]))
        
        if not children:
            return
            
        total_w = sum(c["weight"] for c in children)
        area = w * d
        
        for c in children:
            c["area"] = (c["weight"] / total_w) * area if total_w > 0 else 0
            
        squarify(children, [], w, d, x, z)

    def worst_ratio(row, side):
        if not row or side == 0:
            return float('inf')
        s = sum(c["area"] for c in row)
        if s == 0:
            return float('inf')
        row_max = max(c["area"] for c in row)
        row_min = min(c["area"] for c in row)
        side2 = side * side
        s2 = s * s
        return max(side2 * row_max / s2, s2 / (side2 * row_min))

    def layout_row(row, w, d, x, z):
        s = sum(c["area"] for c in row)
        if w <= d:
            h = s / w if w > 0 else 0
            cx = x
            for c in row:
                cw = c["area"] / h if h > 0 else 0
                layout_node(c, cx, z, cw, h)
                cx += cw
            return x, z + h, w, d - h
        else:
            wid = s / d if d > 0 else 0
            cz = z
            for c in row:
                ch = c["area"] / wid if wid > 0 else 0
                layout_node(c, x, cz, wid, ch)
                cz += ch
            return x + wid, z, w - wid, d

    def squarify(children, row, w, d, x, z):
        """Iterative on purpose: the recursive form recursed once per child and
        blew the interpreter stack on directories with >1000 files."""
        i = 0
        row = list(row)
        n = len(children)
        while i < n:
            c = children[i]
            side = min(w, d)
            if not row:
                row = [c]
                i += 1
                continue
            if worst_ratio(row + [c], side) <= worst_ratio(row, side):
                row.append(c)
                i += 1
            else:
                x, z, w, d = layout_row(row, w, d, x, z)
                row = []
        if row:
            layout_row(row, w, d, x, z)

    layout_node(nodes["/"], 0, 0, world_size, world_size)
    
    roads = []
    traffic_edges = []
    if traffic_source == "cochange" and cochange_edges:
        traffic_edges = cochange_edges
    elif import_edges:
        traffic_edges = import_edges
        
    for edge in traffic_edges:
        a_idx, b_idx = edge[0], edge[1]
        pa = plots[a_idx]
        pb = plots[b_idx]
        if not pa or not pb:
            continue
            
        ax, az = pa["x"] + pa["w"]/2, pa["z"] + pa["d"]/2
        bx, bz = pb["x"] + pb["w"]/2, pb["z"] + pb["d"]/2
        
        h_max = max(pa["h"], pb["h"])
        ctrl_y = round(h_max * 1.4, 3)
        
        pts = []
        for t_step in range(11):
            t = t_step / 10.0
            mt = 1 - t
            cx = (ax + bx) / 2
            cz = (az + bz) / 2
            
            px = mt*mt*ax + 2*mt*t*cx + t*t*bx
            py = mt*mt*0 + 2*mt*t*ctrl_y + t*t*0
            pz = mt*mt*az + 2*mt*t*cz + t*t*bz
            pts.append([round(px, 3), round(py, 3), round(pz, 3)])
            
        roads.append({
            "a": a_idx,
            "b": b_idx,
            "pts": pts,
            "kind": traffic_source
        })

    return {
        "world": {"width": world_size, "depth": world_size},
        "districts": districts,
        "plots": plots,
        "roads": roads,
        # The viewer needs this to know where the carriageway is: district
        # rectangles tile with no gap between them, so the street is the
        # street_width margin *inside* each district, not a gap outside it.
        "street_width": street_width,
        "height_formula": f"h = {height_scale} * max(complexity, sloc/18) ** 0.75",
        "road_style": "arcs"
    }

