"""Interactive 3D warehouse visualization using Plotly."""

from typing import Dict, List, Tuple, Optional, Any
import plotly.graph_objects as go
from core.grid import WarehouseGrid
from simulation.engine import RobotState
from visualization.renderer import ROBOT_COLORS


class Warehouse3DRenderer:
    """Renders a 3D digital-twin of the warehouse using Plotly 3D."""

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

        # 8 vertices of a cuboid
        vx = [x0, x1, x1, x0, x0, x1, x1, x0]
        vy = [y0, y0, y1, y1, y0, y0, y1, y1]
        vz = [z0, z0, z0, z0, z1, z1, z1, z1]

        # 12 triangular faces
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
        height: int = 700,
    ) -> go.Figure:
        """
        Generates interactive 3D scene containing floor, shelves, docks,
        stations, dynamic obstacles, robot bodies, trails, and deadlock alerts.
        """
        fig = go.Figure()
        w, h = self.grid.width, self.grid.height

        # 1. Warehouse Floor Grid Surface
        fig.add_trace(go.Surface(
            x=[[-0.5, w - 0.5], [-0.5, w - 0.5]],
            y=[[-0.5, -0.5], [h - 0.5, h - 0.5]],
            z=[[0, 0], [0, 0]],
            colorscale=[[0, "#F2F4F4"], [1, "#E5E8E8"]],
            showscale=False,
            opacity=0.95,
            name="Floor",
            hoverinfo="skip",
        ))

        # Floor gridlines
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
            line=dict(color='#BDC3C7', width=1.5),
            hoverinfo='skip',
            showlegend=False,
        ))

        # 2. Charging Docks (Green pads)
        dock_x = [d[0] for d in self.grid.charging_docks]
        dock_y = [d[1] for d in self.grid.charging_docks]
        dock_z = [0.03] * len(dock_x)
        fig.add_trace(go.Scatter3d(
            x=dock_x,
            y=dock_y,
            z=dock_z,
            mode='markers+text',
            marker=dict(symbol='square', size=14, color='#2ECC71', line=dict(color='#27AE60', width=2)),
            text=[f"Dock {i+1}" for i in range(len(dock_x))],
            textposition='top center',
            textfont=dict(size=9, color='#1E8449'),
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
            mode='markers+text',
            marker=dict(symbol='square', size=14, color='#F39C12', line=dict(color='#D35400', width=2)),
            text=[f"Pack {i+1}" for i in range(len(pack_x))],
            textposition='bottom center',
            textfont=dict(size=9, color='#B9770E'),
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
                color="#2C3E50",
                name="Shelf Rack",
            )
            fig.add_trace(shelf_mesh)

        # 5. Dynamic Obstacles (Hazard Red 3D Blocks)
        for ox, oy in self.grid.dynamic_obstacles:
            obs_mesh = self._create_cuboid_traces(
                x=ox,
                y=oy,
                z_min=0.0,
                z_max=0.9,
                dx=0.86,
                dy=0.86,
                color="#E74C3C",
                name="Dynamic Obstacle",
            )
            fig.add_trace(obs_mesh)

        # Flat legend proxies for Shelves and Dynamic Obstacles
        fig.add_trace(go.Scatter3d(
            x=[None], y=[None], z=[None],
            mode='markers',
            marker=dict(size=10, color='#2C3E50', symbol='square'),
            name="Shelf Racks (3D)",
        ))
        if self.grid.dynamic_obstacles:
            fig.add_trace(go.Scatter3d(
                x=[None], y=[None], z=[None],
                mode='markers',
                marker=dict(size=10, color='#E74C3C', symbol='square'),
                name="Dynamic Obstacles",
            ))

        # Flatten deadlock cycles to a set of affected robot IDs
        deadlocked_robot_ids: Set[int] = set()
        if deadlock_cycles:
            for c in deadlock_cycles:
                deadlocked_robot_ids.update(c)

        # 6. Planned Paths (3D Floating Lines)
        for r_id, robot in robots.items():
            color = ROBOT_COLORS.get(r_id, '#7F8C8D')
            if robot.path and len(robot.path) > 1:
                # Remaining trajectory
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

        # 7. Robots (3D Mobile Units)
        rx, ry, rz = [], [], []
        r_colors = []
        r_labels = []
        r_hovers = []

        for r_id, robot in sorted(robots.items()):
            color = ROBOT_COLORS.get(r_id, '#3498DB')
            rx.append(robot.pos[0])
            ry.append(robot.pos[1])
            rz.append(0.35)
            r_colors.append(color)
            r_labels.append(f"R{r_id}")
            r_hovers.append(
                f"<b>Robot R{r_id}</b><br>State: {robot.state}<br>Pos: {robot.pos}<br>Goal: {robot.goal}"
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

        # 8. Deadlock Warning Indicators
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
                marker=dict(size=14, color='#E74C3C', symbol='diamond'),
                text=dl_text,
                textposition='top center',
                textfont=dict(color='#E74C3C', size=11, family='Arial Black'),
                name="Deadlock Warning",
            ))

        # Scene camera and axes layout
        fig.update_layout(
            title=dict(
                text=f"<b>SmartWarehouse 3D Digital Twin</b> — Step: {step_count}",
                x=0.05,
                y=0.96,
                font=dict(size=16, color='#2C3E50'),
            ),
            height=height,
            margin=dict(l=0, r=0, t=40, b=0),
            scene=dict(
                xaxis=dict(
                    title="X (m)",
                    range=[-0.5, w - 0.5],
                    backgroundcolor="#F8F9FA",
                    gridcolor="#BDC3C7",
                    showbackground=True,
                    dtick=1,
                ),
                yaxis=dict(
                    title="Y (m)",
                    range=[h - 0.5, -0.5],  # Invert so Y=0 is top
                    backgroundcolor="#F8F9FA",
                    gridcolor="#BDC3C7",
                    showbackground=True,
                    dtick=1,
                ),
                zaxis=dict(
                    title="Z (m)",
                    range=[0, 1.8],
                    backgroundcolor="#EAEDED",
                    gridcolor="#BDC3C7",
                    showbackground=True,
                    dtick=0.5,
                ),
                aspectmode="manual",
                aspectratio=dict(x=1.0, y=1.0, z=0.25),
                camera=dict(
                    eye=dict(x=1.25, y=-1.35, z=1.35),
                    up=dict(x=0, y=0, z=1),
                    center=dict(x=0, y=0, z=-0.1),
                ),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.08,
                xanchor="center",
                x=0.5,
                font=dict(size=10),
            ),
        )

        return fig
