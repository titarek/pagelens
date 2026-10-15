import statistics
from typing import List, Dict, Any, Optional
from app.schemas.report import TimingMetrics, ResourceEntry


def aggregate_timing_runs(runs: List[TimingMetrics]) -> TimingMetrics:
    """
    Computes median values across multiple Playwright benchmark runs and logs variance.
    """
    if not runs:
        return TimingMetrics()

    if len(runs) == 1:
        return runs[0]

    def median_of(vals: List[float]) -> float:
        return round(float(statistics.median(vals)), 2)

    def variance_of(vals: List[float]) -> float:
        if len(vals) < 2:
            return 0.0
        return round(float(statistics.variance(vals)), 2)

    fcp_vals = [r.fcp_ms for r in runs]
    lcp_vals = [r.lcp_ms for r in runs]
    cls_vals = [r.cls for r in runs]
    tbt_vals = [r.tbt_ms for r in runs]
    ttfb_vals = [r.ttfb_ms for r in runs]
    load_vals = [r.load_ms for r in runs]
    dcl_vals = [r.dom_content_loaded_ms for r in runs]

    variance_data = {
        "runs_count": len(runs),
        "fcp_var": variance_of(fcp_vals),
        "lcp_var": variance_of(lcp_vals),
        "cls_var": round(float(statistics.variance(cls_vals)) if len(cls_vals) >= 2 else 0.0, 4),
        "tbt_var": variance_of(tbt_vals),
        "ttfb_var": variance_of(ttfb_vals),
    }

    return TimingMetrics(
        ttfb_ms=median_of(ttfb_vals),
        dom_content_loaded_ms=median_of(dcl_vals),
        load_ms=median_of(load_vals),
        fcp_ms=median_of(fcp_vals),
        lcp_ms=median_of(lcp_vals),
        cls=round(float(statistics.median(cls_vals)), 4),
        tbt_ms=median_of(tbt_vals),
        inp_ms=None,
        server_response_ms=median_of([r.server_response_ms for r in runs]),
        dns_ms=median_of([r.dns_ms for r in runs]),
        tls_ms=median_of([r.tls_ms for r in runs]),
        render_runs_variance=variance_data,
    )
