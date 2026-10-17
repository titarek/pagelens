import asyncio
import logging
import sys
from typing import List, Tuple, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError
from app.core.config import settings
from app.core.security import validate_and_resolve_url, SSRFValidationError
from app.schemas.report import TimingMetrics, ResourceEntry, InteractionResult, NetworkRequestLog
from app.metrics.timing import aggregate_timing_runs


logger = logging.getLogger("pagelens.playwright")


def _run_coroutine_with_proactor(coro_factory, *args, **kwargs):
    """
    Spawns a new ProactorEventLoop inside a dedicated worker thread.
    Required on Windows where Uvicorn defaults to WindowsSelectorEventLoopPolicy,
    which does not support subprocess execution needed by Playwright.
    """
    p_loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(p_loop)
    try:
        return p_loop.run_until_complete(coro_factory(*args, **kwargs))
    finally:
        p_loop.close()
        asyncio.set_event_loop(None)


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
        if sys.platform == "win32":
            try:
                loop = asyncio.get_running_loop()
                if isinstance(loop, asyncio.ProactorEventLoop):
                    return await self._render_and_measure_impl(target_url)
            except RuntimeError:
                pass
            return await asyncio.to_thread(
                _run_coroutine_with_proactor, self._render_and_measure_impl, target_url
            )
        return await self._render_and_measure_impl(target_url)

    async def _render_and_measure_impl(
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

    async def simulate_interaction(
        self,
        target_url: str,
        action_type: str,
        selector: Optional[str] = None,
        value: Optional[str] = None,
        target_url_override: Optional[str] = None,
    ) -> InteractionResult:
        if sys.platform == "win32":
            try:
                loop = asyncio.get_running_loop()
                if isinstance(loop, asyncio.ProactorEventLoop):
                    return await self._simulate_interaction_impl(
                        target_url, action_type, selector, value, target_url_override
                    )
            except RuntimeError:
                pass
            return await asyncio.to_thread(
                _run_coroutine_with_proactor,
                self._simulate_interaction_impl,
                target_url,
                action_type,
                selector,
                value,
                target_url_override,
            )
        return await self._simulate_interaction_impl(
            target_url, action_type, selector, value, target_url_override
        )

    async def _simulate_interaction_impl(
        self,
        target_url: str,
        action_type: str,
        selector: Optional[str] = None,
        value: Optional[str] = None,
        target_url_override: Optional[str] = None,
    ) -> InteractionResult:
        """
        Loads the target page in Playwright, sets up network/console watchers,
        executes the chosen interaction (click, select, or navigate), waits for DOM/network
        mutations to settle, and computes the complete before-and-after delta.
        """
        validate_and_resolve_url(target_url, allow_local_for_testing=self.allow_local_for_testing)
        if target_url_override:
            validate_and_resolve_url(target_url_override, allow_local_for_testing=self.allow_local_for_testing)

        import time

        start_time = time.perf_counter()
        console_logs: List[str] = []
        triggered_requests: List[NetworkRequestLog] = []
        is_tracking_post_interaction = False

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
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=settings.user_agent,
                )
                page = await context.new_page()

                def on_console(msg):
                    if msg.type in ("warning", "error", "log"):
                        console_logs.append(f"[{msg.type.upper()}] {msg.text}")

                page.on("console", on_console)

                def on_request_finished(req):
                    if is_tracking_post_interaction:
                        try:
                            resp = req.response()
                            status = resp.status if resp else 200
                            headers = resp.headers if resp else {}
                            cl = headers.get("content-length")
                            size = int(cl) if cl and cl.isdigit() else 512
                            timing = req.timing
                            dur = (timing.get("responseEnd", 0) - timing.get("requestStart", 0)) if timing else 0
                            triggered_requests.append(
                                NetworkRequestLog(
                                    url=req.url,
                                    method=req.method,
                                    status=status,
                                    resource_type=req.resource_type,
                                    size_bytes=size,
                                    duration_ms=max(1.0, float(dur)),
                                )
                            )
                        except Exception:
                            pass

                page.on("requestfinished", on_request_finished)

                # Step 1: Initial navigation
                try:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(1000)
                except Exception as e:
                    logger.warning(f"Initial navigation warning for {target_url}: {e}")

                initial_url = page.url
                dom_before = await page.evaluate("() => document.querySelectorAll('*').length")
                html_before = await page.content()
                html_bytes_before = len(html_before.encode("utf-8"))

                # Step 2: Begin tracking post-interaction activity
                is_tracking_post_interaction = True
                action_start = time.perf_counter()
                action_desc = ""

                try:
                    if action_type == "navigate":
                        nav_target = target_url_override or target_url
                        action_desc = f"Navigated to {nav_target}"
                        await page.goto(nav_target, wait_until="domcontentloaded", timeout=20000)
                        await page.wait_for_timeout(1000)

                    elif action_type == "select":
                        action_desc = f"Selected '{value}' in {selector or 'dropdown'}"
                        if selector:
                            await page.select_option(selector, value=value, timeout=5000)
                        else:
                            await page.evaluate(
                                f"""(val) => {{
                                    const sel = document.querySelector('select');
                                    if (sel) {{
                                        sel.value = val;
                                        sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }}""",
                                value,
                            )
                        await page.wait_for_timeout(1500)

                    elif action_type == "click":
                        action_desc = f"Clicked {selector or 'button'}"
                        if selector:
                            try:
                                await page.click(selector, timeout=5000)
                            except Exception:
                                # Fallback evaluation if selector requires scroll or dispatch
                                await page.evaluate(
                                    f"""(sel) => {{
                                        const el = document.querySelector(sel);
                                        if (el) el.click();
                                    }}""",
                                    selector,
                                )
                        else:
                            await page.evaluate("() => { const b = document.querySelector('button'); if (b) b.click(); }")
                        await page.wait_for_timeout(1500)

                except Exception as act_err:
                    logger.warning(f"Action execution warning ({action_type}): {act_err}")
                    action_desc = f"Attempted {action_type} ({act_err})"

                # Settle and read post-interaction state
                final_url = page.url
                dom_after = await page.evaluate("() => document.querySelectorAll('*').length")
                html_after = await page.content()
                html_bytes_after = len(html_after.encode("utf-8"))
                dom_delta = dom_after - dom_before
                html_bytes_delta = html_bytes_after - html_bytes_before
                action_duration_ms = (time.perf_counter() - action_start) * 1000

                # Extract CSS after interaction
                css_blocks = await page.evaluate(
                    """() => {
                        let out = [];
                        for (let s of document.styleSheets) {
                            try {
                                if (s.cssRules) {
                                    for (let r of s.cssRules) out.push(r.cssText);
                                }
                            } catch (e) {}
                        }
                        return out.slice(0, 300).join('\\n');
                    }"""
                )

                total_req_bytes = sum(r.size_bytes for r in triggered_requests)
                url_changed = initial_url != final_url

                summary_parts = []
                if url_changed:
                    summary_parts.append(f"URL transitioned to {final_url}")
                else:
                    summary_parts.append("Page remained on current route (DOM state mutated)")

                if dom_delta > 0:
                    summary_parts.append(f"Injected +{dom_delta} new DOM elements")
                elif dom_delta < 0:
                    summary_parts.append(f"Removed {abs(dom_delta)} DOM elements")
                else:
                    summary_parts.append("DOM element count remained constant")

                if triggered_requests:
                    summary_parts.append(f"Triggered {len(triggered_requests)} network request(s) ({round(total_req_bytes / 1024, 1)} KB)")
                else:
                    summary_parts.append("No additional network requests triggered")

                summary = ". ".join(summary_parts) + "."

                return InteractionResult(
                    success=True,
                    action_type=action_type,
                    target_description=action_desc,
                    initial_url=initial_url,
                    final_url=final_url,
                    duration_ms=round(action_duration_ms, 2),
                    url_changed=url_changed,
                    dom_elements_before=dom_before,
                    dom_elements_after=dom_after,
                    dom_delta=dom_delta,
                    html_after=html_after,
                    html_bytes_after=html_bytes_after,
                    html_bytes_delta=html_bytes_delta,
                    css_after=css_blocks,
                    css_bytes_after=len(css_blocks.encode("utf-8")),
                    triggered_requests_count=len(triggered_requests),
                    triggered_requests_bytes=total_req_bytes,
                    network_requests=triggered_requests,
                    console_logs=console_logs[:20],
                    summary=summary,
                )

            except Exception as e:
                logger.error(f"Interaction simulation failed for {target_url}: {e}", exc_info=True)
                return InteractionResult(
                    success=False,
                    action_type=action_type,
                    target_description=f"{action_type} on {target_url}",
                    initial_url=target_url,
                    final_url=target_url,
                    duration_ms=round((time.perf_counter() - start_time) * 1000, 2),
                    url_changed=False,
                    summary=f"Interaction simulation failed: {e}",
                    error=str(e),
                )
            finally:
                await browser.close()

