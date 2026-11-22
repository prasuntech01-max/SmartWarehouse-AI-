"""Matplotlib-based warehouse grid renderer."""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, List, Tuple, Optional
from core.grid import WarehouseGrid
from simulation.engine import RobotState


ROBOT_COLORS = {
    1: '#1E88E5',  # Vivid Blue
    2: '#E53935',  # Crimson Red
    3: '#43A047',  # Emerald Green
    4: '#8E24AA',  # Purple
    5: '#FB8C00',  # Warm Amber
}


class WarehouseRenderer:
    def __init__(self, grid: WarehouseGrid):
        self.grid = grid

    def render(
        self,
        robots: Dict[int, RobotState],
        step_count: int,
        figsize: Tuple[float, float] = (8.5, 8.5),
    ) -> plt.Figure:
        """
        Renders the warehouse grid, shelves, stations, dynamic obstacles,
        robot trails, and current robot positions onto a Matplotlib figure.
        """
        fig, ax = plt.subplots(figsize=figsize, dpi=100)
        ax.set_facecolor('#F8F9FA')

        w, h = self.grid.width, self.grid.height

        # Set axes limits and invert y-axis so (0,0) is top-left
        ax.set_xlim(-0.5, w - 0.5)
        ax.set_ylim(h - 0.5, -0.5)
        ax.set_aspect('equal')

        # Grid lines
        ax.set_xticks(range(w))
        ax.set_yticks(range(h))
        ax.grid(color='#E0E0E0', linestyle='-', linewidth=0.8, alpha=0.8)

        # 1. Render Shelves
        for sx, sy in self.grid.shelves:
            shelf_rect = patches.Rectangle(
                (sx - 0.45, sy - 0.45),
                0.9,
                0.9,
                linewidth=1,
                edgecolor='#2C3E50',
                facecolor='#34495E',
                zorder=2,
            )
            ax.add_patch(shelf_rect)

        # 2. Render Charging Docks (top)
        for dx, dy in self.grid.charging_docks:
            dock_rect = patches.Rectangle(
                (dx - 0.42, dy - 0.42),
                0.84,
                0.84,
                linewidth=1.2,
                edgecolor='#27AE60',
                facecolor='#E8F8F5',
                linestyle='--',
                zorder=2,
            )
            ax.add_patch(dock_rect)
            ax.text(dx, dy, 'D', ha='center', va='center', fontsize=9, fontweight='bold', color='#27AE60', zorder=3)

        # 3. Render Delivery / Packing Stations (bottom)
        for px, py in self.grid.packing_stations:
            pack_rect = patches.Rectangle(
                (px - 0.42, py - 0.42),
                0.84,
                0.84,
                linewidth=1.2,
                edgecolor='#E67E22',
                facecolor='#FEF9E7',
                linestyle='--',
                zorder=2,
            )
            ax.add_patch(pack_rect)
            ax.text(px, py, 'P', ha='center', va='center', fontsize=9, fontweight='bold', color='#D35400', zorder=3)

        # 4. Render Dynamic Obstacles
        for ox, oy in self.grid.dynamic_obstacles:
            obs_rect = patches.Rectangle(
                (ox - 0.45, oy - 0.45),
                0.9,
                0.9,
                linewidth=1.5,
                edgecolor='#C0392B',
                facecolor='#FADBD8',
                hatch='//',
                zorder=3,
            )
            ax.add_patch(obs_rect)
            ax.text(ox, oy, 'X', ha='center', va='center', fontsize=11, fontweight='bold', color='#C0392B', zorder=4)

        # 5. Render Robot Trails and Goals
        for r_id, robot in robots.items():
            color = ROBOT_COLORS.get(r_id, '#555555')

            # Render Goal Target Marker if robot is on mission
            if robot.goal is not None and robot.state not in ('IDLE', 'DOCKED'):
                gx, gy = robot.goal
                goal_circle = patches.Circle(
                    (gx, gy),
                    0.35,
                    edgecolor=color,
                    facecolor='none',
                    linestyle=':',
                    linewidth=2.0,
                    zorder=4,
                )
                ax.add_patch(goal_circle)

            # Render Trail
            if len(robot.trail) > 1:
                trail_x = [pos[0] for pos in robot.trail]
                trail_y = [pos[1] for pos in robot.trail]
                ax.plot(
                    trail_x,
                    trail_y,
                    color=color,
                    linestyle='-',
                    linewidth=2.5,
                    alpha=0.35,
                    zorder=3,
                )

        # 6. Render Robots
        for r_id, robot in robots.items():
            color = ROBOT_COLORS.get(r_id, '#555555')
            rx, ry = robot.pos

            # Robot Outer Circle
            robot_circle = patches.Circle(
                (rx, ry),
                0.38,
                facecolor=color,
                edgecolor='#FFFFFF',
                linewidth=1.8,
                zorder=5,
            )
            ax.add_patch(robot_circle)

            # Robot ID text
            ax.text(
                rx,
                ry,
                f"R{r_id}",
                ha='center',
                va='center',
                color='#FFFFFF',
                fontsize=8,
                fontweight='bold',
                zorder=6,
            )

        ax.set_title(
            f"Warehouse Floorplan (15x15) — Step: {step_count}",
            fontsize=12,
            fontweight='bold',
            pad=10,
        )

        # Add custom Legend at bottom
        legend_handles = [
            patches.Patch(facecolor='#34495E', edgecolor='#2C3E50', label='Shelf Pod'),
            patches.Patch(facecolor='#E8F8F5', edgecolor='#27AE60', label='Dock (D)'),
            patches.Patch(facecolor='#FEF9E7', edgecolor='#E67E22', label='Delivery (P)'),
            patches.Patch(facecolor='#FADBD8', edgecolor='#C0392B', hatch='//', label='Obstacle (X)'),
        ]
        for r_id in sorted(robots.keys()):
            legend_handles.append(
                patches.Patch(facecolor=ROBOT_COLORS.get(r_id, '#777'), label=f"Robot R{r_id}")
            )

        ax.legend(
            handles=legend_handles,
            loc='upper center',
            bbox_to_anchor=(0.5, -0.06),
            ncol=min(6, len(legend_handles)),
            frameon=True,
            facecolor='#FFFFFF',
            edgecolor='#D0D0D0',
            fontsize=8,
        )

        plt.tight_layout()
        return fig
