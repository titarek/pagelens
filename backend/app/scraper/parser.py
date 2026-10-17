import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from app.scraper.assets import (
    ParsedScript,
    ParsedImage,
    ParsedStylesheet,
    ParsedFont,
    ParsedPreload,
)
from app.schemas.report import SiteMetadata, DiscoveredOption, DiscoveredOptionsSummary



class HTMLParserResult:
    def __init__(
        self,
        metadata: SiteMetadata,
        num_dom_elements: int,
        raw_html_bytes: int,
        text_bytes: int,
        text_to_html_ratio: float,
        is_html_minified: bool,
        scripts: List[ParsedScript],
        stylesheets: List[ParsedStylesheet],
        images: List[ParsedImage],
        fonts: List[ParsedFont],
        preloads: List[ParsedPreload],
        form_actions: List[str],
        external_links: List[str],
        soup: BeautifulSoup,
        discovered_options: Optional[DiscoveredOptionsSummary] = None,
    ):
        self.metadata = metadata
        self.num_dom_elements = num_dom_elements
        self.raw_html_bytes = raw_html_bytes
        self.text_bytes = text_bytes
        self.text_to_html_ratio = text_to_html_ratio
        self.is_html_minified = is_html_minified
        self.scripts = scripts
        self.stylesheets = stylesheets
        self.images = images
        self.fonts = fonts
        self.preloads = preloads
        self.form_actions = form_actions
        self.external_links = external_links
        self.soup = soup
        self.discovered_options = discovered_options


class HTMLParser:
    def __init__(self, raw_html: str, base_url: str):
        self.raw_html = raw_html
        self.base_url = base_url
        self.soup = BeautifulSoup(raw_html, "html.parser")

    def parse(self) -> HTMLParserResult:
        metadata = self._extract_metadata()
        all_elements = self.soup.find_all()
        num_dom_elements = len(all_elements)

        # Byte calculations and minification heuristic
        html_bytes = len(self.raw_html.encode("utf-8"))
        text_content = self.soup.get_text(separator=" ", strip=True)
        text_bytes = len(text_content.encode("utf-8"))
        text_ratio = round((text_bytes / max(1, html_bytes)), 4)

        line_count = self.raw_html.count("\n")
        avg_line_length = html_bytes / max(1, line_count)
        is_html_minified = avg_line_length > 200 or (line_count <= 2 and html_bytes > 500)

        scripts = self._extract_scripts()
        stylesheets = self._extract_stylesheets()
        images = self._extract_images()
        preloads = self._extract_preloads()
        fonts = self._extract_fonts(preloads)
        form_actions = self._extract_form_actions()
        external_links = self._extract_external_links()
        discovered_options = self._extract_discovered_options()

        return HTMLParserResult(
            metadata=metadata,
            num_dom_elements=num_dom_elements,
            raw_html_bytes=html_bytes,
            text_bytes=text_bytes,
            text_to_html_ratio=text_ratio,
            is_html_minified=is_html_minified,
            scripts=scripts,
            stylesheets=stylesheets,
            images=images,
            fonts=fonts,
            preloads=preloads,
            form_actions=form_actions,
            external_links=external_links,
            soup=self.soup,
            discovered_options=discovered_options,
        )


    def _extract_metadata(self) -> SiteMetadata:
        title_tag = self.soup.find("title")
        title = title_tag.get_text().strip() if title_tag else ""

        # Meta description
        meta_desc_tag = self.soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None

        # Charset
        meta_charset = self.soup.find("meta", attrs={"charset": True})
        charset = meta_charset.get("charset") if meta_charset else None
        if not charset:
            meta_ct = self.soup.find("meta", attrs={"http-equiv": re.compile(r"^content-type$", re.I)})
            if meta_ct and "content" in meta_ct.attrs:
                match = re.search(r"charset=([\w-]+)", meta_ct["content"], re.I)
                if match:
                    charset = match.group(1)

        # Canonical
        canonical_tag = self.soup.find("link", attrs={"rel": lambda r: r and "canonical" in r})
        canonical_url = urljoin(self.base_url, canonical_tag.get("href", "")) if canonical_tag and canonical_tag.get("href") else None

        # Viewport
        meta_vp = self.soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
        viewport = meta_vp.get("content", "").strip() if meta_vp else None

        return SiteMetadata(
            title=title,
            meta_description=meta_desc,
            charset=charset,
            canonical_url=canonical_url,
            viewport=viewport,
        )

    def _extract_scripts(self) -> List[ParsedScript]:
        scripts: List[ParsedScript] = []
        head = self.soup.find("head")
        head_scripts = set(head.find_all("script")) if head else set()

        for tag in self.soup.find_all("script"):
            src = tag.get("src")
            has_async = tag.has_attr("async")
            has_defer = tag.has_attr("defer")
            script_type = tag.get("type", "").lower()
            is_module = script_type == "module"

            if src:
                resolved_src = urljoin(self.base_url, src)
                # A script is render blocking if it is in <head> and not async/defer/module
                is_blocking = (tag in head_scripts) and not (has_async or has_defer or is_module)
                scripts.append(
                    ParsedScript(
                        src=resolved_src,
                        is_inline=False,
                        content="",
                        is_blocking=is_blocking,
                        is_defer=has_defer,
                        is_async=has_async,
                        is_module=is_module,
                        size_bytes=0,
                    )
                )
            else:
                inline_code = tag.string or tag.get_text() or ""
                inline_size = len(inline_code.encode("utf-8"))
                # Inline scripts in <head> block HTML parsing unless deferred/module
                is_blocking = (tag in head_scripts) and not is_module
                scripts.append(
                    ParsedScript(
                        src=None,
                        is_inline=True,
                        content=inline_code,
                        is_blocking=is_blocking,
                        is_defer=has_defer,
                        is_async=has_async,
                        is_module=is_module,
                        size_bytes=inline_size,
                    )
                )

        return scripts

    def _extract_stylesheets(self) -> List[ParsedStylesheet]:
        stylesheets: List[ParsedStylesheet] = []

        # External stylesheets
        for tag in self.soup.find_all("link", rel=lambda r: r and "stylesheet" in r):
            href = tag.get("href")
            if not href:
                continue
            media = tag.get("media", "").lower().strip()
            # Non-blocking if media is specifically print
            is_blocking = media != "print"
            resolved_href = urljoin(self.base_url, href)
            stylesheets.append(
                ParsedStylesheet(
                    href=resolved_href,
                    is_inline=False,
                    content="",
                    size_bytes=0,
                    is_render_blocking=is_blocking,
                )
            )

        # Inline style blocks
        for tag in self.soup.find_all("style"):
            css_code = tag.string or tag.get_text() or ""
            stylesheets.append(
                ParsedStylesheet(
                    href=None,
                    is_inline=True,
                    content=css_code,
                    size_bytes=len(css_code.encode("utf-8")),
                    is_render_blocking=True,
                )
            )

        return stylesheets

    def _extract_images(self) -> List[ParsedImage]:
        images: List[ParsedImage] = []
        for tag in self.soup.find_all("img"):
            src = tag.get("src") or tag.get("data-src") or ""
            is_data_uri = src.startswith("data:")
            resolved_src = src if is_data_uri else urljoin(self.base_url, src)

            # Check dimensions in attributes or inline style
            width = tag.get("width")
            height = tag.get("height")
            style = tag.get("style", "").lower()
            has_style_dims = ("width:" in style or "width :" in style) and ("height:" in style or "height :" in style)
            has_dimensions = bool((width and height) or has_style_dims)

            # Check loading attribute
            loading = tag.get("loading", "").lower().strip()
            is_lazy = loading == "lazy"

            images.append(
                ParsedImage(
                    src=resolved_src,
                    is_data_uri=is_data_uri,
                    width=str(width) if width else None,
                    height=str(height) if height else None,
                    has_dimensions=has_dimensions,
                    is_lazy=is_lazy,
                    alt=tag.get("alt"),
                    size_bytes=len(src.encode("utf-8")) if is_data_uri else 0,
                )
            )

        return images

    def _extract_preloads(self) -> List[ParsedPreload]:
        preloads: List[ParsedPreload] = []
        for tag in self.soup.find_all("link", rel=lambda r: r and "preload" in r):
            href = tag.get("href")
            if not href:
                continue
            as_type = tag.get("as", "script").lower()
            preloads.append(
                ParsedPreload(
                    href=urljoin(self.base_url, href),
                    as_type=as_type,
                )
            )
        return preloads

    def _extract_fonts(self, preloads: List[ParsedPreload]) -> List[ParsedFont]:
        fonts: List[ParsedFont] = []
        for p in preloads:
            if p.as_type == "font":
                fonts.append(ParsedFont(href=p.href, source="preload"))

        # Look for font stylesheets (e.g. Google Fonts)
        for tag in self.soup.find_all("link", rel=lambda r: r and "stylesheet" in r):
            href = tag.get("href", "")
            if "fonts.googleapis.com" in href or "font" in href.lower():
                fonts.append(ParsedFont(href=urljoin(self.base_url, href), source="link"))

        return fonts

    def _extract_form_actions(self) -> List[str]:
        actions: List[str] = []
        for form in self.soup.find_all("form"):
            action = form.get("action", "")
            if action:
                actions.append(urljoin(self.base_url, action))
            else:
                actions.append(self.base_url)
        return actions

    def _extract_external_links(self) -> List[str]:
        links: List[str] = []
        base_host = urlparse(self.base_url).netloc
        for a in self.soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("http://", "https://")):
                link_host = urlparse(href).netloc
                if link_host and link_host != base_host:
                    links.append(href)
        return links

    def _extract_discovered_options(self) -> DiscoveredOptionsSummary:
        base_parsed = urlparse(self.base_url)
        base_host = base_parsed.netloc

        internal_links: List[DiscoveredOption] = []
        seen_links = set()

        for a in self.soup.find_all("a", href=True):
            raw_href = a["href"].strip()
            if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full_url = urljoin(self.base_url, raw_href)
            parsed_full = urlparse(full_url)
            is_internal = (parsed_full.netloc == base_host or not parsed_full.netloc)
            if full_url not in seen_links:
                seen_links.add(full_url)
                anchor_text = a.get_text(separator=" ", strip=True) or a.get("title") or a.get("aria-label") or parsed_full.path or "Link"
                anchor_text = anchor_text[:60].strip()
                selector = f"a[href='{raw_href}']"
                internal_links.append(
                    DiscoveredOption(
                        category="link",
                        label=anchor_text + ("" if is_internal else " (External)"),
                        target=full_url,
                        selector=selector,
                        attributes={"path": parsed_full.path or "/", "is_internal": str(is_internal)}
                    )
                )
                if len(internal_links) >= 50:
                    break

        # Extract <select> dropdown options
        select_options: List[DiscoveredOption] = []
        for select in self.soup.find_all("select"):
            select_name = select.get("name") or select.get("id") or "select"
            select_id = select.get("id")
            selector = f"#{select_id}" if select_id else f"select[name='{select_name}']"
            for opt in select.find_all("option"):
                val = opt.get("value")
                if val is None:
                    val = opt.get_text(strip=True)
                opt_label = opt.get_text(strip=True) or str(val)
                select_options.append(
                    DiscoveredOption(
                        category="select_option",
                        label=f"{select_name} -> {opt_label}",
                        target=str(val),
                        selector=selector,
                        name=select_name,
                        attributes={"value": str(val)}
                    )
                )
                if len(select_options) >= 40:
                    break
            if len(select_options) >= 40:
                break

        # Extract buttons & interactive triggers
        buttons: List[DiscoveredOption] = []
        seen_buttons = set()
        btn_elements = self.soup.find_all(["button", "input"])
        for btn in btn_elements:
            tag_name = btn.name
            if tag_name == "input" and btn.get("type", "").lower() not in ("button", "submit", "reset"):
                continue
            
            btn_id = btn.get("id")
            btn_name = btn.get("name")
            btn_class = btn.get("class")
            
            label = btn.get_text(strip=True) or btn.get("value") or btn.get("aria-label") or btn.get("title") or ""
            label = label[:50].strip()
            if not label and not btn_id:
                continue
            if not label:
                label = btn_id or "Button"

            if btn_id:
                selector = f"#{btn_id}"
            elif btn_name:
                selector = f"{tag_name}[name='{btn_name}']"
            elif btn_class and len(btn_class) > 0:
                selector = f"{tag_name}.{btn_class[0]}"
            else:
                selector = tag_name

            key = (selector, label)
            if key not in seen_buttons:
                seen_buttons.add(key)
                buttons.append(
                    DiscoveredOption(
                        category="button",
                        label=label,
                        target=selector,
                        selector=selector,
                        name=btn_name,
                        attributes={"type": btn.get("type", "button")}
                    )
                )
                if len(buttons) >= 35:
                    break

        # Extract forms
        forms: List[DiscoveredOption] = []
        for form in self.soup.find_all("form"):
            form_id = form.get("id")
            form_action = form.get("action", "")
            resolved_action = urljoin(self.base_url, form_action) if form_action else self.base_url
            form_method = form.get("method", "GET").upper()
            selector = f"#{form_id}" if form_id else "form"
            forms.append(
                DiscoveredOption(
                    category="form",
                    label=f"{form_id or 'Form'} ({form_method})",
                    target=resolved_action,
                    selector=selector,
                    attributes={"method": form_method, "action": resolved_action}
                )
            )

        total_count = len(internal_links) + len(select_options) + len(buttons) + len(forms)
        return DiscoveredOptionsSummary(
            total_count=total_count,
            internal_links=internal_links,
            select_options=select_options,
            buttons=buttons,
            forms=forms,
        )

