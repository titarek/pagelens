from dataclasses import dataclass
from typing import Callable, Any, List, Optional
from app.schemas.report import Shortcoming


@dataclass
class Rule:
    id: str
    severity: str  # "high", "medium", "low"
    title: str
    cause: str
    fix: str
    example: str
    reference: str
    trigger: Callable[[Any], bool]

    def evaluate(self, ctx: Any) -> Optional[Shortcoming]:
        try:
            if self.trigger(ctx):
                return Shortcoming(
                    id=self.id,
                    severity=self.severity,  # type: ignore
                    title=self.title,
                    cause=self.cause,
                    fix=self.fix,
                    example=self.example,
                    reference=self.reference,
                )
        except Exception:
            return None
        return None


# Helper trigger functions
def trigger_large_html(ctx: Any) -> bool:
    return getattr(ctx.structural, "html_bytes", 0) > 100 * 1024


def trigger_large_css(ctx: Any) -> bool:
    return getattr(ctx.structural, "css_bytes", 0) > 100 * 1024


def trigger_large_js(ctx: Any) -> bool:
    return getattr(ctx.structural, "js_bytes", 0) > 300 * 1024


def trigger_too_many_requests(ctx: Any) -> bool:
    return getattr(ctx.structural, "num_requests", 0) > 100


def trigger_too_many_dom(ctx: Any) -> bool:
    return getattr(ctx.structural, "num_dom_elements", 0) > 1500


def trigger_render_blocking(ctx: Any) -> bool:
    return getattr(ctx.structural, "render_blocking_resources", 0) > 0


def trigger_no_compression(ctx: Any) -> bool:
    compression = getattr(ctx.structural, "compression_used", "none")
    return compression == "none"


def trigger_unminified_css(ctx: Any) -> bool:
    css_bytes = getattr(ctx.structural, "css_bytes", 0)
    is_minified = getattr(ctx.structural, "minified_css", False)
    return css_bytes > 2048 and not is_minified


def trigger_unminified_html(ctx: Any) -> bool:
    html_bytes = getattr(ctx.structural, "html_bytes", 0)
    is_minified = getattr(ctx.structural, "minified_html", False)
    return html_bytes > 5120 and not is_minified


def trigger_large_images(ctx: Any) -> bool:
    return getattr(ctx.structural, "images_over_200kb", 0) > 0


def trigger_no_lazy_loading(ctx: Any) -> bool:
    images = getattr(ctx, "parsed_images", [])
    if len(images) <= 2:
        return False
    # If more than 2 images and none or less than 30% are lazy loaded
    lazy_count = sum(1 for img in images if getattr(img, "is_lazy", False))
    return lazy_count == 0


def trigger_missing_dimensions(ctx: Any) -> bool:
    images = getattr(ctx, "parsed_images", [])
    if not images:
        return False
    missing_count = sum(1 for img in images if not getattr(img, "has_dimensions", False) and not getattr(img, "is_data_uri", False))
    return missing_count > 0


def trigger_slow_ttfb(ctx: Any) -> bool:
    ttfb = 0.0
    if hasattr(ctx, "timing") and ctx.timing:
        ttfb = ctx.timing.ttfb_ms
    elif hasattr(ctx, "fetch_ttfb"):
        ttfb = ctx.fetch_ttfb
    return ttfb > 600.0


def trigger_poor_lcp(ctx: Any) -> bool:
    if hasattr(ctx, "timing") and ctx.timing:
        return ctx.timing.lcp_ms > 2500.0
    return False


def trigger_high_cls(ctx: Any) -> bool:
    if hasattr(ctx, "timing") and ctx.timing:
        return ctx.timing.cls > 0.1
    return False


def trigger_long_tasks(ctx: Any) -> bool:
    if hasattr(ctx, "timing") and ctx.timing:
        return ctx.timing.tbt_ms > 300.0
    return False


def trigger_no_cache_headers(ctx: Any) -> bool:
    headers = getattr(ctx, "headers", {})
    cache_control = headers.get("cache-control", "").lower()
    if not cache_control:
        return True
    if "no-store" in cache_control:
        return False
    import re
    match = re.search(r"max-age=(\d+)", cache_control)
    if not match:
        return True
    return int(match.group(1)) < 3600


def trigger_mixed_content(ctx: Any) -> bool:
    url = getattr(ctx, "url", "")
    if not url.startswith("https://"):
        return False
    resources = getattr(ctx, "resources", [])
    for r in resources:
        if r.url.startswith("http://"):
            return True
    # Check parsed external links or scripts
    for s in getattr(ctx, "parsed_scripts", []):
        if s.src and s.src.startswith("http://"):
            return True
    for img in getattr(ctx, "parsed_images", []):
        if img.src and img.src.startswith("http://"):
            return True
    return False


RULES: List[Rule] = [
    Rule(
        id="large-html",
        severity="high",
        title="Excessive HTML Document Size",
        cause="The raw HTML document exceeds 100 KB uncompressed. A bloated DOM requires significant memory and delays initial byte processing.",
        fix="Remove redundant inline data, reduce server-side rendered initial states, and paginate large lists.",
        example="<!-- Replace heavy inline JSON blobs with on-demand API endpoints -->\n<script type=\"application/json\" id=\"initial-state\">...</script>",
        reference="https://web.dev/articles/reduce-dom-size",
        trigger=trigger_large_html,
    ),
    Rule(
        id="large-css",
        severity="high",
        title="Heavy CSS Payload (> 100 KB)",
        cause="CSS is a render-blocking resource. Browsers halt page rendering until all referenced stylesheets are downloaded and parsed.",
        fix="Purge unused CSS rules using PurgeCSS or Tailwind JIT, split vendor styles, and inline critical CSS.",
        example="@media (min-width: 1024px) {\n  /* Split desktop-only rules into separate media query stylesheets */\n}",
        reference="https://web.dev/articles/defer-non-critical-css",
        trigger=trigger_large_css,
    ),
    Rule(
        id="large-js",
        severity="high",
        title="Massive JavaScript Bundle (> 300 KB)",
        cause="JavaScript requires heavy CPU parsing, compilation, and execution on the main thread, directly contributing to long tasks and input delay.",
        fix="Implement route-based dynamic imports (code splitting), tree-shake unused exports, and replace heavy libraries with lighter alternatives.",
        example="// Dynamic import for heavy components\nconst AnalyticsDashboard = React.lazy(() => import('./AnalyticsDashboard'));",
        reference="https://web.dev/articles/reduce-javascript-payloads-with-code-splitting",
        trigger=trigger_large_js,
    ),
    Rule(
        id="too-many-requests",
        severity="medium",
        title="High Request Count (> 100 requests)",
        cause="Issuing more than 100 individual network requests introduces connection congestion, TLS handshake overhead, and serialization bottlenecks.",
        fix="Bundle static assets, combine icon sprites or use SVGs inline, and defer non-critical third-party analytics.",
        example="<svg class=\"icon\"><use href=\"/sprite.svg#chevron\" /></svg>",
        reference="https://developer.mozilla.org/en-US/docs/Web/Performance/Optimizing_content_efficiency",
        trigger=trigger_too_many_requests,
    ),
    Rule(
        id="too-many-dom",
        severity="medium",
        title="Excessive DOM Complexity (> 1,500 nodes)",
        cause="A deep DOM tree (> 1,500 nodes) increases browser memory usage, slows down querySelector lookups, and inflates style recalculation times.",
        fix="Virtualize lengthy lists, avoid excessive wrapper <div> nesting, and render off-screen elements lazily.",
        example="/* Use CSS content-visibility for offscreen sections */\n.offscreen-section {\n  content-visibility: auto;\n  contain-intrinsic-size: 1px 500px;\n}",
        reference="https://web.dev/articles/dom-size-and-interactivity",
        trigger=trigger_too_many_dom,
    ),
    Rule(
        id="render-blocking",
        severity="high",
        title="Render-Blocking Scripts in <head>",
        cause="Synchronous <script> elements inside <head> force the HTML parser to pause until the script is fully downloaded and executed.",
        fix="Add 'defer' or 'async' to external script tags or specify type='module'.",
        example="<!-- Non-blocking script execution -->\n<script src=\"/bundle.js\" defer></script>",
        reference="https://web.dev/articles/render-blocking-resources",
        trigger=trigger_render_blocking,
    ),
    Rule(
        id="no-compression",
        severity="high",
        title="Text Compression Disabled (No Gzip / Brotli)",
        cause="The server response is missing gzip or br Content-Encoding, transferring raw text over the network and consuming 3-5x more bandwidth.",
        fix="Enable Brotli or Gzip compression on your edge CDN, Nginx reverse proxy, or origin server.",
        example="# Nginx configuration:\ngzip on;\ngzip_types text/plain text/css application/javascript application/json;",
        reference="https://web.dev/articles/enable-text-compression",
        trigger=trigger_no_compression,
    ),
    Rule(
        id="unminified-css",
        severity="medium",
        title="Unminified CSS Stylesheets",
        cause="Stylesheets contain unnecessary comments, indentation, and whitespace that should be stripped in production builds.",
        fix="Use cssnano, clean-css, or Lightning CSS during your build pipeline.",
        example="// vite.config.ts\nexport default { build: { cssMinify: 'lightningcss' } };",
        reference="https://web.dev/articles/minify-css",
        trigger=trigger_unminified_css,
    ),
    Rule(
        id="unminified-html",
        severity="low",
        title="Unminified HTML Markup",
        cause="HTML markup contains extraneous indentation, whitespace, and HTML comments.",
        fix="Configure HTML minification in your template engine or static site generator.",
        example="// html-minifier configuration\n{ collapseWhitespace: true, removeComments: true }",
        reference="https://web.dev/articles/reduce-cookie-size",
        trigger=trigger_unminified_html,
    ),
    Rule(
        id="large-images",
        severity="high",
        title="Oversized Images Detected (> 200 KB)",
        cause="Images over 200 KB consume excessive mobile bandwidth and severely delay Largest Contentful Paint (LCP).",
        fix="Compress raster images using modern WebP or AVIF formats and serve responsive sizes via srcset.",
        example="<picture>\n  <source srcset=\"hero.avif\" type=\"image/avif\">\n  <source srcset=\"hero.webp\" type=\"image/webp\">\n  <img src=\"hero.jpg\" alt=\"Hero banner\" width=\"1200\" height=\"600\">\n</picture>",
        reference="https://web.dev/articles/choose-the-right-image-format",
        trigger=trigger_large_images,
    ),
    Rule(
        id="no-lazy-loading",
        severity="medium",
        title="Missing Native Image Lazy Loading",
        cause="Images below the initial viewport without loading='lazy' compete with critical assets for initial network bandwidth.",
        fix="Add loading='lazy' to all non-critical, below-the-fold <img> elements.",
        example="<img src=\"/team-photo.jpg\" loading=\"lazy\" width=\"400\" height=\"300\" alt=\"Team\">",
        reference="https://web.dev/articles/browser-level-image-lazy-loading",
        trigger=trigger_no_lazy_loading,
    ),
    Rule(
        id="missing-dimensions",
        severity="high",
        title="Image Missing Explicit Dimensions (CLS Risk)",
        cause="Images without width and height attributes cause severe Cumulative Layout Shift (CLS) as the page reflows upon image load.",
        fix="Always specify explicit width and height attributes or CSS aspect-ratio on <img> tags.",
        example="<img src=\"avatar.png\" width=\"48\" height=\"48\" style=\"aspect-ratio: 1/1;\" alt=\"User avatar\">",
        reference="https://web.dev/articles/optimize-cls#images-without-dimensions",
        trigger=trigger_missing_dimensions,
    ),
    Rule(
        id="slow-ttfb",
        severity="high",
        title="Slow Time to First Byte (TTFB > 600 ms)",
        cause="Server response took more than 600 ms to return initial headers. High TTFB delays every subsequent page asset request.",
        fix="Implement edge page caching (CDN), optimize database query indexes, or leverage HTTP reverse proxies.",
        example="Cache-Control: public, max-age=0, s-maxage=86400, stale-while-revalidate=3600",
        reference="https://web.dev/articles/ttfb",
        trigger=trigger_slow_ttfb,
    ),
    Rule(
        id="poor-lcp",
        severity="high",
        title="Poor Largest Contentful Paint (LCP > 2,500 ms)",
        cause="The largest visual element took more than 2.5 seconds to render, creating perceived slowness for visitors.",
        fix="Preload the hero image with fetchpriority='high', eliminate render-blocking CSS, and ensure fast CDN delivery.",
        example="<link rel=\"preload\" href=\"/hero.webp\" as=\"image\" fetchpriority=\"high\">",
        reference="https://web.dev/articles/lcp",
        trigger=trigger_poor_lcp,
    ),
    Rule(
        id="high-cls",
        severity="high",
        title="High Cumulative Layout Shift (CLS > 0.1)",
        cause="Visual elements shifted unexpectedly during page load, exceeding Google's recommended 0.1 CLS ceiling.",
        fix="Reserve static space for dynamic ads/embeds, set dimensions on media, and avoid inserting content above existing content.",
        example=".ad-slot {\n  min-height: 250px;\n  display: block;\n}",
        reference="https://web.dev/articles/cls",
        trigger=trigger_high_cls,
    ),
    Rule(
        id="long-tasks",
        severity="high",
        title="Excessive Total Blocking Time (TBT > 300 ms)",
        cause="Long JavaScript execution tasks (> 50 ms) blocked the main browser thread, degrading user responsiveness.",
        fix="Break up synchronous long tasks using scheduler.yield() or requestIdleCallback, and defer non-critical scripts.",
        example="async function processLargeBatch() {\n  for (const item of items) {\n    handle(item);\n    if (scheduler.yield) await scheduler.yield();\n  }\n}",
        reference="https://web.dev/articles/tbt",
        trigger=trigger_long_tasks,
    ),
    Rule(
        id="no-cache-headers",
        severity="medium",
        title="Suboptimal or Missing Cache-Control Headers",
        cause="Static assets lack long-lived Cache-Control headers (minimum 1 hour recommended), forcing redundant downloads on repeat visits.",
        fix="Set immutable Cache-Control headers with long max-age for hashed assets.",
        example="Cache-Control: public, max-age=31536000, immutable",
        reference="https://web.dev/articles/http-cache",
        trigger=trigger_no_cache_headers,
    ),
    Rule(
        id="mixed-content",
        severity="high",
        title="Active Mixed Content Detected (HTTP on HTTPS)",
        cause="The secure HTTPS page references insecure http:// assets. Modern browsers block active mixed content and warn on passive content.",
        fix="Update all resource URLs to use https:// or relative paths, and set Upgrade-Insecure-Requests CSP.",
        example="Content-Security-Policy: upgrade-insecure-requests;",
        reference="https://developer.mozilla.org/en-US/docs/Web/Security/Mixed_content",
        trigger=trigger_mixed_content,
    ),
]


def evaluate_shortcomings(ctx: Any) -> List[Shortcoming]:
    """Runs all registered rules against the analysis context and returns triggered shortcomings."""
    triggered: List[Shortcoming] = []
    for rule in RULES:
        result = rule.evaluate(ctx)
        if result:
            triggered.append(result)
    return triggered
