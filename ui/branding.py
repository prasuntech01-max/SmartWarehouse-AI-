"""Professional Enterprise 3D Branding & Header Components for SmartWarehouse AI.

Official Product Name: SMARTWAREHOUSE AI
Technical Designation: AUTONOMOUS INTELLIGENT WAREHOUSE OPERATIONS & ROBOTICS PLATFORM
Professional Tagline: AUTONOMOUS • INTELLIGENT • OPTIMIZED
"""

import base64
import time
import textwrap
import streamlit as st
from typing import Any, Optional


def get_3d_metallic_logo_svg_raw(width: int = 640, height: int = 220) -> str:
    """Generates the clean raw SVG content for the 3D chrome metallic SmartWarehouse AI logo."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 220" width="{width}" height="{height}">
  <defs>
    <linearGradient id="chromeBase" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="25%" stop-color="#cbd5e1"/>
      <stop offset="48%" stop-color="#64748b"/>
      <stop offset="52%" stop-color="#0f172a"/>
      <stop offset="75%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
    <linearGradient id="chromeCyan" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#e0f2fe"/>
      <stop offset="40%" stop-color="#38bdf8"/>
      <stop offset="70%" stop-color="#00f0ff"/>
      <stop offset="100%" stop-color="#0369a1"/>
    </linearGradient>
    <linearGradient id="chromeMagenta" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fdf4ff"/>
      <stop offset="30%" stop-color="#f472b6"/>
      <stop offset="70%" stop-color="#c084fc"/>
      <stop offset="100%" stop-color="#7e22ce"/>
    </linearGradient>
    <linearGradient id="shieldRim" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="50%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#00f0ff"/>
    </linearGradient>
    <linearGradient id="darkPlate" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0b1329"/>
      <stop offset="100%" stop-color="#040814"/>
    </linearGradient>
    <filter id="neonGlowCyan" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <filter id="neonGlowMagenta" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Hexagonal Shield Background with Gear Base -->
  <g transform="translate(10, 5)">
    <polygon points="110,12 210,12 250,55 250,115 225,145 215,145 210,158 195,158 190,145 170,145 165,158 150,158 145,145 125,145 120,158 105,158 100,145 70,115 70,55"
             fill="url(#shieldRim)" stroke="#00f0ff" stroke-width="2.5" filter="url(#neonGlowCyan)"/>
    <polygon points="113,18 207,18 244,58 244,112 222,140 98,140 76,112 76,58"
             fill="url(#darkPlate)" stroke="rgba(0, 240, 255, 0.4)" stroke-width="1.5"/>

    <!-- Warehouse Gable Outline with Glowing Ribs -->
    <polygon points="160,26 232,68 232,108 88,108 88,68" fill="none" stroke="#00f0ff" stroke-width="2" opacity="0.85"/>
    <line x1="160" y1="26" x2="160" y2="48" stroke="#38bdf8" stroke-width="2"/>
    <line x1="110" y1="58" x2="210" y2="58" stroke="#00f0ff" stroke-width="1.2" stroke-dasharray="3,3"/>
    <line x1="98" y1="80" x2="222" y2="80" stroke="#00f0ff" stroke-width="1.2" stroke-dasharray="4,4"/>

    <!-- AI Chip Microprocessor Emblem in center -->
    <rect x="144" y="36" width="32" height="30" rx="4" fill="#0f172a" stroke="#00f0ff" stroke-width="2" filter="url(#neonGlowCyan)"/>
    <path d="M144 44 h-12 M144 51 h-16 M144 58 h-12 M176 44 h12 M176 51 h16 M176 58 h12 M152 36 v-8 M160 36 v-10 M168 36 v-8 M152 66 v8 M160 66 v10 M168 66 v8"
          stroke="#00f0ff" stroke-width="1.5" stroke-linecap="round"/>
    <text x="160" y="56" fill="#ffffff" font-family="'Orbitron', sans-serif" font-weight="900" font-size="13" text-anchor="middle" letter-spacing="1">AI</text>

    <!-- Silhouettes: AMR in center, Humanoid on left, Arm on right -->
    <path d="M142 98 h36 v12 h-36 z" fill="#38bdf8" opacity="0.9"/>
    <circle cx="147" cy="112" r="3" fill="#00f0ff"/>
    <circle cx="173" cy="112" r="3" fill="#00f0ff"/>
    <circle cx="118" cy="85" r="4" fill="#cbd5e1"/>
    <path d="M114 91 h8 v16 h-8 z" fill="#94a3b8"/>
    <path d="M200 108 l8 -14 l-6 -8 l12 -2" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <!-- 3D Isometric Cube at Bottom Center -->
  <g transform="translate(170, 168)" filter="url(#neonGlowCyan)">
    <polygon points="0,0 -16,-9 -16,10 0,19" fill="#0284c7" opacity="0.85" stroke="#38bdf8" stroke-width="1"/>
    <polygon points="0,0 16,-9 16,10 0,19" fill="#7e22ce" opacity="0.85" stroke="#c084fc" stroke-width="1"/>
    <polygon points="0,0 -16,-9 0,-18 16,-9" fill="#00f0ff" opacity="0.95" stroke="#ffffff" stroke-width="1"/>
    <path d="M-22 5 l-14 -4 l-8 0 M22 5 l14 -4 l8 0" stroke="#00f0ff" stroke-width="2" stroke-linecap="round"/>
    <path d="M-20 12 l-12 -3 l-6 0 M20 12 l12 -3 l6 0" stroke="#c084fc" stroke-width="1.8" stroke-linecap="round"/>
  </g>

  <!-- 3D Chrome Typography: "SmartWarehouse" -->
  <text x="270" y="112"
        font-family="'Orbitron', 'Space Grotesk', -apple-system, sans-serif"
        font-weight="900" font-size="44" letter-spacing="-0.5"
        fill="url(#chromeCyan)"
        stroke="#0f172a" stroke-width="6" paint-order="stroke fill"
        style="font-style: italic;">SmartWarehouse</text>
  <text x="270" y="112"
        font-family="'Orbitron', 'Space Grotesk', -apple-system, sans-serif"
        font-weight="900" font-size="44" letter-spacing="-0.5"
        fill="url(#chromeBase)"
        style="font-style: italic;">SmartWarehouse</text>

  <!-- 3D Chrome Typography: "AI" -->
  <text x="560" y="112"
        font-family="'Orbitron', 'Space Grotesk', -apple-system, sans-serif"
        font-weight="900" font-size="52" letter-spacing="1"
        fill="url(#chromeMagenta)"
        stroke="#0f172a" stroke-width="7" paint-order="stroke fill"
        filter="url(#neonGlowMagenta)"
        style="font-style: italic;">AI</text>
  <text x="560" y="112"
        font-family="'Orbitron', 'Space Grotesk', -apple-system, sans-serif"
        font-weight="900" font-size="52" letter-spacing="1"
        fill="url(#chromeMagenta)"
        style="font-style: italic;">AI</text>

  <!-- Technical Designation Subtitle -->
  <text x="272" y="136"
        font-family="'Rajdhani', -apple-system, sans-serif"
        font-weight="700" font-size="12" letter-spacing="2.8"
        fill="#38bdf8" text-transform="uppercase">
    AUTONOMOUS INTELLIGENT WAREHOUSE OPERATIONS &amp; ROBOTICS PLATFORM
  </text>

  <!-- Product Tagline -->
  <text x="272" y="156"
        font-family="'Rajdhani', -apple-system, sans-serif"
        font-weight="600" font-size="11" letter-spacing="3.5"
        fill="#94a3b8" text-transform="uppercase">
    AUTONOMOUS &#8226; INTELLIGENT &#8226; OPTIMIZED
  </text>

  <!-- Bottom metallic divider line with cyan pulse -->
  <line x1="272" y1="168" x2="620" y2="168" stroke="#00f0ff" stroke-width="1.5" opacity="0.6"/>
  <circle cx="272" cy="168" r="2.5" fill="#00f0ff"/>
  <circle cx="620" cy="168" r="2.5" fill="#d946ef"/>
</svg>"""


def get_3d_metallic_logo_img_tag(width: int = 340, height: int = 100) -> str:
    """Returns an <img> tag with Base64 encoded SVG data.
    
    Using a Base64 data URI completely protects the SVG markup from being
    accidentally parsed as Markdown code blocks by Streamlit.
    """
    raw_svg = get_3d_metallic_logo_svg_raw()
    b64_data = base64.b64encode(raw_svg.encode("utf-8")).decode("ascii")
    return f'<img src="data:image/svg+xml;base64,{b64_data}" width="{width}" height="{height}" alt="SmartWarehouse AI" style="display:block;filter:drop-shadow(0 4px 18px rgba(0,240,255,0.3));" />'


def render_enterprise_header() -> None:
    """Renders the top enterprise header bar with live system status, clock, and user role pill.
    
    Matches the exact layout seen in reference image media_1795457063752_f01d88bf.jpg.
    Protected against markdown code block leakage.
    """
    current_time_str = time.strftime("%H:%M:%S")
    current_date_str = time.strftime("%a, %d %b %Y")

    active_user = st.session_state.get("username", "admin")
    active_role = st.session_state.get("user_role", "ADMIN")
    role_badge_bg = "#EF4444" if active_role == "ADMIN" else "#00F0FF" if active_role == "OPERATOR" else "#64748B"

    logo_img = get_3d_metallic_logo_img_tag(width=340, height=95)

    header_html = f"""<div style="background:linear-gradient(180deg,rgba(11,19,43,0.95) 0%,rgba(6,11,24,0.92) 100%);border:1px solid rgba(0,240,255,0.2);border-radius:12px;padding:8px 16px;margin-bottom:14px;box-shadow:0 8px 32px rgba(0,0,0,0.5),inset 0 1px 0 rgba(0,240,255,0.25);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
<div style="display:flex;align-items:center;gap:12px;">{logo_img}</div>
<div style="text-align:center;display:flex;flex-direction:column;align-items:center;">
<div style="display:flex;align-items:center;gap:8px;"><span style="font-family:'Rajdhani',monospace;font-size:20px;font-weight:700;color:#FFFFFF;letter-spacing:1px;">{current_time_str}</span><span style="font-size:12px;color:#94A3B8;font-weight:500;">{current_date_str}</span></div>
<div style="display:flex;align-items:center;gap:10px;margin-top:3px;"><span style="display:inline-flex;align-items:center;gap:5px;background:rgba(16,185,129,0.15);border:1px solid #10B981;color:#10B981;font-size:11px;font-weight:700;padding:2px 10px;border-radius:12px;letter-spacing:0.5px;"><span style="width:7px;height:7px;border-radius:50%;background:#10B981;box-shadow:0 0 8px #10B981;"></span>System Online</span><span style="color:#64748B;font-size:11px;">|</span><span style="color:#00F0FF;font-size:11px;font-weight:600;letter-spacing:0.5px;">5/5 Fleet Active</span><span style="color:#64748B;font-size:11px;">|</span><span style="color:#38BDF8;font-size:11px;font-weight:600;letter-spacing:0.5px;">Space-Time CBS</span></div>
</div>
<div style="display:flex;align-items:center;gap:10px;"><div style="background:rgba(15,23,42,0.85);border:1px solid rgba(0,240,255,0.25);border-radius:24px;padding:6px 14px;display:flex;align-items:center;gap:10px;box-shadow:0 2px 10px rgba(0,0,0,0.3);"><div style="width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#0284C7,#00F0FF);display:flex;align-items:center;justify-content:center;font-size:14px;box-shadow:0 0 10px rgba(0,240,255,0.5);">👤</div><div><div style="font-size:12px;font-weight:700;color:#F8FAFC;text-transform:capitalize;">{active_user}</div><div style="font-size:9px;font-weight:800;color:{role_badge_bg};letter-spacing:0.8px;">{active_role} CLEARANCE</div></div></div></div>
</div>"""

    st.markdown(header_html, unsafe_allow_html=True)


def render_global_emergency_banner(sim: Any) -> None:
    """Renders a persistent pulsing red emergency banner whenever E-Stop is genuinely active."""
    is_global = bool(getattr(sim, "global_e_stop", False))
    robots = getattr(sim, "robots", {}) or {}
    stopped_ids = [
        rid for rid, r in sorted(robots.items())
        if getattr(r, "e_stopped", False) or str(getattr(r, "state", "")).upper() in ("E_STOPPED", "EMERGENCY")
    ]
    if not is_global and not stopped_ids:
        return

    scope_str = (
        f"ALL FLEET UNITS HALTED ({len(stopped_ids)}/{len(robots)})"
        if is_global or len(stopped_ids) == len(robots)
        else f"AFFECTED UNITS: {', '.join(f'R{rid}' for rid in stopped_ids)}"
    )
    banner_html = (
        '<style>'
        '@keyframes swEmgPulse{0%,100%{box-shadow:0 0 18px rgba(239,68,68,0.55);border-color:#ef4444;}50%{box-shadow:0 0 32px rgba(239,68,68,0.9);border-color:#fca5a5;}}'
        '@keyframes swEmgDot{0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.35;transform:scale(1.3);}}'
        '.sw-emg-banner{background:linear-gradient(90deg,rgba(127,29,29,0.94) 0%,rgba(153,27,27,0.90) 50%,rgba(127,29,29,0.94) 100%);border:2px solid #ef4444;border-radius:10px;padding:12px 18px;margin-bottom:14px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;animation:swEmgPulse 1.4s ease-in-out infinite;}'
        '.sw-emg-dot{width:11px;height:11px;border-radius:50%;background:#ff2e4c;box-shadow:0 0 12px #ff2e4c;display:inline-block;animation:swEmgDot 0.9s ease-in-out infinite;}'
        '</style>'
        '<div class="sw-emg-banner" data-testid="global-emergency-banner">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<span style="font-size:22px;">🚨</span>'
        '<div>'
        '<div style="display:flex;align-items:center;gap:8px;">'
        '<span class="sw-emg-dot"></span>'
        '<span style="font-family:Orbitron,sans-serif;font-size:14px;font-weight:800;color:#ffffff;letter-spacing:1.2px;">EMERGENCY ACTIVE — SAFETY INTERLOCK ENGAGED</span>'
        '</div>'
        f'<div style="font-size:12px;color:#fecaca;margin-top:2px;font-weight:600;">{scope_str} &bull; Autonomous motion &amp; dispatch suspended until operator clears emergency via RESUME ALL / START ALL.</div>'
        '</div>'
        '</div>'
        '<span style="background:#ef4444;color:#ffffff;font-size:11px;font-weight:800;padding:4px 12px;border-radius:6px;letter-spacing:0.8px;border:1px solid #fecaca;">E-STOP LOCKED</span>'
        '</div>'
    )
    st.markdown(banner_html, unsafe_allow_html=True)
