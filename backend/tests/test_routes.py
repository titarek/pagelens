import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.cache import storage
from app.schemas.report import Report, ScoreBreakdown, StructuralMetrics, SiteMetadata, SecurityAudit

client = TestClient(app)


def test_analyze_endpoint_rejects_ssrf():
    response = client.post("/api/v1/analyze", json={"url": "http://localhost:8000"})
    assert response.status_code == 400
    assert "SSRF" in response.json()["error_type"]


def test_analyze_endpoint_queues_job(monkeypatch):
    # Mock validate_and_resolve_url so it doesn't fail on external host lookup in test runner
    from app.api import routes_analyze
    monkeypatch.setattr(
        routes_analyze, "validate_and_resolve_url", lambda url: (url, "93.184.216.34")
    )

    response = client.post("/api/v1/analyze", json={"url": "https://example.com", "mode": "static"})
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["url"] == "https://example.com"


def test_get_report_not_found():
    response = client.get("/api/v1/report/non-existent-uuid")
    assert response.status_code == 404


def test_get_report_and_export_json_and_pdf():
    job_id = "test-job-12345"
    mock_report = {
        "job_id": job_id,
        "url": "https://example.com",
        "final_url": "https://example.com",
        "fetched_at": "2026-10-15T12:00:00Z",
        "mode": "static",
        "status": "ok",
        "score": {
            "total": 92,
            "structure": 23,
            "timing": 32,
            "shortcomings": 23,
            "security": 14,
        },
        "structural": {
            "html_bytes": 12000,
            "css_bytes": 8000,
            "js_bytes": 15000,
            "image_bytes": 25000,
            "font_bytes": 10000,
            "total_bytes": 70000,
            "num_requests": 8,
            "num_dom_elements": 120,
            "num_stylesheets": 1,
            "num_scripts": 2,
            "num_blocking_scripts": 0,
            "num_images": 2,
            "num_fonts": 1,
            "inline_css_ratio": 0.2,
            "inline_js_ratio": 0.1,
            "compression_used": "br",
            "minified_html": True,
            "minified_css": True,
            "text_to_html_ratio": 0.35,
            "css_to_html_ratio": 0.66,
            "images_over_200kb": 0,
            "render_blocking_resources": 0,
        },
        "timing": None,
        "resources": [],
        "shortcomings": [],
        "security": {
            "score": 95,
            "passed": 8,
            "warnings": 1,
            "failures": 0,
            "checks": [],
        },
        "metadata": {
            "title": "Example Domain",
            "meta_description": "Example site description",
            "charset": "utf-8",
        },
        "errors": [],
    }

    storage.set_job(job_id, mock_report)

    # 1. GET Report
    res = client.get(f"/api/v1/report/{job_id}")
    assert res.status_code == 200
    report_data = res.json()
    assert report_data["job_id"] == job_id
    assert report_data["score"]["total"] == 92

    # 2. Export JSON
    res_json = client.get(f"/api/v1/report/{job_id}/export?format=json")
    assert res_json.status_code == 200
    assert res_json.headers["Content-Type"] == "application/json"
    assert "attachment" in res_json.headers["Content-Disposition"]

    # 3. Export PDF
    res_pdf = client.get(f"/api/v1/report/{job_id}/export?format=pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["Content-Type"] == "application/pdf"
    assert "attachment" in res_pdf.headers["Content-Disposition"]
    assert len(res_pdf.content) > 1000  # PDF generated with bytes
