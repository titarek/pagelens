import hashlib
import logging
import sys
import time
from typing import Optional
from app.core.config import settings


def setup_logging() -> logging.Logger:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger = logging.getLogger("pagelens")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()


def hash_ip(ip_address: Optional[str]) -> str:
    """Hash client IP address for privacy while maintaining unique audit identifiers."""
    if not ip_address:
        return "anonymous"
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()[:16]


def log_analysis_audit(url: str, client_ip: Optional[str], duration_ms: float, status: str, job_id: str) -> None:
    ip_h = hash_ip(client_ip)
    logger.info(
        f"[AUDIT] job_id={job_id} url={url} ip_hash={ip_h} duration_ms={duration_ms:.2f} status={status}"
    )
