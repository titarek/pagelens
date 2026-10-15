import json
from typing import Literal
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from app.core.cache import storage
from app.schemas.report import Report
from app.services.pdf_exporter import generate_pdf_report

router = APIRouter(tags=["Report"])


@router.get("/report/{job_id}")
async def get_report(job_id: str):
    """
    Returns the completed Report object once ready,
    or a progress object with status: 'queued' | 'running' | 'failed'.
    """
    job_data = storage.get_job(job_id)
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found.",
        )

    job_status = job_data.get("status", "running")

    # If the job is still queued or running, return progress status
    if job_status in ("queued", "running", "failed"):
        # If it failed, return details
        if job_status == "failed":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "job_id": job_id,
                    "status": "failed",
                    "progress_phase": job_data.get("progress_phase", "Failed"),
                    "errors": job_data.get("errors", ["Analysis pipeline encountered an error."]),
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "job_id": job_id,
                "status": job_status,
                "progress_phase": job_data.get("progress_phase", "Processing"),
            },
        )

    # Job is completed ('ok' or 'partial')
    try:
        # Validate through Pydantic model for schema guarantee
        report = Report.model_validate(job_data)
        return report
    except Exception as e:
        # Fallback to returning the stored raw dict if minor validation edge case
        return job_data


@router.get("/report/{job_id}/export")
async def export_report(
    job_id: str,
    format: Literal["json", "pdf"] = Query(default="json", description="Export format: 'json' or 'pdf'"),
):
    """
    Downloads the completed report as formatted JSON or a printable PDF.
    """
    job_data = storage.get_job(job_id)
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found.",
        )

    if job_data.get("status") in ("queued", "running"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis job is still in progress. Please wait for completion before exporting.",
        )

    if format == "json":
        json_bytes = json.dumps(job_data, indent=2, default=str).encode("utf-8")
        headers = {
            "Content-Disposition": f'attachment; filename="pagelens-report-{job_id[:8]}.json"',
            "Content-Type": "application/json",
        }
        return Response(content=json_bytes, media_type="application/json", headers=headers)

    elif format == "pdf":
        try:
            pdf_buffer = generate_pdf_report(job_data)
            headers = {
                "Content-Disposition": f'attachment; filename="pagelens-report-{job_id[:8]}.pdf"',
                "Content-Type": "application/pdf",
            }
            return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate PDF report: {e}",
            )
