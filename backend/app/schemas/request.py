from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="Target URL to analyze (must be http or https)")
    mode: Literal["static", "full"] = Field(
        default="static",
        description="Analysis mode: 'static' for fast DOM+CSS parsing, 'full' for headless browser rendering",
    )


class AnalyzeResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    mode: Literal["static", "full"]
    submitted_at: datetime
    url: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"] = "ok"
    version: str
    timestamp: datetime
    environment: str


class InteractionRequest(BaseModel):
    url: str = Field(..., description="Target webpage URL")
    action_type: Literal["click", "select", "navigate"] = Field(
        ..., description="Action to perform: 'click' a button/link, 'select' an option, or 'navigate' to a sub-route"
    )
    selector: Optional[str] = Field(None, description="CSS selector or element identifier")
    value: Optional[str] = Field(None, description="Option value or input text to select/fill")
    target_url: Optional[str] = Field(None, description="Direct target URL for navigation")

