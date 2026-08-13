"""Generate an SVG preview of city.json layout."""

import json
import sys
import os

def render_svg(city_path, out_path):
    with open(city_path, "r", encoding="utf-8") as f:
        city = json.load(f)
        
    layout = city["layout"]
    world = layout["world"]
    w, d = world["width"], world["depth"]
    
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {d}" width="1000" height="1000">',
        f'<rect width="{w}" height="{d}" fill="#222"/>'
    ]
    
    colors = ["#333", "#444", "#555", "#666", "#777"]
    for dist in layout.get("districts", []):
        c = colors[dist["depth"] % len(colors)]
        svg.append(f'<rect x="{dist["x"]}" y="{dist["z"]}" width="{dist["w"]}" height="{dist["d"]}" fill="{c}" stroke="#000" stroke-width="1" />')
        
    for p in layout.get("plots", []):
        if p:
            svg.append(f'<rect x="{p["x"]}" y="{p["z"]}" width="{p["w"]}" height="{p["d"]}" fill="#999" stroke="#fff" stroke-width="0.5" />')
            
    for r in layout.get("roads", []):
        pts = r["pts"]
        if pts:
            d_path = f"M {pts[0][0]} {pts[0][2]}"
            for pt in pts[1:]:
                d_path += f" L {pt[0]} {pt[2]}"
            svg.append(f'<path d="{d_path}" fill="none" stroke="#f00" stroke-width="0.5" opacity="0.8" />')
            
    svg.append('</svg>')
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: preview_layout.py <city.json>")
        sys.exit(1)
        
    city_path = sys.argv[1]
    out_path = os.path.join(os.path.dirname(city_path), "layout.svg")
    render_svg(city_path, out_path)
    print(f"Wrote {out_path}")
