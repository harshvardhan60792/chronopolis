import os
import gzip
import base64
import sys
import re


def find_viewer_dist() -> str:
    """Locate the built viewer (index.html + assets/).

    `pip install git+https://...` ships the citygen Python package only -
    viewer/ is a separate JS project, a sibling of citygen/ in this repo's
    source tree, not part of the installed package - so the default
    relative-to-__file__ lookup only works when citygen is run from within
    an actual chronopolis source checkout (dev mode, or this repo's own
    CI). CHRONOPOLIS_VIEWER_DIST lets any other environment (a foreign
    repo's CI that built the viewer as a separate step, for example) point
    at wherever it actually put the built assets.
    """
    override = os.environ.get("CHRONOPOLIS_VIEWER_DIST")
    if override:
        return override
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'viewer', 'dist')


def export_html(city_json_path: str, out_html_path: str):
    viewer_dist = find_viewer_dist()
    index_path = os.path.join(viewer_dist, 'index.html')

    if not os.path.exists(index_path):
        print(f"Error: {index_path} not found. Did you run 'npm run build' in viewer/? "
              f"(or set CHRONOPOLIS_VIEWER_DIST to point at a built viewer)", file=sys.stderr)
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
