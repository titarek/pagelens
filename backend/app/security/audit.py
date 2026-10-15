import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
from app.schemas.report import SecurityAudit, SecurityCheck, ResourceEntry
from app.scraper.assets import ParsedScript, ParsedImage


def run_security_audit(
    url: str,
    final_url: str,
    headers: Dict[str, str],
    redirect_chain: List[str],
    resources: List[ResourceEntry],
    scripts: List[ParsedScript],
    images: List[ParsedImage],
    form_actions: List[str],
    raw_html: str,
) -> SecurityAudit:
    checks: List[SecurityCheck] = []

    # 1. HTTPS Enforced
    is_initial_https = url.startswith("https://")
    is_final_https = final_url.startswith("https://")
    if is_initial_https or is_final_https:
        checks.append(
            SecurityCheck(
                id="https-enforced",
                title="HTTPS Transport Encryption",
                status="pass",
                detail="Traffic is served over secure HTTPS TLS transport.",
                fix="Ensure all subdomains and HTTP variants redirect to HTTPS with 301 Permanent Redirects.",
            )
        )
    else:
        checks.append(
            SecurityCheck(
                id="https-enforced",
                title="HTTPS Transport Encryption",
                status="fail",
                detail="Page is delivered over unencrypted plain HTTP transport.",
                fix="Obtain a valid TLS certificate (e.g. Let's Encrypt) and enforce HTTPS for all incoming requests.",
            )
        )

    # 2. Strict-Transport-Security (HSTS)
    hsts = headers.get("strict-transport-security", "")
    if hsts:
        max_age_match = re.search(r"max-age=(\d+)", hsts, re.I)
        max_age = int(max_age_match.group(1)) if max_age_match else 0
        if max_age >= 10886400:  # ~126 days
            checks.append(
                SecurityCheck(
                    id="hsts",
                    title="Strict-Transport-Security (HSTS)",
                    status="pass",
                    detail=f"HSTS is active with valid duration (max-age={max_age}).",
                    fix="Maintain HSTS with includeSubDomains and preload directives.",
                )
            )
        else:
            checks.append(
                SecurityCheck(
                    id="hsts",
                    title="Strict-Transport-Security (HSTS)",
                    status="warn",
                    detail=f"HSTS max-age is set to {max_age} seconds, which is shorter than recommended (10,886,400+ seconds).",
                    fix="Increase max-age to at least 31536000 (1 year) and consider adding includeSubDomains.",
                )
            )
    else:
        checks.append(
            SecurityCheck(
                id="hsts",
                title="Strict-Transport-Security (HSTS)",
                status="fail" if is_final_https else "warn",
                detail="Missing Strict-Transport-Security header.",
                fix="Configure Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
            )
        )

    # 3. Content-Security-Policy (CSP)
    csp = headers.get("content-security-policy", "")
    if csp:
        has_default = "default-src" in csp
        has_script = "script-src" in csp
        if has_default and has_script:
            checks.append(
                SecurityCheck(
                    id="csp",
                    title="Content-Security-Policy (CSP)",
                    status="pass",
                    detail=f"Robust CSP detected with default-src and script-src directives.",
                    fix="Review CSP reports periodically to enforce strict nonces or hashes.",
                )
            )
        else:
            checks.append(
                SecurityCheck(
                    id="csp",
                    title="Content-Security-Policy (CSP)",
                    status="warn",
                    detail="CSP header is present but lacks strict default-src or script-src constraints.",
                    fix="Add explicit default-src 'self' and restrict external script execution origins.",
                )
            )
    else:
        checks.append(
            SecurityCheck(
                id="csp",
                title="Content-Security-Policy (CSP)",
                status="warn",
                detail="No Content-Security-Policy header detected.",
                fix="Implement a strict CSP header to prevent Cross-Site Scripting (XSS) and data injection attacks.",
            )
        )

    # 4. X-Content-Type-Options
    xcto = headers.get("x-content-type-options", "").lower()
    if "nosniff" in xcto:
        checks.append(
            SecurityCheck(
                id="x-content-type-options",
                title="MIME-Sniffing Prevention",
                status="pass",
                detail="X-Content-Type-Options: nosniff header is present.",
                fix="Keep header enabled on all HTTP responses.",
            )
        )
    else:
        checks.append(
            SecurityCheck(
                id="x-content-type-options",
                title="MIME-Sniffing Prevention",
                status="fail",
                detail="Missing X-Content-Type-Options: nosniff header.",
                fix="Add 'X-Content-Type-Options: nosniff' header to prevent browsers from MIME-sniffing response content types.",
            )
        )

    # 5. Framing Protection (Clickjacking)
    xfo = headers.get("x-frame-options", "").upper()
    has_frame_ancestors = "frame-ancestors" in csp
    if has_frame_ancestors or xfo in ("DENY", "SAMEORIGIN"):
        checks.append(
            SecurityCheck(
                id="clickjacking-protection",
                title="Clickjacking Frame Protection",
                status="pass",
                detail="Frame embedding is restricted via X-Frame-Options or CSP frame-ancestors.",
                fix="Maintain frame-ancestors 'none' or 'self' across all sensitive pages.",
            )
        )
    else:
        checks.append(
            SecurityCheck(
                id="clickjacking-protection",
                title="Clickjacking Frame Protection",
                status="fail",
                detail="No clickjacking defense found (missing X-Frame-Options and CSP frame-ancestors).",
                fix="Set X-Frame-Options: SAMEORIGIN or Content-Security-Policy: frame-ancestors 'self';",
            )
        )

    # 6. Referrer-Policy
    ref_policy = headers.get("referrer-policy", "").lower()
    if any(p in ref_policy for p in ["strict-origin-when-cross-origin", "no-referrer", "same-origin", "strict-origin"]):
        checks.append(
            SecurityCheck(
                id="referrer-policy",
                title="Referrer Information Privacy",
                status="pass",
                detail=f"Secure Referrer-Policy configured ({ref_policy}).",
                fix="Maintain strict-origin-when-cross-origin to avoid leaking URL query parameters.",
            )
        )
    elif "unsafe-url" in ref_policy:
        checks.append(
            SecurityCheck(
                id="referrer-policy",
                title="Referrer Information Privacy",
                status="fail",
                detail="Referrer-Policy is set to 'unsafe-url', which leaks complete URLs including query parameters.",
                fix="Change Referrer-Policy to 'strict-origin-when-cross-origin' or 'no-referrer'.",
            )
        )
    else:
        checks.append(
            SecurityCheck(
                id="referrer-policy",
                title="Referrer Information Privacy",
                status="warn",
                detail="Explicit Referrer-Policy header missing.",
                fix="Send 'Referrer-Policy: strict-origin-when-cross-origin' to protect user privacy.",
            )
        )

    # 7. Permissions-Policy
    perm_policy = headers.get("permissions-policy") or headers.get("feature-policy")
    if perm_policy:
        checks.append(
            SecurityCheck(
                id="permissions-policy",
                title="Hardware & Feature Permissions Policy",
                status="pass",
                detail="Permissions-Policy header is configured to limit browser hardware features.",
                fix="Periodically audit enabled features (camera, microphone, geolocation).",
            )
        )
    else:
        checks.append(
            SecurityCheck(
                id="permissions-policy",
                title="Hardware & Feature Permissions Policy",
                status="warn",
                detail="Permissions-Policy header is missing.",
                fix="Configure Permissions-Policy (e.g. camera=(), microphone=(), geolocation=()) to limit browser API access.",
            )
        )

    # 8. Cookies Security Flags
    set_cookie = headers.get("set-cookie", "")
    if set_cookie:
        is_secure = "secure" in set_cookie.lower()
        is_httponly = "httponly" in set_cookie.lower()
        is_samesite = "samesite" in set_cookie.lower()

        if is_secure and is_httponly and is_samesite:
            checks.append(
                SecurityCheck(
                    id="cookie-security",
                    title="Cookie Security Attributes",
                    status="pass",
                    detail="Cookies are protected with Secure, HttpOnly, and SameSite flags.",
                    fix="Maintain strict cookie flags across all session cookies.",
                )
            )
        else:
            missing_flags = []
            if not is_secure:
                missing_flags.append("Secure")
            if not is_httponly:
                missing_flags.append("HttpOnly")
            if not is_samesite:
                missing_flags.append("SameSite")
            checks.append(
                SecurityCheck(
                    id="cookie-security",
                    title="Cookie Security Attributes",
                    status="fail",
                    detail=f"Cookies are missing essential security flags: {', '.join(missing_flags)}.",
                    fix="Set Secure, HttpOnly, and SameSite=Lax (or Strict) on all set-cookie headers.",
                )
            )
    else:
        checks.append(
            SecurityCheck(
                id="cookie-security",
                title="Cookie Security Attributes",
                status="pass",
                detail="No cookies set on initial HTML document request.",
                fix="Ensure future cookies are flagged with Secure, HttpOnly, and SameSite.",
            )
        )

    # 9. Mixed Content
    mixed_content_found = False
    insecure_urls: List[str] = []
    if is_final_https:
        for r in resources:
            if r.url.startswith("http://"):
                mixed_content_found = True
                insecure_urls.append(r.url)
        for s in scripts:
            if s.src and s.src.startswith("http://"):
                mixed_content_found = True
                insecure_urls.append(s.src)
        for img in images:
            if img.src and img.src.startswith("http://"):
                mixed_content_found = True
                insecure_urls.append(img.src)

    if mixed_content_found:
        checks.append(
            SecurityCheck(
                id="mixed-content",
                title="Mixed Content Inspection",
                status="fail",
                detail=f"Found {len(insecure_urls)} insecure HTTP asset(s) loaded on an HTTPS origin.",
                fix="Upgrade all resource references to HTTPS or use relative URLs.",
            )
        )
    else:
        checks.append(
            SecurityCheck(
                id="mixed-content",
                title="Mixed Content Inspection",
                status="pass",
                detail="No mixed HTTP content detected on secure origin.",
                fix="Enforce upgrade-insecure-requests in CSP header.",
            )
        )

    # 10. Outdated Client Libraries
    outdated_warnings = []
    # Check jQuery
    jq_match = re.search(r"jquery[-.]([0-9.]+)(?:\.min)?\.js", raw_html, re.I) or re.search(r"jQuery v([0-9.]+)", raw_html)
    if jq_match:
        ver = jq_match.group(1)
        try:
            major = int(ver.split(".")[0])
            minor = int(ver.split(".")[1]) if len(ver.split(".")) > 1 else 0
            if major < 3 or (major == 3 and minor < 5):
                outdated_warnings.append(f"jQuery v{ver} (vulnerable to XSS)")
        except Exception:
            pass

    # Check Bootstrap
    bs_match = re.search(r"bootstrap[-.]([0-9.]+)(?:\.min)?\.js", raw_html, re.I)
    if bs_match:
        ver = bs_match.group(1)
        try:
            major = int(ver.split(".")[0])
            if major < 4:
                outdated_warnings.append(f"Bootstrap v{ver} (legacy version with known security issues)")
        except Exception:
            pass

    if outdated_warnings:
        checks.append(
            SecurityCheck(
                id="outdated-libraries",
                title="Third-Party Library Vulnerabilities",
                status="warn",
                detail=f"Detected outdated libraries: {', '.join(outdated_warnings)}.",
                fix="Update third-party client dependencies to latest actively patched releases.",
            )
        )
    else:
        checks.append(
            SecurityCheck(
                id="outdated-libraries",
                title="Third-Party Library Vulnerabilities",
                status="pass",
                detail="No vulnerable legacy library signatures detected in HTML source.",
                fix="Keep client dependencies updated via automated tools like Dependabot or Renovate.",
            )
        )

    # 11. Form Action Security
    insecure_forms = [a for a in form_actions if a.startswith("http://")]
    if insecure_forms:
        checks.append(
            SecurityCheck(
                id="form-action-security",
                title="Form Submission Target Security",
                status="fail",
                detail=f"Form action points to unencrypted endpoint: {insecure_forms[0]}.",
                fix="Always point form action targets to secure HTTPS endpoints.",
            )
        )
    else:
        checks.append(
            SecurityCheck(
                id="form-action-security",
                title="Form Submission Target Security",
                status="pass",
                detail="All form submission targets use secure HTTPS or relative paths.",
                fix="Maintain secure endpoints for all form handlers.",
            )
        )

    # Calculate overall audit score (0-100)
    passed_count = sum(1 for c in checks if c.status == "pass")
    warn_count = sum(1 for c in checks if c.status == "warn")
    fail_count = sum(1 for c in checks if c.status == "fail")

    max_possible = len(checks) * 10
    raw_points = (passed_count * 10) + (warn_count * 4)
    audit_score = round((raw_points / max(1, max_possible)) * 100)

    return SecurityAudit(
        score=audit_score,
        passed=passed_count,
        warnings=warn_count,
        failures=fail_count,
        checks=checks,
    )
