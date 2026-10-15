import pytest
from app.security.audit import run_security_audit
from app.schemas.report import ResourceEntry
from app.scraper.assets import ParsedScript, ParsedImage


def test_security_audit_all_pass():
    headers = {
        "strict-transport-security": "max-age=31536000; includeSubDomains; preload",
        "content-security-policy": "default-src 'self'; script-src 'self'",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "strict-origin-when-cross-origin",
        "permissions-policy": "camera=(), microphone=()",
        "set-cookie": "session=abc; Secure; HttpOnly; SameSite=Strict",
    }
    audit = run_security_audit(
        url="https://secure.example.com",
        final_url="https://secure.example.com",
        headers=headers,
        redirect_chain=["https://secure.example.com"],
        resources=[],
        scripts=[],
        images=[],
        form_actions=["https://secure.example.com/api/login"],
        raw_html="<html><body>Clean app</body></html>",
    )

    assert audit.failures == 0
    assert audit.score >= 90
    assert any(c.id == "hsts" and c.status == "pass" for c in audit.checks)
    assert any(c.id == "x-content-type-options" and c.status == "pass" for c in audit.checks)
    assert any(c.id == "cookie-security" and c.status == "pass" for c in audit.checks)


def test_security_audit_detects_mixed_content_and_insecure_cookies():
    headers = {
        "set-cookie": "session=123",  # Missing Secure, HttpOnly, SameSite
    }
    resources = [
        ResourceEntry(url="http://insecure.example.com/analytics.js", type="script")
    ]
    audit = run_security_audit(
        url="https://example.com",
        final_url="https://example.com",
        headers=headers,
        redirect_chain=["https://example.com"],
        resources=resources,
        scripts=[],
        images=[],
        form_actions=["http://example.com/submit"],
        raw_html="<html><script src='jquery-1.12.4.min.js'></script></html>",
    )

    assert audit.failures > 0
    assert any(c.id == "mixed-content" and c.status == "fail" for c in audit.checks)
    assert any(c.id == "cookie-security" and c.status == "fail" for c in audit.checks)
    assert any(c.id == "form-action-security" and c.status == "fail" for c in audit.checks)
    assert any(c.id == "outdated-libraries" and c.status == "warn" for c in audit.checks)
    assert audit.score < 60
