# PageLens — Deep Web Performance & Security Analyzer

PageLens is an automated, developer-first URL performance analyzer that audits websites for speed, size, and safety. It parses HTML/CSS statically and renders dynamic single-page applications via headless Playwright Chromium to compute actionable performance scores, pinpoint structural anti-patterns, and verify production security postures.

```
       ┌────────────────────────────────────────────────────────┐
       │                   PageLens Frontend                    │
       │    (React 18 + Vite + TypeScript + Tailwind + Recharts) │
       └───────────────────────────┬────────────────────────────┘
                                   │ HTTP / JSON API
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                   FastAPI ASGI Gateway                 │
       │  (Rate Limiter, SSRF Guard, DNS Rebinding Verifier)   │
       └──────────────┬─────────────────────────┬───────────────┘
                      │                         │
                      ▼                         ▼
         ┌────────────────────────┐┌────────────────────────┐
         │ Static Scraping Engine ││ Playwright Headless    │
         │ - httpx HTTP/2 Client  ││ - Throttled 4G / 4x CPU│
         │ - BeautifulSoup4 HTML  ││ - PerformanceObserver  │
         │ - tinycss2 Collector   ││ - Median of 3 Runs     │
         └────────────┬───────────┘└────────────┬───────────┘
                      │                         │
                      └────────────┬────────────┘
                                   │ Raw Metrics & Assets
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │             Rule & Metrics Processing Engine           │
       │  - Structural Sizing & Compression Heuristics          │
       │  - Core Web Vitals Timing (FCP, LCP, CLS, TBT, TTFB)   │
       │  - 18+ Diagnostic Shortcoming Rule Checks              │
       │  - Security & Header Hygiene Audit                     │
       │  - Weighted 0-100 Performance Score Math               │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │               Report & Export Dispatcher               │
       │      (In-Memory / Redis Queue & JSON/PDF Exporter)     │
       └────────────────────────────────────────────────────────┘
```

---

## Features

- **Dual-Mode Inspection**:
  - **Quick (Static)**: Sub-second fetch, DOM parsing, stylesheet analysis, and security header audit.
  - **Deep (Full Render)**: Headless Playwright Chromium mobile emulation (412x915, DPR 3, Slow 4G, 4x CPU throttle), 3-run median aggregation, PerformanceObserver Web Vitals collection, and network waterfall.
- **SSRF & DNS Rebinding Immunity**: Validates private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, `::1`), allowed ports (`80, 443, 8080-8090`), URL length (< 2048), and resolves DNS synchronously to prevent DNS rebinding attacks.
- **Shortcomings Rule Engine**: 18+ technical rules with diagnostic causes, concrete code examples, remediation steps, and web.dev/MDN references.
- **Security Audit**: Strict HTTPS enforcement, HSTS, CSP, X-Content-Type-Options, frame-ancestors/X-Frame-Options, Referrer-Policy, cookie security flags, mixed content detection, and vulnerable legacy library scans.
- **Comprehensive Score Breakdown**: Weighted 0-100 score split across Structure (25%), Timing (35%), Shortcomings (25%), and Security (15%).
- **Developer-Grade Dashboard**: Built with React 18, TailwindCSS, TanStack Query, Zustand, and Recharts, supporting Dark Mode, interactive gauges, resource breakdowns, and waterfall charts.
- **Raw Scraped Source Inspector & Downloads**: Dedicated tab and streaming endpoints to inspect and download raw scraped HTML and aggregated CSS (inline `<style>` blocks + resolved external stylesheets) with real-time keyword search, line numbers, clipboard copying, and file downloads.
- **Export Options**: Downloadable reports in structured JSON and printable PDF formats.

---

## Tech Stack

| Domain | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, TailwindCSS, TanStack Query, Recharts, Zustand, Lucide Icons |
| Backend | Python 3.11+, FastAPI, Uvicorn, Playwright Chromium, httpx, BeautifulSoup4, tinycss2, Pydantic v2 |
| Data & Cache | Redis 7 (with transparent in-memory `fakeredis` fallback), slowapi rate limiting |
| DevOps & CI | Docker, Docker Compose, GNU Makefile, GitHub Actions CI |

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+ & npm
- Docker & Docker Compose (optional, for containerized execution)

### 1. Clone & Configure
```bash
git clone https://github.com/your-org/pagelens.git
cd pagelens
cp .env.example .env
```

### 2. Run with Docker Compose
```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API Docs: `http://localhost:8000/docs`
- Redis: `localhost:6379`

### 3. Run Locally (Without Docker)

#### Backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

---

## API Reference

### 1. Submit Analysis Job
`POST /api/v1/analyze`
```json
{
  "url": "https://example.com",
  "mode": "quick" // or "full"
}
```
**Response (200 OK)**:
```json
{
  "job_id": "a58b29c1-4b13-4e89-a2e6-7b494639e230",
  "status": "queued",
  "mode": "quick",
  "submitted_at": "2026-10-15T12:00:00Z"
}
```

### 2. Fetch Analysis Report
`GET /api/v1/report/{job_id}`

**Pending State (200 OK)**:
```json
{
  "job_id": "a58b29c1-4b13-4e89-a2e6-7b494639e230",
  "status": "running",
  "progress_phase": "Rendering"
}
```

**Completed State (200 OK)**: Returns full `Report` object with metrics, shortcomings, security audit, and waterfall entries.

### 3. Export Report
`GET /api/v1/report/{job_id}/export?format=json|pdf`
Downloads structured JSON or formatted PDF audit report.

### 4. Raw Scraped Source
`GET /api/v1/report/{job_id}/source`
Returns the raw scraped HTML document and aggregated CSS stylesheets:
```json
{
  "job_id": "a58b29c1-4b13-4e89-a2e6-7b494639e230",
  "url": "https://example.com",
  "html": "<!DOCTYPE html><html><head>...",
  "css": "/* === Inline <style> Blocks === */...",
  "html_bytes": 12560,
  "css_bytes": 4820
}
```

### 5. Download Scraped Source File
`GET /api/v1/report/{job_id}/source/download?type=html|css`
Streams raw `.html` or `.css` file as a direct browser attachment download (`Content-Disposition: attachment`).

### 6. Health Check
`GET /api/v1/health`
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-10-15T12:00:00Z"
}
```

---

## Scoring Architecture

PageLens scores URLs on a calibrated 0-100 scale:

| Category | Weight | Description |
|---|---|---|
| **Structure & Size** | 25% | Evaluates total payload size, HTML/CSS/JS weight, request count, and DOM complexity. |
| **Timing & Vitals** | 35% | Evaluates TTFB, FCP, LCP, CLS, and TBT against Google Core Web Vitals thresholds. |
| **Shortcomings** | 25% | Deductions applied based on triggered anti-patterns (High: -12 pts, Medium: -6 pts, Low: -2 pts). |
| **Security Audit** | 15% | Evaluates presence of modern HTTPS, HSTS, CSP, X-Content-Type-Options, and cookie safety. |

---

## Shortcomings Rules & Threshold Rationales

| Rule ID | Severity | Threshold | Technical Rationale |
|---|---|---|---|
| `large-html` | High | > 100 KB uncompressed | Bloated initial DOM delays TTFB parsing and burns main-thread CPU during tokenization. |
| `large-css` | High | > 100 KB uncompressed | CSS is render-blocking. Heavy CSS stalls first paint and increases network latency on mobile. |
| `large-js` | High | > 300 KB uncompressed | V8 script parsing and compilation blocks the main thread, degrading First Input Delay (INP/TBT). |
| `too-many-requests` | Medium | > 100 requests | Connection contention, HTTP/2 multiplexing overhead, and socket queue latency. |
| `too-many-dom` | Medium | > 1,500 elements | Excessive DOM nodes increase memory footprint and prolong style calculation recalculations. |
| `render-blocking` | High | Blocking `<script>`/`<link>` in `<head>` | Head scripts without `defer`/`async` halt the parser until fetched and executed. |
| `no-compression` | High | Missing `gzip` / `br` | Uncompressed text transfers 3-5x more bytes over the wire unnecessarily. |
| `unminified-css` | Medium | Avg line length < 200 chars & spaces | Comments, whitespace, and formatting should be stripped in production builds. |
| `unminified-html` | Low | Avg line length < 200 chars & spaces | Excessive comments and unminified whitespace inflate HTML payload. |
| `large-images` | High | Image payload > 200 KB | Over-budget hero and raster images choke network bandwidth and delay LCP. |
| `no-lazy-loading` | Medium | `<img>` without `loading="lazy"` | Non-critical below-the-fold images compete for initial viewport bandwidth. |
| `missing-dimensions` | High | `<img>` missing `width` & `height` | Missing aspect ratio attributes trigger Cumulative Layout Shift (CLS) upon image load. |
| `slow-ttfb` | High | TTFB > 600 ms | Slow server response delay cascades through every subsequent resource request. |
| `poor-lcp` | High | LCP > 2,500 ms | Web Vitals threshold: over 2.5s causes noticeable user perceived loading delay. |
| `high-cls` | High | CLS > 0.1 | Layout instability creates frustrating misclicks and poor user experience. |
| `long-tasks` | High | TBT > 300 ms | Accumulated CPU tasks > 50ms block user input responsiveness during page hydration. |
| `no-cache-headers` | Medium | `Cache-Control` missing or max-age < 3600 | Missing caching forces repeat visits to re-download unchanged static assets. |
| `mixed-content` | High | `http://` resources on `https://` | Browsers block active mixed content, while passive mixed content risks eavesdropping. |

---

## Known Limitations

1. **JavaScript-Heavy SPAs (Static Mode)**:
   - In Quick (static) mode, Client-Side Rendered (CSR) applications (e.g. pure React/Vue SPAs with empty `<div id="root"></div>`) will only show initial skeleton markup. Use Deep (full render) mode to evaluate the hydrated DOM.
2. **Geographical Variance**:
   - Analysis executes from the server's network location. Edge CDN routing, Geo-DNS, and international latency can produce different results compared to local client testing.
3. **Cold vs. Warm Cache**:
   - Headless Playwright runs with clean incognito browser contexts to emulate first-time visitor experience (cold cache). Repeat visitor performance will typically be faster.
4. **Synthetic Headless Emulation vs. Real Hardware**:
   - Playwright applies 4x CPU throttling and Slow 4G network emulation. While this mimics mid-tier mobile hardware (Moto G4 baseline), real mobile devices possess unique thermal throttling and hardware GPU nuances.

---

## Roadmap

- [ ] Multi-region distributed agent probe testing.
- [ ] Automated Lighthouse JSON parity export and differential comparison.
- [ ] Scheduled recurring audit cron jobs with email alerts.
- [ ] Full CSS AST tree shaking simulation to measure unused CSS percentage.
- [ ] Webhook triggers on performance regression in CI/CD pipelines.

---

## License

MIT License. Built for performance engineers.
