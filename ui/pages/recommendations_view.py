"""Explainable AI Recommendation Engine view."""

import streamlit as st
from typing import Any
from ui.components import render_section_header
from recommendations.engine import RecommendationEngine


def render_recommendations_page(rec_engine: RecommendationEngine) -> None:
    """Renders the transparent, explainable advisory recommendations catalogue."""
    render_section_header(
        "Explainable AI Advisory Recommendations",
        "Deterministic, rule-based diagnostic engine providing transparent operational recommendations with measurable evidence.",
        icon="💡",
    )

    recs = rec_engine.evaluate_all()
    if not recs:
        st.success("✅ **All parameters nominal**. No operational bottlenecks or battery risks detected.")
        st.caption("Advance the simulation or inject workload to trigger diagnostic evaluation.")
        return

    st.markdown(f"Found **{len(recs)} active recommendation(s)** across warehouse operations:")

    for rec in recs:
        pri_class = f"rec-card-{rec.priority.value.lower()}"
        badge_color = "#EF4444" if rec.priority.value == "CRITICAL" else "#F59E0B" if rec.priority.value == "HIGH" else "#0284C7"

        evidence_rows = "".join(
            f"<tr><td><strong>{e.metric_name}</strong></td><td><code>{e.measured_value}</code></td><td><em>{e.threshold_value}</em></td><td>{e.details}</td></tr>"
            for e in rec.evidence
        )

        st.markdown(
            f"""
            <div class="rec-card {pri_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 16px; font-weight: 700; color: #F8FAFC;">{rec.title}</span>
                    <span style="background: {badge_color}; color: #FFFFFF; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 4px;">{rec.priority.value}</span>
                </div>
                <div style="font-size: 13px; color: #CBD5E1; margin: 8px 0;">
                    <strong>Problem:</strong> {rec.problem_detected}
                </div>
                <div style="margin: 10px 0;">
                    <table style="width: 100%; font-size: 12px; color: #94A3B8; border-collapse: collapse;">
                        <thead>
                            <tr style="text-align: left; border-bottom: 1px solid #334155;">
                                <th>Evidence Metric</th>
                                <th>Measured</th>
                                <th>Threshold</th>
                                <th>Diagnostic Context</th>
                            </tr>
                        </thead>
                        <tbody>
                            {evidence_rows}
                        </tbody>
                    </table>
                </div>
                <div style="background: rgba(2, 132, 199, 0.1); border-left: 3px solid #00F0FF; padding: 8px 12px; border-radius: 4px; margin-top: 8px;">
                    <div style="font-size: 12px; color: #00F0FF; font-weight: 600;">👉 Suggested Action:</div>
                    <div style="font-size: 12px; color: #F8FAFC;">{rec.suggested_action}</div>
                    <div style="font-size: 11px; color: #10B981; margin-top: 4px;"><strong>Expected Benefit:</strong> {rec.expected_benefit}</div>
                </div>
                <div style="font-size: 10px; color: #64748B; margin-top: 8px;">
                    Rule ID: <code>{rec.rule_id}</code> | Confidence: <strong>{rec.confidence}</strong> | Advisory Mode: Strictly Non-Mutating
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
