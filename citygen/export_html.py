import os
import gzip
import base64
import sys
import re

def export_html(city_json_path: str, out_html_path: str):
    viewer_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'viewer', 'dist')
    index_path = os.path.join(viewer_dist, 'index.html')

    if not os.path.exists(index_path):
        print("Error: viewer/dist/index.html not found. Did you run 'npm run build' in viewer/?", file=sys.stderr)
        sys.exit(1)

    with open(city_json_path, 'rb') as f:
        city_data = f.read()
    
    # Compress and encode
    compressed = gzip.compress(city_data)
    b64 = base64.b64encode(compressed).decode('ascii')
    city_script = f'<script>window.__CHRONOPOLIS_CITY__="{b64}"</script>'

    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Inline JS and CSS
    def replace_css(match):
        href = match.group(1)
        # Handle case where href might be absolute or relative
        if href.startswith('/'):
            href = href[1:]
        css_path = os.path.join(viewer_dist, href)
        if not os.path.exists(css_path):
            return match.group(0)
        with open(css_path, 'r', encoding='utf-8') as cf:
            return f'<style>{cf.read()}</style>'

    def replace_js(match):
        src = match.group(1)
        if src.startswith('/'):
            src = src[1:]
        js_path = os.path.join(viewer_dist, src)
        if not os.path.exists(js_path):
            return match.group(0)
        with open(js_path, 'r', encoding='utf-8') as jf:
            return f'<script type="module">{jf.read()}</script>'

    html = re.sub(r'<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"[^>]*>', replace_css, html)
    html = re.sub(r'<link[^>]*href="([^"]+)"[^>]*rel="stylesheet"[^>]*>', replace_css, html)
    html = re.sub(r'<script[^>]*src="([^"]+)"[^>]*></script>', replace_js, html)
    
    # Remove modulepreload
    html = re.sub(r'<link[^>]*rel="modulepreload"[^>]*>', '', html)

    # Insert city data before the first script or closing body
    if '<script' in html:
        html = html.replace('<script', city_script + '<script', 1)
    else:
        html = html.replace('</body>', city_script + '</body>')

    with open(out_html_path, 'w', encoding='utf-8') as f:
        f.write(html)
        
    size_mb = len(html) / (1024 * 1024)
    print(f"Exported to {out_html_path} ({size_mb:.2f} MB)")
