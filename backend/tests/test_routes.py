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


def test_get_and_download_scraped_source():
    job_id = "test-job-source-67890"
    html_content = "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
    css_content = "body { margin: 0; background: #fff; } h1 { color: #333; }"

    mock_report = {
        "job_id": job_id,
        "url": "https://example.com",
        "scraped_source": {
            "html": html_content,
            "css": css_content,
            "html_bytes": len(html_content.encode("utf-8")),
            "css_bytes": len(css_content.encode("utf-8")),
        },
    }
    storage.set_job(job_id, mock_report)

    # 1. Fetch raw source JSON
    res_source = client.get(f"/api/v1/report/{job_id}/source")
    assert res_source.status_code == 200
    source_data = res_source.json()
    assert source_data["job_id"] == job_id
    assert source_data["html"] == html_content
    assert source_data["css"] == css_content
    assert source_data["html_bytes"] == len(html_content.encode("utf-8"))
    assert source_data["css_bytes"] == len(css_content.encode("utf-8"))

    # 2. Download raw HTML
    res_html = client.get(f"/api/v1/report/{job_id}/source/download?type=html")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["Content-Type"]
    assert f'filename="pagelens-scraped-{job_id[:8]}.html"' in res_html.headers["Content-Disposition"]
    assert res_html.text == html_content

    # 3. Download raw CSS
    res_css = client.get(f"/api/v1/report/{job_id}/source/download?type=css")
    assert res_css.status_code == 200
    assert "text/css" in res_css.headers["Content-Type"]
    assert f'filename="pagelens-scraped-{job_id[:8]}.css"' in res_css.headers["Content-Disposition"]
    assert res_css.text == css_content

    # 4. 404 check for non-existent job
    res_404 = client.get("/api/v1/report/unknown-job-id/source")
    assert res_404.status_code == 404


def test_simulate_interaction_endpoint_ssrf_and_success(monkeypatch):
    # 1. SSRF reject
    res_ssrf = client.post(
        "/api/v1/analyze/interact",
        json={"url": "http://127.0.0.1:8000", "action_type": "click", "selector": "#btn"}
    )
    assert res_ssrf.status_code == 400

    # 2. Mock PlaywrightRunner.simulate_interaction
    from app.schemas.report import InteractionResult, NetworkRequestLog
    from app.api import routes_analyze

    async def mock_simulate(*args, **kwargs):
        return InteractionResult(
            success=True,
            action_type="click",
            target_description="Clicked #btn",
            initial_url="https://example.com",
            final_url="https://example.com",
            duration_ms=45.2,
            url_changed=False,
            dom_elements_before=10,
            dom_elements_after=12,
            dom_delta=2,
            html_after="<html><body>Mutated</body></html>",
            html_bytes_after=35,
            html_bytes_delta=10,
            css_after="body { color: red; }",
            css_bytes_after=18,
            triggered_requests_count=1,
            triggered_requests_bytes=1024,
            network_requests=[
                NetworkRequestLog(url="https://example.com/api/data", method="POST", status=200, size_bytes=1024, duration_ms=25.0)
            ],
            console_logs=["[LOG] button clicked"],
            summary="Injected +2 new DOM elements. Triggered 1 network request.",
        )

    monkeypatch.setattr(routes_analyze.playwright_runner, "simulate_interaction", mock_simulate)

    res = client.post(
        "/api/v1/analyze/interact",
        json={"url": "https://example.com", "action_type": "click", "selector": "#btn"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["dom_delta"] == 2
    assert len(data["network_requests"]) == 1
    assert data["triggered_requests_count"] == 1
    assert "Injected +2" in data["summary"]


