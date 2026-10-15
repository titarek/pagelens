import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.core.security import validate_and_resolve_url, SSRFValidationError


class FetchResult:
    def __init__(
        self,
        url: str,
        final_url: str,
        status_code: int,
        headers: Dict[str, str],
        content: bytes,
        text: str,
        ttfb_ms: float,
        redirect_chain: List[str],
        transfer_size_bytes: int,
    ):
        self.url = url
        self.final_url = final_url
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.text = text
        self.ttfb_ms = ttfb_ms
        self.redirect_chain = redirect_chain
        self.transfer_size_bytes = transfer_size_bytes


class StaticFetcher:
    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_redirects: Optional[int] = None,
        max_response_bytes: Optional[int] = None,
        allow_local_for_testing: bool = False,
    ):
        self.user_agent = user_agent or settings.user_agent
        self.timeout_seconds = timeout_seconds or settings.default_timeout_seconds
        self.max_redirects = max_redirects or settings.max_redirects
        self.max_response_bytes = max_response_bytes or settings.max_response_size_bytes
        self.allow_local_for_testing = allow_local_for_testing

    async def fetch(self, target_url: str) -> FetchResult:
        """
        Fetches the target URL while strictly validating SSRF constraints at each redirect hop.
        Measures TTFB and records the full redirect chain.
        """
        # Initial SSRF check
        canonical_url, _ = validate_and_resolve_url(
            target_url, allow_local_for_testing=self.allow_local_for_testing
        )

        redirect_chain: List[str] = [canonical_url]
        current_url = canonical_url
        headers_to_send = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
        }

        transport = httpx.AsyncHTTPTransport(retries=1)
        async with httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(self.timeout_seconds, connect=10.0),
            follow_redirects=False,
            verify=False,  # Allow self-signed certs in test environments, security audit checks SSL separately
        ) as client:
            hops = 0
            while hops <= self.max_redirects:
                # SSRF check on each redirect hop
                validate_and_resolve_url(
                    current_url, allow_local_for_testing=self.allow_local_for_testing
                )

                req_start = time.perf_counter()
                try:
                    request = client.build_request("GET", current_url, headers=headers_to_send)
                    response = await client.send(request, stream=True)
                except httpx.TimeoutException:
                    raise TimeoutError(f"Connection timed out while fetching {current_url} (limit: {self.timeout_seconds}s)")
                except Exception as e:
                    raise IOError(f"Network error while fetching {current_url}: {e}")

                # Measure TTFB as time to receive headers
                ttfb_ms = (time.perf_counter() - req_start) * 1000

                # Check redirect
                if response.is_redirect and "location" in response.headers:
                    next_url = httpx.URL(response.headers["location"])
                    # Resolve relative redirect URLs
                    resolved_next = str(response.url.join(next_url))
                    await response.aclose()
                    redirect_chain.append(resolved_next)
                    current_url = resolved_next
                    hops += 1
                    continue

                # Not a redirect - stream and enforce size cap
                content_chunks = []
                total_bytes = 0
                async for chunk in response.aiter_bytes():
                    total_bytes += len(chunk)
                    if total_bytes > self.max_response_bytes:
                        await response.aclose()
                        raise ValueError(
                            f"Response payload exceeded maximum allowed size of {self.max_response_bytes} bytes."
                        )
                    content_chunks.append(chunk)

                await response.aclose()
                raw_bytes = b"".join(content_chunks)
                
                # Detect text encoding or fallback to utf-8 / response.encoding
                encoding = response.encoding or "utf-8"
                try:
                    text_content = raw_bytes.decode(encoding, errors="replace")
                except Exception:
                    text_content = raw_bytes.decode("utf-8", errors="replace")

                # Parse headers into dictionary
                resp_headers = {k.lower(): v for k, v in response.headers.items()}

                return FetchResult(
                    url=target_url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    headers=resp_headers,
                    content=raw_bytes,
                    text=text_content,
                    ttfb_ms=ttfb_ms,
                    redirect_chain=redirect_chain,
                    transfer_size_bytes=len(raw_bytes),
                )

            raise ValueError(f"Exceeded maximum redirect limit of {self.max_redirects} hops.")
