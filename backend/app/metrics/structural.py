from typing import List, Optional
from app.schemas.report import StructuralMetrics, ResourceEntry
from app.scraper.parser import HTMLParserResult
from app.scraper.css_collector import CSSCollectionResult
from app.scraper.fetcher import FetchResult


def compute_structural_metrics(
    fetch_res: FetchResult,
    parser_res: HTMLParserResult,
    css_res: CSSCollectionResult,
    resources: Optional[List[ResourceEntry]] = None,
) -> StructuralMetrics:
    """
    Computes all structural size, count, and quality ratio metrics for the page.
    """
    html_bytes = fetch_res.transfer_size_bytes or parser_res.raw_html_bytes
    css_bytes = css_res.total_css_bytes

    # Estimate JS bytes from inline scripts and external script references
    inline_js_bytes = sum(s.size_bytes for s in parser_res.scripts if s.is_inline)
    num_external_scripts = sum(1 for s in parser_res.scripts if not s.is_inline)
    # Estimate typical 40KB per external script if not yet captured via resource waterfall
    ext_js_bytes = 0
    if resources:
        ext_js_bytes = sum(r.size_bytes for r in resources if r.type == "script" or r.url.endswith(".js"))
    if ext_js_bytes == 0 and num_external_scripts > 0:
        ext_js_bytes = num_external_scripts * 35_000

    js_bytes = inline_js_bytes + ext_js_bytes
    inline_js_ratio = round(inline_js_bytes / max(1, js_bytes), 4)

    # Images bytes
    image_bytes = 0
    images_over_200kb = 0
    if resources:
        image_resources = [r for r in resources if r.type == "image" or any(r.url.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"])]
        image_bytes = sum(r.size_bytes for r in image_resources)
        images_over_200kb = sum(1 for r in image_resources if r.size_bytes > 200 * 1024)
    if image_bytes == 0:
        # Fallback estimation for static mode based on data uris and image count
        data_uri_bytes = sum(img.size_bytes for img in parser_res.images if img.is_data_uri)
        image_bytes = data_uri_bytes + (len(parser_res.images) - sum(1 for img in parser_res.images if img.is_data_uri)) * 50_000

    # Fonts bytes
    font_bytes = 0
    if resources:
        font_bytes = sum(r.size_bytes for r in resources if r.type == "font" or any(r.url.endswith(ext) for ext in [".woff2", ".woff", ".ttf", ".otf"]))
    if font_bytes == 0 and len(parser_res.fonts) > 0:
        font_bytes = len(parser_res.fonts) * 30_000

    total_bytes = html_bytes + css_bytes + js_bytes + image_bytes + font_bytes

    # Request count
    num_requests = len(resources) if resources else (
        1 + len(parser_res.scripts) + len(parser_res.stylesheets) + len(parser_res.images) + len(parser_res.fonts)
    )

    # Blocking resources: blocking head scripts + render blocking stylesheets
    blocking_scripts = sum(1 for s in parser_res.scripts if s.is_blocking)
    render_blocking_stylesheets = sum(1 for s in css_res.stylesheet_entries if s.is_render_blocking)
    render_blocking_resources = blocking_scripts + render_blocking_stylesheets

    # Compression check from headers
    content_encoding = fetch_res.headers.get("content-encoding", "").lower()
    if "br" in content_encoding:
        compression_used = "br"
    elif "gzip" in content_encoding:
        compression_used = "gzip"
    elif "deflate" in content_encoding:
        compression_used = "deflate"
    else:
        compression_used = "none"

    css_to_html_ratio = round(css_bytes / max(1, html_bytes), 4)

    return StructuralMetrics(
        html_bytes=html_bytes,
        css_bytes=css_bytes,
        js_bytes=js_bytes,
        image_bytes=image_bytes,
        font_bytes=font_bytes,
        total_bytes=total_bytes,
        num_requests=num_requests,
        num_dom_elements=parser_res.num_dom_elements,
        num_stylesheets=len(parser_res.stylesheets),
        num_scripts=len(parser_res.scripts),
        num_blocking_scripts=blocking_scripts,
        num_images=len(parser_res.images),
        num_fonts=len(parser_res.fonts),
        inline_css_ratio=css_res.inline_css_ratio,
        inline_js_ratio=inline_js_ratio,
        compression_used=compression_used,
        minified_html=parser_res.is_html_minified,
        minified_css=css_res.is_css_minified,
        text_to_html_ratio=parser_res.text_to_html_ratio,
        css_to_html_ratio=css_to_html_ratio,
        images_over_200kb=images_over_200kb,
        render_blocking_resources=render_blocking_resources,
    )
