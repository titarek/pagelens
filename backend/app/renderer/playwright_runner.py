import asyncio
import logging
from typing import List, Tuple, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError
from app.core.config import settings
from app.core.security import validate_and_resolve_url, SSRFValidationError
from app.schemas.report import TimingMetrics, ResourceEntry
from app.metrics.timing import aggregate_timing_runs

logger = logging.getLogger("pagelens.playwright")

OBSERVER_SCRIPT = """
window.__pagelens_metrics = {
    fcp: 0,
    lcp: 0,
    cls: 0,
    tbt: 0
};

// Observe First Contentful Paint
try {
    const poPaint = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
            if (entry.name === 'first-contentful-paint') {
                window.__pagelens_metrics.fcp = entry.startTime;
            }
        }
    });
    poPaint.observe({ type: 'paint', buffered: true });
} catch (e) {}

// Observe Largest Contentful Paint
try {
    const poLCP = new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        if (entries.length > 0) {
            const lastEntry = entries[entries.length - 1];
            window.__pagelens_metrics.lcp = lastEntry.renderTime || lastEntry.loadTime || lastEntry.startTime;
        }
    });
    poLCP.observe({ type: 'largest-contentful-paint', buffered: true });
} catch (e) {}

// Observe Cumulative Layout Shift
try {
    const poCLS = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
            if (!entry.hadRecentInput) {
                window.__pagelens_metrics.cls += entry.value;
            }
        }
    });
    poCLS.observe({ type: 'layout-shift', buffered: true });
} catch (e) {}

// Observe Long Tasks for Total Blocking Time
try {
    const poLongTask = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
            const blockingDuration = entry.duration - 50;
            if (blockingDuration > 0) {
                window.__pagelens_metrics.tbt += blockingDuration;
            }
        }
    });
    poLongTask.observe({ type: 'longtask', buffered: true });
} catch (e) {}
"""


class PlaywrightRunner:
    def __init__(
        self,
        runs: int = settings.playwright_runs,
        allow_local_for_testing: bool = False,
    ):
        self.runs = runs
        self.allow_local_for_testing = allow_local_for_testing

    async def render_and_measure(
        self, target_url: str
    ) -> Tuple[TimingMetrics, List[ResourceEntry]]:
        """
        Runs headless Playwright Chromium mobile emulation with CPU and network throttling.
        Executes N runs, computes median Web Vitals, and captures the resource waterfall.
        """
        validate_and_resolve_url(target_url, allow_local_for_testing=self.allow_local_for_testing)

        run_metrics_list: List[TimingMetrics] = []
        captured_resources: List[ResourceEntry] = []

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )

            try:
                for run_idx in range(self.runs):
                    logger.info(f"Executing Playwright render run {run_idx + 1}/{self.runs} for {target_url}")
                    context: BrowserContext = await browser.new_context(
                        viewport={
                            "width": settings.mobile_viewport_width,
                            "height": settings.mobile_viewport_height,
                        },
                        device_scale_factor=settings.mobile_device_scale_factor,
                        is_mobile=True,
                        has_touch=True,
                        user_agent=settings.user_agent,
                    )

                    page: Page = await context.new_page()

                    try:
                        # Establish CDP session for hardware & network throttling
                        cdp = await context.new_cdp_session(page)

                        # CPU 4x Throttling
                        await cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})

                        # Slow 4G Network Throttling (1.6 Mbps down, 750 Kbps up, 150ms latency)
                        await cdp.send(
                            "Network.emulateNetworkConditions",
                            {
                                "offline": False,
                                "latency": 150,
                                "downloadThroughput": int(1.6 * 1024 * 1024 / 8),
                                "uploadThroughput": int(750 * 1024 / 8),
                                "connectionType": "cellular4g",
                            },
                        )

                        # Inject PerformanceObserver before any script runs
                        await page.add_init_script(OBSERVER_SCRIPT)

                        # Navigate with timeout and settle
                        try:
                            await page.goto(target_url, wait_until="networkidle", timeout=18000)
                        except PlaywrightError:
                            # Fallback if networkidle takes too long due to streaming/long-polling
                            await page.goto(target_url, wait_until="load", timeout=15000)

                        # Settle time: 1.5s
                        await page.wait_for_timeout(1500)

                        # Extract navigation timing and Web Vitals
                        eval_data = await page.evaluate(
                            """() => {
                            const nav = performance.getEntriesByType('navigation')[0] || {};
                            const obs = window.__pagelens_metrics || {};
                            const resources = performance.getEntriesByType('resource') || [];

                            return {
                                nav: {
                                    startTime: nav.startTime || 0,
                                    responseStart: nav.responseStart || 0,
                                    requestStart: nav.requestStart || 0,
                                    domContentLoadedEventEnd: nav.domContentLoadedEventEnd || 0,
                                    loadEventEnd: nav.loadEventEnd || 0,
                                    domainLookupStart: nav.domainLookupStart || 0,
                                    domainLookupEnd: nav.domainLookupEnd || 0,
                                    connectStart: nav.connectStart || 0,
                                    connectEnd: nav.connectEnd || 0,
                                    secureConnectionStart: nav.secureConnectionStart || 0
                                },
                                vitals: {
                                    fcp: obs.fcp || 0,
                                    lcp: obs.lcp || 0,
                                    cls: obs.cls || 0,
                                    tbt: obs.tbt || 0
                                },
                                resources: resources.slice(0, 150).map(r => ({
                                    url: r.name,
                                    type: r.initiatorType || 'other',
                                    size_bytes: r.transferSize || r.decodedBodySize || 0,
                                    duration_ms: Math.round(r.duration || 0),
                                    start_time_ms: Math.round(r.startTime || 0),
                                    status: r.responseStatus || 200,
                                    renderBlockingStatus: r.renderBlockingStatus || ''
                                }))
                            };
                        }"""
                        )

                        nav = eval_data.get("nav", {})
                        vitals = eval_data.get("vitals", {})
                        res_list = eval_data.get("resources", [])

                        ttfb = max(0.0, nav.get("responseStart", 0) - nav.get("requestStart", 0))
                        dcl = max(0.0, nav.get("domContentLoadedEventEnd", 0))
                        load = max(0.0, nav.get("loadEventEnd", 0))
                        dns = max(0.0, nav.get("domainLookupEnd", 0) - nav.get("domainLookupStart", 0))
                        
                        sec_start = nav.get("secureConnectionStart", 0)
                        tls = max(0.0, nav.get("connectEnd", 0) - sec_start) if sec_start > 0 else 0.0

                        run_metric = TimingMetrics(
                            ttfb_ms=round(float(ttfb), 2),
                            dom_content_loaded_ms=round(float(dcl), 2),
                            load_ms=round(float(load), 2),
                            fcp_ms=round(float(vitals.get("fcp", 0)), 2),
                            lcp_ms=round(float(vitals.get("lcp", 0)), 2),
                            cls=round(float(vitals.get("cls", 0)), 4),
                            tbt_ms=round(float(vitals.get("tbt", 0)), 2),
                            server_response_ms=round(float(ttfb), 2),
                            dns_ms=round(float(dns), 2),
                            tls_ms=round(float(tls), 2),
                        )
                        run_metrics_list.append(run_metric)

                        # Capture waterfall from the first successful run
                        if not captured_resources and res_list:
                            for item in res_list:
                                captured_resources.append(
                                    ResourceEntry(
                                        url=item["url"],
                                        type=item["type"],
                                        size_bytes=int(item["size_bytes"]),
                                        duration_ms=float(item["duration_ms"]),
                                        start_time_ms=float(item["start_time_ms"]),
                                        status=int(item["status"]),
                                        is_render_blocking=(item.get("renderBlockingStatus") == "blocking"),
                                    )
                                )

                    except Exception as run_err:
                        logger.warning(f"Error during render run {run_idx + 1}: {run_err}")
                    finally:
                        await context.close()

            finally:
                await browser.close()

        if not run_metrics_list:
            logger.error(f"All Playwright render runs failed for {target_url}. Returning zeroed metrics.")
            return TimingMetrics(), captured_resources

        # Aggregate across runs (median and variance logging)
        aggregated = aggregate_timing_runs(run_metrics_list)
        logger.info(
            f"Playwright render complete: FCP={aggregated.fcp_ms}ms, LCP={aggregated.lcp_ms}ms, CLS={aggregated.cls}, TBT={aggregated.tbt_ms}ms"
        )
        return aggregated, captured_resources
