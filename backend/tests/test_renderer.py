import pytest
from app.schemas.report import TimingMetrics
from app.metrics.timing import aggregate_timing_runs


def test_aggregate_timing_runs_median():
    run1 = TimingMetrics(
        ttfb_ms=200.0,
        fcp_ms=1000.0,
        lcp_ms=2000.0,
        cls=0.05,
        tbt_ms=100.0,
        load_ms=2500.0,
        dom_content_loaded_ms=1800.0,
    )
    run2 = TimingMetrics(
        ttfb_ms=180.0,
        fcp_ms=1200.0,
        lcp_ms=2200.0,
        cls=0.08,
        tbt_ms=150.0,
        load_ms=2800.0,
        dom_content_loaded_ms=2000.0,
    )
    run3 = TimingMetrics(
        ttfb_ms=250.0,
        fcp_ms=1100.0,
        lcp_ms=2100.0,
        cls=0.06,
        tbt_ms=120.0,
        load_ms=2600.0,
        dom_content_loaded_ms=1900.0,
    )

    agg = aggregate_timing_runs([run1, run2, run3])
    assert agg.ttfb_ms == 200.0
    assert agg.fcp_ms == 1100.0
    assert agg.lcp_ms == 2100.0
    assert agg.cls == 0.06
    assert agg.tbt_ms == 120.0
    assert agg.render_runs_variance is not None
    assert agg.render_runs_variance["runs_count"] == 3
