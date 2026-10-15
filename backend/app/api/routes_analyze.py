import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Request, status
from app.core.cache import storage
from app.core.security import validate_and_resolve_url
from app.schemas.request import AnalyzeRequest, AnalyzeResponse
from app.services.analyzer import analyzer_service

router = APIRouter(tags=["Analyze"])


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_url(
    req: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> AnalyzeResponse:
    # Synchronously validate URL for SSRF before accepting job
    canonical_url, _ = validate_and_resolve_url(req.url)

    job_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"

    initial_job_state = {
        "job_id": job_id,
        "url": canonical_url,
        "mode": req.mode,
        "status": "queued",
        "progress_phase": "Queued",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "errors": [],
    }
    storage.set_job(job_id, initial_job_state)

    # Queue execution asynchronously in background
    background_tasks.add_task(
        analyzer_service.run_analysis,
        job_id=job_id,
        url=canonical_url,
        mode=req.mode,
        client_ip=client_ip,
    )

    return AnalyzeResponse(
        job_id=job_id,
        status="queued",
        mode=req.mode,
        submitted_at=datetime.now(timezone.utc),
        url=canonical_url,
    )
