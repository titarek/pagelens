import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import validate_and_resolve_url, SSRFValidationError

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "PageLens"


def test_ssrf_rejects_localhost():
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("http://localhost:8000")

    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("http://127.0.0.1:8000")


def test_ssrf_rejects_private_ips():
    # 10.x.x.x
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("http://10.0.0.1")

    # 172.16.x.x - 172.31.x.x
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("http://172.16.0.1")

    # 192.168.x.x
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("http://192.168.1.1")

    # 169.254.x.x (AWS metadata / link-local)
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("http://169.254.169.254")

    # ::1 IPv6 loopback
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("http://[::1]")


def test_ssrf_rejects_invalid_schemes():
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("file:///etc/passwd")

    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("ftp://example.com/file")

    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("gopher://example.com")


def test_ssrf_rejects_disallowed_ports():
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("http://example.com:22")

    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url("http://example.com:3306")


def test_ssrf_rejects_oversized_url():
    long_url = "https://example.com/" + "a" * 2050
    with pytest.raises(SSRFValidationError):
        validate_and_resolve_url(long_url)


def test_security_headers_present():
    response = client.get("/api/v1/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "X-Response-Time-Ms" in response.headers
