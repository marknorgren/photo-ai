# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""Render an .excalidraw JSON file to PNG locally via headless Chromium."""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML_TEMPLATE = """<!DOCTYPE html>
<html><head>
<style>body {{ margin:0; background:#fff; overflow:hidden; }}</style>
</head><body>
<div id="root" style="width:{width}px;height:{height}px"></div>
<script type="module">
import {{ exportToSvg }} from "https://esm.sh/@excalidraw/excalidraw?bundle";

const elements = {elements_json};
const appState = {{ viewBackgroundColor: "#ffffff", theme: "light" }};

try {{
  const svg = await exportToSvg({{
    elements: elements,
    appState: appState,
    files: null,
  }});
  svg.setAttribute("width", "{width}");
  svg.setAttribute("height", "{height}");
  document.getElementById("root").appendChild(svg);
  document.title = "RENDER_DONE";
}} catch(e) {{
  document.title = "ERROR:" + e.message;
}}
</script></body></html>"""


def render(input_path: str, output_path: str, width: int = 800, height: int = 600) -> None:
    data = json.loads(Path(input_path).read_text())
    elements = data.get("elements", data) if isinstance(data, dict) else data

    html = HTML_TEMPLATE.format(
        elements_json=json.dumps(elements),
        width=width,
        height=height,
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.on("console", lambda msg: print(f"  console.{msg.type}: {msg.text}"))
        page.set_content(html, wait_until="networkidle")
        page.wait_for_function(
            "document.title.startsWith('RENDER_DONE') || document.title.startsWith('ERROR:')",
            timeout=30000,
        )
        title = page.title()
        if title.startswith("ERROR:"):
            print(f"Render error: {title}")
            sys.exit(1)
        page.screenshot(path=output_path)
        browser.close()

    print(f"Rendered → {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run render_excalidraw.py INPUT.json OUTPUT.png [WIDTH] [HEIGHT]")
        sys.exit(1)
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 800
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 600
    render(sys.argv[1], sys.argv[2], w, h)
