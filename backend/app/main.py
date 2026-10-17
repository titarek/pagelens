import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import routes_health, routes_analyze, routes_report
from app.core.config import settings
from app.core.logging import logger
from app.core.security import SSRFValidationError

# Rate limiter keyed by client remote IP address
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)

app = FastAPI(
    title="PageLens API",
    version=settings.app_version,
    description="High-performance URL scraper, runtime metrics analyzer, and security auditor.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# CORS Configuration
_cors_origins = (
    settings.frontend_origin
    if isinstance(settings.frontend_origin, list)
    else [settings.frontend_origin]
)
_allow_all = "*" in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers_and_timing(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Strict response security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

    return response


@app.exception_handler(SSRFValidationError)
async def ssrf_validation_exception_handler(request: Request, exc: SSRFValidationError):
    logger.warning(f"SSRF validation blocked request: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_type": "SSRFValidationError"},
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"An internal server error occurred while processing the request: {exc}",
            "error_type": type(exc).__name__,
        },
        headers={"Access-Control-Allow-Origin": "*"},
    )


# Include API v1 Routers
app.include_router(routes_health.router, prefix="/api/v1")
app.include_router(routes_analyze.router, prefix="/api/v1")
app.include_router(routes_report.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
