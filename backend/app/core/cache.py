import json
import logging
from typing import Any, Optional, Dict
import redis
import fakeredis
from app.core.config import settings

logger = logging.getLogger("pagelens.cache")


class JobStorage:
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if settings.use_fakeredis:
            logger.info("Initializing in-memory fakeredis client.")
            self._client = fakeredis.FakeRedis(decode_responses=True)
            return

        try:
            logger.info(f"Connecting to Redis at {settings.redis_url}")
            client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            client.ping()
            self._client = client
            logger.info("Successfully connected to Redis server.")
        except Exception as e:
            logger.warning(
                f"Could not connect to Redis server ({e}). Falling back to in-memory fakeredis."
            )
            self._client = fakeredis.FakeRedis(decode_responses=True)

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._initialize_client()
        return self._client

    def set_job(self, job_id: str, payload: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        ttl = ttl_seconds or settings.redis_cache_ttl_seconds
        try:
            serialized = json.dumps(payload, default=str)
            self.client.set(f"pagelens:job:{job_id}", serialized, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Error setting job {job_id} in cache: {e}")
            return False

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            raw = self.client.get(f"pagelens:job:{job_id}")
            if not raw:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Error retrieving job {job_id} from cache: {e}")
            return None

    def update_job_progress(self, job_id: str, status: str, progress_phase: Optional[str] = None, error: Optional[str] = None) -> None:
        job = self.get_job(job_id) or {"job_id": job_id}
        job["status"] = status
        if progress_phase:
            job["progress_phase"] = progress_phase
        if error:
            errors = job.get("errors", [])
            errors.append(error)
            job["errors"] = errors
        self.set_job(job_id, job)


storage = JobStorage()
