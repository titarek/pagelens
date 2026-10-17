import asyncio
import gzip
import re
from typing import Dict, List, Set, Tuple, Optional
from urllib.parse import urljoin
import zlib
import httpx
import tinycss2
from app.core.config import settings
from app.core.logging import logger
from app.core.security import validate_and_resolve_url, SSRFValidationError
from app.scraper.assets import ParsedStylesheet

try:
    import brotli
except ImportError:
    brotli = None



class CSSCollectionResult:
    def __init__(
        self,
        inline_css_text: str,
        inline_bytes: int,
        external_css_bytes: int,
        total_css_bytes: int,
        stylesheets_fetched: int,
        data_uri_count: int,
        inline_css_ratio: float,
        is_css_minified: bool,
        stylesheet_entries: List[ParsedStylesheet],
    ):
        self.inline_css_text = inline_css_text
        self.inline_bytes = inline_bytes
        self.external_css_bytes = external_css_bytes
        self.total_css_bytes = total_css_bytes
        self.stylesheets_fetched = stylesheets_fetched
        self.data_uri_count = data_uri_count
        self.inline_css_ratio = inline_css_ratio
        self.is_css_minified = is_css_minified
        self.stylesheet_entries = stylesheet_entries


class CSSCollector:
    def __init__(
        self,
        max_stylesheets: int = settings.max_css_files,
        max_bytes_per_css: int = settings.max_single_css_bytes,
        max_import_depth: int = settings.max_import_depth,
        allow_local_for_testing: bool = False,
    ):
        self.max_stylesheets = max_stylesheets
        self.max_bytes_per_css = max_bytes_per_css
        self.max_import_depth = max_import_depth
        self.allow_local_for_testing = allow_local_for_testing

    async def collect(
        self,
        parsed_stylesheets: List[ParsedStylesheet],
        base_url: str,
    ) -> CSSCollectionResult:
        inline_blocks: List[str] = []
        external_targets: List[ParsedStylesheet] = []
        data_uri_count = 0

        for s in parsed_stylesheets:
            if s.is_inline:
                inline_blocks.append(s.content)
            elif s.href:
                if s.href.startswith("data:"):
                    data_uri_count += 1
                else:
                    external_targets.append(s)

        concatenated_inline = "\n".join(inline_blocks)
        inline_bytes = len(concatenated_inline.encode("utf-8"))

        fetched_entries: List[ParsedStylesheet] = []
        visited_urls: Set[str] = set()
        queue: List[Tuple[str, int, bool]] = [
            (s.href, 0, s.is_render_blocking) for s in external_targets if s.href
        ]

        # Concurrently fetch external stylesheets up to limit
        external_bytes = 0
        all_css_chunks: List[str] = [concatenated_inline] if concatenated_inline else []

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            verify=False,
            headers={"User-Agent": settings.user_agent},
        ) as client:
            while queue and len(fetched_entries) < self.max_stylesheets:
                current_batch = queue[: min(5, self.max_stylesheets - len(fetched_entries))]
                queue = queue[len(current_batch) :]

                tasks = [
                    self._fetch_stylesheet(client, url, depth, is_blocking, visited_urls)
                    for url, depth, is_blocking in current_batch
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for res in results:
                    if isinstance(res, ParsedStylesheet):
                        fetched_entries.append(res)
                        external_bytes += res.size_bytes
                        all_css_chunks.append(res.content)
                        # Add new imports if within max depth
                        for imp_url in res.imports:
                            if imp_url not in visited_urls and len(queue) + len(fetched_entries) < self.max_stylesheets:
                                # imports are at depth + 1
                                queue.append((imp_url, 1, res.is_render_blocking))

        total_css_bytes = inline_bytes + external_bytes
        inline_ratio = round(inline_bytes / max(1, total_css_bytes), 4)

        # Minification heuristic across all collected CSS
        is_css_minified = False
        if total_css_bytes > 0:
            full_css = "\n".join(all_css_chunks)
            total_lines = full_css.count("\n")
            avg_line_length = len(full_css) / max(1, total_lines)
            is_css_minified = avg_line_length > 200 or (total_lines <= 3 and total_css_bytes > 500)

        # Combine inline entries with fetched external entries
        all_entries = [s for s in parsed_stylesheets if s.is_inline] + fetched_entries

        return CSSCollectionResult(
            inline_css_text=concatenated_inline,
            inline_bytes=inline_bytes,
            external_css_bytes=external_bytes,
            total_css_bytes=total_css_bytes,
            stylesheets_fetched=len(fetched_entries),
            data_uri_count=data_uri_count,
            inline_css_ratio=inline_ratio,
            is_css_minified=is_css_minified,
            stylesheet_entries=all_entries,
        )

    async def _fetch_stylesheet(
        self,
        client: httpx.AsyncClient,
        url: str,
        depth: int,
        is_render_blocking: bool,
        visited_urls: Set[str],
    ) -> Optional[ParsedStylesheet]:
        if url in visited_urls:
            return None
        visited_urls.add(url)

        try:
            validate_and_resolve_url(url, allow_local_for_testing=self.allow_local_for_testing)
        except SSRFValidationError as e:
            logger.warning(f"Blocked stylesheet SSRF attempt: {url} ({e})")
            return None

        try:
            resp = await client.get(url)
            if resp.status_code >= 400:
                logger.debug(f"Failed to fetch stylesheet {url}: status {resp.status_code}")
                return None

            raw_bytes = resp.content
            decompressed_css = raw_bytes
            css_encoding = resp.headers.get("content-encoding", "").lower().strip()
            if "br" in css_encoding and brotli:
                try:
                    decompressed_css = brotli.decompress(raw_bytes)
                except Exception:
                    pass
            elif "gzip" in css_encoding:
                try:
                    decompressed_css = gzip.decompress(raw_bytes)
                except Exception:
                    pass
            elif "deflate" in css_encoding:
                try:
                    decompressed_css = zlib.decompress(raw_bytes)
                except Exception:
                    pass

            if len(decompressed_css) > self.max_bytes_per_css:
                decompressed_css = decompressed_css[: self.max_bytes_per_css]

            css_text = decompressed_css.decode(resp.encoding or "utf-8", errors="replace")
            size_bytes = len(raw_bytes)


            imports: List[str] = []
            if depth < self.max_import_depth:
                imports = self._extract_imports(css_text, url)

            return ParsedStylesheet(
                href=url,
                is_inline=False,
                content=css_text,
                size_bytes=size_bytes,
                is_render_blocking=is_render_blocking,
                imports=imports,
            )
        except Exception as e:
            logger.debug(f"Error fetching stylesheet {url}: {e}")
            return None

    def _extract_imports(self, css_text: str, source_url: str) -> List[str]:
        imports: List[str] = []
        try:
            rules = tinycss2.parse_stylesheet(css_text, skip_comments=True)
            for rule in rules:
                if rule.type == "at-rule" and rule.lower_at_keyword == "import":
                    # Extract URL from prelude
                    prelude_str = tinycss2.serialize(rule.prelude)
                    # Match url(...) or "..." or '...'
                    match = re.search(r'''(?:url\(\s*['"]?([^'")]+)['"]?\s*\)|['"]([^'"]+)['"])''', prelude_str)
                    if match:
                        raw_link = match.group(1) or match.group(2)
                        if raw_link and not raw_link.startswith("data:"):
                            resolved = urljoin(source_url, raw_link.strip())
                            imports.append(resolved)
        except Exception as e:
            logger.debug(f"Error parsing CSS with tinycss2: {e}")
            # Fallback regex
            for m in re.finditer(r'''@import\s+(?:url\(['"]?([^'")]+)['"]?\)|['"]([^'"]+)['"])''', css_text):
                raw_link = m.group(1) or m.group(2)
                if raw_link and not raw_link.startswith("data:"):
                    imports.append(urljoin(source_url, raw_link.strip()))

        return imports
