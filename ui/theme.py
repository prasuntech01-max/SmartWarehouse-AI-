"""Design tokens and custom CSS injection for SmartWarehouse AI."""

import streamlit as st


def inject_custom_theme() -> None:
    """Injects high-end industrial dark styling and Google typography into the Streamlit session."""
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Orbitron:wght@600;700;800;900&family=Rajdhani:wght@500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">

        <style>
            /* Global theme overrides */
            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            .main .block-container {
                padding-top: 1.0rem;
                padding-bottom: 2rem;
                max-width: 98%;
            }

            /* Technical headers */
            h1, h2, h3 {
                font-family: 'Space Grotesk', 'Orbitron', sans-serif !important;
                letter-spacing: -0.3px;
            }

            /* Industrial KPI Cards */
            .industry-kpi {
                background: linear-gradient(135deg, #090e1a 0%, #111a2e 100%);
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-left: 4px solid #00F0FF;
                border-radius: 10px;
                padding: 14px 16px;
                color: #F8FAFC;
                margin-bottom: 12px;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
                transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
            }
            .industry-kpi:hover {
                transform: translateY(-2px);
                border-color: #00F0FF;
                box-shadow: 0 6px 20px rgba(0, 240, 255, 0.15);
            }
            .kpi-label {
                font-family: 'Rajdhani', sans-serif;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #94A3B8;
                font-weight: 700;
                margin-bottom: 4px;
            }
            .kpi-main-val {
                font-family: 'Rajdhani', monospace;
                font-size: 26px;
                font-weight: 700;
                color: #00F0FF;
                display: flex;
                align-items: baseline;
                gap: 6px;
                text-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
            }
            .kpi-unit-val {
                font-size: 12px;
                font-weight: 500;
                color: #64748B;
            }
            .kpi-delta-positive {
                color: #10B981;
                font-size: 11px;
                font-weight: 600;
            }
            .kpi-delta-negative {
                color: #EF4444;
                font-size: 11px;
                font-weight: 600;
            }

            /* Keyframes */
            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.4; transform: scale(0.92); }
            }

            /* Provenance Badges */
            .badge-provenance {
                display: inline-block;
                font-family: 'Rajdhani', sans-serif;
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
                padding: 2px 7px;
                border-radius: 4px;
                margin-top: 6px;
                letter-spacing: 0.04em;
            }
            .badge-measured { background-color: #059669; color: #FFFFFF; }
            .badge-simulated { background-color: #0284C7; color: #FFFFFF; }
            .badge-telemetry { background-color: #7C3AED; color: #FFFFFF; }
            .badge-estimated { background-color: #D97706; color: #FFFFFF; }

            /* Status Chips */
            .status-chip {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
            }
            .chip-normal { background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981; }
            .chip-warning { background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; }
            .chip-critical { background: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444; }
            .chip-idle { background: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid #94A3B8; }

            /* Recommendation Cards */
            .rec-card {
                background: #090e1a;
                border: 1px solid rgba(0, 240, 255, 0.15);
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 14px;
            }
            .rec-card-critical { border-left: 4px solid #EF4444; }
            .rec-card-high { border-left: 4px solid #F59E0B; }
            .rec-card-medium { border-left: 4px solid #0284C7; }
            .rec-card-low { border-left: 4px solid #64748B; }

            /* Action buttons */
            .stButton>button {
                border-radius: 6px;
                font-family: 'Rajdhani', sans-serif;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 0.5px;
                transition: all 0.2s ease;
                border: 1px solid rgba(0, 240, 255, 0.25);
            }
            .stButton>button:hover {
                box-shadow: 0 0 14px rgba(0, 240, 255, 0.4);
                border-color: #00F0FF;
            }

            /* Dataframes */
            .stDataFrame {
                border: 1px solid rgba(0, 240, 255, 0.15);
                border-radius: 8px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
