"""Interactive 3D Robotics Laboratory & Hero Robot Backdrop for Command Centre.

Uses the compiled Three.js WebGL bundle (`frontend/threejs_digital_twin/dist/lab_backdrop.js`)
embedded inline with zero external network dependencies.
"""

import os
import streamlit.components.v1 as components

_LAB_BUNDLE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "frontend",
    "threejs_digital_twin",
    "dist",
    "lab_backdrop.js",
)


def render_vacant_warehouse_backdrop(height_px: int = 500) -> None:
    """Render the interactive 3D Three.js Hero Robot & Robotics Lab environment."""
    js_code = ""
    if os.path.isfile(_LAB_BUNDLE):
        with open(_LAB_BUNDLE, "r", encoding="utf-8") as f:
            js_code = f.read()

    components.html(
        f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8"/>
        <style>
          * {{ margin: 0; padding: 0; box-sizing: border-box; }}
          html, body {{
            width: 100%; height: 100%; overflow: hidden;
            background: #050b16;
          }}
          #lab-canvas-wrap {{
            position: relative;
            width: 100%;
            height: {height_px}px;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(0, 240, 255, 0.22);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.55), inset 0 0 40px rgba(0, 240, 255, 0.08);
            background: radial-gradient(circle at 50% 40%, #0b1930 0%, #050b16 100%);
          }}
          #lab-canvas-wrap canvas {{
            display: block;
            width: 100% !important;
            height: 100% !important;
          }}
        </style>
        </head>
        <body>
          <div id="lab-canvas-wrap"></div>
          <script type="text/javascript">{js_code}</script>
        </body>
        </html>
        """,
        height=height_px,
        scrolling=False,
    )
