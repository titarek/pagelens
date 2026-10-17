from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field



class ScoreBreakdown(BaseModel):
    total: int = Field(..., ge=0, le=100, description="Overall weighted performance score (0-100)")
    structure: int = Field(..., ge=0, le=25, description="Structure & size score (0-25)")
    timing: int = Field(..., ge=0, le=35, description="Timing & Web Vitals score (0-35)")
    shortcomings: int = Field(..., ge=0, le=25, description="Shortcoming penalty score (0-25)")
    security: int = Field(..., ge=0, le=15, description="Security posture score (0-15)")


class StructuralMetrics(BaseModel):
    html_bytes: int = 0
    css_bytes: int = 0
    js_bytes: int = 0
    image_bytes: int = 0
    font_bytes: int = 0
    total_bytes: int = 0
    num_requests: int = 0
    num_dom_elements: int = 0
    num_stylesheets: int = 0
    num_scripts: int = 0
    num_blocking_scripts: int = 0
    num_images: int = 0
    num_fonts: int = 0
    inline_css_ratio: float = 0.0
    inline_js_ratio: float = 0.0
    compression_used: str = "none"  # "gzip", "br", "deflate", "none"
    minified_html: bool = False
    minified_css: bool = False
    text_to_html_ratio: float = 0.0
    css_to_html_ratio: float = 0.0
    images_over_200kb: int = 0
    render_blocking_resources: int = 0


class TimingMetrics(BaseModel):
    ttfb_ms: float = 0.0
    dom_content_loaded_ms: float = 0.0
    load_ms: float = 0.0
    fcp_ms: float = 0.0
    lcp_ms: float = 0.0
    cls: float = 0.0
    tbt_ms: float = 0.0
    inp_ms: Optional[float] = None
    server_response_ms: float = 0.0
    dns_ms: float = 0.0
    tls_ms: float = 0.0
    render_runs_variance: Optional[dict] = None


class ResourceEntry(BaseModel):
    url: str
    type: str = "other"  # document, stylesheet, script, image, font, xhr, other
    size_bytes: int = 0
    duration_ms: float = 0.0
    status: int = 200
    start_time_ms: float = 0.0
    is_render_blocking: bool = False


class Shortcoming(BaseModel):
    id: str
    severity: Literal["high", "medium", "low"]
    title: str
    cause: str
    fix: str
    example: str
    reference: str


class SecurityCheck(BaseModel):
    id: str
    title: str
    status: Literal["pass", "warn", "fail"]
    detail: str
    fix: str


class SecurityAudit(BaseModel):
    score: int = 0
    passed: int = 0
    warnings: int = 0
    failures: int = 0
    checks: List[SecurityCheck] = []


class SiteMetadata(BaseModel):
    title: str = ""
    meta_description: Optional[str] = None
    charset: Optional[str] = None
    canonical_url: Optional[str] = None
    viewport: Optional[str] = None
    content_type: Optional[str] = None


class ScrapedSourceData(BaseModel):
    html: str = ""
    css: str = ""
    html_bytes: int = 0
    css_bytes: int = 0


class DiscoveredOption(BaseModel):
    category: Literal["link", "select_option", "button", "form"]
    label: str
    target: str  # URL, option value, form action, or button description
    selector: Optional[str] = None
    name: Optional[str] = None
    attributes: Dict[str, str] = {}


class DiscoveredOptionsSummary(BaseModel):
    total_count: int = 0
    internal_links: List[DiscoveredOption] = []
    select_options: List[DiscoveredOption] = []
    buttons: List[DiscoveredOption] = []
    forms: List[DiscoveredOption] = []


class NetworkRequestLog(BaseModel):
    url: str
    method: str = "GET"
    status: int = 200
    resource_type: str = "other"
    size_bytes: int = 0
    duration_ms: float = 0.0


class InteractionResult(BaseModel):
    success: bool
    action_type: str
    target_description: str
    initial_url: str
    final_url: str
    duration_ms: float
    url_changed: bool
    dom_elements_before: int = 0
    dom_elements_after: int = 0
    dom_delta: int = 0
    html_after: str = ""
    html_bytes_after: int = 0
    html_bytes_delta: int = 0
    css_after: str = ""
    css_bytes_after: int = 0
    triggered_requests_count: int = 0
    triggered_requests_bytes: int = 0
    network_requests: List[NetworkRequestLog] = []
    console_logs: List[str] = []
    summary: str
    error: Optional[str] = None


class Report(BaseModel):
    job_id: str
    url: str
    final_url: str
    fetched_at: datetime
    mode: Literal["static", "full"]
    status: Literal["ok", "partial", "failed"]
    score: ScoreBreakdown
    structural: StructuralMetrics
    timing: Optional[TimingMetrics] = None
    resources: List[ResourceEntry] = []
    shortcomings: List[Shortcoming] = []
    security: SecurityAudit
    metadata: SiteMetadata
    scraped_source: Optional[ScrapedSourceData] = None
    discovered_options: Optional[DiscoveredOptionsSummary] = None
    errors: List[str] = []

