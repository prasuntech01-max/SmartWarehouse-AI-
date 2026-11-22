"""Interactive 3D warehouse visualization using Plotly."""

from typing import Dict, List, Tuple, Optional, Any, Set
import plotly.graph_objects as go
from core.grid import WarehouseGrid
from simulation.engine import RobotState
from visualization.renderer import ROBOT_COLORS


PRIORITY_COLORS = {
    1: "#95A5A6",  # Low (Gray)
    2: "#3498DB",  # Normal (Blue)
    3: "#E67E22",  # High (Orange)
    4: "#E74C3C",  # Urgent (Red)
}

CAMERA_PRESETS = {
    'iso': dict(
        eye=dict(x=1.35, y=-1.45, z=1.35),
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=-0.1),
    ),
    'top': dict(
        eye=dict(x=0.001, y=-0.001, z=2.45),
        up=dict(x=0, y=1, z=0),
        center=dict(x=0, y=0, z=0),
    ),
    'front': dict(
        eye=dict(x=0.001, y=-2.4, z=0.55),
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
    ),
    'side': dict(
        eye=dict(x=2.4, y=0.001, z=0.55),
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
    ),
}


class Warehouse3DRenderer:
    """Renders an interactive 3D digital-twin of the warehouse using Plotly 3D."""

    def __init__(self, grid: WarehouseGrid):
        self.grid = grid

    def _create_cuboid_traces(
        self,
        x: float,
        y: float,
        z_min: float,
        z_max: float,
        dx: float = 0.85,
        dy: float = 0.85,
        color: str = "#34495E",
        opacity: float = 0.9,
        name: str = "Shelf",
    ) -> go.Mesh3d:
        """Constructs a 3D box/cuboid mesh for shelves or obstacles."""
        x0, x1 = x - dx / 2, x + dx / 2
        y0, y1 = y - dy / 2, y + dy / 2
        z0, z1 = z_min, z_max

        vx = [x0, x1, x1, x0, x0, x1, x1, x0]
        vy = [y0, y0, y1, y1, y0, y0, y1, y1]
        vz = [z0, z0, z0, z0, z1, z1, z1, z1]

        i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
        j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
        k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]

        return go.Mesh3d(
            x=vx,
            y=vy,
            z=vz,
            i=i,
            j=j,
            k=k,
            color=color,
            opacity=opacity,
            flatshading=True,
            name=name,
            showlegend=False,
            hoverinfo="name",
        )

    def render_3d(
        self,
        robots: Dict[int, RobotState],
        step_count: int,
        deadlock_cycles: Optional[List[List[int]]] = None,
        updated_paths: Optional[Dict[int, List[Tuple[int, int]]]] = None,
        height: int = 700,
        camera_view: str = 'iso',
        theme: str = 'dark',
        congestion_heatmap: Optional[Dict[Tuple[int, int], float]] = None,
        shelf_optimizations: Optional[List[Dict[str, Any]]] = None,
        selected_robot_id: Optional[int] = None,
        show_trails: bool = True,
        show_paths: bool = True,
        show_beacons: bool = True,
        show_heatmaps: bool = True,
        show_labels: bool = True,
        show_grid: bool = True,
    ) -> go.Figure:
        """
        Generates interactive 3D digital-twin containing warehouse layout, perimeter walls,
        active task pickup/delivery beacons, mission rays, robot telemetry, deadlock alerts,
        congestion heatmap overlays, and shelf optimization recommendations.
        """
        fig = go.Figure()
        w, h = self.grid.width, self.grid.height

        is_dark = (theme == 'dark')
        floor_color = [[0, "#0F172A"], [1, "#1E293B"]] if is_dark else [[0, "#F2F4F4"], [1, "#E5E8E8"]]
        grid_color = "#334155" if is_dark else "#BDC3C7"
        wall_color = "#0284C7" if is_dark else "#7F8C8D"
        shelf_color = "#1E293B" if is_dark else "#2C3E50"
        bg_color = "rgba(10,22,40,1.0)" if is_dark else "#F8F9FA"
        axis_font_color = "#94A3B8" if is_dark else "#2C3E50"

        # 1. Warehouse Floor Grid Surface
        fig.add_trace(go.Surface(
            x=[[-0.5, w - 0.5], [-0.5, w - 0.5]],
            y=[[-0.5, -0.5], [h - 0.5, h - 0.5]],
            z=[[0, 0], [0, 0]],
            colorscale=floor_color,
            showscale=False,
            opacity=0.98 if is_dark else 0.95,
            name="Floor",
            hoverinfo="skip",
        ))

        # Floor gridlines
        if show_grid:
            grid_lines_x, grid_lines_y, grid_lines_z = [], [], []
            for x in range(w + 1):
                grid_lines_x.extend([x - 0.5, x - 0.5, None])
                grid_lines_y.extend([-0.5, h - 0.5, None])
                grid_lines_z.extend([0.005, 0.005, None])
            for y in range(h + 1):
                grid_lines_x.extend([-0.5, w - 0.5, None])
                grid_lines_y.extend([y - 0.5, y - 0.5, None])
                grid_lines_z.extend([0.005, 0.005, None])

            fig.add_trace(go.Scatter3d(
                x=grid_lines_x,
                y=grid_lines_y,
                z=grid_lines_z,
                mode='lines',
                line=dict(color=grid_color, width=1.5),
                hoverinfo='skip',
                showlegend=False,
            ))

        # 1b. Perimeter Boundary Walls
        wall_x = [-0.5, w - 0.5, w - 0.5, -0.5, -0.5]
        wall_y = [-0.5, -0.5, h - 0.5, h - 0.5, -0.5]
        wall_z_top = [0.45] * 5

        fig.add_trace(go.Scatter3d(
            x=wall_x,
            y=wall_y,
            z=wall_z_top,
            mode='lines',
            line=dict(color=wall_color, width=3.5 if is_dark else 3),
            name="Perimeter Wall",
            showlegend=False,
            hoverinfo='skip',
        ))

        # 1c. Congestion Heatmap Floor Overlay (Module 10)
        if show_heatmaps and congestion_heatmap:
            heat_x, heat_y, heat_z, heat_c, heat_text = [], [], [], [], []
            for (cx, cy), c_val in congestion_heatmap.items():
                if c_val > 0.05:
                    heat_x.append(cx)
                    heat_y.append(cy)
                    heat_z.append(0.012)
                    heat_c.append(c_val)
                    severity = "Critical" if c_val >= 0.75 else "High" if c_val >= 0.5 else "Moderate"
                    heat_text.append(f"Congestion: {c_val:.2f} ({severity})")

            if heat_x:
                fig.add_trace(go.Scatter3d(
                    x=heat_x,
                    y=heat_y,
                    z=heat_z,
                    mode='markers',
                    marker=dict(
                        symbol='square',
                        size=15,
                        color=heat_c,
                        colorscale='YlOrRd',
                        cmin=0.0,
                        cmax=1.0,
                        opacity=0.65,
                        showscale=False,
                    ),
                    text=heat_text,
                    hoverinfo='text',
                    name="Congestion Heatmap",
                ))

        # 2. Charging Docks (Green pads)
        dock_x = [d[0] for d in self.grid.charging_docks]
        dock_y = [d[1] for d in self.grid.charging_docks]
        dock_z = [0.03] * len(dock_x)
        fig.add_trace(go.Scatter3d(
            x=dock_x,
            y=dock_y,
            z=dock_z,
            mode='markers+text' if show_labels else 'markers',
            marker=dict(symbol='square', size=14, color='#10B981', line=dict(color='#059669', width=2)),
            text=[f"Dock {i+1}" for i in range(len(dock_x))],
            textposition='top center',
            textfont=dict(size=9, color='#10B981' if is_dark else '#1E8449'),
            name="Charging Docks",
        ))

        # 3. Packing Stations (Orange pads)
        pack_x = [p[0] for p in self.grid.packing_stations]
        pack_y = [p[1] for p in self.grid.packing_stations]
        pack_z = [0.03] * len(pack_x)
        fig.add_trace(go.Scatter3d(
            x=pack_x,
            y=pack_y,
            z=pack_z,
            mode='markers+text' if show_labels else 'markers',
            marker=dict(symbol='square', size=14, color='#F59E0B', line=dict(color='#D97706', width=2)),
            text=[f"Pack {i+1}" for i in range(len(pack_x))],
            textposition='bottom center',
            textfont=dict(size=9, color='#F59E0B' if is_dark else '#B9770E'),
            name="Packing Stations",
        ))

        # 4. Storage Shelves (3D Racks)
        for sx, sy in self.grid.shelves:
            shelf_mesh = self._create_cuboid_traces(
                x=sx,
                y=sy,
                z_min=0.0,
                z_max=1.2,
                dx=0.82,
                dy=0.82,
                color=shelf_color,
                name="Shelf Rack",
            )
            fig.add_trace(shelf_mesh)

        # 4b. Shelf Relocation Recommendations (Module 10)
        if shelf_optimizations:
            opt_x, opt_y, opt_z, opt_text = [], [], [], []
            for rec in shelf_optimizations:
                s_pos = rec.get('shelf')
                if s_pos:
                    opt_x.append(s_pos[0])
                    opt_y.append(s_pos[1])
                    opt_z.append(1.35)
                    tgt = rec.get('target_swap', '')
                    opt_text.append(f"🔄 SWAP -> {tgt}")

            if opt_x:
                fig.add_trace(go.Scatter3d(
                    x=opt_x,
                    y=opt_y,
                    z=opt_z,
                    mode='markers+text',
                    marker=dict(size=9, color='#F59E0B', symbol='diamond'),
                    text=opt_text,
                    textposition='top center',
                    textfont=dict(size=8, color='#FBBF24', family='Arial Bold'),
                    name="Shelf Relocation Advisory",
                ))

        # 5. Dynamic Obstacles (Hazard Red 3D Blocks)
        for ox, oy in self.grid.dynamic_obstacles:
            obs_mesh = self._create_cuboid_traces(
                x=ox,
                y=oy,
                z_min=0.0,
                z_max=0.9,
                dx=0.86,
                dy=0.86,
                color="#EF4444",
                name="Dynamic Obstacle",
            )
            fig.add_trace(obs_mesh)

        # Legend proxies
        fig.add_trace(go.Scatter3d(
            x=[None], y=[None], z=[None],
            mode='markers',
            marker=dict(size=10, color=shelf_color, symbol='square'),
            name="Shelf Racks (3D)",
        ))
        if self.grid.dynamic_obstacles:
            fig.add_trace(go.Scatter3d(
                x=[None], y=[None], z=[None],
                mode='markers',
                marker=dict(size=10, color='#EF4444', symbol='square'),
                name="Dynamic Obstacles",
            ))

            obs_x = [o[0] for o in self.grid.dynamic_obstacles]
            obs_y = [o[1] for o in self.grid.dynamic_obstacles]
            obs_z = [1.05] * len(obs_x)
            fig.add_trace(go.Scatter3d(
                x=obs_x,
                y=obs_y,
                z=obs_z,
                mode='markers+text',
                marker=dict(size=12, color='#EF4444', symbol='diamond'),
                text=["⚠️ OBSTACLE"] * len(obs_x),
                textposition='top center',
                textfont=dict(size=9, color='#EF4444', family='Arial Black'),
                name="Obstacle Alert",
                showlegend=False,
            ))

        # Flatten deadlock cycles to a set of affected robot IDs
        deadlocked_robot_ids: Set[int] = set()
        if deadlock_cycles:
            for c in deadlock_cycles:
                deadlocked_robot_ids.update(c)

        # 6. Task Mission Beacons & Connecting Mission Rays
        if show_beacons:
            for r_id, robot in robots.items():
                if robot.assigned_task:
                    task = robot.assigned_task
                    p_color = PRIORITY_COLORS.get(int(getattr(task, 'priority', 2)), "#3498DB")

                    # Pickup spot beacon
                    fig.add_trace(go.Scatter3d(
                        x=[task.pick_spot[0]],
                        y=[task.pick_spot[1]],
                        z=[0.25],
                        mode='markers+text' if show_labels else 'markers',
                        marker=dict(size=10, color=p_color, symbol='diamond-open', line=dict(color=p_color, width=2.5)),
                        text=[f"Pick T#{task.task_id}"],
                        textposition='top center',
                        textfont=dict(size=8, color=p_color, family='Arial Bold'),
                        name=f"Pick T#{task.task_id}",
                        showlegend=False,
                    ))

                    # Mission ray: connecting robot to current mission target
                    target_pos = task.pick_spot if robot.state in ('MOVING_TO_PICK', 'PICKING') else task.delivery_station
                    fig.add_trace(go.Scatter3d(
                        x=[robot.pos[0], target_pos[0]],
                        y=[robot.pos[1], target_pos[1]],
                        z=[0.30, 0.30],
                        mode='lines',
                        line=dict(color=p_color, width=2, dash='dashdot'),
                        name=f"Task T#{task.task_id} Ray",
                        hoverinfo='name',
                        showlegend=False,
                    ))

        # 7. Planned Paths and Recent Movement Trails
        for r_id, robot in robots.items():
            color = ROBOT_COLORS.get(r_id, '#7F8C8D')

            # Recent trail trace
            if show_trails and robot.trail and len(robot.trail) > 1:
                tx = [p[0] for p in robot.trail]
                ty = [p[1] for p in robot.trail]
                tz = [0.04] * len(tx)
                fig.add_trace(go.Scatter3d(
                    x=tx,
                    y=ty,
                    z=tz,
                    mode='lines',
                    line=dict(color=color, width=2, dash='dot'),
                    name=f"Trail R{r_id}",
                    hoverinfo='skip',
                    showlegend=False,
                ))

            # Active remaining planned path
            if show_paths and robot.path and len(robot.path) > 1:
                rem_path = robot.path[robot.path_index:]
                px = [p[0] for p in rem_path]
                py = [p[1] for p in rem_path]
                pz = [0.08] * len(px)
                fig.add_trace(go.Scatter3d(
                    x=px,
                    y=py,
                    z=pz,
                    mode='lines',
                    line=dict(color=color, width=5, dash='solid'),
                    name=f"Path R{r_id}",
                    hoverinfo='name',
                ))

            # Optional dynamically updated replanned path overlay
            if updated_paths and r_id in updated_paths:
                up_path = updated_paths[r_id]
                if up_path:
                    ux = [p[0] for p in up_path]
                    uy = [p[1] for p in up_path]
                    uz = [0.12] * len(ux)
                    fig.add_trace(go.Scatter3d(
                        x=ux,
                        y=uy,
                        z=uz,
                        mode='lines',
                        line=dict(color='#E67E22', width=4, dash='dash'),
                        name=f"Replanned R{r_id}",
                        hoverinfo='name',
                    ))

            # Destination marker
            if robot.goal is not None and robot.state not in ('IDLE', 'DOCKED'):
                fig.add_trace(go.Scatter3d(
                    x=[robot.goal[0]],
                    y=[robot.goal[1]],
                    z=[0.09],
                    mode='markers',
                    marker=dict(symbol='circle-open', size=12, color=color, line=dict(width=3)),
                    name=f"Goal R{r_id}",
                    hoverinfo='name',
                    showlegend=False,
                ))

        # 8. Robots (3D Mobile Units) with Direction Cues and Telemetry
        rx, ry, rz = [], [], []
        r_colors = []
        r_labels = []
        r_hovers = []

        for r_id, robot in sorted(robots.items()):
            base_color = ROBOT_COLORS.get(r_id, '#3498DB')
            if robot.state in ('PICKING', 'DELIVERING'):
                status_color = '#F59E0B'
            elif robot.state == 'IDLE':
                status_color = '#94A3B8'
            else:
                status_color = base_color

            rx.append(robot.pos[0])
            ry.append(robot.pos[1])
            rz.append(0.35)
            r_colors.append(status_color)
            r_labels.append(f"R{r_id}")

            task_info = f"Task #{robot.assigned_task.task_id} ({robot.assigned_task.priority_label})" if robot.assigned_task else "None"
            battery_val = getattr(robot, 'battery', 100.0)
            completed_val = getattr(robot, 'completed_tasks', 0)
            dist_val = getattr(robot, 'total_distance', 0)

            r_hovers.append(
                f"<b>Robot R{r_id}</b><br>"
                f"State: {robot.state}<br>"
                f"Pos: {robot.pos} | Goal: {robot.goal}<br>"
                f"Assigned: {task_info}<br>"
                f"Battery: {battery_val:.1f}%<br>"
                f"Completed: {completed_val} tasks | Dist: {dist_val}m"
            )

        fig.add_trace(go.Scatter3d(
            x=rx,
            y=ry,
            z=rz,
            mode='markers+text',
            marker=dict(
                size=18,
                color=r_colors,
                symbol='circle',
                line=dict(color='#FFFFFF', width=2),
            ),
            text=r_labels,
            textposition='middle center',
            textfont=dict(color='#FFFFFF', size=10, family='Arial Black'),
            hovertext=r_hovers,
            hoverinfo='text',
            name="Robot Fleet",
        ))

        # 8b. Selected Robot Highlight Beacon (Module 10)
        if selected_robot_id and selected_robot_id in robots:
            sel_r = robots[selected_robot_id]
            fig.add_trace(go.Scatter3d(
                x=[sel_r.pos[0]],
                y=[sel_r.pos[1]],
                z=[0.75],
                mode='markers+text',
                marker=dict(size=14, color='#00F0FF', symbol='diamond'),
                text=[f"🎯 R{selected_robot_id}"],
                textposition='top center',
                textfont=dict(color='#00F0FF', size=10, family='Arial Bold'),
                name=f"Selected Robot R{selected_robot_id}",
                showlegend=False,
            ))

        # 9. Deadlock Warning Indicators
        if deadlocked_robot_ids:
            dl_x, dl_y, dl_z, dl_text = [], [], [], []
            for r_id in deadlocked_robot_ids:
                if r_id in robots:
                    bot = robots[r_id]
                    dl_x.append(bot.pos[0])
                    dl_y.append(bot.pos[1])
                    dl_z.append(1.0)
                    dl_text.append(f"⚠️ DEADLOCK: R{r_id}")

            fig.add_trace(go.Scatter3d(
                x=dl_x,
                y=dl_y,
                z=dl_z,
                mode='markers+text',
                marker=dict(size=14, color='#EF4444', symbol='diamond'),
                text=dl_text,
                textposition='top center',
                textfont=dict(color='#EF4444', size=11, family='Arial Black'),
                name="Deadlock Warning",
            ))

        # Camera layout
        cam_setting = CAMERA_PRESETS.get(camera_view, CAMERA_PRESETS['iso'])

        fig.update_layout(
            title=dict(
                text=f"<b>SmartWarehouse 3D Digital Twin</b> — Step: {step_count}",
                x=0.05,
                y=0.96,
                font=dict(size=16, color=axis_font_color),
            ),
            paper_bgcolor=bg_color,
            plot_bgcolor=bg_color,
            height=height,
            margin=dict(l=0, r=0, t=40, b=0),
            scene=dict(
                xaxis=dict(
                    title="X (m)",
                    range=[-0.5, w - 0.5],
                    backgroundcolor=bg_color,
                    gridcolor=grid_color,
                    showbackground=True,
                    dtick=2,
                    color=axis_font_color,
                ),
                yaxis=dict(
                    title="Y (m)",
                    range=[h - 0.5, -0.5],
                    backgroundcolor=bg_color,
                    gridcolor=grid_color,
                    showbackground=True,
                    dtick=2,
                    color=axis_font_color,
                ),
                zaxis=dict(
                    title="Z (m)",
                    range=[0, 1.8],
                    backgroundcolor=bg_color,
                    gridcolor=grid_color,
                    showbackground=True,
                    dtick=0.5,
                    color=axis_font_color,
                ),
                aspectmode="manual",
                aspectratio=dict(x=1.0, y=1.0, z=0.25),
                camera=cam_setting,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.08,
                xanchor="center",
                x=0.5,
                font=dict(size=10, color=axis_font_color),
            ),
        )

        return fig
