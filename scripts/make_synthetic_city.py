import json
import argparse
import sys
import math
from pathlib import Path

# Add the project root to sys.path so we can import citygen
sys.path.append(str(Path(__file__).resolve().parent.parent))
from citygen.layout import generate_layout

def make_synthetic_city(target_buildings: int, out_path: str):
    # Load the template city
    with open("flask.city.json") as f:
        data = json.load(f)
        
    orig_tree = data["tree"]
    orig_builds = data["buildings"]
    
    orig_count = len(orig_builds)
    if orig_count == 0:
        print("Template city has no buildings!")
        sys.exit(1)
        
    N = math.ceil(target_buildings / orig_count)
    
    new_tree = []
    new_builds = []
    
    for i in range(N):
        root_node = {
            'id': f"{i}_root",
            'path': f"{i}_root",
            'name': f"replica_{i}",
            'parent': "",
            'depth': 1,
            'files': 0,
            'loc': 0,
            'complexity': 0,
            'type': 'dir' # ensure type is set if needed
        }
        new_tree.append(root_node)
        
        for node in orig_tree:
            n = dict(node)
            n['id'] = f"{i}_{node['id']}"
            n['path'] = f"{i}/{node['path']}"
            n['parent'] = f"{i}_root" if n['parent'] == "" else f"{i}_{node['parent']}"
            n['depth'] = node.get('depth', 1) + 1
            new_tree.append(n)
            
        for b in orig_builds:
            if len(new_builds) >= target_buildings:
                break
                
            nb = dict(b)
            nb['id'] = f"{i}_{b['id']}"
            nb['path'] = f"{i}/{b['path']}"
            nb['dir'] = f"{i}_root" if nb['dir'] == "" else f"{i}_{nb['dir']}"
            new_builds.append(nb)
            
        if len(new_builds) >= target_buildings:
            break
            
    print(f"Synthesized {len(new_builds)} buildings from {orig_count} original buildings (N={N})")
    
    # We must also clean up the tree, in case we cut off some buildings.
    # Actually, extra tree nodes for buildings we skipped won't hurt much,
    # but let's just leave them.
    
    print("Calculating layout...")
    layout = generate_layout(new_builds, new_tree)
    
    new_data = dict(data)
    new_data["tree"] = new_tree
    new_data["buildings"] = new_builds
    new_data["layout"] = layout
    new_data["stats"]["files"] = len(new_builds)
    new_data["stats"]["dirs"] = len(new_tree)
    # The instructions say: "Label every result as synthetic."
    # We can put it in repo.name maybe?
    new_data["repo"]["name"] = f"synthetic-{target_buildings}"
    
    print(f"Writing to {out_path} ...")
    with open(out_path, "w") as f:
        json.dump(new_data, f)
    print("Done.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate synthetic city json')
    parser.add_argument('--buildings', type=int, required=True, help='Target number of buildings')
    parser.add_argument('-o', '--output', type=str, required=True, help='Output JSON path')
    args = parser.parse_args()
    
    make_synthetic_city(args.buildings, args.output)
