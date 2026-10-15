import asyncio
from datetime import datetime, timezone
import time
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.logging import logger, log_analysis_audit
from app.core.security import validate_and_resolve_url, SSRFValidationError
from app.core.cache import storage
from app.scraper.fetcher import StaticFetcher
from app.scraper.parser import HTMLParser
from app.scraper.css_collector import CSSCollector
from app.renderer.playwright_runner import PlaywrightRunner
from app.metrics.structural import compute_structural_metrics
from app.metrics.shortcomings import evaluate_shortcomings
from app.metrics.scoring import compute_overall_score
from app.security.audit import run_security_audit
from app.schemas.report import Report, TimingMetrics, ResourceEntry, ScoreBreakdown


class AnalysisContext:
    def __init__(
        self,
        url: str,
        structural: Any,
        timing: Optional[TimingMetrics],
        headers: Dict[str, str],
        resources: List[ResourceEntry],
        parsed_images: List[Any],
        parsed_scripts: List[Any],
        fetch_ttfb: float,
    ):
        self.url = url
        self.structural = structural
        self.timing = timing
        self.headers = headers
        self.resources = resources
        self.parsed_images = parsed_images
        self.parsed_scripts = parsed_scripts
        self.fetch_ttfb = fetch_ttfb


class AnalyzerService:
    def __init__(self, allow_local_for_testing: bool = False):
        self.allow_local_for_testing = allow_local_for_testing
        self.fetcher = StaticFetcher(allow_local_for_testing=allow_local_for_testing)
        self.css_collector = CSSCollector(allow_local_for_testing=allow_local_for_testing)
        self.renderer = PlaywrightRunner(allow_local_for_testing=allow_local_for_testing)

    async def run_analysis(
        self, job_id: str, url: str, mode: str = "static", client_ip: Optional[str] = None
    ) -> Report:
        start_time = time.perf_counter()
        errors: List[str] = []

        try:
            # Step 1: Pre-validation
            storage.update_job_progress(job_id, status="running", progress_phase="Fetching")
            canonical_url, resolved_ip = validate_and_resolve_url(
                url, allow_local_for_testing=self.allow_local_for_testing
            )

            # Step 2: Static Fetch
            fetch_res = await self.fetcher.fetch(canonical_url)

            # Step 3: Parse HTML
            storage.update_job_progress(job_id, status="running", progress_phase="Parsing")
            parser = HTMLParser(fetch_res.text, fetch_res.final_url)
            parser_res = parser.parse()

            # Step 4: Collect CSS
            css_res = await self.css_collector.collect(parser_res.stylesheets, fetch_res.final_url)

            # Step 5: Full Render (if mode == "full")
            timing_metrics: Optional[TimingMetrics] = None
            resources: List[ResourceEntry] = []

            if mode == "full":
                storage.update_job_progress(job_id, status="running", progress_phase="Rendering")
                try:
                    timing_metrics, resources = await self.renderer.render_and_measure(fetch_res.final_url)
                except Exception as e:
                    logger.error(f"Playwright rendering failed for {fetch_res.final_url}: {e}")
                    errors.append(f"Full browser rendering error: {str(e)}")

            # If mode == "static" or Playwright had no waterfall entries, synthesize resources from parser
            if not resources:
                resources = self._build_static_resources(fetch_res, parser_res, css_res)

            # Step 6: Compute Structural Metrics
            structural = compute_structural_metrics(fetch_res, parser_res, css_res, resources)

            # Step 7: Security Audit
            storage.update_job_progress(job_id, status="running", progress_phase="Auditing")
            security_audit = run_security_audit(
                url=url,
                final_url=fetch_res.final_url,
                headers=fetch_res.headers,
                redirect_chain=fetch_res.redirect_chain,
                resources=resources,
                scripts=parser_res.scripts,
                images=parser_res.images,
                form_actions=parser_res.form_actions,
                raw_html=fetch_res.text,
            )

            # Step 8: Evaluate Shortcomings
            ctx = AnalysisContext(
                url=fetch_res.final_url,
                structural=structural,
                timing=timing_metrics,
                headers=fetch_res.headers,
                resources=resources,
                parsed_images=parser_res.images,
                parsed_scripts=parser_res.scripts,
                fetch_ttfb=fetch_res.ttfb_ms,
            )
            shortcomings = evaluate_shortcomings(ctx)

            # Step 9: Compute Scoring
            storage.update_job_progress(job_id, status="running", progress_phase="Scoring")
            score = compute_overall_score(
                structural=structural,
                timing=timing_metrics,
                shortcomings=shortcomings,
                security_audit=security_audit,
                fetch_ttfb_ms=fetch_res.ttfb_ms,
            )

            report = Report(
                job_id=job_id,
                url=url,
                final_url=fetch_res.final_url,
                fetched_at=datetime.now(timezone.utc),
                mode=mode,  # type: ignore
                status="ok" if not errors else "partial",
                score=score,
                structural=structural,
                timing=timing_metrics,
                resources=resources,
                shortcomings=shortcomings,
                security=security_audit,
                metadata=parser_res.metadata,
                errors=errors,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000
            log_analysis_audit(url, client_ip, duration_ms, "success", job_id)

            # Persist completed report to Redis / fakeredis
            storage.set_job(job_id, report.model_dump())
            return report

        except Exception as e:
            logger.error(f"Analysis pipeline failed for {url}: {e}", exc_info=True)
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_analysis_audit(url, client_ip, duration_ms, "failed", job_id)
            storage.update_job_progress(job_id, status="failed", error=str(e))
            raise

    def _build_static_resources(
        self, fetch_res: Any, parser_res: Any, css_res: Any
    ) -> List[ResourceEntry]:
        """Synthesizes resource entries for static mode waterfall display."""
        res: List[ResourceEntry] = [
            ResourceEntry(
                url=fetch_res.final_url,
                type="document",
                size_bytes=fetch_res.transfer_size_bytes,
                duration_ms=round(fetch_res.ttfb_ms + 40.0, 1),
                status=fetch_res.status_code,
                start_time_ms=0.0,
                is_render_blocking=True,
            )
        ]

        curr_time = max(50.0, round(fetch_res.ttfb_ms))
        for s in css_res.stylesheet_entries:
            if not s.is_inline and s.href:
                res.append(
                    ResourceEntry(
                        url=s.href,
                        type="stylesheet",
                        size_bytes=s.size_bytes,
                        duration_ms=65.0,
                        status=200,
                        start_time_ms=curr_time,
                        is_render_blocking=s.is_render_blocking,
                    )
                )
                curr_time += 15.0

        for sc in parser_res.scripts:
            if not sc.is_inline and sc.src:
                res.append(
                    ResourceEntry(
                        url=sc.src,
                        type="script",
                        size_bytes=35_000,
                        duration_ms=75.0,
                        status=200,
                        start_time_ms=curr_time,
                        is_render_blocking=sc.is_blocking,
                    )
                )
                curr_time += 20.0

        for img in parser_res.images[:15]:
            if not img.is_data_uri and img.src:
                res.append(
                    ResourceEntry(
                        url=img.src,
                        type="image",
                        size_bytes=45_000,
                        duration_ms=90.0,
                        status=200,
                        start_time_ms=curr_time,
                        is_render_blocking=False,
                    )
                )
                curr_time += 10.0

        for f in parser_res.fonts:
            if f.href:
                res.append(
                    ResourceEntry(
                        url=f.href,
                        type="font",
                        size_bytes=28_000,
                        duration_ms=80.0,
                        status=200,
                        start_time_ms=curr_time,
                        is_render_blocking=False,
                    )
                )
                curr_time += 15.0

        return res


analyzer_service = AnalyzerService()
