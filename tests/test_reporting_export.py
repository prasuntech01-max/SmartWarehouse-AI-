"""Unit tests for the Reporting and Export system (Module 13 Stage 3)."""

import pytest
import zipfile
import io
import pandas as pd
from simulation.engine import WarehouseSimulator
from analytics.service import AnalyticsService
from reporting.csv_exporter import sanitize_for_csv, export_dataframe_to_csv
from reporting.html_exporter import generate_executive_html_report
from reporting.zip_exporter import generate_report_zip_bundle
from reporting.builder import ReportBuilder
from persistence.repo import ReportRepo


@pytest.fixture
def sim():
    return WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)


@pytest.fixture
def analytics_service(sim):
    return AnalyticsService(sim)


def test_csv_sanitization_neutralizes_formula_injection():
    assert sanitize_for_csv("=1+1") == "'=1+1"
    assert sanitize_for_csv("+cmd") == "'+cmd"
    assert sanitize_for_csv("-2+3") == "'-2+3"
    assert sanitize_for_csv("@SUM(A1)") == "'@SUM(A1)"
    assert sanitize_for_csv("Normal Text") == "Normal Text"
    assert sanitize_for_csv(123) == 123


def test_csv_export_bytes():
    df = pd.DataFrame([{"Title": "=1+1", "Count": 42}])
    csv_bytes = export_dataframe_to_csv(df)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    text = csv_bytes.decode("utf-8-sig")
    assert "'=1+1" in text
    assert "42" in text


def test_html_report_generation(analytics_service):
    snap = analytics_service.get_snapshot()
    df_fleet = analytics_service.get_fleet_dataframe()
    html_doc = generate_executive_html_report(snap, title="Test Report", df_fleet=df_fleet)
    assert "<!DOCTYPE html>" in html_doc
    assert "Test Report" in html_doc
    assert "@media print" in html_doc
    assert "window.print()" in html_doc
    assert "R1" in html_doc


def test_zip_bundle_integrity(analytics_service):
    snap = analytics_service.get_snapshot()
    df_fleet = analytics_service.get_fleet_dataframe()
    zip_bytes = generate_report_zip_bundle(snap, df_fleet=df_fleet)
    
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "Executive_Report.html" in namelist
        assert "Fleet_Status.csv" in namelist
        assert "MANIFEST.txt" in namelist
        manifest = zf.read("MANIFEST.txt").decode("utf-8")
        assert "ARCHIVE CHECKSUMS (SHA-256):" in manifest


def test_report_builder_and_persistence(analytics_service):
    builder = ReportBuilder(analytics_service)
    result = builder.build_report(title="Persistence Verification Report", generated_by="TEST_ADMIN", persist=True)
    assert "report_id" in result
    assert result["report_id"].startswith("REP-")
    assert len(result["zip_bundle"]) > 0

    saved_reports = ReportRepo.list_reports(limit=5)
    matching = [r for r in saved_reports if r["report_id"] == result["report_id"]]
    assert len(matching) == 1
    assert matching[0]["generated_by"] == "TEST_ADMIN"
