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
            /* ── Global Theme Overrides & Immersive Warehouse Command Environment ── */
            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            /* Immersive Multi-Layered Industrial Background */
            .stApp {
                background-color: #07111F !important;
                background-image: 
                    radial-gradient(circle at 18% 12%, rgba(0, 229, 255, 0.08) 0%, transparent 45%),
                    radial-gradient(circle at 85% 15%, rgba(168, 85, 247, 0.08) 0%, transparent 40%),
                    radial-gradient(circle at 50% 90%, rgba(22, 139, 255, 0.09) 0%, transparent 55%),
                    linear-gradient(rgba(0, 229, 255, 0.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 229, 255, 0.025) 1px, transparent 1px),
                    linear-gradient(180deg, #07111F 0%, #091326 50%, #050B16 100%) !important;
                background-size: 100% 100%, 100% 100%, 100% 100%, 48px 48px, 48px 48px, 100% 100% !important;
                background-attachment: fixed !important;
            }

            /* Translucent Glassmorphic Sidebar with Cyber Border */
            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(7, 17, 31, 0.95) 0%, rgba(9, 15, 30, 0.97) 100%) !important;
                border-right: 1px solid rgba(0, 229, 255, 0.22) !important;
                box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5) !important;
                backdrop-filter: blur(20px) !important;
                -webkit-backdrop-filter: blur(20px) !important;
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
                color: #F8FAFC !important;
            }

            /* Industrial KPI Cards with Glassmorphism */
            .industry-kpi {
                background: linear-gradient(135deg, rgba(11, 19, 43, 0.88) 0%, rgba(9, 14, 28, 0.92) 100%);
                border: 1px solid rgba(0, 229, 255, 0.22);
                border-left: 4px solid #00E5FF;
                border-radius: 10px;
                padding: 14px 16px;
                color: #F8FAFC;
                margin-bottom: 12px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
            }
            .industry-kpi:hover {
                transform: translateY(-2px);
                border-color: #00E5FF;
                box-shadow: 0 10px 28px rgba(0, 229, 255, 0.2);
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
                border: 1px solid rgba(0, 229, 255, 0.2);
                border-radius: 8px;
                backdrop-filter: blur(12px);
                background: rgba(11, 19, 43, 0.75);
            }

            /* Custom Industrial Scrollbar */
            ::-webkit-scrollbar {
                width: 6px;
                height: 6px;
            }
            ::-webkit-scrollbar-track {
                background: #07111F;
            }
            ::-webkit-scrollbar-thumb {
                background: rgba(0, 229, 255, 0.35);
                border-radius: 3px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #00E5FF;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
