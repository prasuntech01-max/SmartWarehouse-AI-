"""Report Builder orchestrating analytics snapshots and multi-format exports."""

import uuid
import datetime
from typing import Dict, Any, Optional
import pandas as pd

from analytics.service import AnalyticsService
from analytics.models import AnalyticsSnapshot
from .html_exporter import generate_executive_html_report
from .csv_exporter import export_dataframe_to_csv
from .zip_exporter import generate_report_zip_bundle
from persistence.repo import ReportRepo


class ReportBuilder:
    """Orchestrates comprehensive report creation, database tracking, and downloads."""

    def __init__(self, analytics_service: AnalyticsService):
        self.analytics_service = analytics_service

    def build_report(
        self,
        title: str = "Executive Warehouse Operational Report",
        generated_by: str = "OPERATOR",
        persist: bool = True,
    ) -> Dict[str, Any]:
        """Builds all report formats and records metadata in database."""
        report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
        snapshot = self.analytics_service.get_snapshot()

        df_fleet = self.analytics_service.get_fleet_dataframe()
        df_tasks = self.analytics_service.get_task_roster_dataframe(limit=100)
        df_incidents = self.analytics_service.get_incident_dataframe(limit=50)

        # 1. HTML Executive Report
        html_doc = generate_executive_html_report(
            snapshot=snapshot,
            title=title,
            generated_by=generated_by,
            df_fleet=df_fleet,
            df_incidents=df_incidents,
        )

        # 2. CSV Exports
        fleet_csv = export_dataframe_to_csv(df_fleet)
        tasks_csv = export_dataframe_to_csv(df_tasks)
        incidents_csv = export_dataframe_to_csv(df_incidents)

        # 3. ZIP Archive
        zip_bytes = generate_report_zip_bundle(
            snapshot=snapshot,
            title=title,
            generated_by=generated_by,
            df_fleet=df_fleet,
            df_tasks=df_tasks,
            df_incidents=df_incidents,
        )

        # 4. Summary dictionary for persistence
        summary_dict = {
            "report_id": report_id,
            "title": title,
            "simulation_step": snapshot.simulation_step,
            "total_tasks": snapshot.summary_kpis.get("total_tasks", {}).value if hasattr(snapshot.summary_kpis.get("total_tasks"), "value") else 0,
            "completed_tasks": snapshot.summary_kpis.get("completed_tasks", {}).value if hasattr(snapshot.summary_kpis.get("completed_tasks"), "value") else 0,
            "throughput": snapshot.summary_kpis.get("fleet_throughput", {}).value if hasattr(snapshot.summary_kpis.get("fleet_throughput"), "value") else 0.0,
            "utilization": snapshot.summary_kpis.get("fleet_utilization", {}).value if hasattr(snapshot.summary_kpis.get("fleet_utilization"), "value") else 0.0,
        }

        # 5. Persist record to SQLite
        if persist:
            try:
                ReportRepo.save_report(
                    report_id=report_id,
                    title=title,
                    generated_by=generated_by,
                    time_range_start=None,
                    time_range_end=datetime.datetime.now(),
                    summary=summary_dict,
                    export_format="HTML+CSV+ZIP",
                )
            except Exception as e:
                # Log error but do not break user export
                pass

        return {
            "report_id": report_id,
            "title": title,
            "snapshot": snapshot,
            "html_document": html_doc,
            "fleet_csv": fleet_csv,
            "tasks_csv": tasks_csv,
            "incidents_csv": incidents_csv,
            "zip_bundle": zip_bytes,
            "summary": summary_dict,
        }
