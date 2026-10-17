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


@router.get("/report/{job_id}/source")
async def get_scraped_source(job_id: str):
    """
    Returns the raw scraped HTML and collected CSS for inspection.
    """
    job_data = storage.get_job(job_id)
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found.",
        )

    scraped_source = job_data.get("scraped_source") or {}
    html_content = scraped_source.get("html") or job_data.get("raw_html") or ""
    css_content = scraped_source.get("css") or job_data.get("raw_css") or ""

    return {
        "job_id": job_id,
        "url": job_data.get("url", ""),
        "html": html_content,
        "css": css_content,
        "html_bytes": len(html_content.encode("utf-8")),
        "css_bytes": len(css_content.encode("utf-8")),
    }


@router.get("/report/{job_id}/source/download")
async def download_scraped_source(
    job_id: str,
    type: Literal["html", "css"] = Query(default="html", description="Source asset type to download: 'html' or 'css'"),
):
    """
    Downloads the scraped HTML document or aggregated CSS stylesheet as a raw file.
    """
    job_data = storage.get_job(job_id)
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found.",
        )

    scraped_source = job_data.get("scraped_source") or {}

    if type == "html":
        content = scraped_source.get("html") or job_data.get("raw_html") or "<!-- No HTML captured -->"
        headers = {
            "Content-Disposition": f'attachment; filename="pagelens-scraped-{job_id[:8]}.html"',
            "Content-Type": "text/html; charset=utf-8",
        }
        return Response(content=content.encode("utf-8"), media_type="text/html", headers=headers)

    elif type == "css":
        content = scraped_source.get("css") or job_data.get("raw_css") or "/* No CSS captured */"
        headers = {
            "Content-Disposition": f'attachment; filename="pagelens-scraped-{job_id[:8]}.css"',
            "Content-Type": "text/css; charset=utf-8",
        }
        return Response(content=content.encode("utf-8"), media_type="text/css", headers=headers)
