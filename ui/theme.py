"""Design tokens and custom CSS injection for SmartWarehouse AI."""

import streamlit as st


def inject_custom_theme() -> None:
    """Injects high-end industrial dark styling into the Streamlit session."""
    st.markdown(
        """
        <style>
            /* Global theme overrides */
            .main .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
                max-width: 96%;
            }
            
            /* Industrial KPI Cards */
            .industry-kpi {
                background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
                border: 1px solid #334155;
                border-left: 4px solid #00F0FF;
                border-radius: 8px;
                padding: 14px 16px;
                color: #F8FAFC;
                margin-bottom: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
                transition: transform 0.15s ease, border-color 0.15s ease;
            }
            .industry-kpi:hover {
                transform: translateY(-2px);
                border-color: #00F0FF;
            }
            .kpi-label {
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #94A3B8;
                font-weight: 600;
                margin-bottom: 4px;
            }
            .kpi-main-val {
                font-size: 24px;
                font-weight: 700;
                color: #F8FAFC;
                display: flex;
                align-items: baseline;
                gap: 6px;
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

            /* Provenance Badges */
            .badge-provenance {
                display: inline-block;
                font-size: 9px;
                font-weight: 700;
                text-transform: uppercase;
                padding: 2px 6px;
                border-radius: 4px;
                margin-top: 6px;
                letter-spacing: 0.03em;
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
                background: #0F172A;
                border: 1px solid #1E293B;
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
                font-weight: 600;
                transition: all 0.2s ease;
            }
            .stButton>button:hover {
                box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
            }

            /* Dataframes */
            .stDataFrame {
                border: 1px solid #1E293B;
                border-radius: 6px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
