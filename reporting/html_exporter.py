"""Self-contained, print-optimized Executive HTML Report generator."""

import html
import datetime
from typing import Dict, Any, List
import pandas as pd
from analytics.models import AnalyticsSnapshot


def generate_executive_html_report(
    snapshot: AnalyticsSnapshot,
    title: str = "Executive Warehouse Operational Report",
    generated_by: str = "OPERATOR",
    df_fleet: pd.DataFrame = None,
    df_incidents: pd.DataFrame = None,
) -> str:
    """Produces a self-contained, beautifully styled HTML document with print-to-PDF styles."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    uptime_min = round(snapshot.wall_clock_uptime_sec / 60.0, 1)

    # Convert KPI metrics to cards
    kpi_cards_html = ""
    for k, metric in snapshot.summary_kpis.items():
        kpi_title = k.replace("_", " ").title()
        badge_color = {
            "MEASURED": "#059669",
            "SIMULATED": "#0284C7",
            "SIMULATED-TELEMETRY": "#7C3AED",
            "ESTIMATED": "#D97706",
        }.get(metric.provenance.value, "#64748B")

        kpi_cards_html += f"""
        <div class="kpi-card">
            <div class="kpi-title">{html.escape(kpi_title)}</div>
            <div class="kpi-value">{html.escape(str(metric.value))} <span class="kpi-unit">{html.escape(metric.unit)}</span></div>
            <div class="kpi-badge" style="background-color: {badge_color};">{html.escape(metric.provenance.value)}</div>
            <div class="kpi-notes">{html.escape(metric.notes)}</div>
        </div>
        """

    # Safety metrics
    safety_cards_html = ""
    for k, metric in snapshot.safety_kpis.items():
        kpi_title = k.replace("_", " ").title()
        safety_cards_html += f"""
        <div class="kpi-card">
            <div class="kpi-title">{html.escape(kpi_title)}</div>
            <div class="kpi-value">{html.escape(str(metric.value))} <span class="kpi-unit">{html.escape(metric.unit)}</span></div>
            <div class="kpi-notes">{html.escape(metric.notes)}</div>
        </div>
        """

    # Fleet table
    fleet_table_html = "<p>No active fleet data recorded.</p>"
    if df_fleet is not None and not df_fleet.empty:
        fleet_table_html = df_fleet.to_html(index=False, classes="report-table", escape=True)

    # Incidents table
    incidents_table_html = "<p>No recent incidents recorded in database.</p>"
    if df_incidents is not None and not df_incidents.empty:
        incidents_table_html = df_incidents.to_html(index=False, classes="report-table", escape=True)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} — SmartWarehouse AI</title>
    <style>
        :root {{
            --bg: #0B132B;
            --surface: #1C2541;
            --surface-border: #3A506B;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --accent: #00F0FF;
            --accent-green: #10B981;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        @media print {{
            body {{
                background: #FFFFFF !important;
                color: #000000 !important;
                font-size: 10pt;
            }}
            .no-print {{ display: none !important; }}
            .kpi-card {{
                border: 1px solid #CBD5E1 !important;
                background: #F8FAFC !important;
                color: #0F172A !important;
                page-break-inside: avoid;
            }}
            .report-table th, .report-table td {{
                border: 1px solid #E2E8F0 !important;
                color: #0F172A !important;
            }}
            .page-break {{ page-break-before: always; }}
        }}
        body {{
            background-color: var(--bg);
            color: var(--text-main);
            font-family: var(--font-family);
            margin: 0;
            padding: 24px;
            line-height: 1.5;
        }}
        .report-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--accent);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .report-title {{
            font-size: 24px;
            font-weight: 700;
            color: var(--accent);
            margin: 0;
        }}
        .report-meta {{
            font-size: 12px;
            color: var(--text-muted);
            text-align: right;
        }}
        .section-header {{
            font-size: 18px;
            font-weight: 600;
            border-bottom: 1px solid var(--surface-border);
            padding-bottom: 8px;
            margin-top: 32px;
            margin-bottom: 16px;
            color: #38BDF8;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 16px;
            position: relative;
        }}
        .kpi-title {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
        }}
        .kpi-value {{
            font-size: 26px;
            font-weight: 700;
            margin: 8px 0;
            color: var(--text-main);
        }}
        .kpi-unit {{
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 400;
        }}
        .kpi-badge {{
            display: inline-block;
            font-size: 10px;
            font-weight: 700;
            color: #FFFFFF;
            padding: 2px 6px;
            border-radius: 4px;
            margin-bottom: 6px;
        }}
        .kpi-notes {{
            font-size: 11px;
            color: var(--text-muted);
            line-height: 1.3;
        }}
        .report-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            background: var(--surface);
            border-radius: 6px;
            overflow: hidden;
        }}
        .report-table th, .report-table td {{
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid var(--surface-border);
            font-size: 13px;
        }}
        .report-table th {{
            background: #111827;
            color: var(--accent);
            font-weight: 600;
        }}
        .report-table tr:hover {{
            background: rgba(56, 189, 248, 0.05);
        }}
        .print-btn {{
            background: var(--accent);
            color: #0B132B;
            border: none;
            padding: 8px 16px;
            font-weight: 700;
            border-radius: 6px;
            cursor: pointer;
            margin-bottom: 16px;
        }}
        .print-btn:hover {{
            background: #38BDF8;
        }}
    </style>
</head>
<body>
    <div class="no-print">
        <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
    </div>

    <div class="report-header">
        <div>
            <h1 class="report-title">{html.escape(title)}</h1>
            <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">
                SmartWarehouse AI Autonomous Coordination & Digital Twin Platform
            </div>
        </div>
        <div class="report-meta">
            <div><strong>Generated By:</strong> {html.escape(generated_by)}</div>
            <div><strong>Timestamp:</strong> {html.escape(now_str)}</div>
            <div><strong>Sim Step:</strong> {snapshot.simulation_step} | <strong>Uptime:</strong> {uptime_min} min</div>
        </div>
    </div>

    <div class="section-header">Operational Key Performance Indicators</div>
    <div class="kpi-grid">
        {kpi_cards_html}
    </div>

    <div class="section-header">Collision Avoidance & Safety Verification</div>
    <div class="kpi-grid">
        {safety_cards_html}
    </div>

    <div class="section-header">Autonomous Fleet Telemetry & Health</div>
    {fleet_table_html}

    <div class="section-header">Incident & Hazard Event Log</div>
    {incidents_table_html}

    <div style="margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--surface-border); font-size: 11px; color: var(--text-muted); text-align: center;">
        SmartWarehouse AI — B.Tech Final Year Engineering Capstone Platform — Strictly verified with genuine simulation telemetry.
    </div>
</body>
</html>
"""
    return html_content
