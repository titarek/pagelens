import pytest
from app.scraper.parser import HTMLParser
from app.scraper.css_collector import CSSCollector
from app.scraper.assets import ParsedStylesheet


SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Sample Test Site</title>
    <meta name="description" content="A fast test website for PageLens verification.">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="canonical" href="https://example.com/canonical">
    <link rel="stylesheet" href="/assets/style.css">
    <link rel="preload" href="/fonts/inter.woff2" as="font" type="font/woff2">
    <style>
        body { font-family: sans-serif; margin: 0; }
        .hero { color: #333; }
    </style>
    <script src="/js/blocking.js"></script>
    <script src="/js/deferred.js" defer></script>
</head>
<body>
    <h1>Welcome to PageLens</h1>
    <p>This is a paragraph with content.</p>
    <img src="/images/banner.jpg" width="800" height="400" alt="Banner">
    <img src="/images/no-dims.png" alt="Missing dimensions">
    <form action="/submit" method="POST">
        <input type="text" name="name">
    </form>
    <a href="https://external-domain.com/docs">External Link</a>
</body>
</html>
"""


def test_html_parser_extracts_metadata():
    parser = HTMLParser(SAMPLE_HTML, "https://example.com/index.html")
    res = parser.parse()

    assert res.metadata.title == "Sample Test Site"
    assert res.metadata.meta_description == "A fast test website for PageLens verification."
    assert res.metadata.charset == "utf-8"
    assert res.metadata.viewport == "width=device-width, initial-scale=1.0"
    assert res.metadata.canonical_url == "https://example.com/canonical"
    assert res.num_dom_elements > 10


def test_html_parser_extracts_scripts_and_blocking():
    parser = HTMLParser(SAMPLE_HTML, "https://example.com")
    res = parser.parse()

    assert len(res.scripts) == 2
    blocking_script = next(s for s in res.scripts if "blocking.js" in (s.src or ""))
    deferred_script = next(s for s in res.scripts if "deferred.js" in (s.src or ""))

    assert blocking_script.is_blocking is True
    assert deferred_script.is_blocking is False
    assert deferred_script.is_defer is True


def test_html_parser_extracts_images_and_dimensions():
    parser = HTMLParser(SAMPLE_HTML, "https://example.com")
    res = parser.parse()

    assert len(res.images) == 2
    banner = next(img for img in res.images if "banner.jpg" in img.src)
    assert banner.has_dimensions is True
    assert banner.width == "800"
    assert banner.height == "400"

    no_dims = next(img for img in res.images if "no-dims.png" in img.src)
    assert no_dims.has_dimensions is False
    assert no_dims.is_lazy is False


def test_html_parser_extracts_stylesheets_and_fonts():
    parser = HTMLParser(SAMPLE_HTML, "https://example.com")
    res = parser.parse()

    assert len(res.stylesheets) == 2  # 1 external, 1 inline
    ext_css = next(s for s in res.stylesheets if not s.is_inline)
    assert ext_css.href == "https://example.com/assets/style.css"

    inline_css = next(s for s in res.stylesheets if s.is_inline)
    assert "body { font-family" in inline_css.content

    assert len(res.fonts) == 1
    assert "inter.woff2" in res.fonts[0].href


@pytest.mark.asyncio
async def test_css_collector_inline():
    inline_sheet = ParsedStylesheet(
        is_inline=True,
        content="""
        .container { max-width: 1200px; margin: 0 auto; }
        .text { color: red; }
        """,
        size_bytes=80,
    )
    collector = CSSCollector()
    res = await collector.collect([inline_sheet], "https://example.com")

    assert res.inline_bytes > 0
    assert res.total_css_bytes > 0
    assert res.inline_css_ratio == 1.0
    assert res.data_uri_count == 0


def test_html_parser_extracts_discovered_options():
    html = """<!DOCTYPE html>
    <html>
    <head><title>Test Options</title></head>
    <body>
        <nav>
            <a href="/about">About Us</a>
            <a href="/pricing">Pricing Plans</a>
            <a href="https://other.com">External</a>
        </nav>
        <form id="contact-form" action="/contact" method="POST">
            <select name="plan" id="plan-select">
                <option value="basic">Basic Tier</option>
                <option value="pro">Pro Tier</option>
            </select>
            <button type="submit" id="submit-btn">Submit Request</button>
            <button type="button" class="btn-cancel">Cancel</button>
        </form>
    </body>
    </html>
    """
    parser = HTMLParser(html, "https://example.com/home")
    res = parser.parse()

    assert res.discovered_options is not None
    opts = res.discovered_options
    assert opts.total_count >= 5

    # Check internal links
    link_targets = [l.target for l in opts.internal_links]
    assert "https://example.com/about" in link_targets
    assert "https://example.com/pricing" in link_targets

    # Check select options
    select_values = [s.target for s in opts.select_options]
    assert "basic" in select_values
    assert "pro" in select_values

    # Check buttons
    button_labels = [b.label for b in opts.buttons]
    assert "Submit Request" in button_labels
    assert "Cancel" in button_labels

