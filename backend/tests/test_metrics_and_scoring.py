import pytest
from app.schemas.report import (
    StructuralMetrics,
    TimingMetrics,
    Shortcoming,
    SecurityAudit,
)
from app.metrics.scoring import (
    compute_structure_score,
    compute_timing_score,
    compute_shortcomings_score,
    compute_security_score,
    compute_overall_score,
)
from app.metrics.shortcomings import (
    RULES,
    evaluate_shortcomings,
    trigger_large_html,
    trigger_large_css,
    trigger_large_js,
    trigger_too_many_requests,
    trigger_too_many_dom,
    trigger_render_blocking,
    trigger_no_compression,
    trigger_unminified_css,
    trigger_unminified_html,
    trigger_large_images,
    trigger_no_lazy_loading,
    trigger_missing_dimensions,
    trigger_slow_ttfb,
    trigger_poor_lcp,
    trigger_high_cls,
    trigger_long_tasks,
    trigger_no_cache_headers,
    trigger_mixed_content,
)


class MockContext:
    def __init__(self, **kwargs):
        self.structural = kwargs.get("structural", StructuralMetrics())
        self.timing = kwargs.get("timing", None)
        self.headers = kwargs.get("headers", {})
        self.url = kwargs.get("url", "https://example.com")
        self.resources = kwargs.get("resources", [])
        self.parsed_images = kwargs.get("parsed_images", [])
        self.parsed_scripts = kwargs.get("parsed_scripts", [])
        self.fetch_ttfb = kwargs.get("fetch_ttfb", 100.0)


def test_scoring_math_perfect():
    structural = StructuralMetrics(
        total_bytes=300 * 1024,
        num_requests=20,
        num_dom_elements=400,
        compression_used="br",
        minified_html=True,
        minified_css=True,
    )
    timing = TimingMetrics(
        ttfb_ms=120.0,
        fcp_ms=800.0,
        lcp_ms=1500.0,
        cls=0.01,
        tbt_ms=50.0,
    )
    shortcomings = []
    sec_audit = SecurityAudit(score=100)

    score = compute_overall_score(structural, timing, shortcomings, sec_audit)
    assert score.structure == 25
    assert score.timing == 35
    assert score.shortcomings == 25
    assert score.security == 15
    assert score.total == 100


def test_scoring_math_degraded():
    structural = StructuralMetrics(
        total_bytes=6_000 * 1024,
        num_requests=150,
        num_dom_elements=3000,
        compression_used="none",
        minified_html=False,
        minified_css=False,
    )
    timing = TimingMetrics(
        ttfb_ms=1200.0,
        fcp_ms=3500.0,
        lcp_ms=5000.0,
        cls=0.35,
        tbt_ms=800.0,
    )
    shortcomings = [
        Shortcoming(
            id="large-html", severity="high", title="", cause="", fix="", example="", reference=""
        ),
        Shortcoming(
            id="large-css", severity="high", title="", cause="", fix="", example="", reference=""
        ),
    ]
    sec_audit = SecurityAudit(score=20)

    score = compute_overall_score(structural, timing, shortcomings, sec_audit)
    assert score.structure <= 10
    assert score.timing <= 10
    assert score.shortcomings <= 15
    assert score.security <= 5
    assert score.total < 40


def test_rule_triggers_positive_and_negative():
    # 1. large-html
    ctx_pos = MockContext(structural=StructuralMetrics(html_bytes=150 * 1024))
    ctx_neg = MockContext(structural=StructuralMetrics(html_bytes=50 * 1024))
    assert trigger_large_html(ctx_pos) is True
    assert trigger_large_html(ctx_neg) is False

    # 2. large-css
    ctx_pos = MockContext(structural=StructuralMetrics(css_bytes=120 * 1024))
    ctx_neg = MockContext(structural=StructuralMetrics(css_bytes=40 * 1024))
    assert trigger_large_css(ctx_pos) is True
    assert trigger_large_css(ctx_neg) is False

    # 3. large-js
    ctx_pos = MockContext(structural=StructuralMetrics(js_bytes=350 * 1024))
    ctx_neg = MockContext(structural=StructuralMetrics(js_bytes=150 * 1024))
    assert trigger_large_js(ctx_pos) is True
    assert trigger_large_js(ctx_neg) is False

    # 4. too-many-requests
    ctx_pos = MockContext(structural=StructuralMetrics(num_requests=105))
    ctx_neg = MockContext(structural=StructuralMetrics(num_requests=45))
    assert trigger_too_many_requests(ctx_pos) is True
    assert trigger_too_many_requests(ctx_neg) is False

    # 5. too-many-dom
    ctx_pos = MockContext(structural=StructuralMetrics(num_dom_elements=1600))
    ctx_neg = MockContext(structural=StructuralMetrics(num_dom_elements=500))
    assert trigger_too_many_dom(ctx_pos) is True
    assert trigger_too_many_dom(ctx_neg) is False

    # 6. render-blocking
    ctx_pos = MockContext(structural=StructuralMetrics(render_blocking_resources=2))
    ctx_neg = MockContext(structural=StructuralMetrics(render_blocking_resources=0))
    assert trigger_render_blocking(ctx_pos) is True
    assert trigger_render_blocking(ctx_neg) is False

    # 7. no-compression
    ctx_pos = MockContext(structural=StructuralMetrics(compression_used="none"))
    ctx_neg = MockContext(structural=StructuralMetrics(compression_used="gzip"))
    assert trigger_no_compression(ctx_pos) is True
    assert trigger_no_compression(ctx_neg) is False

    # 8. unminified-css
    ctx_pos = MockContext(structural=StructuralMetrics(css_bytes=5000, minified_css=False))
    ctx_neg = MockContext(structural=StructuralMetrics(css_bytes=5000, minified_css=True))
    assert trigger_unminified_css(ctx_pos) is True
    assert trigger_unminified_css(ctx_neg) is False

    # 9. unminified-html
    ctx_pos = MockContext(structural=StructuralMetrics(html_bytes=10000, minified_html=False))
    ctx_neg = MockContext(structural=StructuralMetrics(html_bytes=10000, minified_html=True))
    assert trigger_unminified_html(ctx_pos) is True
    assert trigger_unminified_html(ctx_neg) is False

    # 10. large-images
    ctx_pos = MockContext(structural=StructuralMetrics(images_over_200kb=2))
    ctx_neg = MockContext(structural=StructuralMetrics(images_over_200kb=0))
    assert trigger_large_images(ctx_pos) is True
    assert trigger_large_images(ctx_neg) is False

    # 11. slow-ttfb
    ctx_pos = MockContext(timing=TimingMetrics(ttfb_ms=750.0))
    ctx_neg = MockContext(timing=TimingMetrics(ttfb_ms=150.0))
    assert trigger_slow_ttfb(ctx_pos) is True
    assert trigger_slow_ttfb(ctx_neg) is False

    # 12. poor-lcp
    ctx_pos = MockContext(timing=TimingMetrics(lcp_ms=3000.0))
    ctx_neg = MockContext(timing=TimingMetrics(lcp_ms=1800.0))
    assert trigger_poor_lcp(ctx_pos) is True
    assert trigger_poor_lcp(ctx_neg) is False

    # 13. high-cls
    ctx_pos = MockContext(timing=TimingMetrics(cls=0.18))
    ctx_neg = MockContext(timing=TimingMetrics(cls=0.02))
    assert trigger_high_cls(ctx_pos) is True
    assert trigger_high_cls(ctx_neg) is False

    # 14. long-tasks
    ctx_pos = MockContext(timing=TimingMetrics(tbt_ms=450.0))
    ctx_neg = MockContext(timing=TimingMetrics(tbt_ms=80.0))
    assert trigger_long_tasks(ctx_pos) is True
    assert trigger_long_tasks(ctx_neg) is False

    # 15. no-cache-headers
    ctx_pos = MockContext(headers={"cache-control": "max-age=600"})
    ctx_neg = MockContext(headers={"cache-control": "public, max-age=86400"})
    assert trigger_no_cache_headers(ctx_pos) is True
    assert trigger_no_cache_headers(ctx_neg) is False

    # 16. mixed-content
    class DummyRes:
        def __init__(self, url):
            self.url = url
    ctx_pos = MockContext(url="https://site.com", resources=[DummyRes("http://insecure.com/script.js")])
    ctx_neg = MockContext(url="https://site.com", resources=[DummyRes("https://secure.com/script.js")])
    assert trigger_mixed_content(ctx_pos) is True
    assert trigger_mixed_content(ctx_neg) is False
