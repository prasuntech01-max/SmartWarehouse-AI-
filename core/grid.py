"""Warehouse grid module.

Re-exports Warehouse and WarehouseGrid directly from warehouse.py
to maintain a single canonical definition across the codebase.
"""

from warehouse import Warehouse, WarehouseGrid

__all__ = ["Warehouse", "WarehouseGrid"]
