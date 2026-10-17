import http.server
import os
import socketserver
import threading
import pytest
from app.services.analyzer import AnalyzerService
from app.core.security import validate_and_resolve_url, SSRFValidationError


class FixtureHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        super().__init__(*args, directory=fixtures_dir, **kwargs)

    def log_message(self, format, *args):
        # Suppress logging in test runner
        pass


@pytest.fixture(scope="module")
def fixture_server():
    # Bind to 127.0.0.1 on an allowed port, e.g. 8088
    port = 8088
    server = socketserver.TCPServer(("127.0.0.1", port), FixtureHTTPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
async def test_ssrf_rejects_fixture_server_by_default(fixture_server):
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url(f"{fixture_server}/good_site.html", allow_local_for_testing=False)


@pytest.mark.asyncio
async def test_analyze_good_fixture(fixture_server):
    analyzer = AnalyzerService(allow_local_for_testing=True)
    url = f"{fixture_server}/good_site.html"
    report = await analyzer.run_analysis(job_id="test-good-1", url=url, mode="static")

    assert report.status == "ok"
    assert report.score.total >= 70
    assert report.structural.html_bytes < 50 * 1024
    assert report.structural.num_dom_elements < 100
    # No large-html or too-many-dom shortcomings
    shortcoming_ids = [s.id for s in report.shortcomings]
    assert "large-html" not in shortcoming_ids
    assert "too-many-dom" not in shortcoming_ids


@pytest.mark.asyncio
async def test_analyze_bad_fixture(fixture_server):
    analyzer = AnalyzerService(allow_local_for_testing=True)
    url = f"{fixture_server}/bad_site.html"
    report = await analyzer.run_analysis(job_id="test-bad-1", url=url, mode="static")

    assert report.status in ("ok", "partial")
    assert report.score.total < 60
    assert report.structural.html_bytes > 100 * 1024
    assert report.structural.num_dom_elements > 1500

    shortcoming_ids = [s.id for s in report.shortcomings]
    assert "large-html" in shortcoming_ids
    assert "too-many-dom" in shortcoming_ids
    assert "render-blocking" in shortcoming_ids

    # Check security failures
    sec_failure_ids = [c.id for c in report.security.checks if c.status == "fail"]
    assert "form-action-security" in sec_failure_ids
