from typing import List, Optional
from app.schemas.report import (
    ScoreBreakdown,
    StructuralMetrics,
    TimingMetrics,
    Shortcoming,
    SecurityAudit,
)


def compute_structure_score(structural: StructuralMetrics) -> int:
    """Calculates structure and size score out of 25 points."""
    score = 0.0

    # 1. Total payload size (max 10 points)
    bytes_total = structural.total_bytes
    if bytes_total <= 500 * 1024:
        score += 10.0
    elif bytes_total <= 1_500 * 1024:
        score += 8.0
    elif bytes_total <= 3_000 * 1024:
        score += 5.0
    elif bytes_total <= 5_000 * 1024:
        score += 2.5
    else:
        score += 1.0

    # 2. Number of requests (max 5 points)
    reqs = structural.num_requests
    if reqs <= 30:
        score += 5.0
    elif reqs <= 60:
        score += 4.0
    elif reqs <= 100:
        score += 2.5
    else:
        score += 1.0

    # 3. DOM node complexity (max 5 points)
    nodes = structural.num_dom_elements
    if nodes <= 800:
        score += 5.0
    elif nodes <= 1400:
        score += 3.5
    elif nodes <= 2000:
        score += 2.0
    else:
        score += 0.5

    # 4. Compression (max 3 points)
    if structural.compression_used in ("br", "gzip"):
        score += 3.0
    elif structural.compression_used == "deflate":
        score += 1.5

    # 5. Minification (max 2 points)
    if structural.minified_css:
        score += 1.0
    if structural.minified_html:
        score += 1.0

    return max(0, min(25, int(round(score))))


def compute_timing_score(timing: Optional[TimingMetrics], fetch_ttfb_ms: float = 0.0) -> int:
    """Calculates timing & Web Vitals score out of 35 points."""
    if timing is not None and timing.fcp_ms > 0:
        score = 0.0

        # FCP (max 8 points)
        if timing.fcp_ms <= 1200:
            score += 8.0
        elif timing.fcp_ms <= 1800:
            score += 6.0
        elif timing.fcp_ms <= 3000:
            score += 3.0
        else:
            score += 1.0

        # LCP (max 10 points)
        if timing.lcp_ms <= 2000:
            score += 10.0
        elif timing.lcp_ms <= 2500:
            score += 8.0
        elif timing.lcp_ms <= 4000:
            score += 4.0
        else:
            score += 1.0

        # CLS (max 7 points)
        if timing.cls <= 0.05:
            score += 7.0
        elif timing.cls <= 0.10:
            score += 5.5
        elif timing.cls <= 0.25:
            score += 2.5
        else:
            score += 0.0

        # TBT (max 6 points)
        if timing.tbt_ms <= 150:
            score += 6.0
        elif timing.tbt_ms <= 300:
            score += 4.5
        elif timing.tbt_ms <= 600:
            score += 2.0
        else:
            score += 0.0

        # TTFB (max 4 points)
        ttfb = timing.ttfb_ms
        if ttfb <= 200:
            score += 4.0
        elif ttfb <= 500:
            score += 3.0
        elif ttfb <= 800:
            score += 1.5
        else:
            score += 0.0

        return max(0, min(35, int(round(score))))

    # Fallback for Static Mode: calibrate based on TTFB
    score = 20.0  # baseline estimate for static parse
    ttfb = fetch_ttfb_ms
    if ttfb <= 200:
        score += 15.0
    elif ttfb <= 500:
        score += 10.0
    elif ttfb <= 800:
        score += 5.0
    else:
        score += 1.0

    return max(0, min(35, int(round(score))))


def compute_shortcomings_score(shortcomings: List[Shortcoming]) -> int:
    """Calculates shortcomings score out of 25 points with severity-based deductions."""
    deductions = 0.0
    for s in shortcomings:
        if s.severity == "high":
            deductions += 7.0
        elif s.severity == "medium":
            deductions += 3.5
        elif s.severity == "low":
            deductions += 1.5

    remaining = max(0.0, 25.0 - deductions)
    return int(round(remaining))


def compute_security_score(security_audit: SecurityAudit) -> int:
    """Scales security audit score (0-100) to 15 points."""
    return max(0, min(15, int(round((security_audit.score / 100.0) * 15.0))))


def compute_overall_score(
    structural: StructuralMetrics,
    timing: Optional[TimingMetrics],
    shortcomings: List[Shortcoming],
    security_audit: SecurityAudit,
    fetch_ttfb_ms: float = 0.0,
) -> ScoreBreakdown:
    """Calculates complete weighted performance breakdown (0-100)."""
    struct_score = compute_structure_score(structural)
    timing_score = compute_timing_score(timing, fetch_ttfb_ms)
    short_score = compute_shortcomings_score(shortcomings)
    sec_score = compute_security_score(security_audit)

    total = struct_score + timing_score + short_score + sec_score
    clamped_total = max(0, min(100, total))

    return ScoreBreakdown(
        total=clamped_total,
        structure=struct_score,
        timing=timing_score,
        shortcomings=short_score,
        security=sec_score,
    )
