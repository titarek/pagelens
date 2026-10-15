from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    app_name: str = "PageLens"
    app_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Server Configuration
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_origin: Union[str, List[str]] = ["http://localhost:5173", "http://localhost:80", "http://127.0.0.1:5173"]

    @field_validator("frontend_origin", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Redis & Cache
    redis_url: str = "redis://redis:6379/0"
    use_fakeredis: bool = True
    redis_cache_ttl_seconds: int = 86400  # 24 hours

    # Rate Limiting & Safety Budgets
    rate_limit_per_minute: int = 10
    max_response_size_bytes: int = 5 * 1024 * 1024  # 5 MB per resource
    max_total_analysis_bytes: int = 20 * 1024 * 1024  # 20 MB total per analysis
    default_timeout_seconds: float = 15.0
    hard_timeout_seconds: float = 30.0
    max_redirects: int = 5
    user_agent: str = "PageLensBot/1.0 (+https://pagelens.dev/bot)"

    # Scraping & CSS limits
    max_css_files: int = 20
    max_single_css_bytes: int = 500 * 1024  # 500 KB
    max_import_depth: int = 3

    # Rendering
    playwright_runs: int = 3
    mobile_viewport_width: int = 412
    mobile_viewport_height: int = 915
    mobile_device_scale_factor: float = 3.0


settings = Settings()
