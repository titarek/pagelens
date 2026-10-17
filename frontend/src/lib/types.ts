export type AnalysisMode = 'static' | 'full';

export interface ScoreBreakdown {
  total: number;
  structure: number;
  timing: number;
  shortcomings: number;
  security: number;
}

export interface StructuralMetrics {
  html_bytes: number;
  css_bytes: number;
  js_bytes: number;
  image_bytes: number;
  font_bytes: number;
  total_bytes: number;
  num_requests: number;
  num_dom_elements: number;
  num_stylesheets: number;
  num_scripts: number;
  num_blocking_scripts: number;
  num_images: number;
  num_fonts: number;
  inline_css_ratio: number;
  inline_js_ratio: number;
  compression_used: string;
  minified_html: boolean;
  minified_css: boolean;
  text_to_html_ratio: number;
  css_to_html_ratio: number;
  images_over_200kb: number;
  render_blocking_resources: number;
}

export interface TimingMetrics {
  ttfb_ms: number;
  dom_content_loaded_ms: number;
  load_ms: number;
  fcp_ms: number;
  lcp_ms: number;
  cls: number;
  tbt_ms: number;
  inp_ms?: number | null;
  server_response_ms: number;
  dns_ms: number;
  tls_ms: number;
  render_runs_variance?: {
    runs_count: number;
    fcp_var: number;
    lcp_var: number;
    cls_var: number;
    tbt_var: number;
    ttfb_var: number;
  } | null;
}

export interface ResourceEntry {
  url: string;
  type: string;
  size_bytes: number;
  duration_ms: number;
  status: number;
  start_time_ms: number;
  is_render_blocking?: boolean;
}

export interface Shortcoming {
  id: string;
  severity: 'high' | 'medium' | 'low';
  title: string;
  cause: string;
  fix: string;
  example: string;
  reference: string;
}

export interface SecurityCheck {
  id: string;
  title: string;
  status: 'pass' | 'warn' | 'fail';
  detail: string;
  fix: string;
}

export interface SecurityAudit {
  score: number;
  passed: number;
  warnings: number;
  failures: number;
  checks: SecurityCheck[];
}

export interface SiteMetadata {
  title: string;
  meta_description?: string | null;
  charset?: string | null;
  canonical_url?: string | null;
  viewport?: string | null;
  content_type?: string | null;
}

export interface ScrapedSourceData {
  html: string;
  css: string;
  html_bytes: number;
  css_bytes: number;
}

export interface DiscoveredOption {
  category: 'link' | 'select_option' | 'button' | 'form';
  label: string;
  target: string;
  selector?: string | null;
  name?: string | null;
  attributes?: Record<string, string>;
}

export interface DiscoveredOptionsSummary {
  total_count: number;
  internal_links: DiscoveredOption[];
  select_options: DiscoveredOption[];
  buttons: DiscoveredOption[];
  forms: DiscoveredOption[];
}

export interface NetworkRequestLog {
  url: string;
  method: string;
  status: number;
  resource_type: string;
  size_bytes: number;
  duration_ms: number;
}

export interface InteractionRequest {
  url: string;
  action_type: 'click' | 'select' | 'navigate';
  selector?: string | null;
  value?: string | null;
  target_url?: string | null;
}

export interface InteractionResult {
  success: boolean;
  action_type: string;

  target_description: string;
  initial_url: string;
  final_url: string;
  duration_ms: number;
  url_changed: boolean;
  dom_elements_before: number;
  dom_elements_after: number;
  dom_delta: number;
  html_after: string;
  html_bytes_after: number;
  html_bytes_delta: number;
  css_after: string;
  css_bytes_after: number;
  triggered_requests_count: number;
  triggered_requests_bytes: number;
  network_requests: NetworkRequestLog[];
  console_logs: string[];
  summary: string;
  error?: string | null;
}

export interface Report {
  job_id: string;
  url: string;
  final_url: string;
  fetched_at: string;
  mode: AnalysisMode;
  status: 'ok' | 'partial' | 'failed';
  score: ScoreBreakdown;
  structural: StructuralMetrics;
  timing?: TimingMetrics | null;
  resources: ResourceEntry[];
  shortcomings: Shortcoming[];
  security: SecurityAudit;
  metadata: SiteMetadata;
  scraped_source?: ScrapedSourceData | null;
  discovered_options?: DiscoveredOptionsSummary | null;
  errors: string[];
}

export interface AnalyzeRequest {

  url: string;
  mode: AnalysisMode;
}

export interface AnalyzeResponse {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  mode: AnalysisMode;
  submitted_at: string;
  url: string;
}

export interface JobProgressResponse {
  job_id: string;
  status: 'queued' | 'running' | 'failed';
  progress_phase?: string;
  errors?: string[];
}

export interface RecentAnalysis {
  job_id: string;
  url: string;
  mode: AnalysisMode;
  score?: number;
  timestamp: string;
}
