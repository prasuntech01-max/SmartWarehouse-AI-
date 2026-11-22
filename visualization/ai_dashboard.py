"""Module 10 — AI Analytics Dashboard Plotly Rendering Functions.

Provides modular chart functions for the Module 10 Streamlit UI.
All functions accept pre-computed analytics objects and return go.Figure.
"""

from typing import Dict, List, Any, Optional, Tuple
import plotly.graph_objects as go


# ------------------------------------------------------------------
# Colour palette (industrial dark-blue theme)
# ------------------------------------------------------------------
NAVY     = '#0A1628'
CYAN     = '#00C2FF'
BLUE     = '#0284C7'
ORANGE   = '#E67E22'
RED      = '#E74C3C'
GREEN    = '#27AE60'
YELLOW   = '#F1C40F'
GRAY     = '#7F8C8D'
LIGHT    = '#ECF0F1'


def _base_layout(**kwargs) -> dict:
    """Shared Plotly layout base with professional dark industrial styling."""
    base = dict(
        paper_bgcolor='rgba(10,22,40,0.0)',
        plot_bgcolor='rgba(10,22,40,0.0)',
        font=dict(color=LIGHT, size=12),
        margin=dict(t=45, b=35, l=45, r=25),
        height=320,
    )
    base.update(kwargs)
    return base


# ------------------------------------------------------------------
# 1. Demand Forecast Chart
# ------------------------------------------------------------------

def render_demand_forecast_chart(forecaster: Any) -> go.Figure:
    """Line chart showing demand trend for the top shelf location."""
    top = forecaster.get_top_shelves(1)
    fig = go.Figure()

    if not top or not forecaster.data_sufficient:
        fig.add_annotation(
            text=(
                "Advance the simulation to complete more tasks.<br>"
                "Demand forecasting requires at least 3 completed tasks."
            ),
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color=GRAY, size=13),
        )
        fig.update_layout(
            _base_layout(title='<b>📈 Demand Trend (Top Shelf)</b>')
        )
        return fig

    shelf_loc, count = top[0]
    trend = forecaster.get_demand_trend(shelf_loc, window=5)

    if trend:
        x_vals = list(range(1, len(trend) + 1))
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=trend,
            mode='lines+markers',
            name=f'Shelf {shelf_loc}',
            line=dict(color=CYAN, width=2.5),
            marker=dict(size=6, color=CYAN),
            fill='tozeroy',
            fillcolor='rgba(0,194,255,0.12)',
        ))

    # Forecast annotation
    forecast = forecaster.forecast_next_demand(steps_ahead=10)
    if forecast['predicted_tasks'] > 0:
        fig.add_hline(
            y=forecast['predicted_tasks'],
            line_dash='dash',
            line_color=ORANGE,
            annotation_text=f"Forecast: {forecast['predicted_tasks']:.1f} tasks",
            annotation_font_color=ORANGE,
        )

    label = '(Preliminary Data)' if forecast.get('preliminary') else ''
    fig.update_layout(_base_layout(
        title=f'<b>📈 Demand Trend — Top Shelf {shelf_loc} {label}</b>',
        xaxis_title='Time Window',
        yaxis_title='Avg Tasks per Window',
    ))
    return fig


# ------------------------------------------------------------------
# 2. Top Shelves Bar Chart
# ------------------------------------------------------------------

def render_top_shelves_chart(forecaster: Any, n: int = 10) -> go.Figure:
    """Horizontal bar chart of most frequently picked shelves."""
    top = forecaster.get_top_shelves(n)
    fig = go.Figure()

    if not top:
        fig.add_annotation(
            text="No completed tasks yet — advance the simulation.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(color=GRAY, size=13),
        )
        fig.update_layout(_base_layout(title='<b>📦 Top Demand Shelves</b>'))
        return fig

    labels = [str(pos) for pos, _ in top]
    counts = [cnt for _, cnt in top]
    colours = [CYAN if i == 0 else BLUE for i in range(len(top))]

    fig.add_trace(go.Bar(
        y=labels,
        x=counts,
        orientation='h',
        marker_color=colours,
        text=counts,
        textposition='outside',
    ))
    fig.update_layout(_base_layout(
        title='<b>📦 Top Demand Shelf Locations</b>',
        xaxis_title='Pick Frequency',
        yaxis_title='Shelf (x, y)',
        height=max(280, len(top) * 36),
    ))
    return fig


# ------------------------------------------------------------------
# 3. Congestion Heatmap 3D
# ------------------------------------------------------------------

def render_congestion_heatmap_3d(predictor: Any, grid: Any, robots: Dict) -> go.Figure:
    """3D scatter heatmap of warehouse congestion hotspots."""
    heatmap = predictor.get_congestion_heatmap(robots)
    fig = go.Figure()

    if not heatmap:
        fig.add_annotation(
            text="No active robot paths — run the simulation to populate congestion data.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(color=GRAY, size=13),
        )
        fig.update_layout(_base_layout(title='<b>🌡 Congestion Intelligence Map</b>', height=420))
        return fig

    xs = [cell[0] for cell in heatmap]
    ys = [cell[1] for cell in heatmap]
    scores = [heatmap[cell] for cell in heatmap]
    hover = [f'Cell ({x},{y})<br>Congestion: {s:.2f}' for x, y, s in zip(xs, ys, scores)]

    fig.add_trace(go.Scatter3d(
        x=xs,
        y=ys,
        z=scores,
        mode='markers',
        marker=dict(
            size=[6 + s * 10 for s in scores],
            color=scores,
            colorscale='YlOrRd',
            colorbar=dict(title='Congestion', tickfont=dict(color=LIGHT)),
            opacity=0.85,
            cmin=0,
            cmax=1,
        ),
        text=hover,
        hoverinfo='text',
        name='Traffic Density',
    ))

    fig.update_layout(
        title='<b>🌡 Warehouse Congestion Heatmap (3D)</b>',
        height=440,
        scene=dict(
            xaxis=dict(title='X', backgroundcolor='rgba(0,0,0,0)', gridcolor='#1e3050'),
            yaxis=dict(title='Y', backgroundcolor='rgba(0,0,0,0)', gridcolor='#1e3050'),
            zaxis=dict(title='Congestion', backgroundcolor='rgba(0,0,0,0)', gridcolor='#1e3050'),
            bgcolor='rgba(10,22,40,0.0)',
        ),
        paper_bgcolor='rgba(10,22,40,0.0)',
        font=dict(color=LIGHT),
        margin=dict(t=50, b=20, l=0, r=0),
    )
    return fig


# ------------------------------------------------------------------
# 4. Fleet Health Dashboard
# ------------------------------------------------------------------

def render_fleet_health_dashboard(monitor: Any) -> go.Figure:
    """Bar chart showing each robot's health score with colour-coded status."""
    summary = monitor.get_fleet_health_summary()

    if not summary:
        fig = go.Figure()
        fig.add_annotation(text="No robots in fleet.", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(color=GRAY))
        fig.update_layout(_base_layout(title='<b>🤖 Fleet Health Dashboard</b>'))
        return fig

    robot_ids = sorted(summary.keys())
    scores = [summary[r]['score'] for r in robot_ids]
    statuses = [summary[r]['status'] for r in robot_ids]
    colours = [summary[r]['colour'] for r in robot_ids]
    labels = [f'R{r}' for r in robot_ids]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=scores,
        marker_color=colours,
        text=[f"{s:.0f}%<br>{st}" for s, st in zip(scores, statuses)],
        textposition='inside',
        textfont=dict(color='white', size=11),
        name='Health Score',
    ))

    fig.add_hline(y=80, line_dash='dot', line_color=GREEN,
                  annotation_text='Excellent', annotation_font_color=GREEN)
    fig.add_hline(y=60, line_dash='dot', line_color=BLUE,
                  annotation_text='Good', annotation_font_color=BLUE)
    fig.add_hline(y=40, line_dash='dot', line_color=ORANGE,
                  annotation_text='Warning', annotation_font_color=ORANGE)

    fig.update_layout(_base_layout(
        title='<b>🤖 Fleet Health Scores (Simulated Telemetry)</b>',
        xaxis_title='Robot',
        yaxis_title='Health Score (0–100)',
        yaxis=dict(range=[0, 115]),
    ))
    return fig


# ------------------------------------------------------------------
# 5. Strategy Comparison Chart
# ------------------------------------------------------------------

def render_strategy_comparison(benchmark_data: List[Dict[str, Any]]) -> go.Figure:
    """Grouped bar chart comparing all 6 assignment strategies."""
    if not benchmark_data:
        fig = go.Figure()
        fig.add_annotation(text="Run strategy benchmark to see comparison.",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(color=GRAY, size=13))
        fig.update_layout(_base_layout(title='<b>🔬 Strategy Benchmark Comparison</b>'))
        return fig

    labels = [r.get('strategy_label', r['strategy'])[:20] for r in benchmark_data]
    tasks = [r['completed_tasks'] for r in benchmark_data]
    distances = [r['total_distance'] for r in benchmark_data]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Completed Tasks',
        x=labels, y=tasks,
        marker_color=CYAN,
        yaxis='y',
    ))
    fig.add_trace(go.Bar(
        name='Total Distance (m)',
        x=labels, y=distances,
        marker_color=ORANGE,
        yaxis='y2',
        opacity=0.7,
    ))

    fig.update_layout(
        _base_layout(
            title='<b>🔬 Assignment Strategy Comparison</b>',
            xaxis_title='Strategy',
            barmode='group',
            height=340,
            yaxis=dict(title='Completed Tasks', color=CYAN),
            yaxis2=dict(
                title='Total Fleet Distance (m)',
                overlaying='y',
                side='right',
                color=ORANGE,
            ),
            legend=dict(orientation='h', y=-0.3),
        )
    )
    return fig


# ------------------------------------------------------------------
# 6. Shelf Optimisation 3D Scatter
# ------------------------------------------------------------------

def render_shelf_optimization_3d(optimizer: Any, grid: Any) -> go.Figure:
    """3D scatter showing shelves coloured by optimisation priority score."""
    report = optimizer.get_optimization_report()
    shelf_distances = report['layout_analysis'].get('shelf_distances', [])
    demand_heatmap = optimizer.demand_heatmap

    fig = go.Figure()

    if not shelf_distances:
        fig.add_annotation(text="Shelf layout data unavailable.",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(color=GRAY))
        fig.update_layout(_base_layout(
            title='<b>🏭 Shelf Optimisation View (3D)</b>', height=420))
        return fig

    xs = [sd['shelf'][0] for sd in shelf_distances]
    ys = [sd['shelf'][1] for sd in shelf_distances]
    dists = [sd['dist'] for sd in shelf_distances]
    demands = [demand_heatmap.get(sd['shelf'], 0.0) for sd in shelf_distances]
    scores = [(d + 0.1) * dist for d, dist in zip(demands, dists)]
    hover = [
        f"Shelf {sd['shelf']}<br>Demand: {dm:.2f}<br>Dist to station: {sd['dist']}<br>Score: {sc:.2f}"
        for sd, dm, sc in zip(shelf_distances, demands, scores)
    ]

    fig.add_trace(go.Scatter3d(
        x=xs,
        y=ys,
        z=scores,
        mode='markers',
        marker=dict(
            size=[5 + sc for sc in scores],
            color=scores,
            colorscale='RdYlGn_r',
            colorbar=dict(title='Relocation\nScore', tickfont=dict(color=LIGHT)),
            opacity=0.85,
        ),
        text=hover,
        hoverinfo='text',
        name='Shelf Score',
    ))

    fig.update_layout(
        title='<b>🏭 Shelf Relocation Priority (3D) — Advisory Only</b>',
        height=440,
        scene=dict(
            xaxis=dict(title='X', backgroundcolor='rgba(0,0,0,0)', gridcolor='#1e3050'),
            yaxis=dict(title='Y', backgroundcolor='rgba(0,0,0,0)', gridcolor='#1e3050'),
            zaxis=dict(title='Score', backgroundcolor='rgba(0,0,0,0)', gridcolor='#1e3050'),
            bgcolor='rgba(10,22,40,0.0)',
        ),
        paper_bgcolor='rgba(10,22,40,0.0)',
        font=dict(color=LIGHT),
        margin=dict(t=50, b=20, l=0, r=0),
    )
    return fig


# ------------------------------------------------------------------
# 7. Maintenance Priority Chart
# ------------------------------------------------------------------

def render_maintenance_priority(monitor: Any) -> go.Figure:
    """Horizontal bar chart: robots ranked by maintenance urgency (lowest health first)."""
    summary = monitor.get_fleet_health_summary()
    priority_order = monitor.get_maintenance_priority()

    fig = go.Figure()
    if not summary:
        fig.add_annotation(text="No robots in fleet.",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(color=GRAY))
        fig.update_layout(_base_layout(title='<b>🔧 Maintenance Priority</b>'))
        return fig

    labels = [f'R{r_id}' for r_id in priority_order]
    scores = [summary[r_id]['score'] for r_id in priority_order]
    colours = [summary[r_id]['colour'] for r_id in priority_order]

    fig.add_trace(go.Bar(
        y=labels,
        x=scores,
        orientation='h',
        marker_color=colours,
        text=[f"{s:.0f}" for s in scores],
        textposition='outside',
        textfont=dict(color=LIGHT),
    ))

    fig.update_layout(_base_layout(
        title='<b>🔧 Maintenance Priority (Lowest Health = Most Urgent)</b>',
        xaxis_title='Health Score (0–100)',
        xaxis=dict(range=[0, 115]),
    ))
    return fig
