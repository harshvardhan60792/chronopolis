import argparse
import math
import os
import sys

from citygen.metrics import generic_metrics, curly_metrics, ruby_metrics, go_metrics, js_metrics, python_metrics
from citygen.parsers.treesitter import get_metrics as ts_get_metrics
from citygen.walk import walk_repo, WalkOptions, read_text

def pearson_r(x, y):
    n = len(x)
    if n == 0:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = sum((xi - mean_x)**2 for xi in x)
    den_y = sum((yi - mean_y)**2 for yi in y)
    
    if den_x == 0 or den_y == 0:
        return 0.0
        
    return num / math.sqrt(den_x * den_y)

def get_builtin_metrics(lang, text):
    if lang == "python":
        res = python_metrics(text)
        return res.functions, len(res.classes), res.complexity, len(res.imports)
    elif lang in ("javascript", "typescript"):
        res = js_metrics(text)
        return res.functions, res.classes, res.complexity, len(res.imports)
    elif lang == "go":
        res = go_metrics(text)
        return res.functions, 0, res.complexity, len(res.imports)
    elif lang == "ruby":
        res = ruby_metrics(text)
        return res.functions, res.classes, res.complexity, len(res.imports)
    elif lang in ("java", "csharp", "c_sharp", "cpp", "c", "php", "kotlin", "swift", "rust"):
        res = curly_metrics(lang, text)
        return res.functions, res.classes, res.complexity, len(res.imports)
    return 0, 0, 1, 0

def get_ts_metrics(lang, text):
    res = ts_get_metrics(lang, text)
    if res is None:
        return None
    return res.functions, res.classes, res.complexity, len(res.imports)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--lang", required=True)
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    opts = WalkOptions()
    files = walk_repo(args.repo, opts)
    
    results = []
    
    for f in files:
        if f.lang == args.lang:
            text = read_text(f.abs)
            if not text:
                continue
                
            # Compute builtin
            try:
                os.environ["CITYGEN_PARSER"] = "builtin"
                b_fn, b_cl, b_cx, b_im = get_builtin_metrics(args.lang, text)
            except Exception as e:
                continue
            finally:
                if "CITYGEN_PARSER" in os.environ:
                    del os.environ["CITYGEN_PARSER"]
                
            # Compute TS
            ts_res = get_ts_metrics(args.lang, text)
            if not ts_res:
                continue
            ts_fn, ts_cl, ts_cx, ts_im = ts_res
            
            diff_fn = abs(ts_fn - b_fn) if isinstance(b_fn, int) else abs(ts_fn - len(b_fn))
            
            results.append({
                "path": f.rel,
                "b_fn": b_fn if isinstance(b_fn, int) else len(b_fn),
                "b_cl": b_cl,
                "b_cx": b_cx,
                "b_im": b_im,
                "ts_fn": ts_fn,
                "ts_cl": ts_cl,
                "ts_cx": ts_cx,
                "ts_im": ts_im,
                "divergence": diff_fn + abs(ts_cl - b_cl) + abs(ts_cx - b_cx) + abs(ts_im - b_im)
            })

    if not results:
        print(f"No {args.lang} files found in {args.repo}")
        return

    results.sort(key=lambda r: r["path"])

    mad_fn = sum(abs(r["ts_fn"] - r["b_fn"]) for r in results) / len(results)
    mad_cl = sum(abs(r["ts_cl"] - r["b_cl"]) for r in results) / len(results)
    mad_cx = sum(abs(r["ts_cx"] - r["b_cx"]) for r in results) / len(results)
    mad_im = sum(abs(r["ts_im"] - r["b_im"]) for r in results) / len(results)

    corr_cx = pearson_r([r["b_cx"] for r in results], [r["ts_cx"] for r in results])

    out = []
    out.append(f"# Parser Parity Diff: {args.lang} on {args.repo}")
    out.append("")
    out.append("## Summary")
    out.append(f"- **Files**: {len(results)}")
    out.append(f"- **Complexity correlation**: r = {corr_cx:.4f}")
    out.append(f"- **Mean Absolute Difference (MAD)**:")
    out.append(f"  - Functions: {mad_fn:.2f}")
    out.append(f"  - Classes: {mad_cl:.2f}")
    out.append(f"  - Complexity: {mad_cx:.2f}")
    out.append(f"  - Imports: {mad_im:.2f}")
    out.append("")
    
    out.append("## Top 20 Largest Divergences")
    out.append("| File | fn (ts-b) | cl (ts-b) | cx (ts-b) | im (ts-b) |")
    out.append("|---|---|---|---|---|")
    
    top20 = sorted(results, key=lambda r: r["divergence"], reverse=True)[:20]
    for r in top20:
        d_fn = f"{r['ts_fn']}-{r['b_fn']}"
        d_cl = f"{r['ts_cl']}-{r['b_cl']}"
        d_cx = f"{r['ts_cx']}-{r['b_cx']}"
        d_im = f"{r['ts_im']}-{r['b_im']}"
        out.append(f"| `{r['path']}` | {d_fn} | {d_cl} | {d_cx} | {d_im} |")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
    else:
        print("\n".join(out))


if __name__ == "__main__":
    main()
